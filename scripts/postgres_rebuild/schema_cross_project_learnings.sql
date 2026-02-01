-- Cross-Project Learnings Table
-- Transfer learning records
CREATE TABLE IF NOT EXISTS cross_project_learnings (
    learning_id SERIAL PRIMARY KEY,
    source_project_id INTEGER NOT NULL,
    target_project_id INTEGER NOT NULL,
    pattern_id INTEGER,
    similarity_score FLOAT DEFAULT 0.0,
    applied BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    applied_at TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (source_project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (target_project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (pattern_id) REFERENCES learned_patterns(pattern_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_learnings_target_applied ON cross_project_learnings(target_project_id, applied);
CREATE INDEX IF NOT EXISTS idx_learnings_source ON cross_project_learnings(source_project_id);
