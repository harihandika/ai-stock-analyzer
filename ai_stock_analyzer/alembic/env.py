"""
Alembic Migration Environment Configuration
Mengkonfigurasi Alembic agar menggunakan settings dari aplikasi (SYNC_DATABASE_URL)
dan mengimpor semua model ORM agar auto-detection migrasi bisa bekerja.
"""

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---- Tambahkan root proyek ke sys.path ----
# Ini memungkinkan Alembic mengimpor modul dari folder 'app/'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- Import Settings & Models ----
from app.core.config import settings
from app.infrastructure.database import Base

# Import SEMUA model agar Base.metadata mengetahui semua tabel
# Alembic menggunakan metadata ini untuk mendeteksi perubahan schema
from app.domain.models.models import (
    User,
    Stock,
    DailyPrice,
    TechnicalIndicator,
    AIAnalysis,
    Watchlist,
)

# ---- Konfigurasi Alembic ----
config = context.config

# Intepretasi file log dari alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url menggunakan SYNC_DATABASE_URL dari settings
# (Alembic membutuhkan sync driver, tidak bisa menggunakan asyncpg)
config.set_main_option("sqlalchemy.url", settings.SYNC_DATABASE_URL)

# Target metadata untuk auto-detect migrasi
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Jalankan migrasi dalam mode 'offline'.
    Menghasilkan SQL script tanpa koneksi DB aktual.
    Berguna untuk: review SQL, staging deployment.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,     # Deteksi perubahan tipe kolom
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Jalankan migrasi dalam mode 'online'.
    Terhubung langsung ke database dan menjalankan migration DDL.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Jangan pool koneksi di migration
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
