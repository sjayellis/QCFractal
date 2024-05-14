"""remove qcengine from versions

Revision ID: cabe9df168a5
Revises: ae97b389022a
Create Date: 2021-11-04 14:11:40.200284

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "cabe9df168a5"
down_revision = "ae97b389022a"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("versions", "engine_version")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("versions", sa.Column("engine_version", sa.VARCHAR(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
