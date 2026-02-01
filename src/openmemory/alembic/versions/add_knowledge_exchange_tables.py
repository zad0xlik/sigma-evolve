"""Add knowledge exchange tables

Revision ID: add_knowledge_exchange_tables
Revises: fix_cross_project_learnings_schema
Create Date: 2026-01-22 12:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_knowledge_exchange_tables'
down_revision = 'fix_cross_project_learnings_schema'
branch_labels = None
depends_on = None

def upgrade():
    # Create knowledge_exchange table
    op.create_table(
        'knowledge_exchange',
        sa.Column('exchange_id', sa.Integer(), nullable=False),
        sa.Column('source_worker', sa.String(length=50), nullable=False),
        sa.Column('target_worker', sa.String(length=50), nullable=True),
        sa.Column('knowledge_type', sa.String(length=50), nullable=False),
        sa.Column('knowledge_data', postgresql.JSONB(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('freshness_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('validation_status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('exchange_id')
    )
    op.create_index('idx_exchange_source_type', 'knowledge_exchange', ['source_worker', 'knowledge_type'])
    op.create_index('idx_exchange_target', 'knowledge_exchange', ['target_worker'])
    op.create_index('idx_exchange_freshness', 'knowledge_exchange', ['freshness_score'])
    
    # Create worker_knowledge_state table
    op.create_table(
        'worker_knowledge_state',
        sa.Column('worker_name', sa.String(length=50), nullable=False),
        sa.Column('knowledge_snapshot', postgresql.JSONB(), nullable=True),
        sa.Column('last_exchange', sa.DateTime(), nullable=True),
        sa.Column('exchange_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('received_knowledge', postgresql.JSONB(), nullable=True),
        sa.Column('broadcast_knowledge', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('worker_name')
    )
    op.create_index('idx_worker_knowledge_last', 'worker_knowledge_state', ['last_exchange'])
    
    # Create knowledge_validation table
    op.create_table(
        'knowledge_validation',
        sa.Column('validation_id', sa.Integer(), nullable=False),
        sa.Column('exchange_id', sa.Integer(), nullable=False),
        sa.Column('validator_worker', sa.String(length=50), nullable=False),
        sa.Column('is_valid', sa.Boolean(), nullable=True),
        sa.Column('validation_score', sa.Float(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['exchange_id'], ['knowledge_exchange.exchange_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('validation_id')
    )
    op.create_index('idx_validation_exchange', 'knowledge_validation', ['exchange_id'])
    op.create_index('idx_validation_validator', 'knowledge_validation', ['validator_worker'])
    op.create_index('idx_validation_valid', 'knowledge_validation', ['is_valid'])


def downgrade():
    # Drop tables in reverse order
    op.drop_index('idx_validation_valid', table_name='knowledge_validation')
    op.drop_index('idx_validation_validator', table_name='knowledge_validation')
    op.drop_index('idx_validation_exchange', table_name='knowledge_validation')
    op.drop_table('knowledge_validation')
    
    op.drop_index('idx_worker_knowledge_last', table_name='worker_knowledge_state')
    op.drop_table('worker_knowledge_state')
    
    op.drop_index('idx_exchange_freshness', table_name='knowledge_exchange')
    op.drop_index('idx_exchange_target', table_name='knowledge_exchange')
    op.drop_index('idx_exchange_source_type', table_name='knowledge_exchange')
    op.drop_table('knowledge_exchange')
