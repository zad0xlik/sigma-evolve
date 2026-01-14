"""
MCP Server for OpenMemory with resilient memory client handling.

This module implements an MCP (Model Context Protocol) server that provides
memory operations for OpenMemory. The memory client is initialized lazily
to prevent server crashes when external dependencies (like Ollama) are
unavailable. If the memory client cannot be initialized, the server will
continue running with limited functionality and appropriate error messages.

Key features:
- Lazy memory client initialization
- Graceful error handling for unavailable dependencies
- Fallback to database-only mode when vector store is unavailable
- Proper logging for debugging connection issues
- Environment variable parsing for API keys
"""

import contextvars
import datetime
import json
import logging
import sys
import uuid
from pathlib import Path

from app.database import SessionLocal
from app.models import Memory, MemoryAccessLog, MemoryState, MemoryStatusHistory, User
from app.utils.db import get_user_and_app
from app.utils.memory import get_memory_client
from app.utils.permissions import check_memory_access_permissions
from app.utils.graphiti import (
    Decision,
    add_decision as graphiti_add_decision,
    search_decisions as graphiti_search_decisions,
    is_graphiti_enabled,
    check_graphiti_health,
)
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.routing import APIRouter
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

# Add scripts directory to path for importing loaders
scripts_path = Path(__file__).parent.parent.parent.parent / "scripts"
if str(scripts_path) not in sys.path:
    sys.path.insert(0, str(scripts_path))

# Load environment variables
load_dotenv()

# Initialize MCP
mcp = FastMCP("mem0-mcp-server")

# Don't initialize memory client at import time - do it lazily when needed
def get_memory_client_safe():
    """Get memory client with error handling. Returns None if client cannot be initialized."""
    try:
        return get_memory_client()
    except Exception as e:
        logging.warning(f"Failed to get memory client: {e}")
        return None

# Context variables for user_id and client_name
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id")
client_name_var: contextvars.ContextVar[str] = contextvars.ContextVar("client_name")

# Create a router for MCP endpoints
mcp_router = APIRouter(prefix="/mcp")

# Initialize SSE transport
sse = SseServerTransport("/mcp/messages/")

@mcp.tool(description="Add a new memory. This method is called everytime the user informs anything about themselves, their preferences, or anything that has any relevant information which can be useful in the future conversation. This can also be called when the user asks you to remember something.")
async def add_memories(text: str) -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)

    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=uid, app_id=client_name)

            # Check if app is active
            if not app.is_active:
                return f"Error: App {app.name} is currently paused on OpenMemory. Cannot create new memories."

            response = memory_client.add(text,
                                         user_id=uid,
                                         metadata={
                                            "source_app": "openmemory",
                                            "mcp_client": client_name,
                                        })

            # Process the response and update database
            if isinstance(response, dict) and 'results' in response:
                for result in response['results']:
                    memory_id = uuid.UUID(result['id'])
                    memory = db.query(Memory).filter(Memory.id == memory_id).first()

                    if result['event'] == 'ADD':
                        if not memory:
                            memory = Memory(
                                id=memory_id,
                                user_id=user.id,
                                app_id=app.id,
                                content=result['memory'],
                                state=MemoryState.active
                            )
                            db.add(memory)
                        else:
                            memory.state = MemoryState.active
                            memory.content = result['memory']

                        # Create history entry
                        history = MemoryStatusHistory(
                            memory_id=memory_id,
                            changed_by=user.id,
                            old_state=MemoryState.deleted if memory else None,
                            new_state=MemoryState.active
                        )
                        db.add(history)

                    elif result['event'] == 'DELETE':
                        if memory:
                            memory.state = MemoryState.deleted
                            memory.deleted_at = datetime.datetime.now(datetime.UTC)
                            # Create history entry
                            history = MemoryStatusHistory(
                                memory_id=memory_id,
                                changed_by=user.id,
                                old_state=MemoryState.active,
                                new_state=MemoryState.deleted
                            )
                            db.add(history)

                db.commit()

            return json.dumps(response, indent=2)
        finally:
            db.close()
    except Exception as e:
        logging.exception(f"Error adding to memory: {e}")
        return f"Error adding to memory: {e}"


