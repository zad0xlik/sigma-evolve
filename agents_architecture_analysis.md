# SIGMA Agent Architecture - Complete Analysis

## Current Architecture Overview

### Agent Hierarchy
```
DreamerMetaAgent (Meta-level)
    ├── ThinkWorker (Decision-making, committee scoring)
    ├── LearningWorker (Pattern extraction, cross-project learnings)
    ├── AnalysisWorker (Code quality, complexity, issues)
    ├── DreamWorker (Proposal generation)
    └── RecallWorker (Knowledge retrieval)
```

### Core Components

#### 1. **Base Worker** (`base_worker.py`)
- Foundation class for all workers
- Threading with configurable intervals
- Statistics tracking (success/failure counts, error rates)
- Error handling with exponential backoff
- Worker state management (running, paused, error)

#### 2. **Agent Config** (`agent_config.py`)
Centralized configuration system with 7 dataclasses:
- **AutonomyConfig**: Worker autonomy levels (0-1)
- **ProjectConfig**: Repository and workspace settings
- **WorkerConfig**: Intervals, evolution rates, model settings
- **ExecutionConfig**: Risk thresholds, approval requirements
- **CrossProjectConfig**: Similarity thresholds, language matching
- **AgentCommitteeConfig**: Committee member weights for scoring
- **ExternalIntelligenceConfig**: LLM integration settings

#### 3. **Multi-Agent Committee Pattern**
Used in ThinkWorker and DreamWorker:
- **Architect**: Code structure and design (weight: 0.25)
- **Reviewer**: Code quality and standards (weight: 0.20)
- **Tester**: Test coverage and reliability (weight: 0.25)
- **Security**: Security implications (weight: 0.15)
- **Optimizer**: Performance considerations (weight: 0.15)

Weighted confidence = Σ(agent_score × weight)

#### 4. **Graphiti Integration**
All workers integrate with Graphiti/Neo4j knowledge graph:

**ThinkWorker**:
- Queries historical decisions for risk assessment
- Searches for similar past proposals
- Assesses pattern quality based on historical outcomes
- Adjusts confidence based on historical success rates

**LearningWorker**:
- Queries pattern history for quality assessment
- Stores learned patterns in knowledge graph
- Tracks pattern outcomes over time
- Assesses pattern quality (success rate, establishment level)

**AnalysisWorker**:
- Queries issue history for severity assessment
- Learns from historical issue patterns
- Tracks which issues lead to failures
- Adjusts issue severity based on historical outcomes

**DreamWorker**:
- Queries historical fix patterns for proposals
- Learns from successful and failed fixes
- Stores fix patterns in knowledge graph
- Adjusts proposal confidence based on historical success

**RecallWorker**:
- Queries knowledge graph for relevant entities/facts
- Searches for decisions, patterns, dependencies
- Retrieves cross-project insights
- Enriches proposals with contextual information

#### 5. **Experimentation Framework**
**DreamerMetaAgent** orchestrates:
- **Evolution Rate**: 15% chance per cycle to experiment
- **Experiment Generation**: LLM proposes novel approaches
- **Outcome Tracking**: Success/failure with improvement metrics
- **Promotion Mechanism**: Auto-promote >20% improvement
- **Knowledge Sharing**: Successful patterns cached in-memory

**Worker Integration**:
- Each worker checks for promoted experiments
- Adopts new strategies when available
- Tracks current strategy for comparison
- Reports experiment context to Dreamer

#### 6. **Cross-Project Learning**
**LearningWorker**:
- Records patterns with project context
- Calculates project similarity (language, framework)
- Suggests patterns to similar projects
- Tracks pattern application success

**ThinkWorker**:
- Queries cross-project learnings for risk assessment
- Uses similarity scores to weight historical outcomes
- Adjusts confidence based on cross-project success rates

**RecallWorker**:
- Retrieves cross-project insights for context enrichment
- Filters by similarity threshold
- Aggregates insights from multiple sources

## Current Prompts and Query Patterns

### ThinkWorker Prompts

#### Multi-Agent Committee Decision
```
System: "You are an expert committee member. Score the proposal 0-1 considering:
- Technical feasibility
- Risk level
- Business value
- Implementation complexity
- Test coverage

Return JSON: {"score": 0.85, "confidence": 0.90, "risks": ["...", "..."]}"
```

#### Risk Assessment Query
```python
search_decisions(
    query=f"risk assessment for {change_type} in {description[:100]}",
    limit=10
)
```

