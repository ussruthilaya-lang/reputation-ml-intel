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
load_dotenv()

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
# IMPORT INGESTION
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
# RECENT REVIEWS (RAW)
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
