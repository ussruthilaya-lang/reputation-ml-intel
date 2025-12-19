Reputation & Sentiment Intelligence Platform

An ML-first reputation intelligence system that ingests live customer feedback and public signals to track sentiment, detect emerging issues, cluster themes, and surface anomaly-driven risk — delivered through a clean, SaaS-style Streamlit interface.

The system is designed with real-world ML pipelines in mind: source-agnostic ingestion, idempotent writes, historical backfills, graceful fallbacks, and scalability beyond a single data source.

Day 0 Snapshot — Setup & Infra
✔️ What was completed

Repository created with production-grade, ML-first folder structure.

Virtual environment initialized; core dependencies installed.

Supabase Postgres database provisioned.

schema.sql applied successfully.

Secure .env configuration integrated and ignored via .gitignore.

Streamlit application skeleton built with verified DB connectivity.

Successful end-to-end local execution.

🧠 Key Decisions Made

Chose Supabase over Railway for long-term free-tier stability and predictable limits.

Designed database with raw vs ML output separation (mentions_raw vs mentions_ml) to support scalable pipelines.

Built UI early to validate system wiring and reduce downstream integration risk.

⚠️ Obstacles Faced

PowerShell mkdir incompatibility → resolved by creating folders individually.

Initial Postgres driver and environment configuration issues → resolved with Supabase-compatible setup.

Day 1 Snapshot — Data Ingestion Backbone (Reviews-First Pivot)
✔️ What was completed

Implemented source-agnostic ingestion pipeline with idempotent writes.

Added Google Play Store reviews as the primary live data source.

Extended schema to support review-specific metadata:

rating

version

source_context

Built a safe, paginated historical backfill for reviews.

Completed one-time backfill (~180 reviews per brand) to establish a meaningful historical baseline.

Verified ingestion stability, deduplication, and timeline continuity.

Streamlit UI updated to display live and cached review data cleanly.

🧠 Key Decisions Made (Important)

Pivoted away from Reddit-first ingestion due to ecosystem instability and API unreliability.

Adopted a reviews-first strategy (Google Play) as the primary sentiment signal:

Higher volume

Stronger emotional signal

Closer to real enterprise feedback (support tickets, NPS, CSAT)

Designed ingestion in two modes:

Live fetch (small, safe batches for freshness)

One-time historical backfill (paginated, controlled, idempotent)

Ensured ingestion is not tied to UI interactions, preventing accidental overuse or upstream abuse.

Explicitly avoided over-ingestion to stay within API and DB limits while preserving signal quality.

⚠️ Obstacles Faced

Reddit ecosystem instability (Pushshift, snscrape, API gating).

Initial ingestion logic assumed Reddit-shaped fields (e.g., subreddit) → refactored loader to be source-agnostic.

Python import path issues for standalone scripts → resolved via explicit project-root path handling.

📌 Data Policy (Intentional Design)

Ingestion batches are deliberately capped (e.g., 30 reviews per fetch).

Database storage is unbounded but controlled by policy, not accidents.

Historical window established via backfill; future growth handled incrementally.

Retention (3–6 months) planned as a separate cleanup policy, not mixed into ingestion logic.

Current System State (End of Day 1)

✅ Stable, live data ingestion from Google Play reviews.

✅ Historical baseline available for trend and anomaly analysis.

✅ Source-agnostic ingestion layer ready for App Store, Yelp, and News APIs.

✅ Clean, reliable Postgres-backed data store.

✅ Streamlit UI accurately reflecting system state with graceful fallbacks.

This foundation enables meaningful ML work without being blocked by upstream data volatility.

Next Milestone — Day 2

Sentiment & Toxicity ML Pipeline

Baseline sentiment scoring.

ML-based sentiment classification.

Writing outputs to mentions_ml.

Visualizing sentiment trends per brand.

Preparing data for clustering and anomaly detection.