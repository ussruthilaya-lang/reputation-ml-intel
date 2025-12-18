import streamlit as st
import psycopg2
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Reputation & Sentiment Intelligence", layout="wide")

st.title("🔍 Reputation & Sentiment Intelligence Platform")

# --- DB Connection ---
@st.cache_resource
def get_connection():
    conn = psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        database=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
    )
    return conn

conn = get_connection()

st.success("Connected to Supabase Postgres")

# --- Brand Selector (Day 0 placeholder) ---
brands = ["Chase", "Wells Fargo", "Bank of America", "Capital One", "Generic"]
selected_brand = st.selectbox("Select brand", brands)

st.write(f"Selected brand: **{selected_brand}**")

st.info("Day 0 UI placeholder. Raw mentions will appear here once ingestion is added.")
