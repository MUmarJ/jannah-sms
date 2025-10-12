"""
Migration script to add SMS opt-in tracking fields to tenants table.
For A2P compliance with text-to-join functionality.

Run this migration with:
    python migrations/add_sms_opt_in_fields.py
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


def upgrade():
    """Add SMS opt-in tracking columns to tenants table."""
    db_path = settings.database_url.replace("sqlite:///", "")

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(tenants)")
        existing_columns = [row[1] for row in cursor.fetchall()]

        columns_to_add = [
            ("sms_opt_in_status", "VARCHAR(20) DEFAULT 'pending'"),
            ("sms_opt_in_date", "DATETIME"),
            ("sms_opt_out_date", "DATETIME"),
            ("initial_opt_in_message_sent", "BOOLEAN DEFAULT 0"),
            ("initial_opt_in_sent_date", "DATETIME"),
        ]

        for column_name, column_def in columns_to_add:
            if column_name not in existing_columns:
                print(f"Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE tenants ADD COLUMN {column_name} {column_def}")
            else:
                print(f"Column {column_name} already exists, skipping")

        conn.commit()
        print("✅ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


def downgrade():
    """
    Remove SMS opt-in tracking columns from tenants table.
    Note: SQLite doesn't support DROP COLUMN, so this creates a new table without the columns.
    """
    db_path = settings.database_url.replace("sqlite:///", "")

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("⚠️  Creating backup table...")
        cursor.execute("""
            CREATE TABLE tenants_backup AS
            SELECT id, name, contact, rent, due_date, building, tenant_type, active,
                   is_current_month_rent_paid, last_payment_date, late_fee_applicable,
                   notes, created_at, updated_at
            FROM tenants
        """)

        print("Dropping original table...")
        cursor.execute("DROP TABLE tenants")

        print("Recreating table without opt-in columns...")
        cursor.execute("ALTER TABLE tenants_backup RENAME TO tenants")

        conn.commit()
        print("✅ Downgrade completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"❌ Downgrade failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate SMS opt-in fields")
    parser.add_argument(
        "--downgrade",
        action="store_true",
        help="Remove opt-in fields (WARNING: data loss)"
    )

    args = parser.parse_args()

    if args.downgrade:
        confirm = input("⚠️  This will remove opt-in data. Type 'yes' to confirm: ")
        if confirm.lower() == "yes":
            downgrade()
        else:
            print("Downgrade cancelled")
    else:
        upgrade()
