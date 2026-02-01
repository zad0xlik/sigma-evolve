#!/usr/bin/env python3
"""
Test script to insert and retrieve data from the PostgreSQL agent tables.

This script verifies that the database rebuild was successful by:
1. Inserting sample data into all agent tables
2. Retrieving and displaying the data
3. Verifying relationships and constraints work correctly
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class DatabaseTester:
    """Test PostgreSQL database with sample data."""

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        # Parse database URL
        import re
        match = re.match(r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", self.database_url)
        if not match:
            raise ValueError(f"Invalid DATABASE_URL format: {self.database_url}")
        
        self.db_user, self.db_password, self.db_host, self.db_port, self.db_name = match.groups()
        self.db_port = int(self.db_port)

    def get_connection(self):
        """Get PostgreSQL connection."""
        return psycopg2.connect(
            host=self.db_host,
            port=self.db_port,
            user=self.db_user,
            password=self.db_password,
            dbname=self.db_name
        )

    def insert_test_data(self):
        """Insert sample data into all tables."""
        print("Inserting test data...")
        print()
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # 1. Insert Project
                print("1. Inserting project...")
                cursor.execute("""
                    INSERT INTO projects (repo_url, branch, workspace_path, language, framework, domain)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING project_id
                """, (
                    "https://github.com/user/sigma-project",
                    "main",
                    "/tmp/sigma-workspace/sigma-project",
                    "Python",
                    "FastAPI",
                    "AI/ML Agent System"
                ))
                project_id = cursor.fetchone()[0]
                print(f"   ✓ Created project (ID: {project_id})")
                
                # 2. Insert Code Snapshot
                print("2. Inserting code snapshot...")
                cursor.execute("""
                    INSERT INTO code_snapshots (
                        project_id, complexity, test_coverage, issues_found, metrics_json,
                        graph_entity_count, graphiti_episode_id, indexed_at, qdrant_point_ids
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING snapshot_id
                """, (
                    project_id,
                    7.5,
                    0.85,
                    3,
                    '{"functions": 45, "classes": 12, "lines": 1250}',
                    15,
                    "episode_abc123",
                    datetime.now(timezone.utc),
                    '["point_1", "point_2", "point_3"]'
                ))
                snapshot_id = cursor.fetchone()[0]
                print(f"   ✓ Created code snapshot (ID: {snapshot_id})")
                
                # 3. Insert Proposal
                print("3. Inserting proposal...")
                cursor.execute("""
                    INSERT INTO proposals (
                        project_id, title, description, agents_json, changes_json,
                        confidence, critic_score, status, pr_url, commit_sha
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING proposal_id
                """, (
                    project_id,
                    "Refactor analysis worker for better performance",
                    "Improve the analysis worker by implementing parallel processing",
                    '[{"agent": "architect", "score": 0.9, "reason": "Good approach"}, {"agent": "reviewer", "score": 0.85, "reason": "Solid plan"}]',
                    '{"files": ["src/openmemory/app/agents/analysis_worker.py"], "changes": ["Add thread pool", "Optimize queries"]}',
                    0.87,
                    0.82,
                    "pending",
                    "https://github.com/user/sigma-project/pull/42",
                    None
                ))
                proposal_id = cursor.fetchone()[0]
                print(f"   ✓ Created proposal (ID: {proposal_id})")
                
                # 4. Insert Experiment
                print("4. Inserting experiment...")
                cursor.execute("""
                    INSERT INTO experiments (
                        project_id, worker_name, experiment_name, hypothesis, approach,
                        metrics, risk_level, rollback_plan, status, baseline_metrics,
                        result_metrics, outcome_json, success, improvement,
                        promoted_to_production, started_at, completed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING experiment_id
                """, (
                    project_id,
                    "analysis",
                    "Parallel Processing Test",
                    "Using thread pool will improve analysis speed by 40%",
                    "Implemented ThreadPoolExecutor with 4 workers",
                    '["execution_time", "memory_usage", "accuracy"]',
                    "medium",
                    "Revert to sequential processing",
                    "completed",
                    '{"execution_time": 120.5, "memory_usage": 512, "accuracy": 0.92}',
                    '{"execution_time": 72.3, "memory_usage": 640, "accuracy": 0.94}',
                    '{"improvement": 40, "notes": "Successfully reduced processing time"}',
                    True,
                    40.0,
                    True,
                    datetime.now(timezone.utc),
                    datetime.now(timezone.utc)
                ))
                experiment_id = cursor.fetchone()[0]
                print(f"   ✓ Created experiment (ID: {experiment_id})")
                
                # 5. Insert Learned Pattern
                print("5. Inserting learned pattern...")
                cursor.execute("""
                    INSERT INTO learned_patterns (
                        pattern_name, pattern_type, description, code_template,
                        language, framework, domain, confidence, success_count, failure_count
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING pattern_id
                """, (
                    "Async Task Processing",
                    "optimize",
                    "Use asyncio and ThreadPoolExecutor for CPU-bound tasks",
                    """from concurrent.futures import ThreadPoolExecutor
import asyncio

async def process_tasks_async(tasks, max_workers=4):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return await asyncio.gather(*[
            loop.run_in_executor(executor, process_task, task)
            for task in tasks
        ])""",
                    "Python",
                    "FastAPI",
                    "AI/ML Backend",
                    0.88,
                    12,
                    2
                ))
                pattern_id = cursor.fetchone()[0]
                print(f"   ✓ Created learned pattern (ID: {pattern_id})")
                
                # 6. Insert Cross-Project Learning
                print("6. Inserting cross-project learning...")
                cursor.execute("""
                    INSERT INTO cross_project_learnings (
                        source_project_id, target_project_id, pattern_id, similarity_score,
                        applied, applied_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING learning_id
                """, (
                    project_id,
                    project_id,
                    pattern_id,
                    0.85,
                    True,
                    datetime.now(timezone.utc)
                ))
                learning_id = cursor.fetchone()[0]
                print(f"   ✓ Created cross-project learning (ID: {learning_id})")
                
                # 7. Insert Worker Stats
                print("7. Inserting worker stats...")
                cursor.execute("""
                    INSERT INTO worker_stats (
                        worker_name, cycles_run, experiments_run, total_time, errors, last_run
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING stat_id
                """, (
                    "analysis",
                    145,
                    8,
                    18600.5,
                    12,
                    datetime.now(timezone.utc)
                ))
                stat_id = cursor.fetchone()[0]
                print(f"   ✓ Created worker stats (ID: {stat_id})")
                
                conn.commit()
                print()
                print("✓ All test data inserted successfully!")
                print()
                
                return project_id

    def retrieve_test_data(self, project_id):
        """Retrieve and display test data."""
        print("Retrieving test data...")
        print()
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Retrieve project
                print("1. Project:")
                cursor.execute("SELECT * FROM projects WHERE project_id = %s", (project_id,))
                row = cursor.fetchone()
                print(f"   ID: {row[0]}")
                print(f"   Repo: {row[1]}")
                print(f"   Language: {row[4]}, Framework: {row[5]}, Domain: {row[6]}")
                print(f"   Created: {row[7]}")
                print()
                
                # Retrieve code snapshot
                print("2. Code Snapshot:")
                cursor.execute("SELECT * FROM code_snapshots WHERE project_id = %s", (project_id,))
                row = cursor.fetchone()
                print(f"   ID: {row[0]}")
                print(f"   Complexity: {row[2]}, Coverage: {row[3]}")
                print(f"   Graph Entities: {row[7]}, Episode: {row[8]}")
                print(f"   Created: {row[5]}")
                print()
                
                # Retrieve proposal
                print("3. Proposal:")
                cursor.execute("SELECT * FROM proposals WHERE project_id = %s", (project_id,))
                row = cursor.fetchone()
                print(f"   ID: {row[0]}")
                print(f"   Title: {row[2]}")
                print(f"   Confidence: {row[6]}, Status: {row[8]}")
                print()
                
                # Retrieve experiment
                print("4. Experiment:")
                cursor.execute("SELECT * FROM experiments WHERE project_id = %s", (project_id,))
                row = cursor.fetchone()
                print(f"   ID: {row[0]}")
                print(f"   Name: {row[2]}")
                print(f"   Worker: {row[2]}, Success: {row[12]}")
                print(f"   Improvement: {row[13]}%")
                print()
                
                # Retrieve learned pattern
                print("5. Learned Pattern:")
                cursor.execute("SELECT * FROM learned_patterns WHERE pattern_id = (SELECT pattern_id FROM cross_project_learnings WHERE target_project_id = %s LIMIT 1)", (project_id,))
                row = cursor.fetchone()
                print(f"   ID: {row[0]}")
                print(f"   Name: {row[1]}")
                print(f"   Type: {row[2]}")
                print(f"   Confidence: {row[7]}, Success Count: {row[8]}")
                print()
                
                # Retrieve cross-project learning
                print("6. Cross-Project Learning:")
                cursor.execute("SELECT * FROM cross_project_learnings WHERE target_project_id = %s", (project_id,))
                row = cursor.fetchone()
                print(f"   ID: {row[0]}")
                print(f"   Similarity: {row[4]}")
                print(f"   Applied: {row[5]}")
                print()
                
                # Retrieve worker stats
                print("7. Worker Stats:")
                cursor.execute("SELECT * FROM worker_stats WHERE worker_name = 'analysis'")
                row = cursor.fetchone()
                print(f"   ID: {row[0]}")
                print(f"   Worker: {row[1]}")
                print(f"   Cycles: {row[2]}, Experiments: {row[3]}")
                print(f"   Errors: {row[5]}")
                print()
                
                print("✓ All data retrieved successfully!")

    def verify_constraints(self):
        """Verify foreign key constraints and indexes."""
        print("Verifying constraints and indexes...")
        print()
        
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Check foreign key constraints
                print("1. Foreign Key Constraints:")
                cursor.execute("""
                    SELECT
                        tc.table_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = 'public'
                    ORDER BY tc.table_name
                """)
                
                fks = cursor.fetchall()
                for fk in fks:
                    print(f"   {fk[0]}.{fk[1]} -> {fk[2]}.{fk[3]}")
                print()
                
                # Check indexes
                print("2. Indexes:")
                cursor.execute("""
                    SELECT
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    AND tablename IN (
                        'projects', 'code_snapshots', 'proposals', 'experiments',
                        'learned_patterns', 'cross_project_learnings', 'worker_stats'
                    )
                    ORDER BY tablename, indexname
                """)
                
                indexes = cursor.fetchall()
                for idx in indexes:
                    print(f"   {idx[0]}: {idx[1]}")
                print()
                
                print("✓ Constraints and indexes verified!")

    def test_database(self):
        """Run complete database test."""
        print("=" * 70)
        print("PostgreSQL Database Test for SIGMA Agent System")
        print("=" * 70)
        print()
        
        try:
            # Test connection
            print("Testing database connection...")
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]
                    print(f"✓ Connected successfully!")
                    print(f"  PostgreSQL version: {version[:50]}...")
            print()
            
            # Insert test data
            project_id = self.insert_test_data()
            
            # Retrieve test data
            self.retrieve_test_data(project_id)
            
            # Verify constraints
            self.verify_constraints()
            
            print()
            print("=" * 70)
            print("✓ All tests passed! Database is working correctly.")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"\n✗ Test failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point."""
    tester = DatabaseTester()
    success = tester.test_database()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
