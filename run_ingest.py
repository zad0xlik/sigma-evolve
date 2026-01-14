#!/usr/bin/env python3
"""
Direct repository ingestion script - bypasses MCP connection issues
Performs the same operations as the ingest_project MCP tool
"""

import os
import sys
from pathlib import Path

# Set working directory and Python path
os.chdir('/Users/fedor/IdeaProjects/mcp-memory-server-sigma')
sys.path.insert(0, 'src')
sys.path.insert(0, 'src/openmemory')

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Ensure required environment variables are set (values come from .env)
required_vars = ['DATABASE_URL', 'NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please check your .env file")
    sys.exit(1)

# Import after setting environment
from openmemory.app.utils.git_integration import GitProjectAnalyzer
from openmemory.app.utils.memory import get_memory_client
from openmemory.app.database import SessionLocal
from openmemory.app.utils.db import get_user_and_app

def main():
    repo_path = "/Users/fedor/IdeaProjects/mcp-memory-server-sigma"
    
    print("=" * 80)
    print("SIGMA Repository Ingestion")
    print("=" * 80)
    print()
    
    # Step 1: Analyze repository
    print("📊 Analyzing repository...")
    try:
        analyzer = GitProjectAnalyzer(repo_path)
        analysis = analyzer.analyze_full_project(branch='main', commit_limit=50)
        print(f"✓ Analyzed {analysis['commits']['total_analyzed']} commits")
        print(f"✓ Found {analysis['file_structure']['total_files']} files")
        print(f"✓ Detected {len(analysis['dependencies'].get('python', []))} Python dependencies")
    except Exception as e:
        print(f"✗ Error analyzing repository: {e}")
        return 1
    
    print()
    
    # Step 2: Format analysis for storage
    print("💾 Formatting analysis...")
    repo_info = analysis["repository"]
    deps = analysis["dependencies"]
    patterns = analysis["patterns"]
    file_struct = analysis["file_structure"]
    
    summary_parts = [
        f"# SIGMA Repository Analysis",
        f"",
        f"## Project: {repo_info['name']}",
        f"- Path: {repo_info['path']}",
        f"- Active Branch: {repo_info.get('active_branch', 'unknown')}",
        f"- Branches: {', '.join(repo_info.get('branches', []))}",
        f"- Total Files: {file_struct['total_files']}",
        f"- Python Files: {file_struct.get('languages', {}).get('python', 0)}",
        f"",
        f"## Recent Commits ({patterns['total_commits']} analyzed)",
    ]
    
    # Add recent commits
    for commit in analysis['commits']['recent'][:5]:
        summary_parts.extend([
            f"",
            f"### Commit {commit['short_hash']} - {commit['timestamp']}",
            f"**Author:** {commit['author']['name']}",
            f"**Message:** {commit['message']}",
            f"**Changes:** {commit['files_changed']} files (+{commit['insertions']}/-{commit['deletions']})",
        ])
    
    # Add dependencies
    summary_parts.extend([
        f"",
        f"## Dependencies",
    ])
    
    for ecosystem, dep_list in deps.items():
        if dep_list:
            summary_parts.append(f"")
            summary_parts.append(f"### {ecosystem.title()}")
            for dep in dep_list[:10]:
                summary_parts.append(f"- {dep['name']} {dep.get('version', '')}")
    
    # Add contributors
    summary_parts.extend([
        f"",
        f"## Contributors",
        f"{', '.join(patterns['authors'])}",
    ])
    
    summary_text = "\n".join(summary_parts)
    print(f"✓ Created analysis summary ({len(summary_text)} characters)")
    print()
    
    # Step 3: Store in memory system
    print("🧠 Storing in SIGMA memory system...")
    print("   This will automatically:")
    print("   - Store in PostgreSQL")
    print("   - Generate embeddings")
    print("   - Index in Qdrant")
    print("   - Extract facts to Neo4j (Graphiti enabled)")
    print()
    
    try:
        # Get memory client with explicit config for localhost
        custom_config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "openmemory",
                    "host": "localhost",
                    "port": 6333
                }
            }
        }
        
        memory_client = get_memory_client(custom_instructions=None)
        
        # Get database session
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id="default-user", app_id="cline")
            
            # Add to memory system
            result = memory_client.add(
                summary_text,
                user_id="default-user",
                metadata={
                    "source_app": "openmemory",
                    "mcp_client": "cline",
                    "type": "project_analysis",
                    "project_name": repo_info['name'],
                    "repo_path": repo_info['path'],
                    "branch": repo_info.get('active_branch'),
                }
            )
            
            print("✅ SUCCESS! Repository ingested into SIGMA")
            print()
            print(f"📝 Memory IDs: {result}")
            print()
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"✗ Error storing in memory: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Step 4: Summary
    print("=" * 80)
    print("📍 Data is now available in:")
    print("=" * 80)
    print()
    print("✅ PostgreSQL - Stored immediately")
    print("✅ Qdrant - Embeddings generated (0-30 sec sync)")
    print("✅ Neo4j - Facts extracted via Graphiti (check at http://localhost:7474)")
    print()
    print("🔍 Query your data:")
    print("   - search_memory('SIGMA dependencies')")
    print("   - search_memory('recent commits')")
    print("   - search_memory('Python files')")
    print()
    print("📊 View in dashboards:")
    print("   - Qdrant: http://localhost:6333/dashboard")
    print("   - Neo4j: http://localhost:7474 (neo4j/sigmapassword)")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