@mcp.tool(description="Search through stored memories. This method is called EVERYTIME the user asks anything.")
async def search_memory(query: str) -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=uid, app_id=client_name)

            # If memory client available, use vector search
            if memory_client:
                # Get accessible memory IDs based on ACL
                user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
                accessible_memory_ids = [memory.id for memory in user_memories if check_memory_access_permissions(db, memory, app.id)]

                filters = {
                    "user_id": uid
                }

                embeddings = memory_client.embedding_model.embed(query, "search")

                hits = memory_client.vector_store.search(
                    query=query, 
                    vectors=embeddings, 
                    limit=10, 
                    filters=filters,
                )

                allowed = set(str(mid) for mid in accessible_memory_ids) if accessible_memory_ids else None

                results = []
                for h in hits:
                    # All vector db search functions return OutputData class
                    id, score, payload = h.id, h.score, h.payload
                    if allowed and h.id is None or h.id not in allowed: 
                        continue
                    
                    results.append({
                        "id": id, 
                        "memory": payload.get("data"), 
                        "hash": payload.get("hash"),
                        "created_at": payload.get("created_at"), 
                        "updated_at": payload.get("updated_at"), 
                        "score": score,
                    })

                for r in results: 
                    if r.get("id"): 
                        access_log = MemoryAccessLog(
                            memory_id=uuid.UUID(r["id"]),
                            app_id=app.id,
                            access_type="search",
                            metadata_={
                                "query": query,
                                "score": r.get("score"),
                                "hash": r.get("hash"),
                            },
                        )
                        db.add(access_log)
                db.commit()

                return json.dumps({"results": results}, indent=2)
            
            # Fallback: Database text search (when vector store unavailable)
            else:
                logging.info(f"Using database fallback search for query: {query}")
                logging.info(f"User: {uid} (UUID: {user.id}), App: {client_name} (UUID: {app.id})")
                
                # Simple text search in database
                memories = db.query(Memory).filter(
                    Memory.user_id == user.id,
                    Memory.app_id == app.id,
                    Memory.state == MemoryState.active,
                    Memory.content.ilike(f"%{query}%")
                ).limit(10).all()
                
                logging.info(f"Found {len(memories)} memories from database query")
                
                results = []
                for memory in memories:
                    # Check permissions
                    has_permission = check_memory_access_permissions(db, memory, app.id)
                    logging.info(f"Memory {memory.id}: permission={has_permission}")
                    
                    if has_permission:
                        results.append({
                            "id": str(memory.id),
                            "memory": memory.content,
                            "created_at": memory.created_at.isoformat() if memory.created_at else None,
                            "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
                            "score": 1.0,  # No semantic score in text search
                        })
                        
                        # Log access
                        access_log = MemoryAccessLog(
                            memory_id=memory.id,
                            app_id=app.id,
                            access_type="search",
                            metadata_={
                                "query": query,
                                "search_method": "database_text",
                            },
                        )
                        db.add(access_log)
                
                db.commit()
                
                logging.info(f"Returning {len(results)} results to client")
                
                return json.dumps({
                    "results": results,
                    "search_method": "database_text",
                    "note": "Using text search (vector store unavailable)"
                }, indent=2)
                
        finally:
            db.close()
    except Exception as e:
        logging.exception(e)
        return f"Error searching memory: {e}"


