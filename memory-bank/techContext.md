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
    
    subgraph Phase2["Phase 2: Git Integration ✅"]
        GIT[GitPython 3.1.46]
        ANALYZER[GitProjectAnalyzer]
        DEPS[Dependency Detection]
    end
    
    subgraph Phase3["Phase 3: Multi-Agent System 🔄"]
        AGENTS[5 Worker Agents]
        DREAMER[DreamerMetaAgent]
        DOCKER[Docker Executor]
        GITHUB[GitHub API]
    end
    
    Current --> Phase1 --> Phase2 --> Phase3
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

# Knowledge Graph (Phase 1)
graphiti-core>=0.5.0
neo4j>=5.0.0

# Database
sqlalchemy==2.0.36
alembic==1.14.0
psycopg2-binary==2.9.10

# AI
openai==1.57.4

# Integrations (Phase 2)
slack-sdk==3.33.5
gitpython==3.1.46  # ✅ Installed

# Multi-Agent System (Phase 3) - Planned
# docker>=7.0.0  # Container execution
# PyGithub>=2.0.0  # GitHub API
# radon>=6.0.0  # Code complexity metrics

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

**Root Level:**
- `docker/` - Docker configuration (compose, Dockerfile, entrypoint)
- `src/openmemory/` - Main application code
- `memory-bank/` - Project documentation
- `aws/` - AWS deployment configuration
- `digitalocean/` - DigitalOcean deployment

**Application (`src/openmemory/app/`):**
- `mcp_server.py` - MCP tools implementation
- `models.py` - SQLAlchemy database models
- `routers/` - FastAPI route handlers
  - `memories.py` - Memory CRUD endpoints
  - `apps.py` - Application management
  - `graph.py` - Knowledge graph endpoints
  - `intelligence.py` - Intelligence features

**Utilities (`src/openmemory/app/utils/`):**
- `memory.py` - Memory operations
- `graphiti.py` - Graphiti client integration
- `query_router.py` - Query routing logic
- `git_integration.py` - Git repository processing
- `pattern_learner.py` - Pattern learning system

**Database:**
- `alembic/` - Database migrations and versioning

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

## Multi-Agent System Architecture (Phase 3)

### Worker Thread Model

```python
# Threading architecture for 5 workers

class WorkerController:
    """Manages all worker threads"""
    def __init__(self):
        self.workers: List[BaseWorker] = []
        self.dreamer = DreamerMetaAgent()
        
    def start_all(self):
        """Start all 5 workers in background threads"""
        self.workers = [
            AnalysisWorker(self.db, self.dreamer),
            DreamWorker(self.db, self.dreamer),
            RecallWorker(self.db, self.dreamer),
            LearningWorker(self.db, self.dreamer),
            ThinkWorker(self.db, self.dreamer)
        ]
        
        for worker in self.workers:
            worker.start()
    
    def stop_all(self):
        """Graceful shutdown of all workers"""
        for worker in self.workers:
            worker.stop()
        
        for worker in self.workers:
            worker.thread.join(timeout=10)
```

### Database Schema for Agents

```python
# New tables added in Phase 3

class Project(Base):
    """Track multiple projects for cross-learning"""
    __tablename__ = "projects"
    
    project_id = Column(Integer, primary_key=True)
    repo_url = Column(String, nullable=False)
    branch = Column(String, default="main")
    workspace_path = Column(String)
    language = Column(String)  # python, javascript, etc.
    framework = Column(String)  # django, react, etc.
    domain = Column(String)  # ecommerce, saas, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    last_analyzed = Column(DateTime)

class CodeSnapshot(Base):
    """Store analysis results over time"""
    __tablename__ = "code_snapshots"
    
    snapshot_id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    complexity = Column(Float)
    test_coverage = Column(Float)
    issues_found = Column(Integer)
    metrics_json = Column(Text)  # JSON with detailed metrics
    created_at = Column(DateTime, default=datetime.utcnow)

class Proposal(Base):
    """Agent committee decisions"""
    __tablename__ = "proposals"
    
    proposal_id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"))
    title = Column(String, nullable=False)
    description = Column(Text)
    agents_json = Column(Text)  # Which agents participated
    changes_json = Column(Text)  # Proposed changes
    confidence = Column(Float)
    critic_score = Column(Float)
    status = Column(String)  # pending, approved, rejected, executed
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime)
    pr_url = Column(String)
    commit_sha = Column(String)

class Experiment(Base):
    """Track dreaming experiments"""
    __tablename__ = "experiments"
    
    experiment_id = Column(Integer, primary_key=True)
    worker_name = Column(String, nullable=False)
    experiment_name = Column(String)
    hypothesis = Column(Text)
    approach = Column(Text)
    baseline_metrics = Column(Text)
    result_metrics = Column(Text)
    success = Column(Boolean)
    improvement = Column(Float)  # % improvement
    promoted_to_production = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class LearnedPattern(Base):
    """Cross-project pattern library"""
    __tablename__ = "learned_patterns"
    
    pattern_id = Column(Integer, primary_key=True)
    pattern_name = Column(String, nullable=False)
    pattern_type = Column(String)  # error_handling, auth, caching, etc.
    description = Column(Text)
    code_template = Column(Text)
    language = Column(String)
    framework = Column(String)
    domain = Column(String)
    confidence = Column(Float)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)

class WorkerStats(Base):
    """Performance tracking for workers"""
    __tablename__ = "worker_stats"
    
    stat_id = Column(Integer, primary_key=True)
    worker_name = Column(String, nullable=False)
    cycles_run = Column(Integer, default=0)
    experiments_run = Column(Integer, default=0)
    total_time = Column(Float, default=0.0)
    errors = Column(Integer, default=0)
    last_run = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Execution Infrastructure

```python
# Docker execution for safe code changes

