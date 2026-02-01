-- Proposals Table
-- Agent committee decisions
CREATE TABLE IF NOT EXISTS proposals (
    proposal_id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    title VARCHAR NOT NULL,
    description TEXT,
    agents_json TEXT,  -- Agent committee responses
    changes_json TEXT,  -- Proposed code changes
    confidence FLOAT DEFAULT 0.0,
    critic_score FLOAT DEFAULT 0.0,
    status VARCHAR DEFAULT 'pending',
    pr_url VARCHAR,
    commit_sha VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    executed_at TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_proposals_project_status ON proposals(project_id, status);
CREATE INDEX IF NOT EXISTS idx_proposals_confidence ON proposals(confidence);
