"""Migrate agent tables to PostgreSQL with proper types

Revision ID: migrate_agents_to_postgres
Revises: fix_cross_project_learnings
Create Date: 2026-01-20 14:30:00.000000

This migration:
1. Drops the SQLite agent tables (if they exist)
2. Recreates them with PostgreSQL-compatible types
3. Fixes the missing created_at field in experiments table
4. Uses proper DateTime types instead of String for timestamps
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'migrate_agents_to_postgres'
down_revision = 'fix_cross_project_learnings'
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing tables if they exist (from SQLite migration)
    # We'll recreate them with proper types
    tables_to_drop = [
        'worker_stats',
        'cross_project_learnings',
        'learned_patterns',
        'experiments',
        'proposals',
        'code_snapshots',
        'projects'
    ]
    
    for table in tables_to_drop:
        try:
            op.drop_table(table)
        except:
            pass  # Table may not exist
    
    # =========================================================================
    # PROJECTS TABLE - Track multiple projects for cross-project learning
    # =========================================================================
    op.create_table(
        'projects',
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('repo_url', sa.String(), nullable=False),
        sa.Column('branch', sa.String(), nullable=True, server_default='main'),
        sa.Column('workspace_path', sa.String(), nullable=False),
        sa.Column('language', sa.String(), nullable=True),
        sa.Column('framework', sa.String(), nullable=True),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_analyzed', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('project_id')
    )
    op.create_index('idx_projects_language', 'projects', ['language'])
    op.create_index('idx_projects_framework', 'projects', ['framework'])
    op.create_index('idx_projects_domain', 'projects', ['domain'])
    
    # =========================================================================
    # CODE SNAPSHOTS TABLE - Store analysis results over time
    # =========================================================================
    op.create_table(
        'code_snapshots',
        sa.Column('snapshot_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('complexity', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('test_coverage', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('issues_found', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('metrics_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # New fields for Graphiti integration
        sa.Column('graph_entity_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('graphiti_episode_id', sa.String(), nullable=True),
        # New fields for Qdrant integration
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('qdrant_point_ids', sa.Text(), nullable=True),  # JSON array
        sa.PrimaryKeyConstraint('snapshot_id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE')
    )
    op.create_index('idx_snapshots_project_created', 'code_snapshots', ['project_id', 'created_at'])
    op.create_index('idx_snapshots_indexed', 'code_snapshots', ['indexed_at'])
    
    # =========================================================================
    # PROPOSALS TABLE - Agent committee decisions
    # =========================================================================
    op.create_table(
        'proposals',
        sa.Column('proposal_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('agents_json', sa.Text(), nullable=True),  # Agent committee responses
        sa.Column('changes_json', sa.Text(), nullable=True),  # Proposed code changes
        sa.Column('confidence', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('critic_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('status', sa.String(), nullable=True, server_default='pending'),
        sa.Column('pr_url', sa.String(), nullable=True),
        sa.Column('commit_sha', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('proposal_id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE')
    )
    op.create_index('idx_proposals_project_status', 'proposals', ['project_id', 'status'])
    op.create_index('idx_proposals_confidence', 'proposals', ['confidence'])
    
    # =========================================================================
    # EXPERIMENTS TABLE - Track dreaming experiments (FIXED)
    # =========================================================================
    op.create_table(
        'experiments',
        sa.Column('experiment_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),  # NULL for cross-project experiments
        sa.Column('worker_name', sa.String(), nullable=False),  # analysis, dream, recall, learning, think
        sa.Column('experiment_name', sa.String(), nullable=False),
        sa.Column('hypothesis', sa.Text(), nullable=True),
        sa.Column('approach', sa.Text(), nullable=True),
        sa.Column('metrics', sa.Text(), nullable=True),  # JSON array of metric names
        sa.Column('risk_level', sa.String(), nullable=True),  # low, medium, high
        sa.Column('rollback_plan', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, server_default='proposed'),
        sa.Column('baseline_metrics', sa.Text(), nullable=True),
        sa.Column('result_metrics', sa.Text(), nullable=True),
        sa.Column('outcome_json', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('improvement', sa.Float(), nullable=True),
        sa.Column('promoted_to_production', sa.Boolean(), nullable=True, server_default='false'),
        # Timestamp fields (ALL FIXED)
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('promoted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('experiment_id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE')
    )
    op.create_index('idx_experiments_worker_status', 'experiments', ['worker_name', 'status'])
    op.create_index('idx_experiments_success', 'experiments', ['success'])
    op.create_index('idx_experiments_promoted', 'experiments', ['promoted_to_production'])
    
    # =========================================================================
    # LEARNED PATTERNS TABLE - Cross-project pattern library
    # =========================================================================
    op.create_table(
        'learned_patterns',
        sa.Column('pattern_id', sa.Integer(), nullable=False),
        sa.Column('pattern_name', sa.String(), nullable=False),
        sa.Column('pattern_type', sa.String(), nullable=False),  # refactor, fix, optimize, etc.
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('code_template', sa.Text(), nullable=True),  # Code template for the pattern
        sa.Column('language', sa.String(), nullable=False),
        sa.Column('framework', sa.String(), nullable=True),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('success_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('pattern_id')
    )
    op.create_index('idx_patterns_type_confidence', 'learned_patterns', ['pattern_type', 'confidence'])
    op.create_index('idx_patterns_language_framework', 'learned_patterns', ['language', 'framework'])
    
    # =========================================================================
    # CROSS-PROJECT LEARNINGS TABLE - Transfer learning records
    # =========================================================================
    op.create_table(
        'cross_project_learnings',
        sa.Column('learning_id', sa.Integer(), nullable=False),
        sa.Column('source_project_id', sa.Integer(), nullable=False),
        sa.Column('target_project_id', sa.Integer(), nullable=False),
        sa.Column('pattern_id', sa.Integer(), nullable=True),
        sa.Column('similarity_score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('applied', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('learning_id'),
        sa.ForeignKeyConstraint(['source_project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pattern_id'], ['learned_patterns.pattern_id'], ondelete='SET NULL')
    )
    op.create_index('idx_learnings_target_applied', 'cross_project_learnings', ['target_project_id', 'applied'])
    op.create_index('idx_learnings_source', 'cross_project_learnings', ['source_project_id'])
    
    # =========================================================================
    # WORKER STATISTICS TABLE - Track worker performance
    # =========================================================================
    op.create_table(
        'worker_stats',
        sa.Column('stat_id', sa.Integer(), nullable=False),
        sa.Column('worker_name', sa.String(), nullable=False),
        sa.Column('cycles_run', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('experiments_run', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_time', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('errors', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_run', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('stat_id')
    )
    op.create_index('idx_worker_stats_worker', 'worker_stats', ['worker_name'])
    op.create_index('idx_worker_stats_last_run', 'worker_stats', ['last_run'])


def downgrade():
    # Drop all agent tables
    op.drop_table('worker_stats')
    op.drop_table('cross_project_learnings')
    op.drop_table('learned_patterns')
    op.drop_table('experiments')
    op.drop_table('proposals')
    op.drop_table('code_snapshots')
    op.drop_table('projects')
