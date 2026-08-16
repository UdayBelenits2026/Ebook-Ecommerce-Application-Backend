import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import your models so all tables are registered
from app.models.domain import Base

# postgresql://ebookstore_gcag_user:ZCudA9apQoH4dD7dBbg4tocBhbql0lmX@dpg-da0tv0vlk1mc738pj8cg-a.oregon-postgres.render.com/ebookstore_gcag
# ---------------------------------------------------------
# SOURCE DATABASE
# ---------------------------------------------------------

SQLITE_URL = "sqlite:///./bookstore.db"

sqlite_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
)


# ---------------------------------------------------------
# TARGET DATABASE
# ---------------------------------------------------------

POSTGRES_URL = os.getenv("TARGET_DATABASE_URL")

if not POSTGRES_URL:
    print("ERROR: TARGET_DATABASE_URL environment variable is missing.")
    print()
    print("Set TARGET_DATABASE_URL to your Render PostgreSQL")
    print("EXTERNAL Database URL before running this script.")
    sys.exit(1)


# Convert normal PostgreSQL URL to psycopg driver URL
if POSTGRES_URL.startswith("postgresql://"):
    POSTGRES_URL = POSTGRES_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )


postgres_engine = create_engine(
    POSTGRES_URL,
    pool_pre_ping=True,
)


# ---------------------------------------------------------
# CONFIRMATION
# ---------------------------------------------------------

print("=" * 70)
print("SQLite → PostgreSQL Migration")
print("=" * 70)

print()
print("SOURCE:")
print("  SQLite: bookstore.db")

print()
print("TARGET:")
print("  Render PostgreSQL")

print()
print("WARNING:")
print("This migration will replace existing data in the")
print("TARGET PostgreSQL database.")

print()
confirmation = input("Type MIGRATE to continue: ")

if confirmation != "MIGRATE":
    print("Migration cancelled.")
    sys.exit(0)


# ---------------------------------------------------------
# CREATE TARGET TABLES
# ---------------------------------------------------------

print()
print("Creating PostgreSQL tables...")

Base.metadata.create_all(bind=postgres_engine)

print("✓ Tables created")


# ---------------------------------------------------------
# READ SQLITE TABLES
# ---------------------------------------------------------

metadata = Base.metadata

# SQLAlchemy returns tables in dependency order
tables = metadata.sorted_tables

print()
print("Tables to migrate:")

for table in tables:
    print(f"  - {table.name}")


# ---------------------------------------------------------
# CLEAR TARGET DATA
# ---------------------------------------------------------

print()
print("Clearing existing PostgreSQL data...")

with postgres_engine.begin() as connection:

    # PostgreSQL CASCADE handles foreign-key dependencies.
    for table in reversed(tables):
        connection.execute(
            text(
                f'TRUNCATE TABLE "{table.name}" '
                f'RESTART IDENTITY CASCADE'
            )
        )

print("✓ Existing PostgreSQL data cleared")


# ---------------------------------------------------------
# MIGRATE DATA
# ---------------------------------------------------------

print()
print("Starting data migration...")
print()

total_rows = 0

with sqlite_engine.connect() as source_connection:
    with postgres_engine.begin() as target_connection:

        for table in tables:

            table_name = table.name

            result = source_connection.execute(
                table.select()
            )

            rows = result.mappings().all()

            if not rows:
                print(f"{table_name:25} → 0 rows")
                continue

            # Convert SQLAlchemy RowMapping objects to dictionaries
            row_data = [dict(row) for row in rows]

            target_connection.execute(
                table.insert(),
                row_data
            )

            total_rows += len(row_data)

            print(
                f"{table_name:25} → {len(row_data)} rows"
            )


# ---------------------------------------------------------
# RESET POSTGRES SEQUENCES
# ---------------------------------------------------------

print()
print("Resetting PostgreSQL ID sequences...")

with postgres_engine.begin() as connection:

    for table in tables:

        # Only tables that have an integer primary key
        # need sequence synchronization.
        primary_keys = list(table.primary_key.columns)

        if len(primary_keys) != 1:
            continue

        primary_key = primary_keys[0]

        if str(primary_key.type).upper() != "INTEGER":
            continue

        table_name = table.name

        try:
            connection.execute(
                text(
                    f"""
                    SELECT setval(
                        pg_get_serial_sequence(
                            '"{table_name}"',
                            '{primary_key.name}'
                        ),
                        COALESCE(
                            (
                                SELECT MAX("{primary_key.name}")
                                FROM "{table_name}"
                            ),
                            1
                        ),
                        CASE
                            WHEN EXISTS (
                                SELECT 1
                                FROM "{table_name}"
                            )
                            THEN true
                            ELSE false
                        END
                    )
                    """
                )
            )
        except Exception as exc:
            print(
                f"  Sequence warning for {table_name}: {exc}"
            )


# ---------------------------------------------------------
# FINISHED
# ---------------------------------------------------------

print()
print("=" * 70)
print("MIGRATION COMPLETED")
print("=" * 70)
print()
print(f"Total rows migrated: {total_rows}")
print()
print("Your SQLite database was NOT modified.")
print("Your PostgreSQL database now contains the migrated data.")
print()