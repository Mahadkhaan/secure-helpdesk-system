"""Widen User.password from VARCHAR(128) to TEXT

Werkzeug 3.x scrypt hashes exceed 128 characters.

Revision ID: c3d4e5f6a7b8
Revises: a799db9efe81
Create Date: 2026-06-25 18:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d4e5f6a7b8'
down_revision = 'a799db9efe81'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password',
               existing_type=sa.String(length=128),
               type_=sa.Text(),
               existing_nullable=False)


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password',
               existing_type=sa.Text(),
               type_=sa.String(length=128),
               existing_nullable=False)
