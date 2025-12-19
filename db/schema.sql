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
    escalation_score       NUMERIC(5,3),
    cluster_id             INT,
    embedding_vector       BYTEA,
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
