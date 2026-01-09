# System Patterns: SIGMA - The Self-Evolving Developer Intelligence System

## Architecture Overview

### Complete SIGMA Architecture

```mermaid
flowchart TB
    subgraph Clients["Developer Interfaces"]
        IDE[IDE Extension<br/>VSCode/JetBrains]
        CLI[CLI Tool]
        WEB[Web Dashboard]
        SLACK[Slack Bot]
    end
    
    subgraph Core["SIGMA Core"]
        MCP[MCP Server<br/>FastAPI + SSE]
        SCHEDULER[Autonomous Scheduler]
        WEBHOOK[Project Webhooks]
    end
    
    subgraph Intelligence["Intelligence Layer"]
        PATTERN[Pattern Learning Engine]
        RESEARCH[Research Engine]
        CROSS[Cross-Project Synthesizer]
        HEALTH[Code Health Monitor]
    end
    
    subgraph Knowledge["Graphiti Knowledge Graph"]
        GRAPHITI[Graphiti Core]
        NEO[Neo4j Graph DB]
    end
    
    subgraph Storage["Data Storage"]
        PG[PostgreSQL<br/>Source of Truth]
        QD[Qdrant<br/>Vector Search]
    end
    
    subgraph Sources["Data Sources"]
        GIT[Git Commits/PRs]
        JIRA[Jira/Linear]
        SLACKDATA[Slack History]
        WEBRES[Web Research]
    end
    
    Clients --> Core
    Core --> Intelligence
    Intelligence --> Knowledge
    Knowledge --> Storage
    Sources --> Intelligence
```

### Data Flow - Complete Pipeline

```mermaid
flowchart LR
    subgraph Input["Data Ingestion"]
        GIT[Git Events]
        SLACK[Slack Messages]
        MANUAL[Manual Input]
        RESEARCH[Web Research]
    end
    
    subgraph Process["Processing"]
        EXTRACT[Entity Extraction]
        RELATE[Relationship Mapping]
        TEMPORAL[Temporal Tagging]
        PATTERN[Pattern Detection]
    end
    
    subgraph Store["Storage"]
        GRAPH[Knowledge Graph]
        VECTOR[Vector Index]
        RELATIONAL[Relational DB]
    end
    
    subgraph Output["Intelligence"]
        QUERY[Query Answering]
        SUGGEST[Proactive Suggestions]
        ALERT[Alerts & Briefings]
    end
    
    Input --> Process --> Store --> Output
```

## Developer Entity Schema

### Neo4j Entity Types

```mermaid
erDiagram
    Project ||--o{ File : contains
    Project ||--o{ Decision : has
    Project ||--o{ Pattern : uses
    Project ||--o{ Library : depends_on
    
    File ||--o{ Function : defines
    File ||--o{ Class : defines
    
    Decision ||--o{ Rationale : justified_by
    Decision }o--o{ Commit : implemented_in
    Decision }o--o{ SlackMessage : discussed_in
    
    Pattern ||--o{ PatternInstance : instantiated_as
    Pattern }o--o{ Issue : solves
    
    Library ||--o{ SecurityAlert : has
    Library }o--o{ Pattern : enables
    
    Issue ||--o{ Solution : resolved_by
    Solution }o--o{ Commit : implemented_in
    
    Developer ||--o{ Commit : authored
    Developer ||--o{ Decision : made
    Developer ||--o{ Pattern : prefers
```

### Entity Definitions

```python
# Core Developer Entities (Neo4j Labels)

class Project:
    uuid: str
    name: str
    path: str
    language: str
    framework: str
    created_at: datetime
    last_active: datetime

class File:
    uuid: str
    path: str
    language: str
    purpose: str  # Extracted or inferred
    complexity: int
    last_modified: datetime

class Function:
    uuid: str
    name: str
    signature: str
    purpose: str
    complexity: int
    line_count: int
    test_coverage: float

class Decision:
    uuid: str
    title: str
    description: str
    rationale: str
    valid_from: datetime
    valid_to: datetime  # None if current
    confidence: float
    source: str  # git, slack, manual

class Pattern:
    uuid: str
    name: str
    description: str
    category: str  # error-handling, auth, caching, etc.
    code_template: str
    usage_count: int
    success_rate: float

class Library:
    uuid: str
    name: str
    version: str
    purpose: str
    added_at: datetime
    security_status: str  # ok, warning, critical

class Issue:
    uuid: str
    title: str
    description: str
    severity: str
    status: str  # open, resolved, recurring
    created_at: datetime
    resolved_at: datetime

class Commit:
    uuid: str
    sha: str
    message: str
    files_changed: int
    additions: int
    deletions: int
    created_at: datetime
```

