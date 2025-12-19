import psycopg2
import os
from dotenv import load_dotenv

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


from analytics.sentiment import (
    transformer_sentiment,
    combine_sentiment,
    sentiment_label
)
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
    SELECT raw_id, body, rating
    FROM mentions_raw
    WHERE raw_id NOT IN (
        SELECT raw_id FROM mentions_ml
    );
""")

rows = cur.fetchall()
print(f"[INFO] Processing {len(rows)} reviews")

insert_q = """
INSERT INTO mentions_ml (
    raw_id,
    sentiment_label,
    sentiment_score,
    toxicity_score,
    escalation_score
)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (raw_id) DO NOTHING;
"""

for raw_id, body, rating in rows:
    text_score = transformer_sentiment(body)
    final_score = combine_sentiment(text_score, rating)
    tox = toxicity_score(body)
    esc = escalation_flag(final_score, tox, body)

    cur.execute(
        insert_q,
        (
            raw_id,
            sentiment_label(final_score),
            round(final_score, 3),
            round(tox, 3),
            float(esc),
        ),
    )

conn.commit()
cur.close()
conn.close()

print("[INFO] Sentiment pipeline completed")
