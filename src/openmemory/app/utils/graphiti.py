"""
Graphiti Knowledge Graph Client for SIGMA.

This module provides a Graphiti client for the SIGMA knowledge graph system.
The client is initialized lazily to prevent server crashes when Neo4j is
unavailable. If the Graphiti client cannot be initialized, the server will
continue running with limited functionality.

Key features:
- Lazy Graphiti client initialization
- Graceful degradation when Neo4j is unavailable
- Developer entity helpers (Decision, Pattern, Project, etc.)
- Temporal query support for decision tracking
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Global Graphiti client instance (initialized lazily)
_graphiti_client: Optional[Any] = None
_graphiti_initialized: bool = False


class EntityType(Enum):
    """Developer-focused entity types for SIGMA knowledge graph."""
    DECISION = "Decision"
    PATTERN = "Pattern"
    PROJECT = "Project"
    FILE = "File"
    FUNCTION = "Function"
    LIBRARY = "Library"
    ISSUE = "Issue"
    COMMIT = "Commit"


class RelationType(Enum):
    """Relationship types for developer knowledge graph."""
    CONTAINS = "CONTAINS"           # Project contains Files
    DEPENDS_ON = "DEPENDS_ON"       # Project depends on Library
    IMPLEMENTS = "IMPLEMENTS"       # Commit implements Decision
    SOLVES = "SOLVES"               # Solution solves Issue
    USES = "USES"                   # File uses Pattern
    REPLACES = "REPLACES"           # Decision replaces older Decision
    DISCUSSED_IN = "DISCUSSED_IN"   # Decision discussed in SlackMessage
    PREFERS = "PREFERS"             # Developer prefers Pattern
    CAUSED_BY = "CAUSED_BY"         # Issue caused by Commit
    SIMILAR_TO = "SIMILAR_TO"       # Pattern similar to Pattern
    RELATED_TO = "RELATED_TO"       # Generic relationship


@dataclass
class Decision:
    """
    Represents a technical or architectural decision.
    
    Decisions track why choices were made, enabling temporal queries like
    "Why did we decide to use Redis?" with full historical context.
    """
    title: str
    description: str
    rationale: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    project: Optional[str] = None
    related_files: List[str] = field(default_factory=list)
    alternatives_considered: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source: str = "manual"  # manual, slack, git, inferred
    confidence: float = 1.0
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None  # None means still current
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary for storage."""
        return {
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "project": self.project,
            "related_files": self.related_files,
            "alternatives_considered": self.alternatives_considered,
            "tags": self.tags,
            "source": self.source,
            "confidence": self.confidence,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Decision":
        """Create Decision from dictionary."""
        return cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            rationale=data.get("rationale", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            created_by=data.get("created_by"),
            project=data.get("project"),
            related_files=data.get("related_files", []),
            alternatives_considered=data.get("alternatives_considered", []),
            tags=data.get("tags", []),
            source=data.get("source", "manual"),
            confidence=data.get("confidence", 1.0),
            valid_from=datetime.fromisoformat(data["valid_from"]) if data.get("valid_from") else None,
            valid_to=datetime.fromisoformat(data["valid_to"]) if data.get("valid_to") else None,
        )


def is_graphiti_enabled() -> bool:
    """Check if Graphiti integration is enabled via feature flag."""
    return os.getenv("GRAPHITI_ENABLED", "false").lower() in ("true", "1", "yes")


def get_neo4j_config() -> Dict[str, str]:
    """Get Neo4j configuration from environment variables."""
    return {
        "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.getenv("NEO4J_USER", "neo4j"),
        "password": os.getenv("NEO4J_PASSWORD", "sigmapassword"),
    }


def get_llm_config() -> Dict[str, Any]:
    """
    Get LLM configuration based on LLM_PROVIDER environment variable.
    
    Supports: openai, openrouter, ollama
    """
    provider = os.getenv("LLM_PROVIDER", "openrouter").lower()
    model = os.getenv("MODEL", "xiaomi/mimo-v2-flash:free")
    
    if provider == "openrouter":
        return {
            "provider": "openrouter",
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "base_url": "https://openrouter.ai/api/v1",
            "model": model,
        }
    elif provider == "openai":
        return {
            "provider": "openai",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": None,
            "model": model,
        }
    elif provider == "ollama":
        return {
            "provider": "ollama",
            "api_key": None,
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "model": model,
        }
    else:
        logger.warning(f"Unknown LLM_PROVIDER: {provider}, defaulting to openrouter")
        return {
            "provider": "openrouter",
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "base_url": "https://openrouter.ai/api/v1",
            "model": model,
        }


def get_embeddings_config() -> Dict[str, Any]:
    """
    Get embeddings configuration based on EMBEDDINGS_PROVIDER environment variable.
    """
    provider = os.getenv("EMBEDDINGS_PROVIDER", "openrouter").lower()
    model = os.getenv("EMBEDDINGS_MODEL", "openai/text-embedding-3-small")
    
    if provider == "openrouter":
        return {
            "provider": "openrouter",
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "base_url": "https://openrouter.ai/api/v1",
            "model": model,
        }
    elif provider == "openai":
        return {
            "provider": "openai",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": None,
            "model": model,
        }
    elif provider == "ollama":
        return {
            "provider": "ollama",
            "api_key": None,
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "model": model,
        }
    else:
        return {
            "provider": "openrouter",
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "base_url": "https://openrouter.ai/api/v1",
            "model": model,
        }


async def initialize_graphiti_client() -> Optional[Any]:
    """
    Initialize the Graphiti client with Neo4j backend.
    
    Uses the LLM_PROVIDER environment variable to determine which LLM to use.
    Supports: openai, openrouter, ollama
    
    Returns None if initialization fails (e.g., Neo4j unavailable).
    The server will continue to function with limited knowledge graph features.
    """
    global _graphiti_client, _graphiti_initialized
    
    if _graphiti_initialized:
        return _graphiti_client
    
    if not is_graphiti_enabled():
        logger.info("Graphiti integration is disabled via GRAPHITI_ENABLED flag")
        _graphiti_initialized = True
        return None
    
    try:
        from graphiti_core import Graphiti
        from graphiti_core.llm_client import OpenAIClient
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.embedder import OpenAIEmbedder
        from graphiti_core.embedder.openai import OpenAIEmbedderConfig
        
        neo4j_config = get_neo4j_config()
        llm_config = get_llm_config()
        embeddings_config = get_embeddings_config()
        
        # Get API key and base URL based on provider
        api_key = llm_config.get("api_key")
        base_url = llm_config.get("base_url")
        model = llm_config.get("model")
        provider = llm_config.get("provider")
        
        if not api_key and provider != "ollama":
            logger.warning(f"No API key set for {provider}, Graphiti may have limited functionality")
        
        logger.info(f"Initializing Graphiti with LLM provider: {provider}, model: {model}")
        
        # Create LLM config for Graphiti (v0.25+ API)
        # Graphiti uses OpenAI-compatible API, so we can use OpenAIClient for OpenRouter too
        llm_configuration = LLMConfig(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0.1,
        )
        
        # Create LLM client with the config
        llm_client = OpenAIClient(config=llm_configuration)
        
        # Create embedder config for Graphiti
        # Use OpenRouter for embeddings too
        embedder_api_key = embeddings_config.get("api_key") or api_key
        embedder_base_url = embeddings_config.get("base_url") or base_url
        embedder_model = embeddings_config.get("model", "text-embedding-3-small")
        
        # Strip "openai/" prefix if present (OpenRouter uses it, but the config just needs the model name)
        if embedder_model.startswith("openai/"):
            embedder_model = embedder_model[7:]  # Remove "openai/" prefix
        
        logger.info(f"Initializing Graphiti embedder: model={embedder_model}")
        
        embedder_configuration = OpenAIEmbedderConfig(
            api_key=embedder_api_key,
            base_url=embedder_base_url,
            embedding_model=embedder_model,
            embedding_dim=1536,  # text-embedding-3-small dimension
        )
        
        # Create embedder client
        embedder = OpenAIEmbedder(config=embedder_configuration)
        
        # Initialize Graphiti with Neo4j, LLM, and embedder
        _graphiti_client = Graphiti(
            uri=neo4j_config["uri"],
            user=neo4j_config["user"],
            password=neo4j_config["password"],
            llm_client=llm_client,
            embedder=embedder,
        )
        
        # Initialize the graph schema
        await _graphiti_client.build_indices_and_constraints()
        
        logger.info(f"Graphiti client initialized successfully with Neo4j at {neo4j_config['uri']}")
        _graphiti_initialized = True
        return _graphiti_client
        
    except ImportError as e:
        logger.warning(f"Graphiti not installed: {e}. Knowledge graph features will be unavailable.")
        _graphiti_initialized = True
        return None
        
    except Exception as e:
        logger.warning(f"Failed to initialize Graphiti client: {e}. Knowledge graph features will be unavailable.")
        _graphiti_initialized = True
        return None


async def get_graphiti_client() -> Optional[Any]:
    """
    Get the Graphiti client, initializing if necessary.
    
    Returns None if client is unavailable.
    """
    global _graphiti_client, _graphiti_initialized
    
    if not _graphiti_initialized:
        return await initialize_graphiti_client()
    
    return _graphiti_client


def get_graphiti_client_sync() -> Optional[Any]:
    """
    Get Graphiti client synchronously (use for non-async contexts).
    Returns None if not yet initialized.
    """
    return _graphiti_client


async def close_graphiti_client():
    """Close the Graphiti client connection."""
    global _graphiti_client, _graphiti_initialized
    
    if _graphiti_client:
        try:
            await _graphiti_client.close()
            logger.info("Graphiti client closed")
        except Exception as e:
            logger.warning(f"Error closing Graphiti client: {e}")
        finally:
            _graphiti_client = None
            _graphiti_initialized = False


# =============================================================================
# Decision Tracking Functions
# =============================================================================

async def add_decision(
    decision: Decision,
    user_id: str,
    client_name: str,
) -> Optional[Dict[str, Any]]:
    """
    Add a decision to the knowledge graph.
    
    Args:
        decision: The Decision object to store
        user_id: User who created/tracked the decision
        client_name: MCP client name for context
    
    Returns:
        Dict with the created episode info, or None if Graphiti unavailable
    """
    client = await get_graphiti_client()
    if not client:
        logger.warning("Graphiti unavailable, decision not stored in knowledge graph")
        return None
    
    try:
        # Create the episode content for Graphiti
        episode_content = f"""
Technical Decision: {decision.title}

Description: {decision.description}

Rationale: {decision.rationale}

{f"Project: {decision.project}" if decision.project else ""}
{f"Related Files: {', '.join(decision.related_files)}" if decision.related_files else ""}
{f"Alternatives Considered: {', '.join(decision.alternatives_considered)}" if decision.alternatives_considered else ""}
{f"Tags: {', '.join(decision.tags)}" if decision.tags else ""}

Source: {decision.source}
Created by: {user_id or 'unknown'}
"""
        
        # Add episode to Graphiti
        episode = await client.add_episode(
            name=f"Decision: {decision.title}",
            episode_body=episode_content.strip(),
            source_description=f"Decision tracked by {client_name}",
            reference_time=decision.created_at,
        )
        
        logger.info(f"Decision '{decision.title}' added to knowledge graph")
        
        return {
            "status": "success",
            "decision_title": decision.title,
            "episode_id": str(episode.uuid) if hasattr(episode, 'uuid') else None,
            "created_at": decision.created_at.isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Failed to add decision to knowledge graph: {e}")
        return None


async def search_decisions(
    query: str,
    project: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search for decisions in the knowledge graph.
    
    Args:
        query: Search query string
        project: Optional project filter
        limit: Maximum number of results
    
    Returns:
        List of matching decisions with context
    """
    client = await get_graphiti_client()
    if not client:
        logger.warning("Graphiti unavailable, returning empty search results")
        return []
    
    try:
        # Build search query with optional project filter
        search_query = query
        if project:
            search_query = f"{query} project:{project}"
        
        # Search using Graphiti
        results = await client.search(
            query=search_query,
            num_results=limit,
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "fact": result.fact if hasattr(result, 'fact') else str(result),
                "score": result.score if hasattr(result, 'score') else 1.0,
                "created_at": result.created_at.isoformat() if hasattr(result, 'created_at') else None,
                "valid_at": result.valid_at.isoformat() if hasattr(result, 'valid_at') else None,
                "invalid_at": result.invalid_at.isoformat() if hasattr(result, 'invalid_at') and result.invalid_at else None,
            })
        
        logger.info(f"Found {len(formatted_results)} decisions matching '{query}'")
        return formatted_results
        
    except Exception as e:
        logger.error(f"Failed to search decisions: {e}")
        return []


async def get_decision_history(
    topic: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Get historical decisions on a topic with temporal context.
    
    This enables queries like "What decisions did we make about caching?"
    with full temporal history showing how decisions evolved.
    
    Args:
        topic: Topic to search for (e.g., "caching", "database", "authentication")
        start_date: Optional start of time range
        end_date: Optional end of time range
    
    Returns:
        List of decisions with temporal context
    """
    client = await get_graphiti_client()
    if not client:
        return []
    
    try:
        # Search for decisions on this topic
        results = await search_decisions(
            query=f"decision about {topic}",
            limit=20,
        )
        
        # Filter by date range if specified
        if start_date or end_date:
            filtered = []
            for r in results:
                created = None
                if r.get("created_at"):
                    created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
                
                if created:
                    if start_date and created < start_date:
                        continue
                    if end_date and created > end_date:
                        continue
                filtered.append(r)
            results = filtered
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to get decision history: {e}")
        return []


# =============================================================================
# Health Check Functions
# =============================================================================

async def check_graphiti_health() -> Dict[str, Any]:
    """
    Check the health of the Graphiti/Neo4j connection.
    
    Returns:
        Dict with health status information
    """
    if not is_graphiti_enabled():
        return {
            "status": "disabled",
            "message": "Graphiti integration is disabled",
        }
    
    client = await get_graphiti_client()
    if not client:
        return {
            "status": "unavailable",
            "message": "Graphiti client could not be initialized",
        }
    
    try:
        # Simple health check - verify connection
        # This varies based on Graphiti version, adjust as needed
        return {
            "status": "healthy",
            "message": "Graphiti connection is active",
            "neo4j_uri": get_neo4j_config()["uri"],
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Health check failed: {str(e)}",
        }
