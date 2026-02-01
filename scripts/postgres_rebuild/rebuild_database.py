#!/usr/bin/env python3
"""
PostgreSQL Database Rebuild Script

This script automatically rebuilds the PostgreSQL database for the SIGMA agent system.
It checks if the database exists, optionally drops and recreates it based on the
POSTGRES_OVERWRITE_DB environment variable, and creates all agent tables.

Usage:
    python rebuild_database.py

Environment Variables:
    DATABASE_URL - PostgreSQL connection string (e.g., postgresql://user:pass@host:port/db)
    POSTGRES_OVERWRITE_DB - If true, drop and recreate the database (default: false)
    POSTGRES_USER - PostgreSQL username (for database creation)
    POSTGRES_PASSWORD - PostgreSQL password (for database creation)
    POSTGRES_DB - Database name (extracted from DATABASE_URL if not set)

Features:
    - Checks if database exists
    - Optionally drops and recreates database based on POSTGRES_OVERWRITE_DB flag
    - Creates all 7 agent tables from SQL schema files
    - Updates alembic_version table to mark migration as applied
    - Provides detailed logging
"""

import os
import sys
import time
from pathlib import Path
from typing import Tuple

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class DatabaseRebuilder:
    """PostgreSQL database rebuilder for SIGMA agent system."""

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.overwrite_db = os.getenv("POSTGRES_OVERWRITE_DB", "false").lower() == "true"
        
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        # Parse database URL
        self.db_user, self.db_password, self.db_host, self.db_port, self.db_name = self.parse_database_url()
        
        # Schema files directory
        self.schema_dir = Path(__file__).parent
        
        # Log configuration
        print(f"Database Configuration:")
        print(f"  Host: {self.db_host}")
        print(f"  Port: {self.db_port}")
        print(f"  Database: {self.db_name}")
        print(f"  User: {self.db_user}")
        print(f"  Overwrite: {self.overwrite_db}")
        print()

    def parse_database_url(self) -> Tuple[str, str, str, int, str]:
        """Parse PostgreSQL connection URL."""
        # Format: postgresql://username:password@host:port/database
        import re
        
        match = re.match(r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", self.database_url)
        if not match:
            raise ValueError(f"Invalid DATABASE_URL format: {self.database_url}")
        
        return match.group(1), match.group(2), match.group(3), int(match.group(4)), match.group(5)

    def get_connection(self, dbname=None):
        """Get PostgreSQL connection."""
        connect_kwargs = {
            "host": self.db_host,
            "port": self.db_port,
            "user": self.db_user,
            "password": self.db_password,
        }
        if dbname:
            connect_kwargs["dbname"] = dbname
        
        return psycopg2.connect(**connect_kwargs)

    def database_exists(self) -> bool:
        """Check if database exists."""
        try:
            conn = self.get_connection(dbname="postgres")
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.db_name,))
            exists = cursor.fetchone() is not None
            cursor.close()
            conn.close()
            return exists
        except Exception as e:
            print(f"Error checking database existence: {e}")
            return False

    def create_database(self):
        """Create the database."""
        try:
            conn = self.get_connection(dbname="postgres")
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Create database with UTF-8 encoding
            cursor.execute(f'CREATE DATABASE "{self.db_name}" WITH ENCODING = \'UTF8\'')
            print(f"✓ Database '{self.db_name}' created successfully")
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"✗ Error creating database: {e}")
            raise

    def drop_database(self):
        """Drop the database."""
        try:
            conn = self.get_connection(dbname="postgres")
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Terminate existing connections
            cursor.execute(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid()
            """, (self.db_name,))
            
            # Drop database
            cursor.execute(f'DROP DATABASE IF EXISTS "{self.db_name}"')
            print(f"✓ Database '{self.db_name}' dropped successfully")
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"✗ Error dropping database: {e}")
            raise

    def run_sql_file(self, filepath):
        """Execute SQL from a file."""
        print(f"  Running: {filepath.name}")
        try:
            with self.get_connection(dbname=self.db_name) as conn:
                with conn.cursor() as cursor:
                    sql_content = filepath.read_text()
                    cursor.execute(sql_content)
                    conn.commit()
            print(f"    ✓ Success")
        except Exception as e:
            print(f"    ✗ Error: {e}")
            raise

    def update_alembic_version(self):
        """Update alembic_version table to mark migration as applied."""
        print("  Updating alembic_version table...")
        try:
            with self.get_connection(dbname=self.db_name) as conn:
                with conn.cursor() as cursor:
                    # Check if table exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = 'alembic_version'
                        )
                    """)
                    table_exists = cursor.fetchone()[0]
                    
                    if not table_exists:
                        # Create table if it doesn't exist
                        cursor.execute("""
                            CREATE TABLE alembic_version (
                                version_num VARCHAR(32) NOT NULL,
                                PRIMARY KEY (version_num)
                            )
                        """)
                        print("    ✓ Created alembic_version table")
                    
                    # Insert migration version
                    cursor.execute("""
                        INSERT INTO alembic_version (version_num)
                        VALUES (%s)
                        ON CONFLICT (version_num) DO NOTHING
                    """, ("migrate_agents_to_postgres",))
                    
                    conn.commit()
                    print("    ✓ Updated alembic_version with 'migrate_agents_to_postgres'")
        except Exception as e:
            print(f"    ✗ Error updating alembic_version: {e}")
            raise

    def rebuild(self):
        """Main rebuild process."""
        print("=" * 70)
        print("PostgreSQL Database Rebuild for SIGMA Agent System")
        print("=" * 70)
        print()
        
        # Check if database exists
        exists = self.database_exists()
        print(f"Database '{self.db_name}' exists: {exists}")
        print()
        
        if exists and self.overwrite_db:
            print("⚠️  POSTGRES_OVERWRITE_DB is true - dropping existing database...")
            self.drop_database()
            print()
            exists = False
        
        if not exists:
            print("Creating new database...")
            self.create_database()
            print()
        
        # Define schema files in dependency order
        schema_files = [
            "schema_projects.sql",
            "schema_code_snapshots.sql",
            "schema_proposals.sql",
            "schema_experiments.sql",
            "schema_learned_patterns.sql",
            "schema_cross_project_learnings.sql",
            "schema_worker_stats.sql",
        ]
        
        print("Creating tables...")
        for schema_file in schema_files:
            filepath = self.schema_dir / schema_file
            if not filepath.exists():
                print(f"  ✗ Schema file not found: {filepath}")
                continue
            self.run_sql_file(filepath)
            time.sleep(0.1)  # Small delay for readability
        print()
        
        # Update alembic_version
        self.update_alembic_version()
        print()
        
        # Verify tables were created
        print("Verifying tables...")
        try:
            with self.get_connection(dbname=self.db_name) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                        ORDER BY table_name
                    """)
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    expected_tables = [
                        "alembic_version",
                        "projects",
                        "code_snapshots",
                        "proposals",
                        "experiments",
                        "learned_patterns",
                        "cross_project_learnings",
                        "worker_stats",
                    ]
                    
                    missing = [t for t in expected_tables if t not in tables]
                    unexpected = [t for t in tables if t not in expected_tables and t != "alembic_version"]
                    
                    if missing:
                        print(f"  ✗ Missing tables: {missing}")
                    if unexpected:
                        print(f"  ⚠ Unexpected tables: {unexpected}")
                    
                    if not missing:
                        print(f"  ✓ All {len(expected_tables)} expected tables exist")
                        for table in tables:
                            print(f"    - {table}")
        except Exception as e:
            print(f"  ✗ Error verifying tables: {e}")
        
        print()
        print("=" * 70)
        print("Rebuild complete!")
        print("=" * 70)
        
        return True


def main():
    """Main entry point."""
    try:
        rebuilder = DatabaseRebuilder()
        rebuilder.rebuild()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Rebuild failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