@mcp.tool(description="List all memories in the user's memory")
async def list_memories() -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=uid, app_id=client_name)

            # Get all memories
            memories = memory_client.get_all(user_id=uid)
            
            # Special case: slack-bot is a virtual user that should access all memories without PostgreSQL filtering
            if uid == "slack-bot":
                # Return all memories from Qdrant without filtering
                if isinstance(memories, dict) and 'results' in memories:
                    return json.dumps(memories['results'], indent=2)
                else:
                    return json.dumps(memories, indent=2)
            
            filtered_memories = []

            # Filter memories based on permissions
            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [memory.id for memory in user_memories if check_memory_access_permissions(db, memory, app.id)]
            if isinstance(memories, dict) and 'results' in memories:
                for memory_data in memories['results']:
                    if 'id' in memory_data:
                        memory_id = uuid.UUID(memory_data['id'])
                        if memory_id in accessible_memory_ids:
                            # Create access log entry
                            access_log = MemoryAccessLog(
                                memory_id=memory_id,
                                app_id=app.id,
                                access_type="list",
                                metadata_={
                                    "hash": memory_data.get('hash')
                                }
                            )
                            db.add(access_log)
                            filtered_memories.append(memory_data)
                db.commit()
            else:
                for memory in memories:
                    memory_id = uuid.UUID(memory['id'])
                    memory_obj = db.query(Memory).filter(Memory.id == memory_id).first()
                    if memory_obj and check_memory_access_permissions(db, memory_obj, app.id):
                        # Create access log entry
                        access_log = MemoryAccessLog(
                            memory_id=memory_id,
                            app_id=app.id,
                            access_type="list",
                            metadata_={
                                "hash": memory.get('hash')
                            }
                        )
                        db.add(access_log)
                        filtered_memories.append(memory)
                db.commit()
            return json.dumps(filtered_memories, indent=2)
        finally:
            db.close()
    except Exception as e:
        logging.exception(f"Error getting memories: {e}")
        return f"Error getting memories: {e}"


@mcp.tool(description="Load Slack channel history into memory. This tool fetches all messages from a Slack channel and stores them in OpenMemory for future retrieval. Use this when you need to import historical Slack conversations.")
async def load_slack_channel(channel_name: str, days: int = None, include_threads: bool = True) -> str:
    """
    Load Slack channel history into OpenMemory.
    
    Args:
        channel_name: Name of the Slack channel (without # prefix)
        days: Optional number of days to look back (None = all history)
        include_threads: Whether to include thread replies (default: True)
    
    Returns:
        JSON string with loading statistics
    """
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    
    if not uid:
        return json.dumps({"error": "user_id not provided"})
    if not client_name:
        return json.dumps({"error": "client_name not provided"})
    
    try:
        # Import here to avoid import errors if scripts not available
        from slack_channel_loader import SlackChannelLoader
        
        # Initialize loader
        loader = SlackChannelLoader()
        
        # Load channel
        stats = loader.load_channel(
            channel_name=channel_name,
            include_threads=include_threads,
            days=days
        )
        
        # Close database connection
        loader.db.close()
        
        return json.dumps({
            "status": "success" if "error" not in stats else "error",
            "channel": channel_name,
            "statistics": stats
        }, indent=2)
        
    except ImportError as e:
        logging.error(f"Failed to import SlackChannelLoader: {e}")
        return json.dumps({
            "error": "Slack channel loader not available",
            "details": str(e)
        })
    except Exception as e:
        logging.exception(f"Error loading Slack channel: {e}")
        return json.dumps({
            "error": "Failed to load Slack channel",
            "details": str(e)
        })


