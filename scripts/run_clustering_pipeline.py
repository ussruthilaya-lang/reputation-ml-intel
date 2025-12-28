import os
import sys
from typing import List, Tuple, Optional

import psycopg2
import numpy as np
from dotenv import load_dotenv
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv()

CLUSTERING_MODEL_NAME = "kmeans_v1_cosine_norm"
MIN_REVIEWS_PER_BRAND = 15
FETCH_LIMIT_PER_BRAND = 5000
MAX_K = 8  # upper cap, adaptive selection below


def connect():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        database=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
    )


def fetch_brands_with_unclustered(cur) -> List[str]:
    cur.execute(
        """
        SELECT DISTINCT mr.brand
        FROM mentions_raw mr
        JOIN review_embeddings re ON re.raw_id = mr.raw_id
        LEFT JOIN review_clusters rc ON rc.raw_id = mr.raw_id
        WHERE rc.raw_id IS NULL
        ORDER BY mr.brand;
        """
    )
    return [r[0] for r in cur.fetchall()]


def fetch_embeddings_for_brand(cur, brand: str, limit: int) -> List[Tuple[int, bytes]]:
    cur.execute(
        """
        SELECT re.raw_id, re.embedding
        FROM review_embeddings re
        JOIN mentions_raw mr ON mr.raw_id = re.raw_id
        LEFT JOIN review_clusters rc ON rc.raw_id = re.raw_id
        WHERE rc.raw_id IS NULL
          AND mr.brand = %s
        ORDER BY re.raw_id ASC
        LIMIT %s;
        """,
        (brand, limit),
    )
    return cur.fetchall()


def insert_clusters(cur, rows: List[Tuple[int, int, str]]):
    cur.executemany(
        """
        INSERT INTO review_clusters (raw_id, cluster_id, clustering_model)
        VALUES (%s, %s, %s)
        ON CONFLICT (raw_id) DO NOTHING;
        """,
        rows,
    )


def bytes_to_vec(b: bytes, dim: int = 384) -> Optional[np.ndarray]:
    if b is None:
        return None
    v = np.frombuffer(b, dtype=np.float32)
    if v.shape[0] != dim:
        return None
    return v


def choose_k(n: int) -> int:
    """
    Adaptive cluster count:
    - grows slowly with data size
    - capped to avoid fragmentation
    """
    if n < 30:
        return 3
    if n < 75:
        return 4
    if n < 150:
        return 5
    return min(MAX_K, int(np.sqrt(n)))


def main():
    print(f"[INFO] Clustering pipeline starting | model={CLUSTERING_MODEL_NAME}")

    conn = connect()
    cur = conn.cursor()

    total_brands = 0
    total_clustered_rows = 0
    total_skipped_brands = 0
    total_failed_brands = 0

    try:
        brands = fetch_brands_with_unclustered(cur)
        if not brands:
            print("[INFO] No brands found with unclustered embeddings. Done.")
            return

        for brand in brands:
            total_brands += 1
            try:
                rows = fetch_embeddings_for_brand(cur, brand, FETCH_LIMIT_PER_BRAND)

                if len(rows) < MIN_REVIEWS_PER_BRAND:
                    total_skipped_brands += 1
                    print(f"[INFO] Skipping brand='{brand}' (rows={len(rows)} < {MIN_REVIEWS_PER_BRAND})")
                    continue

                raw_ids: List[int] = []
                vecs: List[np.ndarray] = []
                bad = 0

                for rid, emb_bytes in rows:
                    v = bytes_to_vec(emb_bytes)
                    if v is None:
                        bad += 1
                        continue
                    raw_ids.append(rid)
                    vecs.append(v)

                if len(vecs) < MIN_REVIEWS_PER_BRAND:
                    total_skipped_brands += 1
                    print(f"[INFO] Skipping brand='{brand}' after decode (valid={len(vecs)}, bad={bad})")
                    continue

                X = np.vstack(vecs).astype(np.float32)

                # Normalize → cosine similarity via euclidean
                Xn = normalize(X, norm="l2")

                k = choose_k(len(Xn))
                km = KMeans(
                    n_clusters=k,
                    random_state=42,
                    n_init="auto",
                )

                labels = km.fit_predict(Xn)

                out_rows = [(rid, int(lbl), CLUSTERING_MODEL_NAME) for rid, lbl in zip(raw_ids, labels)]

                insert_clusters(cur, out_rows)
                conn.commit()

                total_clustered_rows += len(out_rows)

                print(
                    f"[INFO] brand='{brand}' clustered={len(out_rows)} "
                    f"k={k} bad_vecs={bad}"
                )

            except Exception as e:
                conn.rollback()
                total_failed_brands += 1
                print(f"[WARN] Brand clustering failed brand='{brand}'. Skipping. Error={e}")

    finally:
        cur.close()
        conn.close()

    print(
        "[INFO] Clustering pipeline completed | "
        f"brands_seen={total_brands} skipped={total_skipped_brands} "
        f"failed={total_failed_brands} clustered_rows={total_clustered_rows}"
    )


if __name__ == "__main__":
    main()
