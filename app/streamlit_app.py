import streamlit as st
import psycopg2
import pandas as pd
import os
import sys
from dotenv import load_dotenv

# ------------------------------------------------
# PATH FIX
# ------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ------------------------------------------------
# ENV + DB
# ------------------------------------------------
load_dotenv(os.path.join(ROOT, ".env"))

@st.cache_resource
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        database=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
    )

conn = get_db_connection()

# ------------------------------------------------
# INGESTION IMPORTS
# ------------------------------------------------
from ingestion.load_to_db import insert_mentions
from ingestion.reviews.google_play import fetch_google_play_reviews

# ------------------------------------------------
# BRAND → APP ID MAPPING
# ------------------------------------------------
GOOGLE_PLAY_APPS = {
    "Chase": "com.chase.sig.android",
    "Bank of America": "com.infonow.bofa",
    "Capital One": "com.konylabs.capitalone",
    "Wells Fargo": "com.wf.wellsfargomobile",
}

# ------------------------------------------------
# CLUSTER HELPERS (DAY 4)
# ------------------------------------------------
def fetch_clusters(conn, brand: str):
    q = """
    SELECT
        rc.cluster_id,
        COUNT(*) AS review_count,
        AVG(ml.sentiment_score) AS avg_sentiment
    FROM review_clusters rc
    JOIN mentions_raw mr ON mr.raw_id = rc.raw_id
    LEFT JOIN mentions_ml ml ON ml.raw_id = rc.raw_id
    WHERE mr.brand = %s
    GROUP BY rc.cluster_id
    ORDER BY review_count DESC;
    """
    with conn.cursor() as cur:
        cur.execute(q, (brand.lower(),))
        return cur.fetchall()


def fetch_cluster_examples(conn, brand: str, cluster_id: int, limit: int = 5):
    q = """
    SELECT
        mr.body,
        ml.sentiment_score
    FROM review_clusters rc
    JOIN mentions_raw mr ON mr.raw_id = rc.raw_id
    JOIN mentions_ml ml ON ml.raw_id = mr.raw_id
    WHERE mr.brand = %s
      AND rc.cluster_id = %s
    ORDER BY ml.sentiment_score ASC
    LIMIT %s;
    """
    with conn.cursor() as cur:
        cur.execute((q), (brand.lower(), cluster_id, limit))
        return cur.fetchall()

# ------------------------------------------------
# CLUSTER INSIGHTS (DAY 5)
# ------------------------------------------------
def fetch_emerging_issues(conn, brand: str):
    """
    Pulls latest materialized cluster insights.
    """
    q = """
    SELECT
        cluster_id,
        primary_issue,
        summary,
        trend_label,
        user_impact,
        count_last_7d,
        count_prev_7d,
        delta_count
    FROM cluster_insights
    WHERE brand = %s
      AND generated_at = (
        SELECT MAX(generated_at)
        FROM cluster_insights
        WHERE brand = %s
      )
    ORDER BY
        (trend_label = 'growing') DESC,
        (user_impact = 'high') DESC,
        delta_count DESC;
    """
    return pd.read_sql(q, conn, params=(brand.lower(), brand.lower()))

# ------------------------------------------------
# UI HEADER
# ------------------------------------------------
st.title("🔍 Reputation & Sentiment Intelligence Platform")

brand = st.selectbox("Select brand", list(GOOGLE_PLAY_APPS.keys()))
app_id = GOOGLE_PLAY_APPS[brand]

st.caption(f"Source: Google Play reviews · App ID: `{app_id}`")

# ------------------------------------------------
# INGESTION BUTTON
# ------------------------------------------------
if st.button("Fetch latest Google Play reviews"):
    with st.spinner("Fetching reviews from Google Play..."):
        rows, _ = fetch_google_play_reviews(
            app_id=app_id,
            brand=brand,
            limit=30
        )

    if not rows:
        st.warning(
            "Live reviews unavailable right now. "
            "Showing cached reviews instead."
        )
    else:
        insert_mentions(rows)
        st.success(f"Inserted {len(rows)} new reviews.")