@mcp.tool(description="Search all Slack channel conversations. Searches across all users and channels without needing specific user_id. Returns relevant Slack messages with channel and user context.")
async def search_slack_channels(query: str, channel: str = None, limit: int = 10) -> str:
    """
    Search all Slack channel data regardless of user.
    Always uses 'slack-bot' user which owns all Slack memories.
    
    Args:
        query: Search query string
        channel: Optional channel name to filter by (e.g., 'tech-lmk-portal')
        limit: Maximum number of results (default: 10)
    
    Returns:
        JSON string with search results
    """
    # ALWAYS use "slack-bot" for Slack searches
    SLACK_USER_ID = "slack-bot"
    
    try:
        db = SessionLocal()
        try:
            # Get slack-bot user
            slack_bot_user = db.query(User).filter(User.user_id == SLACK_USER_ID).first()
            
            if not slack_bot_user:
                return json.dumps({
                    "results": [],
                    "error": "Slack data not loaded yet. Run load_slack_channel tool first."
                })
            
            # Get memory client safely
            memory_client = get_memory_client_safe()
            
            if memory_client:
                # Build filters for Slack data
                filters = {
                    "user_id": SLACK_USER_ID,  # All Slack data is under slack-bot
                }
                
                # Add channel filter if specified
                if channel:
                    filters["metadata.slack_channel_name"] = channel
                
                # Get embeddings and search
                embeddings = memory_client.embedding_model.embed(query, "search")
                
                hits = memory_client.vector_store.search(
                    query=query,
                    vectors=embeddings,
                    limit=limit,
                    filters=filters
                )
                
                # Format results
                results = []
                for h in hits:
                    payload = h.payload or {}
                    metadata = payload.get("metadata", {})
                    
                    results.append({
                        "id": h.id,
                        "content": payload.get("data"),
                        "channel": metadata.get("slack_channel_name"),
                        "user": metadata.get("slack_real_name") or metadata.get("slack_user_name"),
                        "timestamp": metadata.get("message_ts"),
                        "score": h.score,
                    })
                
                return json.dumps({
                    "results": results,
                    "query": query,
                    "channel_filter": channel,
                    "search_method": "qdrant_vector"
                }, indent=2)
            
            else:
                # Fallback: Database text search
                logging.info(f"Using database fallback for Slack search: {query}")
                
                # Query Slack memories from slack-bot user
                query_filter = db.query(Memory).filter(
                    Memory.user_id == slack_bot_user.id,
                    Memory.state == MemoryState.active,
                    Memory.content.ilike(f"%{query}%")
                )
                
                # Add channel filter if specified
                if channel:
                    query_filter = query_filter.filter(
                        Memory.metadata_["slack_channel_name"].astext == channel
                    )
                
                memories = query_filter.limit(limit).all()
                
                results = []
                for memory in memories:
                    metadata = memory.metadata_ or {}
                    results.append({
                        "id": str(memory.id),
                        "content": memory.content,
                        "channel": metadata.get("slack_channel_name"),
                        "user": metadata.get("slack_real_name") or metadata.get("slack_user_name"),
                        "timestamp": metadata.get("message_ts"),
                        "score": 1.0,
                    })
                
                return json.dumps({
                    "results": results,
                    "query": query,
                    "channel_filter": channel,
                    "search_method": "database_text",
                    "note": "Using text search (vector store unavailable)"
                }, indent=2)
                
        finally:
            db.close()
            
    except Exception as e:
        logging.exception(f"Error searching Slack channels: {e}")
        return json.dumps({
            "error": f"Search failed: {str(e)}",
            "results": []
        })


@mcp.tool(description="Sync Qdrant vector store from PostgreSQL database. Rebuilds Qdrant index from all active memories. Useful after container restarts or when Qdrant data is lost.")
async def sync_vector_store() -> str:
    """
    Manually trigger Qdrant sync from PostgreSQL.
    
    Returns:
        JSON string with sync statistics
    """
    try:
        # Import sync function
        import sys
        from pathlib import Path
        
        # Add parent directory to path
        parent_path = Path(__file__).parent.parent
        if str(parent_path) not in sys.path:
            sys.path.insert(0, str(parent_path))
        
        from sync_qdrant_from_postgres import sync_qdrant
        
        # Run sync
        logging.info("Manual Qdrant sync triggered via MCP")
        result = sync_qdrant(dry_run=False)
        
        if "error" in result:
            return json.dumps({
                "status": "error",
                "error": result["error"]
            })
        
        return json.dumps({
            "status": "success",
            "statistics": {
                "total_memories": result["total"],
                "users_cleared": result["users_cleared"],
                "memories_synced": result["synced"],
                "errors": result["errors"]
            }
        }, indent=2)
        
    except Exception as e:
        logging.exception(f"Error during manual sync: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e)
        })


