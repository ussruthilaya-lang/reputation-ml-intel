"""
Day 5 – Cluster Insights (Offline, Batch Intelligence)

Purpose:
- Generate cluster-level intelligence using an offline LLM (Ollama)
- Compute week-over-week trends
- Persist durable, append-only insights
- No UI triggers, no real-time inference

Run AFTER:
- ingestion
- sentiment
- embeddings
- clustering
"""

import os
import sys
import json
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Any, Tuple

import psycopg2
from dotenv import load_dotenv

def log(msg: str):
    print(f"[cluster_insights] {msg}", flush=True)

# ------------------------------------------------------------
# ENV / PATH
# ------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"))

from llm.ollama_client import call_ollama
from prompts.cluster_summary_prompt import build_cluster_summary_prompt

ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() == "true"

# ------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------
TREND_THRESHOLD = 3
MAX_CLUSTERS_PER_BRAND = 12
EXAMPLES_PER_CLUSTER = 5

TODAY = date.today()
WINDOW_END = TODAY
WINDOW_START = TODAY - timedelta(days=7)
PREV_WINDOW_START = TODAY - timedelta(days=14)
PREV_WINDOW_END = TODAY - timedelta(days=7)

# ------------------------------------------------------------
# DB CONNECTION
# ------------------------------------------------------------
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        database=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
    )

# ------------------------------------------------------------
# DATA FETCH
# ------------------------------------------------------------
def fetch_current_clusters(conn) -> List[Tuple[str, int, int, float]]:
    q = """
    SELECT
        mr.brand,
        rc.cluster_id,
        COUNT(*) AS cluster_size,
        AVG(ml.sentiment_score) AS avg_sentiment
    FROM review_clusters rc
    JOIN mentions_raw mr ON mr.raw_id = rc.raw_id
    JOIN mentions_ml ml ON ml.raw_id = rc.raw_id
    GROUP BY mr.brand, rc.cluster_id;
    """
    with conn.cursor() as cur:
        cur.execute(q)
        return cur.fetchall()


def fetch_cluster_counts(conn, start_date, end_date) -> Dict[Tuple[str, int], int]:
    q = """
    SELECT
        mr.brand,
        rc.cluster_id,
        COUNT(*) AS review_count
    FROM review_clusters rc
    JOIN mentions_raw mr ON mr.raw_id = rc.raw_id
    WHERE mr.created_utc >= %s
      AND mr.created_utc < %s
    GROUP BY mr.brand, rc.cluster_id;
    """
    with conn.cursor() as cur:
        cur.execute(q, (start_date, end_date))
        return {(b, cid): c for b, cid, c in cur.fetchall()}


def fetch_cluster_examples(conn, brand: str, cluster_id: int) -> List[str]:
    q = """
    SELECT mr.body
    FROM review_clusters rc
    JOIN mentions_raw mr ON mr.raw_id = rc.raw_id
    JOIN mentions_ml ml ON ml.raw_id = mr.raw_id
    WHERE mr.brand = %s
      AND rc.cluster_id = %s
      AND mr.body IS NOT NULL
      AND LENGTH(TRIM(mr.body)) > 0
    ORDER BY ml.sentiment_score ASC
    LIMIT %s;
    """
    with conn.cursor() as cur:
        cur.execute(q, (brand, cluster_id, EXAMPLES_PER_CLUSTER))
        return [r[0] for r in cur.fetchall()]

# ------------------------------------------------------------
# DERIVED LOGIC
# ------------------------------------------------------------
def trend_label(delta: int) -> str:
    if delta >= TREND_THRESHOLD:
        return "growing"
    if delta <= -TREND_THRESHOLD:
        return "declining"
    return "stable"


def size_descriptor(size: int) -> str:
    if size < 10:
        return "small"
    if size < 30:
        return "medium"
    return "large"


def sentiment_descriptor(avg: float) -> str:
    if avg < -0.3:
        return "strongly negative"
    if avg < 0.2:
        return "mixed"
    return "positive"


def pct(delta: int, prev: int):
    if prev <= 0:
        return None
    return round((delta / prev) * 100, 2)

