# Technical Context: SIGMA - The Self-Evolving Developer Intelligence System

## Technology Stack Overview

```mermaid
flowchart TB
    subgraph Current["Current Foundation ✅"]
        FAST[FastAPI + MCP]
        PG[PostgreSQL]
        QD[Qdrant]
        SLACK[Slack SDK]
    end
    
    subgraph Phase1["Phase 1: Knowledge Graph ✅"]
        GRAPHITI[Graphiti 0.25.3]
        NEO[Neo4j 5.26]
        OR[OpenRouter]
    end
    
    subgraph Future["Phase 2: Intelligence 📋"]
        GIT[GitPython]
        RESEARCH[Research Engine]
        PATTERN[Pattern Learner]
    end
    
    Current --> Phase1 --> Future
```

## Core Technologies

### Application Framework
- **FastAPI 0.115+**: Async web framework
  - Native async/await support
  - Automatic OpenAPI documentation
  - Pydantic validation
  - MCP SSE transport

### Database Layer

| Database | Purpose | Status |
|----------|---------|--------|
| PostgreSQL 15+ | Source of truth, relational data | ✅ Active |
| Qdrant | Vector similarity search | ✅ Active |
| Neo4j 5.26 | Knowledge graph, temporal entities | ✅ Active |

### Knowledge Graph
- **Graphiti 0.25.3**: Temporal knowledge graph framework
  - Uses `LLMConfig` and `OpenAIEmbedderConfig` (v0.25+ API)
  - Entity extraction from text
  - Relationship mapping with temporal metadata
  - Bi-temporal query support
  - Community detection

### AI/ML Services
- **OpenAI API** (Direct or via OpenRouter)
  - Embeddings: text-embedding-3-small
  - LLM: GPT-4o-mini for categorization
  - Entity extraction (with Graphiti)

- **OpenRouter** (Optional LLM Gateway)
  - Access 100+ models from multiple providers
  - OpenAI-compatible API endpoint
  - Supports: OpenAI, Anthropic, Google, Meta, Mistral, etc.
  - Use any model for LLM operations (chat, categorization)
  - Note: Embeddings still require OpenAI-compatible endpoint

### Integrations
- **Slack SDK**: Channel history, decision tracking
- **GitPython** (Planned): Repository analysis
- **GitHub API** (Planned): PRs, issues, code reviews

## Dependency Matrix

### Core Dependencies
```
# Framework
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4

# MCP
fastmcp==0.6.1
mcp==1.3.2

# Memory
mem0ai==0.1.37
qdrant-client==1.12.1

# Knowledge Graph (Adding)
graphiti-core>=0.3.0
neo4j>=5.0.0

# Database
sqlalchemy==2.0.36
alembic==1.14.0
psycopg2-binary==2.9.10

# AI
openai==1.57.4

# Integrations
slack-sdk==3.33.5
gitpython>=3.1.0  # Planned

# Background Jobs
apscheduler==3.10.4
```

## Environment Configuration

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/sigma

# Qdrant (Vector Search)
QDRANT_URL=http://localhost:6333

# Neo4j (Knowledge Graph)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# LLM Configuration (choose one option below)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=  # Leave empty for direct OpenAI

# SIGMA Configuration
USER_ID=default-user
DEFAULT_APP_ID=sigma-default
LOG_LEVEL=INFO

# Feature Flags
GRAPHITI_ENABLED=true
PATTERN_LEARNING_ENABLED=false
RESEARCH_ENGINE_ENABLED=false

# Integrations
SLACK_BOT_TOKEN=xoxb-...
GITHUB_TOKEN=ghp_...  # Planned
```

### OpenRouter Configuration

SIGMA supports [OpenRouter](https://openrouter.ai) as an LLM gateway, giving you access to 100+ models from multiple providers through a single API.

```mermaid
flowchart LR
    SIGMA[SIGMA] --> |OPENAI_BASE_URL| OR[OpenRouter API]
    OR --> OPENAI[OpenAI<br/>GPT-4o, GPT-4o-mini]
    OR --> ANTH[Anthropic<br/>Claude 3.5 Sonnet]
    OR --> GOOGLE[Google<br/>Gemini Pro 1.5]
    OR --> META[Meta<br/>Llama 3.1]
    OR --> MISTRAL[Mistral<br/>Mixtral, Mistral Large]
```

**To use OpenRouter:**

1. Get an API key at [openrouter.ai/keys](https://openrouter.ai/keys)
2. Set environment variables:
```bash
OPENAI_API_KEY=sk-or-v1-your-openrouter-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

