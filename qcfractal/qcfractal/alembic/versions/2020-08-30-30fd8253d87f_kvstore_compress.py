"""Compression of KVStore

Revision ID: 30fd8253d87f
Revises: 1604623c481a
Create Date: 2020-08-30 10:11:57.574292

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "30fd8253d87f"
down_revision = "1604623c481a"
branch_labels = None
depends_on = None


def upgrade():
    # Appears there is an alembic issue with autogenerating enums:
    # https://github.com/sqlalchemy/alembic/issues/278

    compression_enum = postgresql.ENUM("none", "gzip", "bzip2", "lzma", name="compressionenum")
    compression_enum.create(op.get_bind())

    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("kv_store", sa.Column("compression", compression_enum, nullable=True))
    op.add_column("kv_store", sa.Column("compression_level", sa.Integer(), nullable=True))
    op.add_column("kv_store", sa.Column("data", sa.LargeBinary(), nullable=True))
    op.alter_column("kv_store", "value", existing_type=postgresql.JSON(astext_type=sa.Text()), nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("kv_store", "value", existing_type=postgresql.JSON(astext_type=sa.Text()), nullable=False)
    op.drop_column("kv_store", "data")
    op.drop_column("kv_store", "compression_level")
    op.drop_column("kv_store", "compression")
    op.execute("DROP TYPE compressionenum")
    # ### end Alembic commands ###
