# PostgreSQL Database Rebuild Scripts

This folder contains scripts and SQL schemas to rebuild the PostgreSQL database for the SIGMA agent system.

## Overview

The rebuild system provides a way to:
- Create the PostgreSQL database from scratch
- Create all 7 agent tables with proper PostgreSQL types
- Update alembic_version table to mark migrations as applied
- Optionally drop and recreate the database (with POSTGRES_OVERWRITE_DB flag)

## Files

### SQL Schema Files
- `schema_projects.sql` - Projects table for cross-project learning
- `schema_code_snapshots.sql` - Code snapshots table with Graphiti/Qdrant integration
- `schema_proposals.sql` - Agent committee proposals table
- `schema_experiments.sql` - Dreaming experiments table (fixed timestamp fields)
- `schema_learned_patterns.sql` - Cross-project pattern library
- `schema_cross_project_learnings.sql` - Transfer learning records
- `schema_worker_stats.sql` - Worker performance statistics

### Python Scripts
- `rebuild_database.py` - Main rebuild script

## Usage

### 1. Basic Usage (No Overwrite)

```bash
cd scripts/postgres_rebuild
python rebuild_database.py
```

This will:
- Check if the database exists
- Create the database if it doesn't exist
- Create all agent tables from SQL schemas
- Update alembic_version table

### 2. Force Rebuild (Drop and Recreate)

First, set the environment variable:

```bash
export POSTGRES_OVERWRITE_DB=true
```

Then run the rebuild:

```bash
python rebuild_database.py
```

This will:
- Drop the existing database (if it exists)
- Create a fresh database
- Create all tables from scratch

### 3. Using Custom Database Configuration

You can override the database configuration:

```bash
export DATABASE_URL=postgresql://myuser:mypassword@localhost:5432/mydb
export POSTGRES_OVERWRITE_DB=false
python rebuild_database.py
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string (postgresql://user:pass@host:port/db) | Yes | - |
| `POSTGRES_OVERWRITE_DB` | If true, drop and recreate the database | No | `false` |

## Database Schema

### Projects Table
- Tracks multiple projects for cross-project learning
- Stores repository URL, branch, language, framework, domain
- Links to all other tables via `project_id`

### Code Snapshots Table
- Stores analysis results over time
- Includes Graphiti integration (graph_entity_count, graphiti_episode_id)
- Includes Qdrant integration (indexed_at, qdrant_point_ids)

### Proposals Table
- Agent committee decisions
- Stores proposed changes, confidence scores, PR/commit info
- Tracks execution status

### Experiments Table
- Dreaming experiments with proper timestamp fields
- Tracks hypothesis, approach, metrics, risk levels
- Records outcomes and promotions to production

### Learned Patterns Table
- Cross-project pattern library
- Stores code templates with language/framework/domain tags
- Tracks confidence and success/failure counts

### Cross-Project Learnings Table
- Transfer learning records between projects
- Stores similarity scores and application status
- Links patterns to source and target projects

### Worker Statistics Table
- Tracks worker performance metrics
- Records cycles, experiments, errors, and timing
- One row per worker type

## Dependency Order

SQL schemas are applied in this order (respecting foreign key constraints):

1. `schema_projects.sql` (no dependencies)
2. `schema_code_snapshots.sql` (depends on projects)
3. `schema_proposals.sql` (depends on projects)
4. `schema_experiments.sql` (depends on projects)
5. `schema_learned_patterns.sql` (no dependencies)
6. `schema_cross_project_learnings.sql` (depends on projects, learned_patterns)
7. `schema_worker_stats.sql` (no dependencies)

## Troubleshooting

### Database Connection Errors

```bash
# Verify PostgreSQL is running
docker ps | grep postgres

# Test connection
psql -h localhost -p 5432 -U sigma -d sigma
```

### Missing Dependencies

Install required Python packages:

```bash
pip install psycopg2-binary
```

### Permission Errors

Ensure your PostgreSQL user has permission to:
- Create databases (when using POSTGRES_OVERWRITE_DB=true)
- Create tables
- Create indexes

### Migration Conflicts

If Alembic shows different migration versions, use the rebuild script to sync:

```bash
export POSTGRES_OVERWRITE_DB=true
python rebuild_database.py
```

## Integration with Alembic

The rebuild script updates the `alembic_version` table to mark the `migrate_agents_to_postgres` migration as applied. This ensures Alembic recognizes the database state.

After rebuilding, you can verify with:

```bash
cd src/openmemory
alembic current
```

## Safety Features

1. **CREATE IF NOT EXISTS**: All tables use `CREATE IF NOT EXISTS` to prevent errors
2. **Foreign Key Constraints**: Properly defined with ON DELETE CASCADE/SET NULL
3. **Transaction Safety**: Each SQL file is executed in a transaction
4. **Connection Termination**: Drops terminate existing connections before dropping database
5. **Validation**: Script verifies all expected tables exist after creation

## Example Workflow

```bash
# 1. Configure environment
export DATABASE_URL=postgresql://sigma:sigma@localhost:5432/sigma
export POSTGRES_OVERWRITE_DB=false

# 2. Run rebuild
cd scripts/postgres_rebuild
python rebuild_database.py

# 3. Verify with Alembic
cd ../src/openmemory
alembic current

# 4. Check tables in database
PGPASSWORD=sigma psql -h localhost -p 5432 -U sigma -d sigma -c "\dt"
```

## Production Considerations

⚠️ **WARNING**: Setting `POSTGRES_OVERWRITE_DB=true` will delete all existing data!

For production environments:
1. Always backup the database before rebuilding
2. Use `POSTGRES_OVERWRITE_DB=false` (default) to preserve existing data
3. Consider using migration tools (Alembic) for schema changes
4. Test the rebuild process in a staging environment first

## Future Enhancements

- [ ] Add data migration from old tables
- [ ] Add support for custom schema versions
- [ ] Add backup functionality
- [ ] Add data validation after rebuild
- [ ] Add support for multiple environments (dev, staging, prod)
