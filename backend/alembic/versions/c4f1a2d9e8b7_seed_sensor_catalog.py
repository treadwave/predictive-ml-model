"""seed sensor catalog

Revision ID: c4f1a2d9e8b7
Revises: e74d5734bc65
Create Date: 2026-11-05 01:50:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c4f1a2d9e8b7'
down_revision: str | Sequence[str] | None = 'e74d5734bc65'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

sensor_catalog = sa.table(
    'sensor_catalog',
    sa.column('code', sa.Text),
    sa.column('name', sa.Text),
    sa.column('unit', sa.Text),
    sa.column('is_used', sa.Boolean),
)

SENSORS = [
    ('s1', 'T2 — температура на входе вентилятора', '°R', False),
    ('s2', 'T24 — температура на выходе КНД', '°R', True),
    ('s3', 'T30 — температура на выходе КВД', '°R', True),
    ('s4', 'T50 — температура на выходе ТНД', '°R', True),
    ('s5', 'P2 — давление на входе вентилятора', 'psia', False),
    ('s6', 'P15 — давление в байпасном канале', 'psia', False),
    ('s7', 'P30 — давление на выходе КВД', 'psia', True),
    ('s8', 'Nf — физ. скорость вентилятора', 'об/мин', True),
    ('s9', 'Nc — физ. скорость ядра', 'об/мин', True),
    ('s10', 'epr — степень повышения давления', None, False),
    ('s11', 'Ps30 — статическое давление на выходе КВД', 'psia', True),
    ('s12', 'phi — расход топлива / Ps30', 'pps/psia', True),
    ('s13', 'NRf — приведённая скорость вентилятора', 'об/мин', True),
    ('s14', 'NRc — приведённая скорость ядра', 'об/мин', True),
    ('s15', 'BPR — степень двухконтурности', None, True),
    ('s16', 'farB — топливо/воздух в камере сгорания', None, False),
    ('s17', 'htBleed — энтальпия отбора', None, True),
    ('s18', 'Nf_dmd — заданная скорость вентилятора', 'об/мин', False),
    ('s19', 'PCNfR_dmd — заданная приведённая скорость', 'об/мин', False),
    ('s20', 'W31 — охлаждающий отбор ТВД', 'lbm/s', True),
    ('s21', 'W32 — охлаждающий отбор ТНД', 'lbm/s', True),
]


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(sensor_catalog, [
        {'code': code, 'name': name, 'unit': unit, 'is_used': is_used}
        for code, name, unit, is_used in SENSORS
    ])


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sensor_catalog.delete())
