"""Add conflict resolution tables

Revision ID: add_conflict_resolution_tables
Revises: add_knowledge_exchange_tables
Create Date: 2026-01-22 22:40:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_conflict_resolution_tables'
down_revision = 'add_knowledge_exchange_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade database to add conflict resolution tables"""
    
    # Add conflict resolution metadata to knowledge_exchange table
    op.add_column('knowledge_exchange', sa.Column('is_resolved', sa.Boolean(), nullable=True, default=False))
    op.add_column('knowledge_exchange', sa.Column('resolution_id', sa.String(), nullable=True))
    op.add_column('knowledge_exchange', sa.Column('conflict_type', sa.String(), nullable=True))
    
    # Create conflict_resolutions table
    op.create_table(
        'conflict_resolutions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('conflict_id', sa.String(), nullable=False),
        sa.Column('knowledge_a_id', sa.String(), nullable=False),
        sa.Column('knowledge_b_id', sa.String(), nullable=False),
        sa.Column('conflict_type', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('contradiction_score', sa.Float(), nullable=True),
        sa.Column('overlap_score', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('resolution_strategy', sa.String(), nullable=False),
        sa.Column('selected_knowledge_id', sa.String(), nullable=True),
        sa.Column('merged_knowledge', postgresql.JSONB(), nullable=True),
        sa.Column('resolution_notes', sa.String(), nullable=True),
        sa.Column('resolution_confidence', sa.Float(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('conflict_id', name='uq_conflict_resolution_conflict_id')
    )
    
    # Create indexes for conflict resolution queries
    op.create_index('idx_conflict_resolutions_resolved_at', 'conflict_resolutions', ['resolved_at'])
    op.create_index('idx_conflict_resolutions_conflict_type', 'conflict_resolutions', ['conflict_type'])
    op.create_index('idx_conflict_resolutions_severity', 'conflict_resolutions', ['severity'])
    op.create_index('idx_conflict_resolutions_confidence', 'conflict_resolutions', ['confidence'])
    op.create_index('idx_knowledge_exchange_resolution_id', 'knowledge_exchange', ['resolution_id'])
    op.create_index('idx_knowledge_exchange_is_resolved', 'knowledge_exchange', ['is_resolved'])
    
    # Create conflict_audit table for tracking conflict detection history
    op.create_table(
        'conflict_audit',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('worker_id', sa.String(), nullable=False),
        sa.Column('conflict_check_timestamp', sa.DateTime(), nullable=False),
        sa.Column('knowledge_checked_count', sa.Integer(), nullable=False),
        sa.Column('conflicts_detected_count', sa.Integer(), nullable=False),
        sa.Column('resolutions_made_count', sa.Integer(), nullable=False),
        sa.Column('auto_resolve_enabled', sa.Boolean(), nullable=False),
        sa.Column('detection_confidence', sa.Float(), nullable=False),
        sa.Column('cycle_duration_ms', sa.Float(), nullable=True),
        sa.Column('health_status', sa.String(), nullable=False),
        sa.Column('summary_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for audit queries
    op.create_index('idx_conflict_audit_worker_timestamp', 'conflict_audit', ['worker_id', 'conflict_check_timestamp'])
    op.create_index('idx_conflict_audit_health', 'conflict_audit', ['health_status'])
    op.create_index('idx_conflict_audit_timestamp', 'conflict_audit', ['conflict_check_timestamp'])
    
    # Create conflict_metrics table for monitoring and statistics
    op.create_table(
        'conflict_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('metric_type', sa.String(), nullable=False),
        sa.Column('worker_id', sa.String(), nullable=True),
        sa.Column('conflict_type', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for metrics queries
    op.create_index('idx_conflict_metrics_timestamp', 'conflict_metrics', ['timestamp'])
    op.create_index('idx_conflict_metrics_name', 'conflict_metrics', ['metric_name'])
    op.create_index('idx_conflict_metrics_worker', 'conflict_metrics', ['worker_id'])
    op.create_index('idx_conflict_metrics_type', 'conflict_metrics', ['metric_type'])
    
    # Create unique constraint on worker_knowledge_state for conflict tracking
    op.create_unique_constraint(
        'uq_worker_knowledge_state_worker_type',
        'worker_knowledge_state',
        ['worker_id', 'knowledge_type']
    )
    
    # Add conflict tracking columns to worker_knowledge_state
    op.add_column('worker_knowledge_state', sa.Column('conflicts_detected', sa.Integer(), nullable=False, default=0))
    op.add_column('worker_knowledge_state', sa.Column('conflicts_resolved', sa.Integer(), nullable=False, default=0))
    op.add_column('worker_knowledge_state', sa.Column('last_conflict_check', sa.DateTime(), nullable=True))
    
    # Create view for conflict dashboard (simplified view)
    op.execute("""
        CREATE OR REPLACE VIEW conflict_dashboard_view AS
        SELECT 
            cr.id,
            cr.conflict_id,
            cr.conflict_type,
            cr.severity,
            cr.confidence,
            cr.resolution_strategy,
            cr.resolution_confidence,
            cr.resolved_at,
            ka.id as knowledge_a_id,
            ka.source_worker as knowledge_a_worker,
            kb.id as knowledge_b_id,
            kb.source_worker as knowledge_b_worker
        FROM conflict_resolutions cr
        LEFT JOIN knowledge_exchange ka ON cr.knowledge_a_id = ka.id
        LEFT JOIN knowledge_exchange kb ON cr.knowledge_b_id = kb.id
        WHERE cr.resolved_at >= NOW() - INTERVAL '30 days'
        ORDER BY cr.resolved_at DESC
    """)
    
    # Create summary statistics view
    op.execute("""
        CREATE OR REPLACE VIEW conflict_summary_view AS
        SELECT 
            DATE_TRUNC('day', resolved_at) as day,
            conflict_type,
            severity,
            COUNT(*) as total_conflicts,
            AVG(confidence) as avg_confidence,
            AVG(resolution_confidence) as avg_resolution_confidence,
            resolution_strategy,
            COUNT(*) FILTER (WHERE resolution_strategy = 'merge') as merge_count,
            COUNT(*) FILTER (WHERE resolution_strategy = 'select_newer') as select_newer_count,
            COUNT(*) FILTER (WHERE resolution_strategy = 'select_higher_quality') as select_higher_quality_count,
            COUNT(*) FILTER (WHERE resolution_strategy = 'keep_both') as keep_both_count
        FROM conflict_resolutions
        WHERE resolved_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE_TRUNC('day', resolved_at), conflict_type, severity, resolution_strategy
        ORDER BY day DESC
    """)


def downgrade():
    """Downgrade database by removing conflict resolution tables"""
    
    # Drop views
    op.drop_view('conflict_summary_view')
    op.drop_view('conflict_dashboard_view')
    
    # Drop conflict metrics table
    op.drop_table('conflict_metrics')
    
    # Drop conflict audit table
    op.drop_table('conflict_audit')
    
    # Drop conflict resolutions table
    op.drop_table('conflict_resolutions')
    
    # Remove columns from worker_knowledge_state
    op.drop_column('worker_knowledge_state', 'last_conflict_check')
    op.drop_column('worker_knowledge_state', 'conflicts_resolved')
    op.drop_column('worker_knowledge_state', 'conflicts_detected')
    
    # Drop unique constraint on worker_knowledge_state
    op.drop_constraint('uq_worker_knowledge_state_worker_type', 'worker_knowledge_state', type_='unique')
    
    # Remove indexes from knowledge_exchange
    op.drop_index('idx_knowledge_exchange_is_resolved', table_name='knowledge_exchange')
    op.drop_index('idx_knowledge_exchange_resolution_id', table_name='knowledge_exchange')
    
    # Remove columns from knowledge_exchange
    op.drop_column('knowledge_exchange', 'conflict_type')
    op.drop_column('knowledge_exchange', 'resolution_id')
    op.drop_column('knowledge_exchange', 'is_resolved')
