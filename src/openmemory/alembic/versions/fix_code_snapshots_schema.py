"""Fix code_snapshots schema to match models

Revision ID: fix_code_snapshots
Revises: add_agent_system
Create Date: 2026-01-16 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_code_snapshots'
down_revision = 'add_agent_system'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old index first (before batch alter) - use try/except in case already dropped
    try:
        op.drop_index('idx_snapshots_project_ts', table_name='code_snapshots')
    except:
        pass  # Index may have been dropped in a previous failed migration attempt
    
    # Rename columns to match model
    with op.batch_alter_table('code_snapshots', schema=None) as batch_op:
        # Rename complexity_score to complexity
        batch_op.alter_column('complexity_score', 
                            new_column_name='complexity',
                            existing_type=sa.Float())
        
        # Rename issue_count to issues_found
        batch_op.alter_column('issue_count',
                            new_column_name='issues_found',
                            existing_type=sa.Integer())
        
        # Drop columns not in the model
        batch_op.drop_column('ts')
        batch_op.drop_column('commit_sha')
        batch_op.drop_column('file_count')
        batch_op.drop_column('total_lines')
        batch_op.drop_column('security_issue_count')
        batch_op.drop_column('issues_json')
        
        # Add created_at column that model expects
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))
        
        # Create index on created_at
        batch_op.create_index('ix_code_snapshots_created_at', ['created_at'])
        batch_op.create_index('ix_code_snapshots_project_id', ['project_id'])


def downgrade():
    # Reverse the changes
    with op.batch_alter_table('code_snapshots', schema=None) as batch_op:
        batch_op.drop_index('ix_code_snapshots_created_at')
        batch_op.drop_index('ix_code_snapshots_project_id')
        
        batch_op.drop_column('created_at')
        
        batch_op.add_column(sa.Column('issues_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('security_issue_count', sa.Integer(), server_default='0'))
        batch_op.add_column(sa.Column('total_lines', sa.Integer(), server_default='0'))
        batch_op.add_column(sa.Column('file_count', sa.Integer(), server_default='0'))
        batch_op.add_column(sa.Column('commit_sha', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('ts', sa.String(), nullable=False))
        
        batch_op.alter_column('issues_found',
                            new_column_name='issue_count',
                            existing_type=sa.Integer())
        
        batch_op.alter_column('complexity',
                            new_column_name='complexity_score',
                            existing_type=sa.Float())
    
    op.create_index('idx_snapshots_project_ts', 'code_snapshots', ['project_id', 'ts'])
