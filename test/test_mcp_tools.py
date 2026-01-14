#!/usr/bin/env python3
"""
test_mcp_tools.py - Test SIGMA MCP Tools

Simple script to test the MCP tools via SSE transport.

Usage:
    uv run test_mcp_tools.py
"""

# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp>=1.3.0",
#     "httpx",
# ]
# ///

import asyncio
import json
import httpx
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

# Configuration
MCP_SERVER_URL = "http://localhost:8000/mcp"
CLIENT_NAME = "test-client"
USER_ID = "test-user"

async def list_tools(session: ClientSession):
    """List all available MCP tools"""
    tools = await session.list_tools()
    print("\n📋 Available MCP Tools:")
    print("=" * 60)
    for tool in tools.tools:
        print(f"\n🔧 {tool.name}")
        print(f"   Description: {tool.description[:80]}..." if len(tool.description) > 80 else f"   Description: {tool.description}")
    return tools

async def call_tool(session: ClientSession, tool_name: str, arguments: dict = None):
    """Call an MCP tool and return the result"""
    print(f"\n🚀 Calling tool: {tool_name}")
    print(f"   Arguments: {json.dumps(arguments or {}, indent=2)}")
    
    result = await session.call_tool(tool_name, arguments or {})
    
    print(f"\n📤 Result:")
    for content in result.content:
        if hasattr(content, 'text'):
            try:
                parsed = json.loads(content.text)
                print(json.dumps(parsed, indent=2))
            except json.JSONDecodeError:
                print(content.text)
    
    return result

async def test_knowledge_graph_status(session: ClientSession):
    """Test the check_knowledge_graph_status tool"""
    print("\n" + "=" * 60)
    print("🔬 TEST 1: check_knowledge_graph_status")
    print("=" * 60)
    return await call_tool(session, "check_knowledge_graph_status")

async def test_track_decision(session: ClientSession):
    """Test the track_decision tool"""
    print("\n" + "=" * 60)
    print("🔬 TEST 2: track_decision")
    print("=" * 60)
    return await call_tool(session, "track_decision", {
        "title": "Use Neo4j for Knowledge Graph",
        "description": "Chose Neo4j with Graphiti for temporal knowledge graph storage to enable decision tracking and pattern recognition.",
        "rationale": "Neo4j provides native graph database capabilities with excellent query performance for relationship traversal. Graphiti adds temporal tracking and entity extraction. This enables queries like 'Why did we choose X?' with full historical context.",
        "project": "SIGMA",
        "related_files": "src/openmemory/app/utils/graphiti.py, docker/docker-compose.yaml",
        "alternatives_considered": "PostgreSQL with ltree extension, Amazon Neptune, TigerGraph",
        "tags": "database,knowledge-graph,phase-1,architecture"
    })

async def test_search_decisions(session: ClientSession):
    """Test the search_decisions tool"""
    print("\n" + "=" * 60)
    print("🔬 TEST 3: search_decisions")
    print("=" * 60)
    return await call_tool(session, "search_decisions", {
        "query": "Neo4j knowledge graph",
        "project": "SIGMA"
    })

async def test_add_memory(session: ClientSession):
    """Test the add_memories tool"""
    print("\n" + "=" * 60)
    print("🔬 TEST 4: add_memories")
    print("=" * 60)
    return await call_tool(session, "add_memories", {
        "text": "SIGMA Phase 1 deployed on January 8, 2026. All services running: PostgreSQL, Qdrant, Neo4j. Phase 2 Git Integration is next."
    })

async def test_search_memory(session: ClientSession):
    """Test the search_memory tool"""
    print("\n" + "=" * 60)
    print("🔬 TEST 5: search_memory")
    print("=" * 60)
    return await call_tool(session, "search_memory", {
        "query": "SIGMA Phase 1 deployment"
    })

async def main():
    """Main test function"""
    print("=" * 60)
    print("🧪 SIGMA MCP Tools Test Suite")
    print("=" * 60)
    print(f"Server: {MCP_SERVER_URL}")
    print(f"Client: {CLIENT_NAME}")
    print(f"User: {USER_ID}")
    
    # Connect to MCP server via SSE
    sse_url = f"{MCP_SERVER_URL}/{CLIENT_NAME}/sse/{USER_ID}"
    print(f"\n🔗 Connecting to: {sse_url}")
    
    try:
        async with sse_client(sse_url) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize session
                await session.initialize()
                print("✅ Connected to MCP server")
                
                # List available tools
                await list_tools(session)
                
                # Run tests
                print("\n" + "=" * 60)
                print("🧪 Running MCP Tool Tests")
                print("=" * 60)
                
                # Test 1: Knowledge Graph Status
                await test_knowledge_graph_status(session)
                
                # Test 2: Track a Decision
                await test_track_decision(session)
                
                # Test 3: Search Decisions
                await test_search_decisions(session)
                
                # Test 4: Add Memory
                await test_add_memory(session)
                
                # Test 5: Search Memory
                await test_search_memory(session)
                
                print("\n" + "=" * 60)
                print("✅ All tests completed!")
                print("=" * 60)
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