# ------------------------------------------------
# RECENT REVIEWS
# ------------------------------------------------
st.subheader("Recent Reviews")

df = pd.read_sql(
    """
    SELECT
        created_utc,
        author,
        rating,
        body,
        version
    FROM mentions_raw
    WHERE source = 'google_play'
      AND brand = %s
    ORDER BY created_utc DESC
    LIMIT 20
    """,
    conn,
    params=(brand.lower(),),
)

st.dataframe(df, use_container_width=True)

# ------------------------------------------------
# SENTIMENT DISTRIBUTION
# ------------------------------------------------
st.subheader("Sentiment Distribution")

sent_df = pd.read_sql(
    """
    SELECT
        m.sentiment_label,
        COUNT(*) AS count
    FROM mentions_ml m
    JOIN mentions_raw r
        ON r.raw_id = m.raw_id
    WHERE r.brand = %s
    GROUP BY m.sentiment_label
    """,
    conn,
    params=(brand.lower(),),
)

if not sent_df.empty:
    st.bar_chart(sent_df.set_index("sentiment_label"))
else:
    st.caption("No sentiment scores available yet.")

# ------------------------------------------------
# MOST NEGATIVE REVIEWS
# ------------------------------------------------
st.subheader("Most Negative Reviews")

neg_df = pd.read_sql(
    """
    SELECT
        r.created_utc,
        r.body,
        m.sentiment_score,
        m.toxicity_score
    FROM mentions_raw r
    JOIN mentions_ml m
        ON r.raw_id = m.raw_id
    WHERE r.brand = %s
    ORDER BY m.sentiment_score ASC
    LIMIT 5
    """,
    conn,
    params=(brand.lower(),),
)

if not neg_df.empty:
    st.dataframe(neg_df, use_container_width=True)
else:
    st.caption("No negative reviews detected yet.")

# ------------------------------------------------
# THEMES & ISSUES (DAY 4)
# ------------------------------------------------
st.subheader("🧩 Themes & Issues")

clusters = fetch_clusters(conn, brand)

if not clusters:
    st.caption("Not enough data to surface themes yet.")
else:
    for cluster_id, count, avg_sent in clusters:
        header = f"Cluster {cluster_id} · {count} reviews"

        if avg_sent is not None:
            if avg_sent < -0.3:
                sev = "🔴 Negative"
            elif avg_sent < 0.2:
                sev = "🟠 Mixed"
            else:
                sev = "🟢 Positive"
            header += f" · Avg Sentiment {avg_sent:.2f} ({sev})"

        with st.expander(header):
            examples = fetch_cluster_examples(conn, brand, cluster_id)
            for body, sent in examples:
                st.write(f"• {body}")
                st.caption(f"sentiment: {float(sent):.2f}")

# ------------------------------------------------
# 🚨 EMERGING & HIGH-RISK ISSUES (DAY 5)
# ------------------------------------------------
st.subheader("🚨 Emerging & High-Risk Issues")

insights_df = fetch_emerging_issues(conn, brand)

if insights_df.empty:
    st.caption("No cluster insights generated yet.")
else:
    for _, row in insights_df.iterrows():
        badge = "🟢"
        if row["user_impact"] == "high":
            badge = "🔴"
        elif row["user_impact"] == "medium":
            badge = "🟠"

        title = f"{badge} {row['primary_issue']} · Cluster {row['cluster_id']}"

        with st.expander(title):
            st.write(row["summary"])

            st.caption(
                f"Trend: **{row['trend_label']}** · "
                f"Last 7d: {row['count_last_7d']} · "
                f"Prev 7d: {row['count_prev_7d']} · "
                f"Δ: {row['delta_count']}"
            )