### Relationship Types

```mermaid
flowchart TB
    subgraph Relationships["Neo4j Relationship Types"]
        direction TB
        R1[CONTAINS - Project → File]
        R2[DEPENDS_ON - Project → Library]
        R3[IMPLEMENTS - Commit → Decision]
        R4[SOLVES - Solution → Issue]
        R5[USES - File → Pattern]
        R6[REPLACES - Decision → Decision]
        R7[DISCUSSED_IN - Decision → SlackMessage]
        R8[PREFERS - Developer → Pattern]
        R9[CAUSED_BY - Issue → Commit]
        R10[SIMILAR_TO - Pattern → Pattern]
    end
```

```python
# Relationship definitions with temporal metadata

class Relationship:
    # All relationships track:
    valid_from: datetime      # When relationship became true
    valid_to: datetime        # When relationship ended (None = current)
    created_at: datetime      # When we learned about it
    confidence: float         # How confident we are (0-1)
    source: str              # How we learned (git, slack, inferred)

# Specific relationship types
CONTAINS = "contains"         # Project contains Files
DEPENDS_ON = "depends_on"     # Project depends on Library
IMPLEMENTS = "implements"     # Commit implements Decision
SOLVES = "solves"            # Solution solves Issue
USES = "uses"                # File uses Pattern
REPLACES = "replaces"        # Decision replaces older Decision
DISCUSSED_IN = "discussed_in" # Decision discussed in SlackMessage
PREFERS = "prefers"          # Developer prefers Pattern
CAUSED_BY = "caused_by"      # Issue caused by Commit
SIMILAR_TO = "similar_to"    # Pattern similar to Pattern
```

## Intelligence Layer Architecture

### Pattern Learning Engine

```mermaid
flowchart TB
    subgraph Input["Developer Actions"]
        CODE[Code Written]
        ACCEPT[Suggestions Accepted]
        REJECT[Suggestions Rejected]
        REFACTOR[Refactors Performed]
    end
    
    subgraph Learning["Pattern Learning"]
        DETECT[Pattern Detection]
        WEIGHT[Weight Adjustment]
        CLUSTER[Pattern Clustering]
        DOMAIN[Domain Specialization]
    end
    
    subgraph Output["Pattern Model"]
        PERSONAL[Personal Patterns]
        TEAM[Team Patterns]
        PROJECT[Project Patterns]
    end
    
    Input --> Learning --> Output
```

```python
# Pattern Learning Engine pseudocode

class PatternLearner:
    def on_code_written(self, code: str, context: Context):
        """Extract patterns from new code"""
        patterns = self.extract_patterns(code)
        for pattern in patterns:
            self.record_pattern_usage(pattern, context)
    
    def on_suggestion_accepted(self, suggestion: Suggestion):
        """Increase pattern weight"""
        pattern = suggestion.source_pattern
        pattern.success_count += 1
        pattern.weight = self.calculate_weight(pattern)
    
    def on_suggestion_rejected(self, suggestion: Suggestion):
        """Decrease pattern weight or learn why"""
        pattern = suggestion.source_pattern
        pattern.reject_count += 1
        # If rejected with reason, learn the exception
        if suggestion.reject_reason:
            self.learn_exception(pattern, suggestion.reject_reason)
    
    def get_suggestions(self, context: Context) -> List[Suggestion]:
        """Get relevant patterns for current context"""
        relevant = self.query_patterns(context)
        scored = self.score_patterns(relevant, context)
        return self.filter_by_threshold(scored)
```

### Autonomous Research Engine

```mermaid
flowchart TB
    subgraph Trigger["Research Triggers"]
        NEW_LIB[New Library Added]
        SCHEDULED[Nightly Schedule]
        SECURITY[Security Alert]
        QUESTION[Unanswered Question]
    end
    
    subgraph Research["Research Process"]
        IDENTIFY[Identify Topic]
        SEARCH[Web Search]
        DOCS[Read Documentation]
        GITHUB[Check GitHub Issues]
        SYNTH[Synthesize Findings]
    end
    
    subgraph Output["Knowledge Output"]
        ENTRY[Knowledge Entry]
        ALERT[Alert if Critical]
        SUGGEST[Suggestion if Relevant]
    end
    
    Trigger --> Research --> Output
```

