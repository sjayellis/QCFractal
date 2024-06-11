"""new manybody code

Revision ID: fd95035b773b
Revises: a5a701dc344d
Create Date: 2024-06-11 16:29:38.468745

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "fd95035b773b"
down_revision = "a5a701dc344d"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "manybody_specification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("program", sa.String(), nullable=False),
        sa.Column("bsse_correction", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("keywords_hash", sa.String(), nullable=False),
        sa.CheckConstraint("program = LOWER(program)", name="ck_manybody_specification_program_lower"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manybody_specification_program", "manybody_specification", ["program"], unique=False)
    op.create_table(
        "manybody_specification_levels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("manybody_specification_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("singlepoint_specification_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["manybody_specification_id"],
            ["manybody_specification.id"],
        ),
        sa.ForeignKeyConstraint(
            ["singlepoint_specification_id"],
            ["qc_specification.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manybody_specification_id", "level", name="ux_manybody_specification_levels_unique"),
    )
    op.create_index(
        "ix_manybody_specifications_levels_manybody_specification_id",
        "manybody_specification_levels",
        ["manybody_specification_id"],
        unique=False,
    )
    op.create_index(
        "ix_manybody_specifications_levels_singlepoint_specification_id",
        "manybody_specification_levels",
        ["singlepoint_specification_id"],
        unique=False,
    )
    op.create_table(
        "manybody_dataset",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["id"], ["base_dataset.id"], ondelete="cascade"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "manybody_record",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initial_molecule_id", sa.Integer(), nullable=False),
        sa.Column("specification_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["id"], ["base_record.id"], ondelete="cascade"),
        sa.ForeignKeyConstraint(
            ["initial_molecule_id"],
            ["molecule.id"],
        ),
        sa.ForeignKeyConstraint(
            ["specification_id"],
            ["manybody_specification.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "manybody_cluster",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("manybody_id", sa.Integer(), nullable=True),
        sa.Column("molecule_id", sa.Integer(), nullable=False),
        sa.Column("mc_level", sa.String(), nullable=False),
        sa.Column("fragments", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("basis", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("singlepoint_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("array_length(basis, 1) > 0", name="ck_manybody_cluster_basis"),
        sa.CheckConstraint("array_length(fragments, 1) > 0", name="ck_manybody_cluster_fragments"),
        sa.ForeignKeyConstraint(["manybody_id"], ["manybody_record.id"], ondelete="cascade"),
        sa.ForeignKeyConstraint(
            ["molecule_id"],
            ["molecule.id"],
        ),
        sa.ForeignKeyConstraint(
            ["singlepoint_id"],
            ["singlepoint_record.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manybody_id", "mc_level", "fragments", "basis", name="ux_manybody_cluster_unique"),
    )
    op.create_index("ix_manybody_cluster_molecule_id", "manybody_cluster", ["molecule_id"], unique=False)
    op.create_index("ix_manybody_cluster_singlepoint_id", "manybody_cluster", ["singlepoint_id"], unique=False)
    op.create_table(
        "manybody_dataset_entry",
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("initial_molecule_id", sa.Integer(), nullable=False),
        sa.Column("additional_singlepoint_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["manybody_dataset.id"], ondelete="cascade"),
        sa.ForeignKeyConstraint(
            ["initial_molecule_id"],
            ["molecule.id"],
        ),
        sa.PrimaryKeyConstraint("dataset_id", "name"),
    )
    op.create_index("ix_manybody_dataset_entry_dataset_id", "manybody_dataset_entry", ["dataset_id"], unique=False)
    op.create_index(
        "ix_manybody_dataset_entry_initial_molecule_id", "manybody_dataset_entry", ["initial_molecule_id"], unique=False
    )
    op.create_index("ix_manybody_dataset_entry_name", "manybody_dataset_entry", ["name"], unique=False)
    op.create_table(
        "manybody_dataset_specification",
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("specification_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["manybody_dataset.id"], ondelete="cascade"),
        sa.ForeignKeyConstraint(
            ["specification_id"],
            ["manybody_specification.id"],
        ),
        sa.PrimaryKeyConstraint("dataset_id", "name"),
    )
    op.create_index(
        "ix_manybody_dataset_specification_dataset_id", "manybody_dataset_specification", ["dataset_id"], unique=False
    )
    op.create_index("ix_manybody_dataset_specification_name", "manybody_dataset_specification", ["name"], unique=False)
    op.create_index(
        "ix_manybody_dataset_specification_specification_id",
        "manybody_dataset_specification",
        ["specification_id"],
        unique=False,
    )
    op.create_table(
        "manybody_dataset_record",
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("entry_name", sa.String(), nullable=False),
        sa.Column("specification_name", sa.String(), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id", "entry_name"],
            ["manybody_dataset_entry.dataset_id", "manybody_dataset_entry.name"],
            onupdate="cascade",
            ondelete="cascade",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id", "specification_name"],
            ["manybody_dataset_specification.dataset_id", "manybody_dataset_specification.name"],
            onupdate="cascade",
            ondelete="cascade",
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["manybody_dataset.id"], ondelete="cascade"),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["manybody_record.id"],
        ),
        sa.PrimaryKeyConstraint("dataset_id", "entry_name", "specification_name"),
    )
    op.create_index("ix_manybody_dataset_record_record_id", "manybody_dataset_record", ["record_id"], unique=False)

    op.execute(
        """CREATE TRIGGER qca_manybody_record_delete_base_tr
                  AFTER DELETE ON public.manybody_record
                  FOR EACH ROW EXECUTE FUNCTION qca_base_record_delete();"""
    )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_manybody_dataset_record_record_id", table_name="manybody_dataset_record")
    op.drop_table("manybody_dataset_record")
    op.drop_index("ix_manybody_dataset_specification_specification_id", table_name="manybody_dataset_specification")
    op.drop_index("ix_manybody_dataset_specification_name", table_name="manybody_dataset_specification")
    op.drop_index("ix_manybody_dataset_specification_dataset_id", table_name="manybody_dataset_specification")
    op.drop_table("manybody_dataset_specification")
    op.drop_index("ix_manybody_dataset_entry_name", table_name="manybody_dataset_entry")
    op.drop_index("ix_manybody_dataset_entry_initial_molecule_id", table_name="manybody_dataset_entry")
    op.drop_index("ix_manybody_dataset_entry_dataset_id", table_name="manybody_dataset_entry")
    op.drop_table("manybody_dataset_entry")
    op.drop_index("ix_manybody_cluster_singlepoint_id", table_name="manybody_cluster")
    op.drop_index("ix_manybody_cluster_molecule_id", table_name="manybody_cluster")
    op.drop_table("manybody_cluster")
    op.drop_table("manybody_record")
    op.drop_table("manybody_dataset")
    op.drop_index(
        "ix_manybody_specifications_levels_singlepoint_specification_id", table_name="manybody_specification_levels"
    )
    op.drop_index(
        "ix_manybody_specifications_levels_manybody_specification_id", table_name="manybody_specification_levels"
    )
    op.drop_table("manybody_specification_levels")
    op.drop_index("ix_manybody_specification_program", table_name="manybody_specification")
    op.drop_table("manybody_specification")
    # ### end Alembic commands ###