class DockerExecutor:
    """Execute code changes in isolated Docker containers"""
    
    def __init__(self):
        self.client = docker.from_env()
    
    def create_project_container(self, project_id: int, workspace: str) -> str:
        """Create isolated container for project"""
        container = self.client.containers.run(
            image="python:3.11-slim",
            command="sleep infinity",
            detach=True,
            volumes={workspace: {'bind': '/workspace', 'mode': 'rw'}},
            working_dir='/workspace',
            network_mode='bridge'
        )
        return container.id
    
    def execute_in_container(self, container_id: str, command: str) -> dict:
        """Execute command in container and return result"""
        container = self.client.containers.get(container_id)
        exit_code, output = container.exec_run(command)
        
        return {
            'exit_code': exit_code,
            'output': output.decode('utf-8'),
            'success': exit_code == 0
        }
    
    def run_tests(self, container_id: str) -> dict:
        """Run test suite in container"""
        # Detect test framework
        framework = self._detect_test_framework(container_id)
        
        # Run appropriate test command
        if framework == 'pytest':
            result = self.execute_in_container(container_id, 'pytest --cov --json')
        elif framework == 'jest':
            result = self.execute_in_container(container_id, 'npm test -- --coverage --json')
        else:
            result = {'success': False, 'error': 'Unknown test framework'}
        
        return result
    
    def cleanup_container(self, container_id: str):
        """Stop and remove container"""
        container = self.client.containers.get(container_id)
        container.stop()
        container.remove()
```

### Git/GitHub Operations

```python
# Git operations for autonomous commits and PRs

class GitOperations:
    """Handle Git and GitHub operations"""
    
    def __init__(self, repo_path: str, token: str):
        self.repo = git.Repo(repo_path)
        self.gh = Github(token)
    
    def create_branch(self, branch_name: str) -> bool:
        """Create new feature branch"""
        try:
            self.repo.git.checkout('-b', branch_name)
            return True
        except Exception as e:
            logger.error(f"Failed to create branch: {e}")
            return False
    
    def commit_changes(self, files: List[str], message: str) -> str:
        """Stage and commit changes"""
        self.repo.index.add(files)
        commit = self.repo.index.commit(message)
        return commit.hexsha
    
    def push_branch(self, branch_name: str) -> bool:
        """Push branch to remote"""
        try:
            origin = self.repo.remote('origin')
            origin.push(branch_name)
            return True
        except Exception as e:
            logger.error(f"Failed to push branch: {e}")
            return False
    
    def create_pr(self, branch_name: str, title: str, body: str) -> str:
        """Create pull request"""
        repo_full_name = self._get_repo_full_name()
        gh_repo = self.gh.get_repo(repo_full_name)
        
        pr = gh_repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base='main'
        )
        
        return pr.html_url
    
    def merge_pr(self, pr_number: int) -> bool:
        """Merge pull request"""
        repo_full_name = self._get_repo_full_name()
        gh_repo = self.gh.get_repo(repo_full_name)
        
        pr = gh_repo.get_pull(pr_number)
        result = pr.merge(merge_method='squash')
        
        return result.merged
