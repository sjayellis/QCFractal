"""Add full uri to access log

Revision ID: 5d1989f8b59f
Revises: bba52fa8efbe
Create Date: 2022-03-28 15:17:23.125656

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5d1989f8b59f"
down_revision = "bba52fa8efbe"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("access_log", sa.Column("full_uri", sa.String(), nullable=True))
    op.drop_column("access_log", "extra_params")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("access_log", sa.Column("extra_params", sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column("access_log", "full_uri")
    # ### end Alembic commands ###
