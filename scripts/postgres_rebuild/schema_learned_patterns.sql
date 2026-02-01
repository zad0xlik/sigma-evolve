-- Learned Patterns Table
-- Cross-project pattern library
CREATE TABLE IF NOT EXISTS learned_patterns (
    pattern_id SERIAL PRIMARY KEY,
    pattern_name VARCHAR NOT NULL,
    pattern_type VARCHAR NOT NULL,  -- refactor, fix, optimize, etc.
    description TEXT,
    code_template TEXT,  -- Code template for the pattern
    language VARCHAR NOT NULL,
    framework VARCHAR,
    domain VARCHAR,
    confidence FLOAT DEFAULT 0.0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_used TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_patterns_type_confidence ON learned_patterns(pattern_type, confidence);
CREATE INDEX IF NOT EXISTS idx_patterns_language_framework ON learned_patterns(language, framework);