```python
# Autonomous Research Engine

class ResearchEngine:
    async def nightly_scan(self):
        """Run nightly research on recent changes"""
        # 1. Get recent commits
        commits = await self.get_recent_commits(days=1)
        
        # 2. Identify new libraries
        new_libs = self.extract_new_libraries(commits)
        
        # 3. Research each library
        for lib in new_libs:
            knowledge = await self.research_library(lib)
            await self.store_knowledge(knowledge)
            
            # Check for security issues
            if knowledge.has_security_alerts:
                await self.create_alert(lib, knowledge.alerts)
        
        # 4. Check existing libraries for updates
        await self.check_security_advisories()
        
    async def research_library(self, lib: Library) -> Knowledge:
        """Research a library and build knowledge entry"""
        # Search multiple sources
        npm_info = await self.fetch_npm_info(lib)
        github_issues = await self.fetch_github_issues(lib)
        security_db = await self.check_security_db(lib)
        
        # Synthesize findings
        return Knowledge(
            entity=lib,
            description=npm_info.description,
            known_issues=github_issues.top_issues,
            security_status=security_db.status,
            best_practices=self.extract_best_practices(github_issues),
            alternatives=self.find_alternatives(lib)
        )
```

### Cross-Project Synthesizer

```mermaid
flowchart TB
    subgraph Projects["Your Projects"]
        P1[Project A]
        P2[Project B]
        P3[Project C]
    end
    
    subgraph Synthesis["Cross-Project Analysis"]
        COMMON[Common Patterns]
        TRANSFER[Transferable Solutions]
        CONFLICT[Conflict Detection]
    end
    
    subgraph Output["Intelligence"]
        REUSE[Reusable Code]
        LEARN[Lessons Learned]
        BEST[Best Practices]
    end
    
    Projects --> Synthesis --> Output
```

```python
# Cross-Project Synthesizer

class CrossProjectSynthesizer:
    def find_similar_patterns(self, context: Context) -> List[Pattern]:
        """Find patterns from other projects that match current context"""
        # 1. Extract context signature
        signature = self.extract_signature(context)
        
        # 2. Search all projects
        candidates = []
        for project in self.user_projects:
            patterns = self.query_project_patterns(project, signature)
            candidates.extend(patterns)
        
        # 3. Rank by similarity and success
        ranked = self.rank_patterns(candidates, context)
        
        return ranked[:10]
    
    def get_cross_project_solution(self, issue: Issue) -> Solution:
        """Find solution from another project for similar issue"""
        # 1. Find similar issues
        similar = self.find_similar_issues(issue)
        
        # 2. Get solutions
        solutions = []
        for sim_issue in similar:
            if sim_issue.solutions:
                solutions.extend(sim_issue.solutions)
        
        # 3. Adapt best solution
        if solutions:
            best = self.rank_solutions(solutions)[0]
            return self.adapt_solution(best, issue.context)
```

## Query Router Pattern

```mermaid
flowchart TB
    Q[Query Received] --> CLASSIFY{Classify Query}
    
    CLASSIFY -->|Simple Recall| FAST[Fast Path<br/>Qdrant Vector Search]
    CLASSIFY -->|Decision History| TEMPORAL[Temporal Path<br/>Graphiti Neo4j]
    CLASSIFY -->|Cross-Project| CROSS[Cross-Project Path<br/>Multi-Graph Query]
    CLASSIFY -->|Pattern Match| PATTERN[Pattern Path<br/>Pattern Engine]
    
    FAST --> MERGE[Merge Results]
    TEMPORAL --> MERGE
    CROSS --> MERGE
    PATTERN --> MERGE
    
    MERGE --> RANK[Rank & Filter]
    RANK --> RESPONSE[Response]
```

### Query Classification

```python
class QueryRouter:
    def classify_query(self, query: str, context: Context) -> QueryType:
        """Classify query to determine optimal path"""
        
        # Check for temporal keywords
        if self.has_temporal_markers(query):
            # "why did we", "when was", "history of"
            return QueryType.TEMPORAL
        
        # Check for cross-project keywords
        if self.has_cross_project_markers(query):
            # "in other projects", "have I solved", "similar to"
            return QueryType.CROSS_PROJECT
        
        # Check for pattern-related
        if self.has_pattern_markers(query):
            # "best practice", "how do I usually", "pattern for"
            return QueryType.PATTERN
        
        # Check for decision-related
        if self.has_decision_markers(query):
            # "why", "decided", "chose", "rationale"
            return QueryType.DECISION
        
        # Default to semantic search
        return QueryType.SEMANTIC
    
    async def route_query(self, query: str, context: Context) -> Response:
        """Route query to appropriate handler"""
        query_type = self.classify_query(query, context)
        
        handlers = {
            QueryType.TEMPORAL: self.handle_temporal_query,
            QueryType.CROSS_PROJECT: self.handle_cross_project_query,
            QueryType.PATTERN: self.handle_pattern_query,
            QueryType.DECISION: self.handle_decision_query,
            QueryType.SEMANTIC: self.handle_semantic_query,
        }
        
        return await handlers[query_type](query, context)
```

