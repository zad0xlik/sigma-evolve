-- Worker Statistics Table
-- Track worker performance
CREATE TABLE IF NOT EXISTS worker_stats (
    stat_id SERIAL PRIMARY KEY,
    worker_name VARCHAR NOT NULL,
    cycles_run INTEGER DEFAULT 0,
    experiments_run INTEGER DEFAULT 0,
    total_time FLOAT DEFAULT 0.0,
    errors INTEGER DEFAULT 0,
    last_run TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_worker_stats_worker ON worker_stats(worker_name);
CREATE INDEX IF NOT EXISTS idx_worker_stats_last_run ON worker_stats(last_run);
