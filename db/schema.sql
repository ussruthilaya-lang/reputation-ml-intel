-- mentions_raw
CREATE TABLE IF NOT EXISTS mentions_raw (
    raw_id          SERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    source_id       TEXT NOT NULL,
    brand           TEXT NOT NULL,
    created_utc     TIMESTAMP NOT NULL,
    author          TEXT,
    title           TEXT,
    body            TEXT,
    url             TEXT,
    subreddit       TEXT,
    source_context  TEXT,
    rating          INT,
    version         TEXT,
    collected_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE (source, source_id)
);

CREATE INDEX IF NOT EXISTS idx_mentions_brand_time
    ON mentions_raw(brand, created_utc);

-- mentions_ml
CREATE TABLE IF NOT EXISTS mentions_ml (
    raw_id                 INT PRIMARY KEY REFERENCES mentions_raw(raw_id),
    sentiment_label        TEXT,
    sentiment_score        NUMERIC(5,3),
    toxicity_score         NUMERIC(5,3),
    escalation_score       NUMERIC(5,3)
    processed_at           TIMESTAMP DEFAULT NOW()
);

-- cluster_summaries
CREATE TABLE IF NOT EXISTS cluster_summaries (
    brand            TEXT,
    cluster_id       INT,
    top_terms        TEXT,
    example_post_ids TEXT,
    llm_summary      TEXT,
    updated_at       TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (brand, cluster_id)
);

-- sentiment_timeseries
CREATE TABLE IF NOT EXISTS sentiment_timeseries (
    brand               TEXT,
    date                DATE,
    mention_count       INT,
    avg_sentiment_score NUMERIC(5,3),
    avg_toxicity_score  NUMERIC(5,3),
    anomaly_flag        BOOLEAN DEFAULT FALSE,
    anomaly_reason      TEXT,
    PRIMARY KEY (brand, date)
);

-- review_embeddings and review_clusters
CREATE TABLE IF NOT EXISTS review_embeddings (
    raw_id INT PRIMARY KEY REFERENCES mentions_raw(raw_id),
    embedding BYTEA,
    embedding_model TEXT,
    embedded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS review_clusters (
    raw_id INT PRIMARY KEY REFERENCES mentions_raw(raw_id),
    cluster_id INT,
    clustering_run_id TEXT,
    clustered_at TIMESTAMP DEFAULT NOW()
);

--
CREATE TABLE IF NOT EXISTS cluster_insights (
    insight_id           SERIAL PRIMARY KEY,

    brand                TEXT NOT NULL,
    cluster_id           INT NOT NULL,

    -- LLM-generated interpretation
    summary              TEXT NOT NULL,
    primary_issue        TEXT NOT NULL,
    user_impact          TEXT CHECK (user_impact IN ('low', 'medium', 'high')),

    -- Time window for trend comparison
    window_start         DATE NOT NULL,
    window_end           DATE NOT NULL,

    -- Counts
    count_last_7d        INT NOT NULL,
    count_prev_7d        INT NOT NULL,

    -- Derived deltas
    delta_count          INT NOT NULL,
    delta_pct            NUMERIC(6,2),

    -- Trend label (human-friendly)
    trend_label          TEXT CHECK (trend_label IN ('growing', 'stable', 'declining')),

    generated_at         TIMESTAMP DEFAULT NOW()
);

-- Adding new columns to mentions_raw
ALTER TABLE mentions_raw
ADD COLUMN IF NOT EXISTS rating INT;

ALTER TABLE mentions_raw
ADD COLUMN IF NOT EXISTS version TEXT;

ALTER TABLE mentions_raw
ADD COLUMN IF NOT EXISTS source_context TEXT;


-- Index on processed_at in mentions_ml
CREATE INDEX IF NOT EXISTS idx_mentions_ml_processed
ON mentions_ml(processed_at);

-- Index on created_utc in mentions_raw
CREATE INDEX IF NOT EXISTS idx_mentions_raw_created
ON mentions_raw(created_utc);

CREATE INDEX IF NOT EXISTS idx_review_clusters_cluster
ON review_clusters(cluster_id);

CREATE INDEX IF NOT EXISTS idx_review_clusters_model
ON review_clusters(clustering_model);

-- Indexes for cluster_insights
CREATE INDEX idx_cluster_insights_latest
ON cluster_insights (brand, cluster_id, generated_at DESC);

CREATE INDEX idx_cluster_insights_time
ON cluster_insights (generated_at);