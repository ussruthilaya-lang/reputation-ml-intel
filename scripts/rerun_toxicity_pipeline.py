import os
import sys
import psycopg2
from dotenv import load_dotenv

# ------------------------
# PATH FIX
# ------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from analytics.toxicity import toxicity_score, escalation_flag

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("PGHOST"),
    port=os.getenv("PGPORT"),
    database=os.getenv("PGDATABASE"),
    user=os.getenv("PGUSER"),
    password=os.getenv("PGPASSWORD"),
)

cur = conn.cursor()

cur.execute("""
    SELECT
        r.raw_id,
        r.body,
        m.sentiment_score
    FROM mentions_raw r
    JOIN mentions_ml m
        ON r.raw_id = m.raw_id
""")

rows = cur.fetchall()
print(f"[INFO] Recomputing toxicity for {len(rows)} reviews")

for raw_id, body, sentiment_score in rows:
    tox = toxicity_score(body)
    esc = escalation_flag(sentiment_score, tox, body)

    cur.execute(
        """
        UPDATE mentions_ml
        SET toxicity_score = %s,
            escalation_score = %s
        WHERE raw_id = %s
        """,
        (round(tox, 3), float(esc), raw_id),
    )

conn.commit()
cur.close()
conn.close()

print("[INFO] Toxicity reprocessing completed")