@mcp.tool(description="Delete all memories in the user's memory")
async def delete_all_memories() -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=uid, app_id=client_name)

            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [memory.id for memory in user_memories if check_memory_access_permissions(db, memory, app.id)]

            # delete the accessible memories only
            for memory_id in accessible_memory_ids:
                try:
                    memory_client.delete(memory_id)
                except Exception as delete_error:
                    logging.warning(f"Failed to delete memory {memory_id} from vector store: {delete_error}")

            # Update each memory's state and create history entries
            now = datetime.datetime.now(datetime.UTC)
            for memory_id in accessible_memory_ids:
                memory = db.query(Memory).filter(Memory.id == memory_id).first()
                # Update memory state
                memory.state = MemoryState.deleted
                memory.deleted_at = now

                # Create history entry
                history = MemoryStatusHistory(
                    memory_id=memory_id,
                    changed_by=user.id,
                    old_state=MemoryState.active,
                    new_state=MemoryState.deleted
                )
                db.add(history)

                # Create access log entry
                access_log = MemoryAccessLog(
                    memory_id=memory_id,
                    app_id=app.id,
                    access_type="delete_all",
                    metadata_={"operation": "bulk_delete"}
                )
                db.add(access_log)

            db.commit()
            return "Successfully deleted all memories"
        finally:
            db.close()
    except Exception as e:
        logging.exception(f"Error deleting memories: {e}")
        return f"Error deleting memories: {e}"


# =============================================================================
# SIGMA Phase 1: Knowledge Graph Tools (Decision Tracking)
# =============================================================================

@mcp.tool(description="Track a technical or architectural decision. Use this to record why choices were made, what alternatives were considered, and what files are affected. This creates a permanent record in the knowledge graph that can be queried later with search_decisions.")
async def track_decision(
    title: str,
    description: str,
    rationale: str,
    project: str = None,
    related_files: str = None,
    alternatives_considered: str = None,
    tags: str = None,
) -> str:
    """
    Track a technical decision in the SIGMA knowledge graph.
    
    This enables queries like "Why did we decide to use Redis?" with full
    historical context including who made the decision, when, and why.
    
    Args:
        title: Short title for the decision (e.g., "Use Redis for caching")
        description: Detailed description of the decision
        rationale: Why this decision was made - the reasoning behind it
        project: Optional project name this decision applies to
        related_files: Optional comma-separated list of related file paths
        alternatives_considered: Optional comma-separated list of alternatives that were considered
        tags: Optional comma-separated list of tags (e.g., "caching,performance,database")
    
    Returns:
        JSON string with the result of tracking the decision
    """
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    
    if not uid:
        return json.dumps({"error": "user_id not provided"})
    if not client_name:
        return json.dumps({"error": "client_name not provided"})
    
    # Check if Graphiti is enabled
    if not is_graphiti_enabled():
        return json.dumps({
            "error": "Knowledge graph is disabled",
            "message": "Set GRAPHITI_ENABLED=true to enable decision tracking",
            "fallback": "Decision not stored, but you can still use add_memories for basic storage"
        })
    
    try:
        # Parse comma-separated strings into lists
        files_list = [f.strip() for f in related_files.split(",")] if related_files else []
        alternatives_list = [a.strip() for a in alternatives_considered.split(",")] if alternatives_considered else []
        tags_list = [t.strip() for t in tags.split(",")] if tags else []
        
        # Create Decision object
        decision = Decision(
            title=title,
            description=description,
            rationale=rationale,
            project=project,
            related_files=files_list,
            alternatives_considered=alternatives_list,
            tags=tags_list,
            created_by=uid,
            source="manual",
        )
        
        # Add to knowledge graph
        result = await graphiti_add_decision(
            decision=decision,
            user_id=uid,
            client_name=client_name,
        )
        
        if result:
            # Also store in regular memory for redundancy and fallback search
            memory_client = get_memory_client_safe()
            if memory_client:
                memory_text = f"Decision: {title}\n\nDescription: {description}\n\nRationale: {rationale}"
                if project:
                    memory_text += f"\n\nProject: {project}"
                if files_list:
                    memory_text += f"\n\nRelated Files: {', '.join(files_list)}"
                
                try:
                    db = SessionLocal()
                    try:
                        user, app = get_user_and_app(db, user_id=uid, app_id=client_name)
                        memory_client.add(
                            memory_text,
                            user_id=uid,
                            metadata={
                                "source_app": "openmemory",
                                "mcp_client": client_name,
                                "type": "decision",
                                "decision_title": title,
                                "project": project,
                                "tags": tags_list,
                            }
                        )
                    finally:
                        db.close()
                except Exception as mem_error:
                    logging.warning(f"Failed to store decision in memory system: {mem_error}")
            
            return json.dumps({
                "status": "success",
                "message": f"Decision '{title}' tracked successfully",
                "decision": decision.to_dict(),
                "knowledge_graph": result,
            }, indent=2, default=str)
        else:
            return json.dumps({
                "status": "partial",
                "message": f"Decision '{title}' was not stored in knowledge graph (Graphiti unavailable)",
                "decision": decision.to_dict(),
                "note": "Decision was stored in memory system only"
            }, indent=2, default=str)
            
    except Exception as e:
        logging.exception(f"Error tracking decision: {e}")
        return json.dumps({
            "error": f"Failed to track decision: {str(e)}"
        })


