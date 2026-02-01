-- Code Snapshots Table
-- Store analysis results over time with Graphiti and Qdrant integration
CREATE TABLE IF NOT EXISTS code_snapshots (
    snapshot_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    complexity FLOAT DEFAULT 0.0,
    test_coverage FLOAT DEFAULT 0.0,
    issues_found INTEGER DEFAULT 0,
    metrics_json TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    -- New fields for Graphiti integration
    graph_entity_count INTEGER DEFAULT 0,
    graphiti_episode_id VARCHAR,
    -- New fields for Qdrant integration
    indexed_at TIMESTAMP WITH TIME ZONE,
    qdrant_point_ids TEXT,  -- JSON array
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_snapshots_project_created ON code_snapshots(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_indexed ON code_snapshots(indexed_at);