#### Historical Knowledge Query
```python
search_decisions(
    query=f"outcome of {change_type} decision pattern",
    limit=15
)
```

### LearningWorker Prompts

#### Pattern Quality Assessment
```python
search_decisions(
    query=f"pattern for {change_type} in {description[:100]}",
    limit=15
)
```

Pattern quality factors:
- Historical success rate (>0.7 = +0.08, <0.3 = -0.10)
- Similar pattern count (>=10 = +0.05, ==0 = -0.03)
- Consistency (0.3-0.7 = -0.15 for controversy)
- Context richness (>=3 facts = +0.05)

### AnalysisWorker Prompts

#### Issue Severity Assessment
```python
search_decisions(
    query="issue in {filename}",
    limit=5
)
```

Additional queries:
- "mutable default argument"
- "bare except clause"
- "missing type hint"

### DreamWorker Prompts

#### Error Fix Proposal
```
System: "You are an expert software engineer specialized in fixing code issues.
Your task is to analyze code issues and generate specific code fixes, learning from historical patterns.

Respond with JSON containing:
{
  "title": "Brief title",
  "description": "Detailed explanation",
  "confidence": 0.0-1.0,
  "changes": [
    {
      "file": "path/to/file.py",
      "original": "code to replace",
      "fixed": "corrected code",
      "explanation": "why this fixes it"
    }
  ],
  "testing_strategy": "Verification approach",
  "historical_lessons": "What was learned"
}"
```

Historical context query:
```python
search_decisions(
    query=f"{issue_type} fix pattern",
    limit=5
)
```

#### Warning Fix Proposal
Similar structure with focus on code quality improvements.

### RecallWorker Query Patterns

#### Knowledge Graph Search
```python
search_decisions(
    query=search_query,
    limit=10
)
```

Query construction:
- Type mapping: database_migration → "database migration decision"
- Keyword extraction from description
- Pattern matching for entities

### DreamerMetaAgent Prompts

#### Experiment Generation
```
System: "You are the Dreamer for the {worker_name} worker in SIGMA.
Your role is to propose novel experimental approaches.

Guidelines:
1. Experiments should be SAFE (won't break existing functionality)
2. Must have MEASURABLE outcomes
3. Should have a clear ROLLBACK plan
4. Balance innovation with risk
5. Learn from past successes and failures

Respond in JSON format:
{
  "experiment_name": "descriptive name",
  "hypothesis": "what you think will happen",
  "approach": "detailed implementation steps",
  "metrics": ["metric1", "metric2"],
  "risk_level": "low|medium|high",
  "rollback_plan": "how to undo if it fails",
  "confidence": 0.0-1.0
}"
```

## Current Workflow

1. **AnalysisWorker** analyzes code → stores snapshot
2. **DreamWorker** generates proposals from snapshots → stores proposals
3. **RecallWorker** enriches proposals with context → updates proposals
4. **ThinkWorker** scores proposals with committee → updates scores
5. **LearningWorker** extracts patterns from executed proposals → stores patterns
6. **DreamerMetaAgent** tracks outcomes → promotes successful experiments
7. Workers adopt promoted experiments → system evolves

## Key Observations

### Strengths
1. **Multi-agent collaboration**: Committee scoring reduces individual bias
2. **Historical learning**: All workers use Graphiti for context
3. **Experimentation framework**: Autonomous improvement via Dreamer
4. **Cross-project learning**: Pattern sharing across projects
5. **Graceful degradation**: Graphiti failures don't break workers
6. **Configurable autonomy**: Fine-grained control via AgentConfig

### Limitations
1. **Prompts are hardcoded**: Difficult to adjust without code changes
2. **No UI for prompt management**: Requires developer intervention
3. **Limited cross-worker communication**: Primarily via database
4. **No shared prompt library**: Each worker has independent prompts
5. **Static experimentation**: Fixed evolution rate (15%)
6. **No prompt versioning**: Cannot track prompt changes over time

### Opportunities for Enhancement
1. **Centralized prompt management**: Extract prompts to configurable store
2. **Cross-worker knowledge sharing**: Direct worker-to-worker protocols
3. **Dynamic experimentation**: User-configurable evolution strategies
4. **Prompt library**: Reusable prompt templates with versioning
5. **Real-time collaboration**: Shared context via Graphiti updates
6. **Experimentation UI**: Visual experimentation configuration