@mcp.tool(description="Search for past technical decisions. Query the knowledge graph to find decisions that were made, including their rationale, alternatives considered, and temporal context. Useful for questions like 'Why did we choose Redis?' or 'What decisions were made about authentication?'")
async def search_decisions(
    query: str,
    project: str = None,
    limit: int = 10,
) -> str:
    """
    Search for past decisions in the SIGMA knowledge graph.
    
    This enables temporal queries like "Why did we decide to use Redis?"
    or "What database decisions were made in the last 6 months?"
    
    Args:
        query: Search query (e.g., "caching", "database choice", "Redis")
        project: Optional project name to filter results
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        JSON string with matching decisions and their context
    """
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    
    if not uid:
        return json.dumps({"error": "user_id not provided"})
    if not client_name:
        return json.dumps({"error": "client_name not provided"})
    
    results = {
        "query": query,
        "project_filter": project,
        "knowledge_graph_results": [],
        "memory_results": [],
    }
    
    # Try knowledge graph search first
    if is_graphiti_enabled():
        try:
            graph_results = await graphiti_search_decisions(
                query=query,
                project=project,
                limit=limit,
            )
            results["knowledge_graph_results"] = graph_results
            results["knowledge_graph_status"] = "success"
        except Exception as e:
            logging.warning(f"Knowledge graph search failed: {e}")
            results["knowledge_graph_status"] = f"error: {str(e)}"
    else:
        results["knowledge_graph_status"] = "disabled"
    
    # Also search in regular memory for fallback/additional results
    try:
        memory_client = get_memory_client_safe()
        if memory_client:
            db = SessionLocal()
            try:
                user, app = get_user_and_app(db, user_id=uid, app_id=client_name)
                
                # Search with decision-related query
                search_query = f"decision {query}"
                embeddings = memory_client.embedding_model.embed(search_query, "search")
                
                hits = memory_client.vector_store.search(
                    query=search_query,
                    vectors=embeddings,
                    limit=limit,
                    filters={"user_id": uid}
                )
                
                memory_results = []
                for h in hits:
                    payload = h.payload or {}
                    metadata = payload.get("metadata", {})
                    
                    # Filter for decision-type memories if possible
                    if metadata.get("type") == "decision" or "decision" in payload.get("data", "").lower():
                        memory_results.append({
                            "id": h.id,
                            "content": payload.get("data"),
                            "score": h.score,
                            "decision_title": metadata.get("decision_title"),
                            "project": metadata.get("project"),
                            "tags": metadata.get("tags", []),
                        })
                
                results["memory_results"] = memory_results
                results["memory_status"] = "success"
            finally:
                db.close()
        else:
            results["memory_status"] = "unavailable"
    except Exception as e:
        logging.warning(f"Memory search failed: {e}")
        results["memory_status"] = f"error: {str(e)}"
    
    # Combine and format response
    total_results = len(results.get("knowledge_graph_results", [])) + len(results.get("memory_results", []))
    
    if total_results == 0:
        results["message"] = f"No decisions found matching '{query}'"
        if not is_graphiti_enabled():
            results["hint"] = "Knowledge graph is disabled. Enable GRAPHITI_ENABLED=true for better decision tracking."
    else:
        results["message"] = f"Found {total_results} decision(s) matching '{query}'"
    
    return json.dumps(results, indent=2, default=str)