# ------------------------------------------------------------
# INSERT
# ------------------------------------------------------------
def insert_cluster_insights(conn, rows: List[Dict[str, Any]]):
    q = """
    INSERT INTO cluster_insights (
        brand,
        cluster_id,
        summary,
        primary_issue,
        user_impact,
        window_start,
        window_end,
        count_last_7d,
        count_prev_7d,
        delta_count,
        delta_pct,
        trend_label
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
    """
    with conn.cursor() as cur:
        for r in rows:
            cur.execute(q, (
                r["brand"],
                r["cluster_id"],
                r["summary"],
                r["primary_issue"],
                r["user_impact"],
                WINDOW_START,
                WINDOW_END,
                r["count_last_7d"],
                r["count_prev_7d"],
                r["delta_count"],
                r["delta_pct"],
                r["trend_label"],
            ))

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    log("Starting cluster insights batch job")
    conn = get_db_connection()

    try:
        clusters = fetch_current_clusters(conn)
        log(f"Fetched {len(clusters)} brand-cluster rows")
        last_7d = fetch_cluster_counts(conn, WINDOW_START, WINDOW_END)
        prev_7d = fetch_cluster_counts(conn, PREV_WINDOW_START, PREV_WINDOW_END)

        by_brand = defaultdict(list)

        for brand, cid, size, avg_sent in clusters:
            last = last_7d.get((brand, cid), 0)
            prev = prev_7d.get((brand, cid), 0)
            delta = last - prev

            by_brand[brand].append({
                "cluster_id": cid,
                "cluster_size": size,
                "avg_sentiment": avg_sent,
                "count_last_7d": last,
                "count_prev_7d": prev,
                "delta_count": delta,
                "delta_pct": pct(delta, prev),
                "trend_label": trend_label(delta),
            })

        if not ENABLE_LLM:
            print("LLM disabled. Exiting without generation.")
            return

        total_inserted = 0

        for brand, clist in by_brand.items():
            log(f"Processing brand={brand} with {len(clist)} clusters")
            clist = sorted(clist, key=lambda x: x["cluster_size"], reverse=True)[:MAX_CLUSTERS_PER_BRAND]

            clusters_payload = []
            for c in clist:
                examples = fetch_cluster_examples(conn, brand, c["cluster_id"])
                if not examples:
                    continue

                clusters_payload.append({
                    "cluster_id": c["cluster_id"],
                    "size": size_descriptor(c["cluster_size"]),
                    "sentiment": sentiment_descriptor(c["avg_sentiment"]),
                    "trend": c["trend_label"],
                    "examples": examples,
                })

            if not clusters_payload:
                continue

            prompt = build_cluster_summary_prompt(brand, clusters_payload)
            log(f"Calling Ollama for brand={brand} (this may take ~30–60s)")
            raw = call_ollama(prompt)

            try:
                llm_json = json.loads(raw)
                log(f"Ollama completed for brand={brand}")
            except json.JSONDecodeError:
                raise RuntimeError(f"Ollama returned invalid JSON:\n{raw}")

            summaries = {s["cluster_id"]: s for s in llm_json.get("cluster_summaries", [])}
            insert_rows = []

            for c in clist:
                s = summaries.get(c["cluster_id"])
                if not s:
                    continue

                insert_rows.append({
                    "brand": brand,
                    "cluster_id": c["cluster_id"],
                    "summary": s["summary"][:2000],
                    "primary_issue": s["primary_issue"][:200],
                    "user_impact": s["user_impact"],
                    "count_last_7d": c["count_last_7d"],
                    "count_prev_7d": c["count_prev_7d"],
                    "delta_count": c["delta_count"],
                    "delta_pct": c["delta_pct"],
                    "trend_label": c["trend_label"],
                })

            insert_cluster_insights(conn, insert_rows)
            conn.commit()
            log(f"Inserted {len(insert_rows)} insights for brand={brand}")


            total_inserted += len(insert_rows)
            print(f"[OK] {brand}: inserted {len(insert_rows)} insights")

        print(f"DONE. Total rows inserted: {total_inserted}")
        log("Cluster insights batch job finished")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