## MCP Tools Architecture

### Current Tools (Foundation)

```mermaid
flowchart LR
    subgraph Current["Current MCP Tools ✅"]
        ADD[add_memories]
        SEARCH[search_memory]
        LIST[list_memories]
        DELETE[delete_all_memories]
        SLACK1[load_slack_channel]
        SLACK2[search_slack_channels]
        SYNC[sync_vector_store]
    end
```

### New Developer Intelligence Tools

```mermaid
flowchart LR
    subgraph DevIntel["Developer Intelligence Tools 🔄"]
        direction TB
        INGEST[ingest_project]
        DECISION[track_decision]
        SEARCH_D[search_decisions]
        PATTERN[get_pattern_suggestions]
        CROSS[cross_project_search]
        BRIEF[get_morning_briefing]
        ANALYZE[analyze_code]
    end
```

### Tool Definitions

```python
# New MCP Tools for Developer Intelligence

@mcp.tool
async def ingest_project(repo_path: str, depth: str = "full") -> str:
    """
    Ingest a Git repository into the knowledge graph.
    
    Args:
        repo_path: Path to git repository
        depth: "shallow" (latest only) or "full" (all history)
    
    Creates entities for:
    - Files, functions, classes
    - Commit history and patterns
    - Library dependencies
    - README/documentation
    """
    pass

@mcp.tool
async def track_decision(
    title: str,
    description: str,
    rationale: str,
    related_files: List[str] = None,
    alternatives_considered: List[str] = None
) -> str:
    """
    Manually track an architectural or technical decision.
    
    Creates a Decision entity with relationships to:
    - Related files
    - Current context (project, branch, etc.)
    - Alternatives considered
    """
    pass

@mcp.tool
async def search_decisions(
    query: str,
    project: str = None,
    timeframe: str = None
) -> List[Decision]:
    """
    Search past decisions with temporal context.
    
    Examples:
    - "Why did we choose Redis?"
    - "Database decisions in last 6 months"
    - "Authentication architecture changes"
    """
    pass

@mcp.tool
async def get_pattern_suggestions(
    code_context: str,
    file_path: str = None
) -> List[Suggestion]:
    """
    Get pattern suggestions based on current code context.
    
    Analyzes:
    - Current code structure
    - Your historical patterns
    - Cross-project patterns
    - Team patterns (if applicable)
    """
    pass

@mcp.tool
async def cross_project_search(
    query: str,
    include_projects: List[str] = None
) -> List[Result]:
    """
    Search across all your projects for solutions.
    
    Examples:
    - "Stripe webhook implementation"
    - "Rate limiting pattern"
    - "Similar bug to this error"
    """
    pass

@mcp.tool
async def get_morning_briefing() -> Briefing:
    """
    Get proactive morning briefing with:
    - Security alerts for dependencies
    - Pattern violations in recent code
    - Interesting findings from research
    - Suggestions for improvement
    """
    pass

@mcp.tool
async def analyze_code(
    code: str,
    analysis_type: str = "all"
) -> Analysis:
    """
    Analyze code against learned patterns.
    
    analysis_type options:
    - "patterns": Match against known patterns
    - "issues": Find potential bugs from history
    - "improvements": Suggest improvements
    - "all": All of the above
    """
    pass
```

## Data Source Integrations

### Git Integration

```mermaid
sequenceDiagram
    participant Git as Git Repository
    participant Hook as Webhook/Watcher
    participant Proc as Processor
    participant KG as Knowledge Graph
    
    Git->>Hook: Commit pushed
    Hook->>Proc: Process commit
    Proc->>Proc: Extract entities
    Note over Proc: Files changed<br/>Functions modified<br/>Libraries added<br/>Patterns detected
    Proc->>KG: Create/update entities
    Proc->>KG: Create relationships
    Note over KG: Commit MODIFIES File<br/>Commit ADDS Library<br/>Commit IMPLEMENTS Decision
```