3. Update `config.json` with your preferred model:
```json
{
    "mem0": {
        "llm": {
            "provider": "openai",
            "config": {
                "model": "anthropic/claude-3.5-sonnet",
                "temperature": 0.1,
                "max_tokens": 2000,
                "api_key": "env:OPENAI_API_KEY",
                "openai_base_url": "env:OPENAI_BASE_URL"
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "openai/text-embedding-3-small",
                "api_key": "env:OPENAI_API_KEY",
                "openai_base_url": "env:OPENAI_BASE_URL"
            }
        }
    }
}
```

**Popular OpenRouter Models:**

| Model | Use Case | Cost |
|-------|----------|------|
| `openai/gpt-4o-mini` | Fast, general purpose | $ |
| `openai/gpt-4o` | Powerful reasoning | $$$ |
| `anthropic/claude-3.5-sonnet` | Excellent for code | $$ |
| `anthropic/claude-3-haiku` | Fast, cheap | $ |
| `google/gemini-pro-1.5` | Long context (1M tokens) | $$ |
| `meta-llama/llama-3.1-70b-instruct` | Open source | $ |

## Docker Compose Stack

```mermaid
flowchart TB
    subgraph Docker["Docker Compose Services"]
        APP[sigma-app<br/>Port: 8000]
        PG[postgres:15<br/>Port: 5432]
        QD[qdrant/qdrant<br/>Port: 6333]
        NEO[neo4j:latest<br/>Ports: 7474, 7687]
    end
    
    APP --> PG
    APP --> QD
    APP --> NEO
    
    PG --> PGV[(pgdata)]
    QD --> QDV[(qdrant_data)]
    NEO --> NEOV[(neo4j_data)]
```

```yaml
# docker/docker-compose.yaml (Updated)
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: sigma
      POSTGRES_PASSWORD: sigma
      POSTGRES_DB: sigma
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  neo4j:
    image: neo4j:latest
    environment:
      NEO4J_AUTH: neo4j/sigmapassword
      NEO4J_PLUGINS: '["apoc"]'
    ports:
      - "7474:7474"  # Browser
      - "7687:7687"  # Bolt
    volumes:
      - neo4j_data:/data

  sigma:
    build: 
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://sigma:sigma@postgres:5432/sigma
      - QDRANT_URL=http://qdrant:6333
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=sigmapassword
    depends_on:
      - postgres
      - qdrant
      - neo4j

volumes:
  pgdata:
  qdrant_data:
  neo4j_data:
```

## Multi-Cloud Deployment

### AWS Architecture

```mermaid
flowchart TB
    subgraph AWS["AWS Infrastructure"]
        subgraph Compute["Compute"]
            ECS[ECS Fargate]
            LAMBDA[Lambda<br/>Research Jobs]
        end
        
        subgraph Data["Data Layer"]
            RDS[(RDS PostgreSQL)]
            QDCLOUD[Qdrant Cloud]
            AURA[Neo4j Aura]
        end
        
        subgraph Support["Supporting Services"]
            SM[Secrets Manager]
            CW[CloudWatch]
            S3[S3 Backups]
        end
        
        ALB[Application<br/>Load Balancer] --> ECS
        ECS --> Data
        ECS --> Support
        LAMBDA --> Data
    end
    
    Route53[Route53] --> ALB
```

### DigitalOcean Architecture

```mermaid
flowchart TB
    subgraph DO["DigitalOcean"]
        subgraph App["App Platform"]
            SIGMA[SIGMA Service]
            WORKER[Worker Service<br/>Background Jobs]
        end
        
        subgraph Data["External Services"]
            DOPG[(Managed PostgreSQL)]
            QDCLOUD[Qdrant Cloud]
            AURA[Neo4j Aura]
        end
        
        App --> Data
    end
```

## Configuration Management

### Config File Structure
```json
{
  "sigma": {
    "version": "1.0.0",
    "features": {
      "graphiti": true,
      "pattern_learning": false,
      "research_engine": false,
      "cross_project": false
    }
  },
  "llm": {
    "provider": "openai",
    "config": {
      "model": "gpt-4o-mini",
      "temperature": 0.1
    }
  },
  "embedder": {
    "provider": "openai",
    "config": {
      "model": "text-embedding-3-small"
    }
  },
  "vector_store": {
    "provider": "qdrant",
    "config": {
      "url": "${QDRANT_URL}"
    }
  },
  "graph_store": {
    "provider": "neo4j",
    "config": {
      "uri": "${NEO4J_URI}",
      "user": "${NEO4J_USER}",
      "password": "${NEO4J_PASSWORD}"
    }
  }
}
```

