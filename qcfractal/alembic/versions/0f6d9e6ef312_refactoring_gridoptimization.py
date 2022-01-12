"""refactoring gridoptimization

Revision ID: 0f6d9e6ef312
Revises: bb4804242cea
Create Date: 2022-01-03 15:02:26.005753

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm.session import Session
from sqlalchemy.sql import table, column

from qcfractal.db_socket.column_types import PlainMsgpackExt

# revision identifiers, used by Alembic.
revision = "0f6d9e6ef312"
down_revision = "bb4804242cea"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    # Grid optimization spec table
    op.create_table(
        "gridoptimization_specification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("program", sa.String(length=100), nullable=False),
        sa.Column("optimization_specification_id", sa.Integer(), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint("program = LOWER(program)", name="ck_gridoptimization_specification_program_lower"),
        sa.ForeignKeyConstraint(
            ["optimization_specification_id"],
            ["optimization_specification.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "program", "optimization_specification_id", "keywords", name="ux_gridoptimization_specification_keys"
        ),
    )

    op.create_index(
        "ix_gridoptimization_specification_keywords", "gridoptimization_specification", ["keywords"], unique=False
    )
    op.create_index(
        "ix_gridoptimization_specification_optimization_specification_id",
        "gridoptimization_specification",
        ["optimization_specification_id"],
        unique=False,
    )
    op.create_index(
        "ix_gridoptimization_specification_program", "gridoptimization_specification", ["program"], unique=False
    )

    # Modify the optimization association table
    op.alter_column("grid_optimization_association", "opt_id", new_column_name="optimization_id")
    op.alter_column("grid_optimization_association", "grid_opt_id", new_column_name="gridoptimization_id")

    op.drop_constraint("grid_optimization_association_opt_id_fkey", "grid_optimization_association", type_="foreignkey")
    op.drop_constraint(
        "grid_optimization_association_grid_opt_id_fkey", "grid_optimization_association", type_="foreignkey"
    )
    op.create_foreign_key(
        "gridoptimization_optimizations_optimization_id_fkey",
        "grid_optimization_association",
        "optimization_record",
        ["optimization_id"],
        ["id"],
    )
    op.drop_constraint("grid_optimization_association_pkey", "grid_optimization_association", type_="primary")
    op.create_primary_key(
        "gridoptimization_optimizations_pkey",
        "grid_optimization_association",
        ["gridoptimization_id", "key"],
    )

    # Now the procedure table
    op.add_column("grid_optimization_procedure", sa.Column("specification_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "gridoptimization_record_specification_id_fkey",
        "grid_optimization_procedure",
        "gridoptimization_specification",
        ["specification_id"],
        ["id"],
    )

    op.drop_constraint("grid_optimization_procedure_id_fkey", "grid_optimization_procedure", type_="foreignkey")
    op.create_foreign_key(
        "gridoptimization_record_id_fkey",
        "grid_optimization_procedure",
        "base_record",
        ["id"],
        ["id"],
        ondelete="cascade",
    )

    op.drop_constraint(
        "grid_optimization_procedure_starting_molecule_fkey", "grid_optimization_procedure", type_="foreignkey"
    )
    op.drop_constraint(
        "grid_optimization_procedure_initial_molecule_fkey", "grid_optimization_procedure", type_="foreignkey"
    )
    op.alter_column("grid_optimization_procedure", "initial_molecule", new_column_name="initial_molecule_id")
    op.alter_column("grid_optimization_procedure", "starting_molecule", new_column_name="starting_molecule_id")
    op.create_foreign_key(
        "gridoptimization_record_initial_molecule_id_fkey",
        "grid_optimization_procedure",
        "molecule",
        ["initial_molecule_id"],
        ["id"],
    )
    op.create_foreign_key(
        "gridoptimization_record_starting_molecule_id_fkey",
        "grid_optimization_procedure",
        "molecule",
        ["starting_molecule_id"],
        ["id"],
    )

    op.drop_constraint("grid_optimization_procedure_pkey", "grid_optimization_procedure", type_="primary")
    op.create_primary_key(
        "gridoptimization_record_pkey",
        "grid_optimization_procedure",
        ["id"],
    )

    # Needed to wait for re-creating the primary key
    op.create_foreign_key(
        "gridoptimization_optimizations_gridoptimization_id_fkey",
        "grid_optimization_association",
        "grid_optimization_procedure",
        ["gridoptimization_id"],
        ["id"],
        ondelete="cascade",
    )

    ###########################################################
    # NOW THE BIG MIGRATION
    ###########################################################
    op.execute("ALTER TABLE grid_optimization_procedure ALTER COLUMN qc_spec TYPE JSONB")
    op.execute("ALTER TABLE grid_optimization_procedure ALTER COLUMN optimization_spec TYPE JSONB")
    op.execute("ALTER TABLE grid_optimization_procedure ALTER COLUMN keywords TYPE JSONB")

    # The empty, default keywords
    res = op.get_bind().execute(
        sa.text("SELECT id FROM keywords WHERE hash_index = 'bf21a9e8fbc5a3846fb05b4fa0859e0917b2202f'")
    )
    empty_kw = res.scalar()

    # Fiddle with the specifications
    # First, a hack. The MolSSI database has some old data with a non-existent hash still there. Replace
    # that with the appropriate keyword
    op.execute(
        sa.text(
            r"""UPDATE grid_optimization_procedure SET qc_spec = (qc_spec || '{"keywords": "2"}') WHERE qc_spec->>'keywords' = '5c954fa6b6a2de5f188ea234'"""
        )
    )

    # Remove empty and null keywords
    op.execute(
        sa.text(
            r"UPDATE grid_optimization_procedure SET qc_spec = (qc_spec - 'keywords') WHERE qc_spec->>'keywords' = ''"
        )
    )
    op.execute(
        sa.text(
            r"UPDATE grid_optimization_procedure SET qc_spec = (qc_spec - 'keywords') WHERE qc_spec->>'keywords' = 'null'"
        )
    )

    # Insert the qcspec
    # Protocols for qc_spec were always ignored. So set them with the default
    op.execute(
        sa.text(
            f"""
               INSERT INTO qc_specification (program, driver, method, basis, keywords_id, protocols)
               SELECT DISTINCT go.qc_spec->>'program',
                               'deferred'::singlepointdriver,
                               go.qc_spec->>'method',
                               COALESCE(go.qc_spec->>'basis', ''),
                               COALESCE((go.qc_spec->>'keywords')::int, {empty_kw}),
                               '{{}}'::jsonb
               FROM grid_optimization_procedure go
               ON CONFLICT DO NOTHING
               """
        )
    )

    # remove explicitly specified default protocols
    op.execute(
        sa.text(
            r"""UPDATE grid_optimization_procedure SET optimization_spec = (optimization_spec || '{"protocols": "{}"}') WHERE optimization_spec->'protocols' = '{"trajectory": "all"}'"""
        )
    )

    # Now the optimization_spec
    op.execute(
        sa.text(
            f"""
               INSERT INTO optimization_specification (program, keywords, protocols, qc_specification_id)
               SELECT DISTINCT go.optimization_spec->>'program',
                               COALESCE(go.optimization_spec->'keywords', '{{}}'),
                               COALESCE(go.optimization_spec->'protocols', '{{}}'),
                               (
                               SELECT id from qc_specification sp
                               WHERE sp.program = go.qc_spec->>'program'
                               AND sp.driver = 'deferred'::singlepointdriver
                               AND sp.method = go.qc_spec->>'method'
                               AND sp.basis = COALESCE(go.qc_spec->>'basis', '')
                               AND sp.keywords_id = COALESCE((go.qc_spec->>'keywords')::int, {empty_kw})
                               AND sp.protocols = '{{}}'
                               )
               FROM grid_optimization_procedure go
               ON CONFLICT DO NOTHING
               """
        )
    )

    # And the gridoptimization spec
    op.execute(
        sa.text(
            f"""
               INSERT INTO gridoptimization_specification (program, keywords, optimization_specification_id)
               SELECT DISTINCT 'gridoptimization',
                               go.keywords,
                               (
                                    SELECT id from optimization_specification os
                                    WHERE os.program = go.optimization_spec->>'program'
                                    AND os.keywords = COALESCE(go.optimization_spec->'keywords', '{{}}')
                                    AND os.protocols = COALESCE(go.optimization_spec->'protocols', '{{}}')
                                    AND os.qc_specification_id =
                                       (
                                           SELECT id from qc_specification sp
                                           WHERE sp.program = go.qc_spec->>'program'
                                           AND sp.driver = 'deferred'::singlepointdriver
                                           AND sp.method = go.qc_spec->>'method'
                                           AND sp.basis = COALESCE(go.qc_spec->>'basis', '')
                                           AND sp.keywords_id = COALESCE((go.qc_spec->>'keywords')::int, {empty_kw})
                                           AND sp.protocols = '{{}}'
                                       )
                                )
               FROM grid_optimization_procedure go
               """
        )
    )

    # Now add this to the gridoptimization spec column
    op.execute(
        sa.text(
            f"""
               UPDATE grid_optimization_procedure go
               SET specification_id = (
                   SELECT id FROM gridoptimization_specification gs
                   WHERE gs.program = 'gridoptimization'
                   AND gs.keywords = go.keywords
                   AND gs.optimization_specification_id = (
                             SELECT id from optimization_specification os
                             WHERE os.program = go.optimization_spec->>'program'
                             AND os.keywords = COALESCE(go.optimization_spec->'keywords', '{{}}')
                             AND os.protocols = COALESCE(go.optimization_spec->'protocols', '{{}}')
                             AND os.qc_specification_id = (
                                    SELECT id from qc_specification sp
                                    WHERE sp.program = go.qc_spec->>'program'
                                    AND sp.driver = 'deferred'::singlepointdriver
                                    AND sp.method = go.qc_spec->>'method'
                                    AND sp.basis = COALESCE(go.qc_spec->>'basis', '')
                                    AND sp.keywords_id = COALESCE((go.qc_spec->>'keywords')::int, {empty_kw})
                                    AND sp.protocols = '{{}}'
                            )
                        )
                   )
               """
        )
    )

    # Now migrate the service queue
    # Temporary ORM
    service_table = table(
        "service_queue",
        column("id", sa.Integer),
        column("service_state", PlainMsgpackExt),
    )

    bind = op.get_bind()
    session = Session(bind=bind)

    services = session.query(service_table).all()

    for service in services:

        if "torsiondrive_state" in service.service_state:
            continue

        # We have a gridoptimization
        # Remove the optimization template
        service.service_state.pop("optimization_template")
        session.execute(
            service_table.update()
            .where(service_table.c.id == service.id)
            .values({"service_state": service.service_state})
        )

    # rename "initial_opt" to "preoptimization" in the service dependencies
    op.execute(
        sa.text(
            """UPDATE service_dependencies SET extras = extras || '{"key": "preoptimization"}'
                          WHERE extras->>'key' = 'initial_opt'"""
        )
    )

    # Make columns not nullable now that they are populated
    op.alter_column("grid_optimization_procedure", "specification_id", nullable=False)

    # Drop unused columns
    op.drop_column("grid_optimization_procedure", "optimization_spec")
    op.drop_column("grid_optimization_procedure", "keywords")
    op.drop_column("grid_optimization_procedure", "qc_spec")
    op.drop_column("grid_optimization_procedure", "final_energy_dict")

    # Finally rename the tables
    op.rename_table("grid_optimization_association", "gridoptimization_optimizations")
    op.rename_table("grid_optimization_procedure", "gridoptimization_record")

    # ### end Alembic commands ###


def downgrade():
    raise RuntimeError("Cannot downgrade")