```python
# Git Integration

class GitIntegration:
    async def process_commit(self, commit: GitCommit):
        """Process a git commit and extract knowledge"""
        # 1. Extract changed files
        for file in commit.files:
            await self.process_file_change(file, commit)
        
        # 2. Detect new libraries
        if commit.affects("package.json", "requirements.txt", "Gemfile"):
            await self.process_dependency_changes(commit)
        
        # 3. Extract patterns from message
        patterns = self.extract_patterns_from_message(commit.message)
        
        # 4. Link to related decisions
        decisions = self.find_related_decisions(commit)
        
        # 5. Store in knowledge graph
        await self.store_commit_knowledge(commit, patterns, decisions)
    
    async def ingest_repository(self, repo_path: str):
        """Full repository ingestion"""
        repo = git.Repo(repo_path)
        
        # Process all commits
        for commit in repo.iter_commits():
            await self.process_commit(commit)
        
        # Analyze code patterns
        await self.analyze_codebase_patterns(repo_path)
        
        # Extract documentation
        await self.extract_documentation(repo_path)
```

### Slack Integration (Enhanced)

```mermaid
flowchart TB
    subgraph SlackData["Slack Data"]
        MSG[Messages]
        THREAD[Threads]
        REACT[Reactions]
    end
    
    subgraph Processing["Decision Extraction"]
        DETECT[Detect Decision Discussions]
        EXTRACT[Extract Rationale]
        LINK[Link to Code]
    end
    
    subgraph Output["Knowledge"]
        DECISION[Decision Entity]
        RATIONALE[Rationale Entity]
        RELATION[Code Relationships]
    end
    
    SlackData --> Processing --> Output
```

```python
# Enhanced Slack Integration for Decisions

class SlackDecisionExtractor:
    decision_patterns = [
        r"we decided to",
        r"let's go with",
        r"the plan is to",
        r"after discussing",
        r"agreed on",
        r"rationale:",
        r"because we need",
    ]
    
    async def extract_decisions(self, messages: List[Message]) -> List[Decision]:
        """Extract decisions from Slack messages"""
        decisions = []
        
        for msg in messages:
            if self.is_decision_message(msg):
                decision = Decision(
                    title=self.extract_title(msg),
                    description=self.extract_description(msg),
                    rationale=self.extract_rationale(msg.thread),
                    discussed_in=msg,
                    participants=self.get_thread_participants(msg),
                    valid_from=msg.timestamp,
                )
                decisions.append(decision)
        
        return decisions
```

## Graceful Degradation

```mermaid
flowchart TB
    Q[Query] --> CHECK{Check Systems}
    
    CHECK -->|All Available| FULL[Full Intelligence]
    CHECK -->|Neo4j Down| PARTIAL[Vector + PostgreSQL]
    CHECK -->|Qdrant Down| GRAPH[Graph + PostgreSQL]
    CHECK -->|Both Down| BASIC[PostgreSQL Only]
    
    FULL --> R[Response with full context]
    PARTIAL --> R
    GRAPH --> R
    BASIC --> R
    
    style FULL fill:#90EE90
    style PARTIAL fill:#FFD700
    style GRAPH fill:#FFD700
    style BASIC fill:#FFA500
```

## Multi-Cloud Deployment

```mermaid
flowchart TB
    subgraph Local["Local Development"]
        DC[Docker Compose]
        DC --> PG1[PostgreSQL]
        DC --> QD1[Qdrant]
        DC --> NEO1[Neo4j]
        DC --> APP1[SIGMA App]
    end
    
    subgraph AWS["AWS Production"]
        ECS[ECS Fargate]
        ECS --> RDS[RDS PostgreSQL]
        ECS --> QDCLOUD[Qdrant Cloud]
        ECS --> AURA[Neo4j Aura]
    end
    
    subgraph DO["DigitalOcean"]
        DOAPP[App Platform]
        DOAPP --> DOPG[Managed PostgreSQL]
        DOAPP --> QDCLOUD
        DOAPP --> AURA
    end
```

## Performance Targets

| Operation | Target Latency | Description |
|-----------|---------------|-------------|
| Simple memory search | < 500ms | Vector search in Qdrant |
| Decision history query | < 2s | Temporal graph traversal |
| Cross-project search | < 3s | Multi-graph query |
| Pattern suggestion | < 1s | Pattern engine lookup |
| Full repo ingestion | < 5min | 10K file repository |
| Morning briefing | < 10s | Aggregated intelligence |
