Reputation & Sentiment Intelligence Platform

An ML-first reputation intelligence system that ingests live customer feedback and public signals to track sentiment, detect emerging issues, cluster themes, and surface anomaly-driven risk — delivered through a clean, SaaS-style Streamlit interface.

The system is designed with real-world ML pipelines in mind: source-agnostic ingestion, idempotent writes, historical backfills, graceful fallbacks, and scalability beyond a single data source.
#---------------------------------------------------------------------------------------------#
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
#---------------------------------------------------------------------------------------------#
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
#---------------------------------------------------------------------------------------------#
Day 2 Snapshot — Sentiment & Toxicity ML Pipeline
✔️ What was completed

Implemented a modular sentiment analysis pipeline with clear separation between baseline and ML-based scoring.

Integrated a pre-trained RoBERTa transformer model for final sentiment inference, optimized for short-form review text.

Added a VADER-based baseline sentiment scorer for transparency and interpretability.

Designed and implemented rule-based toxicity and escalation scoring to flag high-risk customer feedback.

Built an idempotent batch ML processor to score all unprocessed reviews and write results to `mentions_ml`.

Successfully processed 700+ historical reviews in a single pipeline run.

Extended the Streamlit UI to visualize:
- Sentiment distribution per brand
- Most negative and potentially toxic reviews

Ensured UI stability with graceful fallbacks when ML outputs are unavailable.

🧠 Key Decisions Made (Important)

Explicitly separated ingestion, ML inference, and UI layers to reflect production-grade architecture.

Chose transformer-based sentiment over LLM APIs to maintain reproducibility, cost control, and ML credibility.

Kept toxicity detection rule-based to preserve explainability and avoid noisy overfitting on limited data.

Modeled sentiment and toxicity as independent signals, acknowledging that negative feedback is not always toxic.

Avoided triggering ML inference from the UI, treating sentiment analysis as a batch pipeline rather than an interactive side effect.

⚠️ Obstacles Faced

Python import path issues for standalone ML scripts on Windows → resolved via explicit project-root resolution.

Dependency isolation challenges (transformers, torch) → resolved through a dedicated virtual environment.

Initial toxicity scores skewed toward zero due to polite review language → validated as a realistic signal rather than a modeling error.

Current System State (End of Day 2)

✅ All ingested reviews are enriched with sentiment and toxicity scores.

✅ ML outputs are persisted in `mentions_ml` with full idempotency guarantees.

✅ Streamlit UI surfaces both raw feedback and ML-derived signals without tight coupling.

✅ System is now ML-ready for clustering, embeddings, and anomaly detection.

Next Milestone — Day 3

Semantic embeddings, review clustering, and theme extraction to identify emerging issues across brands.
