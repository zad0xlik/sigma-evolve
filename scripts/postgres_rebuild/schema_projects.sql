-- Projects Table
-- Track multiple projects for cross-project learning
CREATE TABLE IF NOT EXISTS projects (
    project_id SERIAL PRIMARY KEY,
    repo_url VARCHAR NOT NULL,
    branch VARCHAR DEFAULT 'main',
    workspace_path VARCHAR NOT NULL,
    language VARCHAR,
    framework VARCHAR,
    domain VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_analyzed TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_projects_language ON projects(language);
CREATE INDEX IF NOT EXISTS idx_projects_framework ON projects(framework);
CREATE INDEX IF NOT EXISTS idx_projects_domain ON projects(domain);