@mcp.tool(description="Check the health status of the SIGMA knowledge graph system. Returns information about Neo4j connectivity and Graphiti status.")
async def check_knowledge_graph_status() -> str:
    """
    Check the health of the SIGMA knowledge graph system.
    
    Returns:
        JSON string with health status information
    """
    try:
        health = await check_graphiti_health()
        return json.dumps({
            "knowledge_graph": health,
            "feature_flag": is_graphiti_enabled(),
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        })


# =============================================================================
# SIGMA Phase 2: Git Integration Tools
# =============================================================================

@mcp.tool(description="Analyze and ingest a git repository into SIGMA's knowledge graph. Extracts project metadata, commit history, dependencies, and file structure. Use this to build context about a project's architecture and evolution.")
async def ingest_project(
    repo_path: str,
    branch: str = None,
    commit_limit: int = 50,
) -> str:
    """
    Analyze a git repository and ingest it into SIGMA's knowledge graph.
    
    This extracts:
    - Repository metadata (branches, remotes, etc.)
    - Commit history and patterns
    - Project dependencies from package files
    - File structure and language statistics
    - Decision keywords from commit messages
    
    Args:
        repo_path: Absolute path to the git repository
        branch: Branch to analyze (defaults to active branch)
        commit_limit: Maximum number of commits to analyze (default: 50)
    
    Returns:
        JSON string with analysis results
    """
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    
    if not uid:
        return json.dumps({"error": "user_id not provided"})
    if not client_name:
        return json.dumps({"error": "client_name not provided"})
    
    # Import git integration (lazy to handle missing dependencies gracefully)
    try:
        from app.utils.git_integration import GitProjectAnalyzer, is_git_integration_enabled
    except ImportError as e:
        return json.dumps({
            "error": "Git integration not available",
            "message": "GitPython is not installed",
            "install": "Run: uv sync"
        })
    
    # Check if git integration is enabled
    if not is_git_integration_enabled():
        return json.dumps({
            "error": "Git integration is disabled",
            "message": "Set GIT_INTEGRATION_ENABLED=true to enable repository analysis"
        })
    
    try:
        # Initialize analyzer
        analyzer = GitProjectAnalyzer(repo_path)
        
        # Perform full project analysis
        logging.info(f"Analyzing repository at {repo_path} for user {uid}")
        analysis = analyzer.analyze_full_project(branch=branch, commit_limit=commit_limit)
        
        # Store project info in knowledge graph if Graphiti is enabled
        if is_graphiti_enabled():
            try:
                # Create a comprehensive text summary for Graphiti ingestion
                repo_info = analysis["repository"]
                deps = analysis["dependencies"]
                patterns = analysis["patterns"]
                
                summary_parts = [
                    f"Project: {repo_info['name']}",
                    f"Path: {repo_info['path']}",
                    f"Active Branch: {repo_info.get('active_branch', 'unknown')}",
                ]
                
                # Add languages
                languages = analysis["file_structure"].get("languages", {})
                if languages:
                    top_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
                    summary_parts.append(f"Primary Languages: {', '.join(f'{lang} ({count} files)' for lang, count in top_langs)}")
                
                # Add dependencies
                if deps:
                    for ecosystem, dep_list in deps.items():
                        summary_parts.append(f"{ecosystem.title()} Dependencies: {len(dep_list)} packages")
                        # Store top 10 dependencies
                        for dep in dep_list[:10]:
                            summary_parts.append(f"  - {dep['name']} {dep.get('version', '')}")
                
                # Add commit patterns
                summary_parts.append(f"Recent Commits: {patterns['total_commits']} analyzed")
                summary_parts.append(f"Contributors: {', '.join(patterns['authors'][:10])}")
                
                # Add commit types
                if patterns.get('commit_types'):
                    summary_parts.append(f"Commit Types: {', '.join(f'{k}:{v}' for k, v in patterns['commit_types'].items())}")
                
                # Add decision keywords found in commits
                if patterns.get('decision_keywords'):
                    summary_parts.append(f"Decision Keywords Found: {len(patterns['decision_keywords'])} instances")
                    for decision_kw in patterns['decision_keywords'][:5]:
                        summary_parts.append(f"  - {decision_kw['keyword']}: {decision_kw['message']}")
                
                summary_text = "\n".join(summary_parts)
                
                # Store in memory system for searchability
                memory_client = get_memory_client_safe()
                if memory_client:
                    db = SessionLocal()
                    try:
                        user, app = get_user_and_app(db, user_id=uid, app_id=client_name)
                        memory_client.add(
                            summary_text,
                            user_id=uid,
                            metadata={
                                "source_app": "openmemory",
                                "mcp_client": client_name,
                                "type": "project_analysis",
                                "project_name": repo_info['name'],
                                "repo_path": repo_info['path'],
                                "branch": repo_info.get('active_branch'),
                                "languages": list(languages.keys()),
                            }
                        )
                        analysis["stored_in_memory"] = True
                    finally:
                        db.close()
                
            except Exception as kg_error:
                logging.warning(f"Failed to store project in knowledge graph: {kg_error}")
                analysis["knowledge_graph_storage"] = f"error: {str(kg_error)}"
        else:
            analysis["knowledge_graph_storage"] = "disabled"
        
        return json.dumps({
            "status": "success",
            "message": f"Successfully analyzed repository '{analysis['repository']['name']}'",
            "analysis": analysis,
        }, indent=2, default=str)
        
    except ValueError as ve:
        # Handle git-specific errors (invalid repo, etc.)
        return json.dumps({
            "error": "Invalid repository",
            "message": str(ve)
        })
    except Exception as e:
        logging.exception(f"Error ingesting project: {e}")
        return json.dumps({
            "error": f"Failed to ingest project: {str(e)}"
        })


