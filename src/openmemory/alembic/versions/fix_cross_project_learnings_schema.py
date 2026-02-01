"""Fix cross_project_learnings schema to match models

Revision ID: fix_cross_project_learnings
Revises: fix_code_snapshots
Create Date: 2026-01-17 09:37:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_cross_project_learnings'
down_revision = 'fix_code_snapshots'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old index first (before batch alter) - use try/except in case already dropped
    try:
        op.drop_index('idx_learnings_target_applied', table_name='cross_project_learnings')
    except:
        pass  # Index may have been dropped in a previous failed migration attempt
    
    # Align columns with model
    with op.batch_alter_table('cross_project_learnings', schema=None) as batch_op:
        # Add similarity_score column that model expects
        batch_op.add_column(sa.Column('similarity_score', sa.Float(), nullable=True, server_default='0.0'))
        
        # Drop columns not in the model
        batch_op.drop_column('lesson')
        batch_op.drop_column('context_json')
        batch_op.drop_column('outcome')
        batch_op.drop_column('proposal_id')
        
        # Recreate indexes for the fields that are in the model
        batch_op.create_index('ix_cross_project_learnings_source_project_id', ['source_project_id'])
        batch_op.create_index('ix_cross_project_learnings_target_project_id', ['target_project_id'])
        batch_op.create_index('ix_cross_project_learnings_pattern_id', ['pattern_id'])
        batch_op.create_index('ix_cross_project_learnings_applied', ['applied'])
        batch_op.create_index('ix_cross_project_learnings_created_at', ['created_at'])


def downgrade():
    # Reverse the changes
    with op.batch_alter_table('cross_project_learnings', schema=None) as batch_op:
        # Drop new indexes
        batch_op.drop_index('ix_cross_project_learnings_created_at')
        batch_op.drop_index('ix_cross_project_learnings_applied')
        batch_op.drop_index('ix_cross_project_learnings_pattern_id')
        batch_op.drop_index('ix_cross_project_learnings_target_project_id')
        batch_op.drop_index('ix_cross_project_learnings_source_project_id')
        
        # Remove similarity_score
        batch_op.drop_column('similarity_score')
        
        # Add back the old columns
        batch_op.add_column(sa.Column('proposal_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('outcome', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('context_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('lesson', sa.Text(), nullable=False))
    
    # Recreate old index
    op.create_index('idx_learnings_target_applied', 'cross_project_learnings', ['target_project_id', 'applied'])