## Access Points

| Endpoint | Description |
|----------|-------------|
| `http://localhost:8000` | API Server |
| `http://localhost:8000/docs` | OpenAPI Documentation |
| `http://localhost:8000/health` | Health Check |
| `http://localhost:8000/mcp/{client}/sse/{user}` | MCP SSE Connection |
| `http://localhost:7474` | Neo4j Browser |

## Project Structure

```
mcp-memory-server-sigma/
├── docker/
│   ├── docker-compose.yaml    # Full stack
│   ├── Dockerfile
│   └── entrypoint.sh
├── src/
│   └── openmemory/
│       ├── app/
│       │   ├── mcp_server.py          # MCP tools
│       │   ├── models.py              # SQLAlchemy models
│       │   ├── routers/
│       │   │   ├── memories.py
│       │   │   ├── apps.py
│       │   │   ├── graph.py           # NEW: Graph endpoints
│       │   │   └── intelligence.py    # NEW: Intelligence endpoints
│       │   └── utils/
│       │       ├── memory.py
│       │       ├── graphiti.py        # NEW: Graphiti client
│       │       ├── query_router.py    # NEW: Query routing
│       │       ├── git_integration.py # NEW: Git processing
│       │       └── pattern_learner.py # NEW: Pattern learning
│       └── alembic/                   # Database migrations
├── memory-bank/                       # Project documentation
├── aws/                               # AWS deployment
└── digitalocean/                      # DO deployment
```

## Performance Targets

```mermaid
gantt
    title Response Time Targets (milliseconds)
    dateFormat X
    axisFormat %s
    
    section Fast Path
    Health Check        :0, 50
    Vector Search       :0, 500
    Memory List         :0, 300
    
    section Graph Path
    Decision Query      :0, 2000
    Cross-Project       :0, 3000
    
    section Background
    Repo Ingestion      :0, 300000
    Morning Briefing    :0, 10000
```

| Operation | Target | Notes |
|-----------|--------|-------|
| Health check | < 50ms | Simple ping |
| Vector search | < 500ms | Qdrant query |
| Decision query | < 2s | Graph traversal |
| Cross-project search | < 3s | Multi-graph |
| Pattern suggestion | < 1s | Pattern engine |
| Morning briefing | < 10s | Aggregated |
| Repo ingestion | < 5min | 10K files |

## Security Considerations

### Data Privacy
- All code stays in your infrastructure
- Self-hostable with Docker Compose
- No data sent to external services except:
  - OpenAI for embeddings/LLM (can use local models)
  - Slack API (for Slack integration)
  - GitHub API (for GitHub integration)

### Secrets Management
- AWS: Secrets Manager
- DigitalOcean: App Platform secrets
- Local: .env file (gitignored)

### Access Control
- Per-user memory isolation
- ACL-based permissions
- API authentication via MCP context

## Debugging & Monitoring

### Log Levels
```python
# th_logging configuration
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Enable SQL logging
SQLALCHEMY_ECHO=true

# Enable Graphiti debug
GRAPHITI_DEBUG=true
```

### Key Log Locations
- Application: `docker compose logs sigma`
- PostgreSQL: `docker compose logs postgres`
- Neo4j: `docker compose logs neo4j`
- Qdrant: `docker compose logs qdrant`

### Health Monitoring
```bash
# Check all services
curl http://localhost:8000/health
curl http://localhost:6333/collections
curl http://localhost:7474  # Neo4j browser
```

## Development Workflow

### Local Setup
```bash
# Start all services
cd docker
docker compose up -d

# Run migrations
cd src/openmemory
alembic upgrade head

# Check logs
docker compose logs -f sigma
```

### Testing
```bash
# Run tests
pytest test/ -v

# Test MCP connection
curl -N "http://localhost:8000/mcp/test-client/sse/test-user"
```

### Database Operations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Technology Roadmap

```mermaid
timeline
    title SIGMA Technology Evolution
    
    section Current
        Foundation : PostgreSQL + Qdrant
                   : FastAPI + MCP
                   : Slack Integration
    
    section Phase 1
        Knowledge Graph : Graphiti + Neo4j
                       : Temporal Queries
                       : Decision Tracking
    
    section Phase 2
        Intelligence : Git Integration
                    : Pattern Learning
                    : Research Engine
    
    section Phase 3
        Advanced : Cross-Project Synthesis
                : IDE Extensions
                : Autonomous Agents
```
### AWS Deployment
