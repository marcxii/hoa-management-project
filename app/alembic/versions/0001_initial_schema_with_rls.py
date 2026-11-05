"""initial schema with row-level security

Revision ID: 0001
Revises:
Create Date: 2026-11-05

Creates every application table and, immediately after each one, enables
row-level security and installs a policy tying it to the Postgres session
setting `app.tenant_id`. The app sets that value once per transaction (see
hoa.db.session.get_db); this migration is what makes Postgres actually
enforce it.

Grants on these tables go to `hoa_app` — a role that must already exist and
must NOT own these tables (ownership bypasses RLS). Role creation itself is
deliberately NOT done here: it's one-time database bootstrap, handled by
infra/postgres/init.sql, which Postgres runs automatically on first start.
This migration runs as `hoa_migrator`, the owning role.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables in dependency order — also the order RLS/grants are applied in.
_TENANT_SCOPED_TABLES = [
    "properties",
    "units",
    "residents",
    "users",
    "invoices",
    "payments",
    "work_orders",
]


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {table}_tenant_isolation ON {table}
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """
    )


def upgrade() -> None:
    op.create_table(
        "properties",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("address_line1", sa.String(), nullable=False),
        sa.Column("address_line2", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("postal_code", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_properties"),
    )
    op.create_index("ix_properties_tenant_id", "properties", ["tenant_id"])

    op.create_table(
        "units",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("property_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("unit_number", sa.String(), nullable=False),
        sa.Column("square_feet", sa.Integer(), nullable=True),
        sa.Column("bedrooms", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["property_id"], ["properties.id"], name="fk_units_property_id_properties", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_units"),
    )
    op.create_index("ix_units_tenant_id", "units", ["tenant_id"])
    op.create_index("ix_units_property_id", "units", ["property_id"])

    op.create_table(
        "residents",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("unit_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("is_owner", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("move_in_date", sa.Date(), nullable=True),
        sa.Column("move_out_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["unit_id"], ["units.id"], name="fk_residents_unit_id_units", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_residents"),
    )
    op.create_index("ix_residents_tenant_id", "residents", ["tenant_id"])
    op.create_index("ix_residents_unit_id", "residents", ["unit_id"])

    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("admin", "board_member", "resident", name="user_role"),
            nullable=False,
        ),
        sa.Column("resident_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["resident_id"], ["residents.id"], name="fk_users_resident_id_residents", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "invoices",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("unit_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("unpaid", "partial", "paid", "void", name="invoice_status"),
            nullable=False,
            server_default="unpaid",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["unit_id"], ["units.id"], name="fk_invoices_unit_id_units", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_invoices"),
    )
    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])
    op.create_index("ix_invoices_unit_id", "invoices", ["unit_id"])

    op.create_table(
        "payments",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("invoice_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "method",
            postgresql.ENUM("check", "ach", "card", "cash", "other", name="payment_method"),
            nullable=False,
        ),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["invoices.id"], name="fk_payments_invoice_id_invoices", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
    )
    op.create_index("ix_payments_tenant_id", "payments", ["tenant_id"])
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])

    op.create_table(
        "work_orders",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("unit_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("requested_by_resident_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("open", "in_progress", "completed", "cancelled", name="work_order_status"),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "priority",
            postgresql.ENUM("low", "medium", "high", "urgent", name="work_order_priority"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("assigned_to", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["unit_id"], ["units.id"], name="fk_work_orders_unit_id_units", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_resident_id"],
            ["residents.id"],
            name="fk_work_orders_requested_by_resident_id_residents",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_work_orders"),
    )
    op.create_index("ix_work_orders_tenant_id", "work_orders", ["tenant_id"])
    op.create_index("ix_work_orders_unit_id", "work_orders", ["unit_id"])

    for table in _TENANT_SCOPED_TABLES:
        _enable_rls(table)

    op.execute("GRANT USAGE ON SCHEMA public TO hoa_app")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {', '.join(_TENANT_SCOPED_TABLES)} TO hoa_app")


def downgrade() -> None:
    for table in reversed(_TENANT_SCOPED_TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")

    op.drop_table("work_orders")
    op.drop_table("payments")
    op.drop_table("invoices")
    op.drop_table("users")
    op.drop_table("residents")
    op.drop_table("units")
    op.drop_table("properties")

    for enum_name in ("work_order_priority", "work_order_status", "payment_method", "invoice_status", "user_role"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
