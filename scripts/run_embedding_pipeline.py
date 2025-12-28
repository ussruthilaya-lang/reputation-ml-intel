import os
import sys
import math
from typing import List, Tuple, Optional

import psycopg2
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from analytics.sentiment import normalize_text  # reuse same normalization

load_dotenv(os.path.join(ROOT, ".env"))

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MIN_TOKENS = 1

# Guardrails (not “fixed batch size for scale”, just safety caps)
MAX_FETCH_ROWS = 2000
MAX_EMBED_BATCH = 128
COMMIT_EVERY = 256


def token_count(text: str) -> int:
    return len(text.split())


def connect():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        database=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
    )


def fetch_unembedded(cur, limit: int) -> List[Tuple[int, Optional[str]]]:
    cur.execute(
        """
        SELECT mr.raw_id, mr.body
        FROM mentions_raw mr
        LEFT JOIN review_embeddings re ON re.raw_id = mr.raw_id
        WHERE re.raw_id IS NULL
        ORDER BY mr.raw_id ASC
        LIMIT %s;
        """,
        (limit,),
    )
    return cur.fetchall()


def insert_embeddings(cur, rows: List[Tuple[int, bytes, str]]):
    cur.executemany(
        """
        INSERT INTO review_embeddings (raw_id, embedding, embedding_model)
        VALUES (%s, %s, %s)
        ON CONFLICT (raw_id) DO NOTHING;
        """,
        rows,
    )


def main():
    print(f"[INFO] Embedding pipeline starting | model={EMBEDDING_MODEL_NAME}")
    print("[DEBUG] PGHOST =", os.getenv("PGHOST"))
    print("[DEBUG] PGDATABASE =", os.getenv("PGDATABASE"))
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    conn = connect()
    cur = conn.cursor()

    total_seen = 0
    total_inserted = 0
    total_skipped = 0
    total_failed = 0

    pending_inserts: List[Tuple[int, bytes, str]] = []

    try:
        while True:
            db_rows = fetch_unembedded(cur, MAX_FETCH_ROWS)
            print("[DEBUG] fetched rows:", len(db_rows))

            non_null = sum(1 for _, body in db_rows if body)
            print("[DEBUG] non-null bodies:", non_null)

            sample = next((body for _, body in db_rows if body), None)
            print("[DEBUG] sample raw body:", repr(sample))

            if not db_rows:
                break

            total_seen += len(db_rows)

            filtered: List[Tuple[int, str]] = []
            for raw_id, body in db_rows:
                text = normalize_text(body or "")
                if body and not text:
                    print("[DEBUG] body wiped by normalize:", repr(body))
                    total_skipped += 1
                    continue
                if token_count(text) < MIN_TOKENS:
                    total_skipped += 1
                    continue
                filtered.append((raw_id, text))

            if not filtered:
                print("[INFO] No valid texts in this fetch window; continuing...")
                continue

            n = len(filtered)
            num_batches = math.ceil(n / MAX_EMBED_BATCH)

            for b in range(num_batches):
                chunk = filtered[b * MAX_EMBED_BATCH : (b + 1) * MAX_EMBED_BATCH]
                raw_ids = [x[0] for x in chunk]
                texts = [x[1] for x in chunk]

                try:
                    vecs = model.encode(
                        texts,
                        batch_size=min(32, len(texts)),
                        show_progress_bar=False,
                        convert_to_numpy=True,
                        normalize_embeddings=False,
                    )
                    vecs = np.asarray(vecs, dtype=np.float32)

                    for rid, v in zip(raw_ids, vecs):
                        pending_inserts.append((rid, v.tobytes(), EMBEDDING_MODEL_NAME))

                except Exception as e:
                    total_failed += len(chunk)
                    print(f"[WARN] Batch embed failed (size={len(chunk)}). Skipping batch. Error={e}")
                    continue

                if len(pending_inserts) >= COMMIT_EVERY:
                    try:
                        insert_embeddings(cur, pending_inserts)
                        conn.commit()
                        total_inserted += len(pending_inserts)
                        print(f"[INFO] Committed {len(pending_inserts)} embeddings | total_inserted={total_inserted}")
                        pending_inserts = []
                    except Exception as e:
                        conn.rollback()
                        total_failed += len(pending_inserts)
                        print(f"[WARN] DB insert failed for a commit block. Skipping block. Error={e}")
                        pending_inserts = []

        if pending_inserts:
            try:
                insert_embeddings(cur, pending_inserts)
                conn.commit()
                total_inserted += len(pending_inserts)
                print(f"[INFO] Final commit {len(pending_inserts)} embeddings | total_inserted={total_inserted}")
            except Exception as e:
                conn.rollback()
                total_failed += len(pending_inserts)
                print(f"[WARN] Final DB insert failed. Error={e}")

    finally:
        cur.close()
        conn.close()

    print(
        "[INFO] Embedding pipeline completed | "
        f"seen={total_seen} inserted={total_inserted} skipped={total_skipped} failed={total_failed}"
    )


if __name__ == "__main__":
    main()
