"""Add index column to Shareflow"""
import sqlalchemy as sa
from alembic import op


revision = "df3471a91cd2"
down_revision = "dbacf5b87669"


def upgrade():
    op.add_column(
        "shareflow", sa.Column("index", sa.Integer(), nullable=True)
    )


def downgrade():
    op.drop_column("shareflow", "index")
