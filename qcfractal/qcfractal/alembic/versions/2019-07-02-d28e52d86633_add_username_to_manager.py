"""Add username to manager

Revision ID: d28e52d86633
Revises: 
Create Date: 2019-07-02 22:51:25.613742

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d28e52d86633"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("queue_manager", sa.Column("username", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("queue_manager", "username")
    # ### end Alembic commands ###
