"""create trips"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "trips",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.BigInteger, nullable=False),
        sa.Column("payment", sa.String(4), nullable=False),
        sa.Column("commission", sa.BigInteger, nullable=False),
        sa.CheckConstraint(
            "amount > 0 AND ended_at > started_at AND commission BETWEEN 0 AND amount",
            name="ck_trips_valid",
        ),
    )
    op.create_index("ix_trips_started_at", "trips", ["started_at"])


def downgrade():
    op.drop_table("trips")
