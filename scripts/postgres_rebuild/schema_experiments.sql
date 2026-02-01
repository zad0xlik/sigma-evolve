-- Experiments Table
-- Track dreaming experiments (FIXED with proper timestamp fields)
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id SERIAL PRIMARY KEY,
    project_id INTEGER,  -- NULL for cross-project experiments
    worker_name VARCHAR NOT NULL,  -- analysis, dream, recall, learning, think
    experiment_name VARCHAR NOT NULL,
    hypothesis TEXT,
    approach TEXT,
    metrics TEXT,  -- JSON array of metric names
    risk_level VARCHAR,  -- low, medium, high
    rollback_plan TEXT,
    status VARCHAR DEFAULT 'proposed',
    baseline_metrics TEXT,
    result_metrics TEXT,
    outcome_json TEXT,
    success BOOLEAN,
    improvement FLOAT,
    promoted_to_production BOOLEAN DEFAULT false,
    -- Timestamp fields (ALL FIXED - using TIMESTAMP WITH TIME ZONE)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    promoted_at TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_experiments_worker_status ON experiments(worker_name, status);
CREATE INDEX IF NOT EXISTS idx_experiments_success ON experiments(success);
CREATE INDEX IF NOT EXISTS idx_experiments_promoted ON experiments(promoted_to_production);
