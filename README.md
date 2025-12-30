# Reputation & Sentiment Intelligence Platform

An **ML-first reputation intelligence system** that ingests live customer reviews, enriches them with sentiment and toxicity signals, clusters feedback into semantic themes, and surfaces insights through a clean Streamlit UI.

Built to reflect **real-world ML system design** — not a demo dashboard.

---

## What This System Does

* Ingests live Google Play Store reviews (with safe historical backfill)
* Stores raw data as a single source of truth
* Runs batch ML pipelines for:

  * sentiment analysis
  * toxicity & escalation detection
  * semantic embeddings
  * review clustering
* Surfaces insights in a lightweight Streamlit UI
* Keeps ingestion, ML, and UI **strictly decoupled**

No mock data. No UI-triggered ML. No shortcuts.

---

## Why This Architecture

Most sentiment dashboards collapse ingestion, ML, and UI into one layer.
This project **explicitly avoids that**.

Key principles:

* **Raw vs derived data separation**
* **Idempotent, re-runnable pipelines**
* **Batch ML, not UI side-effects**
* **Explainable ML choices over LLM black boxes**

This makes the system:

* debuggable
* extensible
* interview-defensible

---

## Tech Stack

* **Language:** Python 3
* **Database:** Supabase (Postgres)
* **ML:**

  * Sentiment: `cardiffnlp/twitter-roberta-base-sentiment`
  * Baseline sentiment: VADER
  * Toxicity: rule-based escalation logic
  * Embeddings: Sentence-Transformers (`MiniLM`)
  * Clustering: KMeans (Windows-safe baseline)
* **UI:** Streamlit
* **Infra:** Local venv + Supabase free tier
* **Data Source:** Google Play Store reviews

---

## Project Structure

```
reputation-ml-intel/
│
├── analytics/              # ML logic (sentiment, toxicity)
├── ingestion/              # Data ingestion
│   └── reviews/
│       └── google_play.py
│
├── scripts/                # Batch ML pipelines
│   ├── run_sentiment_pipeline.py
│   ├── run_embedding_pipeline.py
│   └── run_clustering_pipeline.py
│
├── app/
│   └── streamlit_app.py    # UI (read-only, no ML triggers)
│
├── db/
│   └── schema.sql
│
├── .env                    # DB credentials (ignored)
└── README.md
```

---

## Database Design (High Level)

* **`mentions_raw`**
  Raw reviews only. Source of truth.

* **`mentions_ml`**
  Scalar ML outputs (sentiment, toxicity, escalation).

* **`review_embeddings`**
  Dense semantic vectors (decoupled for re-embedding).

* **`review_clusters`**
  Cluster assignments per review.

This separation is intentional and future-proof.

---

## ML Pipelines (How It Works)

### Sentiment & Toxicity

* Transformer-based sentiment scoring
* Rating + text fusion
* Rule-based toxicity and escalation flags
* Written only via batch scripts

### Embeddings

* Light text normalization
* Short/empty reviews skipped
* Stored independently for reuse

### Clustering

* Brand-scoped clustering
* KMeans used as MVP baseline (Windows-safe)
* Architecture supports HDBSCAN upgrade later (Docker/WSL)

## How Insights Are Surfaced

Clustering output is transformed into product-facing signals through lightweight aggregation and evidence-first presentation.

For each brand, reviews are grouped into semantic clusters and surfaced as:

* cluster size (number of reviews)
* average sentiment (severity cue)
* escalation presence
* representative user quotes

Clusters are ordered by **review volume (impact)**, while sentiment severity and quotes provide context *within* each cluster.

No summaries or trend logic are applied at this stage — the UI intentionally surfaces raw evidence to preserve explainability.

### Cluster Insights (Offline LLM)

Cluster-level summaries are generated offline using an instruction-tuned open-source LLM and persisted as derived intelligence.  
The application does not require LLM access at runtime.

---

## How to Run the Project

### 1. Ingest Reviews

```bash
python ingestion/reviews/google_play.py
```

### 2. Run Sentiment + Toxicity

```bash
python scripts/run_sentiment_pipeline.py
```

### 3. Generate Embeddings

```bash
python scripts/run_embedding_pipeline.py
```

### 4. Cluster Reviews

```bash
python scripts/run_clustering_pipeline.py
```

All scripts are **idempotent** — safe to re-run at any time.

---

## Current Status (MVP Complete)

* ✅ Live review ingestion
* ✅ Sentiment & toxicity enrichment
* ✅ Semantic embeddings
* ✅ Review clustering into semantic themes
* ✅ Cluster-level aggregation (size, sentiment, escalation)
* ✅ Interpretable “Themes & Issues” view with supporting user quotes
* ✅ Stable Streamlit UI with graceful empty states

This is a **working ML system** that surfaces actionable product signals — not a prototype dashboard.
---

## Planned Extensions

* Cluster-level summaries (LLM-assisted)
* Theme evolution over time
* Early-warning signals for emerging issues
* Dockerized pipelines (Linux / HDBSCAN upgrade)
* Additional data sources (App Store, Yelp, News)

---

## Final Note

This project is intentionally **ML-first**, not UI-first.
The goal is correctness, explainability, and extensibility — polish comes later.
