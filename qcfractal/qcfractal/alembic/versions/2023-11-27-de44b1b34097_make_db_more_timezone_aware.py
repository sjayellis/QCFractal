"""Make DB more timezone aware

Revision ID: de44b1b34097
Revises: 13cb230def11
Create Date: 2023-11-27 12:14:40.915673

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "de44b1b34097"
down_revision = "13cb230def11"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "access_log",
        "timestamp",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="timestamp at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "base_record",
        "created_on",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="created_on at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "base_record",
        "modified_on",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="modified_on at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "compute_manager",
        "created_on",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="created_on at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "compute_manager",
        "modified_on",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="modified_on at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "compute_manager_log",
        "timestamp",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="timestamp at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "internal_error_log",
        "error_date",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="error_date at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "internal_jobs",
        "added_date",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="added_date at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "internal_jobs",
        "scheduled_date",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="scheduled_date at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "internal_jobs",
        "started_date",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="started_date at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "internal_jobs",
        "last_updated",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="last_updated at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "internal_jobs",
        "ended_date",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="ended_date at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "record_comment",
        "timestamp",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="timestamp at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "record_compute_history",
        "modified_on",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="modified_on at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "record_info_backup",
        "modified_on",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="modified_on at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "server_stats_log",
        "timestamp",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="timestamp at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "server_stats_metadata",
        "date_value",
        type_=sa.TIMESTAMP(timezone=True),
        postgresql_using="date_value at time zone 'Etc/UTC'",
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "access_log",
        "timestamp",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="timestamp at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "base_record",
        "created_on",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="created_on at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "base_record",
        "modified_on",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="modified_on at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "compute_manager",
        "created_on",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="created_on at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "compute_manager",
        "modified_on",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="modified_on at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "compute_manager_log",
        "timestamp",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="timestamp at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "internal_error_log",
        "error_date",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="error_date at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "internal_jobs",
        "added_date",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="added_date at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "internal_jobs",
        "scheduled_date",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="scheduled_date at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "internal_jobs",
        "started_date",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="started_date at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "internal_jobs",
        "last_updated",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="last_updated at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "internal_jobs",
        "ended_date",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="ended_date at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "record_comment",
        "timestamp",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="timestamp at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "record_compute_history",
        "modified_on",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="modified_on at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "record_info_backup",
        "modified_on",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="modified_on at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "server_stats_log",
        "timestamp",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="timestamp at time zone 'Etc/UTC'",
    )
    op.alter_column(
        "server_stats_metadata",
        "date_value",
        type_=sa.TIMESTAMP(timezone=False),
        postgresql_using="date_value at time zone 'Etc/UTC'",
    )
