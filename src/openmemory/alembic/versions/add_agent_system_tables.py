"""Add agent system tables for SIGMA

Revision ID: add_agent_system
Revises: afd00efbd06b
Create Date: 2026-01-14 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_agent_system'
down_revision = 'afd00efbd06b'
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # PROJECTS TABLE - Track multiple projects for cross-project learning
    # =========================================================================
    op.create_table(
        'projects',
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('repo_url', sa.String(), nullable=False),
        sa.Column('branch', sa.String(), nullable=True),
        sa.Column('workspace_path', sa.String(), nullable=False),
        sa.Column('language', sa.String(), nullable=True),
        sa.Column('framework', sa.String(), nullable=True),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('last_analyzed', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('project_id')
    )
    
    # =========================================================================
    # CODE SNAPSHOTS TABLE - Store analysis results over time
    # =========================================================================
    op.create_table(
        'code_snapshots',
        sa.Column('snapshot_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('ts', sa.String(), nullable=False),
        sa.Column('commit_sha', sa.String(), nullable=True),
        sa.Column('file_count', sa.Integer(), default=0),
        sa.Column('total_lines', sa.Integer(), default=0),
        sa.Column('complexity_score', sa.Float(), default=0.0),
        sa.Column('test_coverage', sa.Float(), default=0.0),
        sa.Column('issue_count', sa.Integer(), default=0),
        sa.Column('security_issue_count', sa.Integer(), default=0),
        sa.Column('metrics_json', sa.Text(), nullable=True),  # JSON dump of detailed metrics
        sa.Column('issues_json', sa.Text(), nullable=True),  # JSON dump of detected issues
        sa.PrimaryKeyConstraint('snapshot_id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE')
    )
    op.create_index('idx_snapshots_project_ts', 'code_snapshots', ['project_id', 'ts'])
    
    # =========================================================================
    # PROPOSALS TABLE - Agent committee decisions (like insights in trading)
    # =========================================================================
    op.create_table(
        'proposals',
        sa.Column('proposal_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('agents_json', sa.Text(), nullable=True),  # Agent committee responses
        sa.Column('changes_json', sa.Text(), nullable=True),  # Proposed code changes
        sa.Column('confidence', sa.Float(), default=0.0),
        sa.Column('critic_score', sa.Float(), default=0.0),
        sa.Column('status', sa.String(), default='pending'),  # pending, approved, rejected, executed
        sa.Column('pr_url', sa.String(), nullable=True),
        sa.Column('commit_sha', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('executed_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('proposal_id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE')
    )
    op.create_index('idx_proposals_project_status', 'proposals', ['project_id', 'status'])
    
    # =========================================================================
    # EXPERIMENTS TABLE - Track dreaming experiments
    # =========================================================================
    op.create_table(
        'experiments',
        sa.Column('experiment_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),  # NULL for cross-project experiments
        sa.Column('worker_name', sa.String(), nullable=False),  # analysis, dream, recall, learning, think
        sa.Column('experiment_name', sa.String(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('hypothesis', sa.Text(), nullable=True),
        sa.Column('approach', sa.Text(), nullable=True),
        sa.Column('baseline_metrics', sa.String(), nullable=True),
        sa.Column('result_metrics', sa.String(), nullable=True),
        sa.Column('metrics', sa.Text(), nullable=True),  # JSON array of metric names
        sa.Column('risk_level', sa.String(), nullable=True),  # low, medium, high
        sa.Column('rollback_plan', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), default='proposed'),  # proposed, running, completed, failed, rolled_back
        sa.Column('started_at', sa.String(), nullable=True),
        sa.Column('completed_at', sa.String(), nullable=True),
        sa.Column('outcome_json', sa.Text(), nullable=True),  # Results and measurements
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('improvement', sa.Float(), nullable=True),  # % improvement if successful
        sa.Column('promoted_to_production', sa.Boolean(), default=False),
        sa.Column('promoted_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('experiment_id'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE')
    )
    op.create_index('idx_experiments_worker_status', 'experiments', ['worker_name', 'status'])
    op.create_index('idx_experiments_success', 'experiments', ['success'])
    
    # =========================================================================
    # LEARNED PATTERNS TABLE - Cross-project pattern library
    # =========================================================================
    op.create_table(
        'learned_patterns',
        sa.Column('pattern_id', sa.Integer(), nullable=False),
        sa.Column('pattern_name', sa.String(), nullable=False),
        sa.Column('pattern_type', sa.String(), nullable=False),  # refactor, fix, optimize, etc.
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('code_template', sa.String(), nullable=True),  # Code template for the pattern
        sa.Column('language', sa.String(), nullable=False),
        sa.Column('framework', sa.String(), nullable=True),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), default=0.0),
        sa.Column('success_count', sa.Integer(), default=0),
        sa.Column('failure_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('last_used', sa.String(), nullable=True),
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
        sa.Column('lesson', sa.Text(), nullable=False),
        sa.Column('context_json', sa.Text(), nullable=True),
        sa.Column('applied', sa.Boolean(), default=False),
        sa.Column('outcome', sa.String(), nullable=True),  # success, failure, pending
        sa.Column('proposal_id', sa.Integer(), nullable=True),  # Link to proposal if applied
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('applied_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('learning_id'),
        sa.ForeignKeyConstraint(['source_project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pattern_id'], ['learned_patterns.pattern_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposals.proposal_id'], ondelete='SET NULL')
    )
    op.create_index('idx_learnings_target_applied', 'cross_project_learnings', ['target_project_id', 'applied'])
    
    # =========================================================================
    # WORKER STATISTICS TABLE - Track worker performance
    # =========================================================================
    op.create_table(
        'worker_stats',
        sa.Column('stat_id', sa.Integer(), nullable=False),
        sa.Column('worker_name', sa.String(), nullable=False),
        sa.Column('cycles_run', sa.Integer(), default=0),
        sa.Column('experiments_run', sa.Integer(), default=0),
        sa.Column('total_time', sa.Float(), default=0.0),
        sa.Column('errors', sa.Integer(), default=0),
        sa.Column('last_run', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('stat_id')
    )
    op.create_index('idx_worker_stats_worker', 'worker_stats', ['worker_name'])
    
    # =========================================================================
    # EVENT LOG ENHANCEMENTS - Add worker and experiment tracking
    # =========================================================================
    # Existing event_log table should already exist, just add indexes if needed
    try:
        op.create_index('idx_event_log_worker', 'event_log', ['worker'])
    except:
        pass  # Index might already exist


def downgrade():
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_index('idx_event_log_worker', table_name='event_log', if_exists=True)
    op.drop_table('worker_stats')
    op.drop_index('idx_learnings_target_applied', table_name='cross_project_learnings')
    op.drop_table('cross_project_learnings')
    op.drop_index('idx_patterns_language_framework', table_name='learned_patterns')
    op.drop_index('idx_patterns_type_confidence', table_name='learned_patterns')
    op.drop_table('learned_patterns')
    op.drop_index('idx_experiments_success', table_name='experiments')
    op.drop_index('idx_experiments_worker_status', table_name='experiments')
    op.drop_table('experiments')
    op.drop_index('idx_proposals_project_status', table_name='proposals')
    op.drop_table('proposals')
    op.drop_index('idx_snapshots_project_ts', table_name='code_snapshots')
    op.drop_table('code_snapshots')
    op.drop_table('projects')
