"""Managed accounts: logins, roles, revocable tokens and login throttling.

Revision ID: b48a001
Revises: 1395cb8114bd
"""
import sqlalchemy as sa
from alembic import op

revision = "b48a001"
down_revision = "1395cb8114bd"
branch_labels = None
depends_on = None


def upgrade():
    # This deployment has no existing accounts. Do not silently convert real emails.
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM users)")).scalar():
        raise RuntimeError("Managed-account migration requires an empty users table; existing accounts need an explicit migration plan.")
    op.drop_constraint("users_email_key", "users", type_="unique")
    op.alter_column("users", "email", new_column_name="login", type_=sa.String(64), existing_type=sa.Text())
    op.create_unique_constraint("users_login_key", "users", ["login"])
    op.add_column("users", sa.Column("role", sa.String(16), nullable=False, server_default="employee"))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    op.create_check_constraint("users_role_check", "users", "role IN ('admin', 'employee')")
    op.create_check_constraint("users_login_check", "users", "login ~ '^[a-z0-9._-]{3,64}$'")
    op.create_table("login_attempts",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_login_attempts_expires_at", "login_attempts", ["expires_at"])


def downgrade():
    op.drop_table("login_attempts")
    op.drop_constraint("users_login_check", "users", type_="check")
    op.drop_constraint("users_role_check", "users", type_="check")
    op.drop_column("users", "token_version")
    op.drop_column("users", "is_active")
    op.drop_column("users", "role")
    op.drop_constraint("users_login_key", "users", type_="unique")
    op.alter_column("users", "login", new_column_name="email", type_=sa.Text(), existing_type=sa.String(64))
    op.create_unique_constraint("users_email_key", "users", ["email"])