@mcp_router.get("/{client_name}/sse/{user_id}")
async def handle_sse(request: Request):
    """Handle SSE connections for a specific user and client"""
    # Extract user_id and client_name from path parameters
    uid = request.path_params.get("user_id")
    user_token = user_id_var.set(uid or "")
    client_name = request.path_params.get("client_name")
    client_token = client_name_var.set(client_name or "")

    try:
        # Handle SSE connection
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp._mcp_server.run(
                read_stream,
                write_stream,
                mcp._mcp_server.create_initialization_options(),
            )
    finally:
        # Clean up context variables
        user_id_var.reset(user_token)
        client_name_var.reset(client_token)


@mcp_router.post("/messages/")
async def handle_get_message(request: Request):
    return await handle_post_message(request)


@mcp_router.post("/{client_name}/sse/{user_id}/messages/")
async def handle_post_message(request: Request):
    return await handle_post_message(request)

async def handle_post_message(request: Request):
    """Handle POST messages for SSE"""
    try:
        body = await request.body()

        # Create a simple receive function that returns the body
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        # Create a simple send function that does nothing
        async def send(message):
            return {}

        # Call handle_post_message with the correct arguments
        await sse.handle_post_message(request.scope, receive, send)

        # Return a success response
        return {"status": "ok"}
    finally:
        pass

def setup_mcp_server(app: FastAPI):
    """Setup MCP server with the FastAPI application"""
    mcp._mcp_server.name = "mem0-mcp-server"

    # Include MCP router in the FastAPI app
    app.include_router(mcp_router)
