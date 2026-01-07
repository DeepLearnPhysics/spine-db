#!/usr/bin/env python3
"""Helper script to initialize the database schema."""

import argparse
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from spine_db.schema import create_tables, get_engine


def setup_schema(argv=None):
    """Set up the database schema."""
    parser = argparse.ArgumentParser(description="Initialize SPINE database schema")
    parser.add_argument(
        "--db",
        type=str,
        help="Database URL (overrides DATABASE_URL environment variable)",
    )
    args = parser.parse_args(argv)

    # Load environment variables
    load_dotenv()

    # Get database URL
    db_url = args.db or os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: No database URL provided.", file=sys.stderr)
        print(
            "Either set DATABASE_URL in .env file or use --db flag",
            file=sys.stderr,
        )
        sys.exit(1)

    # Mask password for display
    u = make_url(db_url)
    display_url = u._replace(password="***")
    print(f"Setting up database at: {display_url}")

    # Setup database
    try:
        engine = get_engine(db_url)
        create_tables(engine)
        print("✓ Database tables created successfully!")

        # List tables (SQLAlchemy 2.0+ compatible)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✓ Tables: {', '.join(tables)}")
    except Exception as e:
        print(f"✗ Failed to create tables: {e}", file=sys.stderr)
        sys.exit(1)