```

## Technology Roadmap

```mermaid
timeline
    title SIGMA Technology Evolution
    
    section Phase 1 (Complete)
        Foundation : PostgreSQL + Qdrant
                   : FastAPI + MCP
                   : Slack Integration
        Knowledge Graph : Graphiti + Neo4j
                       : Temporal Queries
                       : Decision Tracking
    
    section Phase 2 (Complete)
        Git Integration : GitPython 3.1.46
                       : Repository Analysis
                       : Dependency Detection
    
    section Phase 3 (In Progress)
        Multi-Agent System : 5 Worker Agents
                          : DreamerMetaAgent
                          : Experimentation
        
    section Phase 4 (Planned)
        Execution Layer : Docker Executor
                       : GitHub Operations
                       : Test Runner
        Advanced : Cross-Project Learning
                : Web UI Dashboard
                : IDE Extensions
```

## Agent System Configuration

### Environment Variables (Phase 3)

```bash
# ========================================
# AGENT AUTONOMY CONFIGURATION
# ========================================
AGENT_AUTONOMY_LEVEL=1  # 1=Propose, 2=Auto-commit, 3=Auto-merge
AGENT_MIN_CONFIDENCE_LEVEL_1=0.70  # Level 1 threshold
AGENT_MIN_CONFIDENCE_LEVEL_2=0.80  # Level 2 threshold
AGENT_MIN_CONFIDENCE_LEVEL_3=0.90  # Level 3 threshold
AGENT_CAN_COMMIT=false
AGENT_CAN_MERGE_PR=false

# ========================================
# PROJECT CONFIGURATION
# ========================================
PROJECT_REPO_URL=https://github.com/user/repo.git
PROJECT_BRANCH=main
PROJECT_WORKSPACE=/workspace/project
GITHUB_TOKEN=ghp_your_token_here

# ========================================
# WORKER INTERVALS (seconds)
# ========================================
AGENT_ANALYSIS_WORKER_INTERVAL=300  # 5 minutes
AGENT_DREAM_WORKER_INTERVAL=240     # 4 minutes
AGENT_RECALL_WORKER_INTERVAL=180    # 3 minutes
AGENT_LEARNING_WORKER_INTERVAL=360  # 6 minutes
AGENT_THINK_WORKER_INTERVAL=480     # 8 minutes

# ========================================
# EVOLUTION SETTINGS
# ========================================
AGENT_EVOLUTION_RATE=0.15  # 15% of cycles are experimental
AGENT_EXPERIMENT_SUCCESS_THRESHOLD=0.20  # 20% improvement to promote

# ========================================
# DOCKER EXECUTION
# ========================================
AGENT_DOCKER_IMAGE=python:3.11-slim
AGENT_TEST_TIMEOUT=300  # 5 minutes
AGENT_BUILD_TIMEOUT=600  # 10 minutes

# ========================================
# AGENT COMMITTEE (weights sum to 1.0)
# ========================================
AGENT_COMMITTEE_ARCHITECT_WEIGHT=0.25
AGENT_COMMITTEE_REVIEWER_WEIGHT=0.20
AGENT_COMMITTEE_TESTER_WEIGHT=0.20
AGENT_COMMITTEE_SECURITY_WEIGHT=0.20
AGENT_COMMITTEE_OPTIMIZER_WEIGHT=0.15

# ========================================
# CROSS-PROJECT LEARNING
# ========================================
AGENT_CROSS_PROJECT_ENABLED=true
AGENT_MIN_LANGUAGE_SIMILARITY=0.80
AGENT_MIN_FRAMEWORK_SIMILARITY=0.70
AGENT_MIN_DOMAIN_SIMILARITY=0.60

# ========================================
# EXTERNAL INTELLIGENCE
# ========================================
AGENT_CONTEXT7_ENABLED=false  # Documentation lookup
AGENT_PLAYWRIGHT_ENABLED=false  # Web research
```

## Project Structure Updates (Phase 3)

**Agent System (`src/openmemory/app/`):**
- `agent_config.py` ✅ - Agent configuration dataclasses
- `agents/` ✅ - Agent system package
  - `__init__.py` ✅
  - `base_worker.py` ✅ - BaseWorker abstract class
  - `dreamer.py` ✅ - DreamerMetaAgent orchestrator
  - `analysis_worker.py` ⏳ - Code analysis worker
  - `dream_worker.py` ⏳ - Knowledge graph worker
  - `recall_worker.py` ⏳ - Semantic search worker
  - `learning_worker.py` ⏳ - Pattern learning worker
  - `think_worker.py` ⏳ - Multi-agent committee worker

**Utilities (`src/openmemory/app/utils/`):**
- `docker_executor.py` ✅ - Docker container execution
- `git_operations.py` ✅ - Git/GitHub operations
- `cross_project.py` ✅ - Cross-project learning
- `test_runner.py` ⏳ - Test execution (TODO)

**Database:**
- `alembic/versions/add_agent_system_tables.py` ✅ - 7 new agent tables

### AWS Deployment
