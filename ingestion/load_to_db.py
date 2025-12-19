import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def insert_mentions(rows):
    if not rows:
        return

    conn = psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        database=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
    )

    cur = conn.cursor()

    query = """
        INSERT INTO mentions_raw (
            source,
            source_id,
            brand,
            created_utc,
            author,
            title,
            body,
            url,
            source_context,
            rating,
            version
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source, source_id) DO NOTHING;
    """

    for r in rows:
        cur.execute(
            query,
            (
                r.get("source"),
                r.get("source_id"),
                r.get("brand"),
                r.get("created_utc"),
                r.get("author"),
                r.get("title"),
                r.get("body"),
                r.get("url"),
                r.get("source_context"),
                r.get("rating"),
                r.get("version"),
            ),
        )

    conn.commit()
    cur.close()
    conn.close()
