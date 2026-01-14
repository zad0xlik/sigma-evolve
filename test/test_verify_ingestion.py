#!/usr/bin/env python3
"""
Verification script to check if repository data was successfully stored
in PostgreSQL, Qdrant, and Neo4j after ingestion.
"""

import sys
import os
from pathlib import Path

# Add project root to path (same as run_ingest.py)
sys.path.insert(0, 'src')
sys.path.insert(0, 'src/openmemory')

# Set environment variables
from dotenv import load_dotenv
load_dotenv()

# Ensure required environment variables are set (values come from .env)
required_vars = ['DATABASE_URL', 'NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please check your .env file")
    sys.exit(1)

print("=" * 60)
print("SIGMA INGESTION VERIFICATION")
print("=" * 60)

# 1. Check PostgreSQL
print("\n1. CHECKING POSTGRESQL...")
try:
    # Import with proper absolute path
    import openmemory.app.database as database_module
    import openmemory.app.models as models_module
    from sqlalchemy import func
    
    db = next(database_module.get_db())
    
    # Get total memory count
    total_memories = db.query(func.count(models_module.Memory.id)).scalar()
    print(f"   ✓ Total memories in PostgreSQL: {total_memories}")
    
    # Get recent memories (last 10)
    recent_memories = db.query(models_module.Memory).order_by(models_module.Memory.created_at.desc()).limit(10).all()
    
    if recent_memories:
        print(f"   ✓ Most recent memory:")
        latest = recent_memories[0]
        print(f"      - ID: {latest.id}")
        print(f"      - Created: {latest.created_at}")
        print(f"      - Text preview: {latest.content[:100]}...")
        
        # Check for repository-related memories
        repo_memories = db.query(models_module.Memory).filter(
            models_module.Memory.content.contains('mcp-memory-server-sigma')
        ).count()
        print(f"   ✓ Memories mentioning 'mcp-memory-server-sigma': {repo_memories}")
    
    db.close()
    
except Exception as e:
    print(f"   ✗ Error checking PostgreSQL: {e}")

# 2. Check Qdrant
print("\n2. CHECKING QDRANT...")
try:
    from qdrant_client import QdrantClient
    import json
    
    # Load config
    with open('src/openmemory/config.json', 'r') as f:
        config = json.load(f)
    
    qdrant_config = config['mem0']['vector_store']['config']
    client = QdrantClient(
        host=qdrant_config['host'],
        port=qdrant_config['port']
    )
    
    collection_name = qdrant_config['collection_name']
    
    # Get collection info
    collection_info = client.get_collection(collection_name)
    print(f"   ✓ Collection: {collection_name}")
    print(f"   ✓ Total vectors: {collection_info.points_count}")
    print(f"   ✓ Vector size: {collection_info.config.params.vectors.size}")
    
    # Search for repository-related content
    if collection_info.points_count > 0:
        # Try to scroll through points to find repo-related content
        points, _ = client.scroll(
            collection_name=collection_name,
            limit=10,
            with_payload=True
        )
        
        repo_related = 0
        for point in points:
            payload_str = str(point.payload)
            if 'mcp-memory-server' in payload_str.lower() or 'sigma' in payload_str.lower():
                repo_related += 1
        
        print(f"   ✓ Points with repo-related content (sampled): {repo_related}/{len(points)}")
    
except Exception as e:
    print(f"   ✗ Error checking Qdrant: {e}")

# 3. Check Neo4j (if Graphiti enabled)
print("\n3. CHECKING NEO4J / GRAPHITI...")
driver = None
try:
    graphiti_enabled = os.getenv('GRAPHITI_ENABLED', 'false').lower() == 'true'
    
    if not graphiti_enabled:
        print("   ⚠ Graphiti is not enabled")
    else:
        from neo4j import GraphDatabase
        
        neo4j_uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD', 'password')
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        with driver.session() as session:
            # Count total nodes
            result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = result.single()['count']
            print(f"   ✓ Total nodes in Neo4j: {node_count}")
            
            # Count total relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()['count']
            print(f"   ✓ Total relationships: {rel_count}")
            
            # Check for repository-related entities (fixed query)
            result = session.run("""
                MATCH (n)
                WHERE toLower(coalesce(n.name, '')) CONTAINS 'mcp-memory' 
                   OR toLower(coalesce(n.name, '')) CONTAINS 'sigma'
                   OR toLower(coalesce(n.summary, '')) CONTAINS 'repository'
                   OR ANY(label IN labels(n) WHERE toLower(label) CONTAINS 'repository')
                RETURN count(n) as count
            """)
            repo_nodes = result.single()['count']
            print(f"   ✓ Repository-related nodes: {repo_nodes}")
            
            # Show sample entities
            result = session.run("""
                MATCH (n)
                RETURN labels(n) as labels, n.name as name
                LIMIT 5
            """)
            print("   ✓ Sample entities:")
            for record in result:
                labels = record['labels']
                name = record['name'] if record['name'] else 'unnamed'
                print(f"      - {labels}: {name}")
        
        # Properly close driver before script ends
        if driver:
            driver.close()
            driver = None
        
except Exception as e:
    print(f"   ✗ Error checking Neo4j: {e}")
finally:
    # Ensure driver is closed even if there's an error
    if driver:
        try:
            driver.close()
        except:
            pass  # Ignore cleanup errors during shutdown

# 4. Summary
print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
print("\nTo manually inspect the data:")
print("  • PostgreSQL: Use psql or a DB client on localhost:5432")
print("  • Qdrant: Visit http://localhost:6333/dashboard")
print("  • Neo4j: Visit http://localhost:7474/browser")
print("=" * 60)
