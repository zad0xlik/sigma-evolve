# Cross-Project Learning System

The Cross-Project Learning System enables SIGMA to extract successful patterns from one project and apply them to similar projects, dramatically accelerating the learning and improvement cycle across multiple codebases.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Usage Examples](#usage-examples)
5. [Integration with Workers](#integration-with-workers)
6. [Pattern Types](#pattern-types)
7. [Similarity Calculation](#similarity-calculation)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

### What is Cross-Project Learning?

Cross-Project Learning is SIGMA's knowledge transfer mechanism that:

1. **Extracts Patterns**: Learns from successful proposals and extracts reusable patterns
2. **Calculates Similarity**: Determines which projects are similar based on language, framework, and domain
3. **Recommends Patterns**: Suggests relevant patterns from similar projects
4. **Tracks Effectiveness**: Monitors pattern success rates and adjusts confidence scores
5. **Evolves Over Time**: Patterns improve as more data is collected

### Key Benefits

- **Faster Learning**: New projects benefit from patterns learned in similar projects
- **Knowledge Reuse**: Successful improvements are automatically shared
- **Risk Reduction**: High-confidence patterns reduce experimental risk
- **Continuous Improvement**: Pattern confidence evolves based on outcomes

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Cross-Project Learning System                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐     ┌───────────────┐     ┌────────────┐ │
│  │   Pattern    │────▶│  Similarity   │────▶│  Pattern   │ │
│  │  Extraction  │     │  Calculator   │     │ Recommender│ │
│  └──────────────┘     └───────────────┘     └────────────┘ │
│         │                     │                     │        │
│         ▼                     ▼                     ▼        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │             LearnedPattern Database                   │  │
│  │  - Pattern name, type, code template                  │  │
│  │  - Language, framework, domain                        │  │
│  │  - Confidence, success/failure counts                 │  │
│  └──────────────────────────────────────────────────────┘  │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        CrossProjectLearning Database                  │  │
│  │  - Source/target project mapping                      │  │
│  │  - Pattern application tracking                       │  │
│  │  - Similarity scores                                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### CrossProjectLearningSystem

The main class that orchestrates all cross-project learning operations.

```python
from sqlalchemy.orm import Session
from openmemory.app.utils.cross_project import CrossProjectLearningSystem

# Initialize
db: Session = get_db_session()
xp_system = CrossProjectLearningSystem(db)
```

### Data Classes

#### PatternMatch
```python
@dataclass
class PatternMatch:
    pattern_id: int
    pattern_name: str
    pattern_type: str
    description: str
    code_template: str
    confidence: float
    similarity_score: float
    source_project_id: int
    success_rate: float
    usage_count: int
```

#### ProjectSimilarity
```python
@dataclass
class ProjectSimilarity:
    project_id: int
    repo_url: str
    language: str
    framework: Optional[str]
    domain: Optional[str]
    similarity_score: float
    language_match: bool
    framework_match: bool
    domain_match: bool
```

## Usage Examples

### Example 1: Extract Pattern from Successful Proposal

When a proposal succeeds, extract a pattern for future use:

```python
from openmemory.app.utils.cross_project import CrossProjectLearningSystem
from openmemory.app.models import Proposal

# Get successful proposal
proposal = db.query(Proposal).filter(
    Proposal.proposal_id == 42,
    Proposal.status == 'executed',
).first()

# Initialize system
xp_system = CrossProjectLearningSystem(db)

# Extract pattern
pattern = xp_system.extract_pattern_from_proposal(
    proposal=proposal,
    pattern_name="Add Error Handling",
    pattern_type="refactoring",
    description="Wrap risky operations in try-except blocks with proper logging",
)

print(f"✅ Extracted pattern: {pattern.pattern_name}")
print(f"   Confidence: {pattern.confidence:.2f}")
print(f"   Language: {pattern.language}")
```

### Example 2: Find Similar Projects

Discover projects similar to your current project:

```python
# Find similar projects
similar_projects = xp_system.find_similar_projects(
    project_id=1,
    min_similarity=0.5,  # 50% similarity threshold
    limit=10,
)

for proj in similar_projects:
    print(f"Project {proj.project_id}: {proj.repo_url}")
    print(f"  Similarity: {proj.similarity_score:.2f}")
    print(f"  Language match: {proj.language_match}")
    print(f"  Framework match: {proj.framework_match}")
    print(f"  Domain match: {proj.domain_match}")
```

### Example 3: Get Pattern Recommendations

Get relevant patterns for a project:

```python
# Get pattern recommendations
patterns = xp_system.suggest_patterns_for_project(
    project_id=1,
    pattern_types=["refactoring", "optimization"],
    min_confidence=0.6,  # Only high-confidence patterns
    limit=20,
)

for pattern in patterns:
    print(f"Pattern: {pattern.pattern_name}")
    print(f"  Type: {pattern.pattern_type}")
    print(f"  Confidence: {pattern.confidence:.2f}")
    print(f"  Similarity: {pattern.similarity_score:.2f}")
    print(f"  Success Rate: {pattern.success_rate:.1%}")
    print(f"  Used {pattern.usage_count} times")
    print()
```

### Example 4: Track Pattern Application

Record when a pattern is applied:

```python
# Record pattern suggestion
learning = xp_system.record_pattern_application(
    source_project_id=5,   # Where pattern was learned
    target_project_id=1,   # Where pattern is being applied
    pattern_id=42,
    applied=True,          # Set to True when actually applied
)

print(f"Recorded pattern application")
print(f"  Similarity: {learning.similarity_score:.2f}")
print(f"  Applied at: {learning.applied_at}")
```

### Example 5: Update Pattern Based on Outcome

Track whether a pattern application succeeded:

```python
# After applying pattern and testing
success = test_results['all_passed'] and build_results['success']

# Update pattern statistics
xp_system.track_pattern_outcome(
    pattern_id=42,
    success=success,
)

# This automatically:
# - Increments success_count or failure_count
# - Adjusts confidence score (+0.05 for success, -0.10 for failure)
# - Updates last_used timestamp
```

### Example 6: Get Comprehensive Insights

Get a full picture of cross-project learning for a project:

```python
insights = xp_system.get_cross_project_insights(project_id=1)

print("=== Cross-Project Learning Insights ===")
print(f"\nProject: {insights['project']['repo_url']}")
print(f"Language: {insights['project']['language']}")
print(f"Framework: {insights['project']['framework']}")

print(f"\nSimilar Projects: {len(insights['similar_projects'])}")
for sp in insights['similar_projects'][:3]:
    print(f"  - {sp['repo_url']} (similarity: {sp['similarity_score']:.2f})")

print(f"\nSuggested Patterns: {len(insights['suggested_patterns'])}")
for pattern in insights['suggested_patterns'][:5]:
    print(f"  - {pattern['pattern_name']} "
          f"(confidence: {pattern['confidence']:.2f}, "
          f"success rate: {pattern['success_rate']:.1%})")

print(f"\nStatistics:")
print(f"  Total suggestions: {insights['statistics']['total_suggestions']}")
print(f"  Total applied: {insights['statistics']['total_applied']}")
print(f"  Application rate: {insights['statistics']['application_rate']:.1%}")
```

### Example 7: Integration with Learning Worker

The Learning Worker uses cross-project learning to improve proposals:

```python
from openmemory.app.agents.learning_worker import LearningWorker
from openmemory.app.utils.cross_project import get_cross_project_system

class LearningWorker(BaseWorker):
    def _analyze_proposal(self, proposal):
        # Get cross-project system
        xp_system = get_cross_project_system(self.db)
        
        # If proposal succeeded, extract pattern
        if proposal.status == 'executed' and proposal.commit_sha:
            pattern = xp_system.extract_pattern_from_proposal(
                proposal=proposal,
                pattern_name=f"Pattern from {proposal.title}",
                pattern_type=self._classify_pattern_type(proposal),
                description=proposal.description,
            )
            
            if pattern:
                logger.info(f"✅ Extracted pattern: {pattern.pattern_name}")
        
        # Get recommended patterns for similar projects
        similar_projects = xp_system.find_similar_projects(
            project_id=proposal.project_id,
            min_similarity=0.6,
        )
        
        for similar_proj in similar_projects:
            patterns = xp_system.suggest_patterns_for_project(
                project_id=similar_proj.project_id,
                min_confidence=0.7,
            )
            
            # Record suggestions for future tracking
            for pattern in patterns:
                xp_system.record_pattern_application(
                    source_project_id=proposal.project_id,
                    target_project_id=similar_proj.project_id,
                    pattern_id=pattern.pattern_id,
                    applied=False,  # Just a suggestion for now
                )
```

## Integration with Workers

### Learning Worker Integration

The Learning Worker is the primary consumer of cross-project learning:

```python
# In LearningWorker._run_cycle()

# After analyzing a successful proposal
if proposal_succeeded:
    # Extract pattern
    pattern = self.xp_system.extract_pattern_from_proposal(
        proposal=proposal,
        pattern_name=self._generate_pattern_name(proposal),
        pattern_type=self._classify_pattern_type(proposal),
    )
    
    # Find similar projects
    similar_projects = self.xp_system.find_similar_projects(
        project_id=proposal.project_id,
        min_similarity=0.5,
    )
    
    # Suggest pattern to similar projects
    for similar_proj in similar_projects:
        self.xp_system.record_pattern_application(
            source_project_id=proposal.project_id,
            target_project_id=similar_proj.project_id,
            pattern_id=pattern.pattern_id,
            applied=False,
        )
```

### Dream Worker Integration

The Dream Worker can use learned patterns when creating proposals:

```python
# In DreamWorker._run_cycle()

# Get relevant patterns for this project
patterns = self.xp_system.suggest_patterns_for_project(
    project_id=project.project_id,
    pattern_types=["refactoring", "optimization"],
    min_confidence=0.7,
    limit=10,
)

# Incorporate high-confidence patterns into proposal
for pattern in patterns[:3]:  # Use top 3
    if pattern.confidence > 0.8:
        # Include pattern in proposal template
        proposal_context += f"\nConsider pattern: {pattern.pattern_name}"
        proposal_context += f"\n{pattern.description}"
```

### Think Worker Integration

The Think Worker tracks pattern outcomes after execution:

```python
# In ThinkWorker._execute_proposal()

# After proposal execution
if execution_successful:
    # Find patterns that were applied
    applied_patterns = self._find_applied_patterns(proposal)
    
    # Track outcomes
    for pattern_id in applied_patterns:
        self.xp_system.track_pattern_outcome(
            pattern_id=pattern_id,
            success=test_results['success'] and build_results['success'],
        )
```

## Pattern Types

### Common Pattern Types

1. **refactoring**: Code structure improvements
   - Extract function/class
   - Simplify complex logic
   - Improve naming

2. **optimization**: Performance improvements
   - Algorithm optimization
   - Caching strategies
   - Resource management

3. **bug_fix**: Error corrections
   - Null checks
   - Error handling
   - Edge case handling

4. **testing**: Test improvements
   - Add missing tests
   - Improve coverage
   - Add integration tests

5. **documentation**: Documentation improvements
   - Add docstrings
   - Update README
   - Add code comments

6. **security**: Security enhancements
   - Input validation
   - Authentication improvements
   - Data sanitization

7. **architecture**: Structural changes
   - Design pattern implementation
   - Module organization
   - Dependency management

## Similarity Calculation

### Scoring Formula

Projects are compared across three dimensions:

```
Similarity = (Language Match × 0.4) + (Framework Match × 0.3) + (Domain Match × 0.3)
```

### Matching Rules

#### Language Match (40% weight)
- **Exact match**: 0.4 points
- **No match**: 0.0 points

#### Framework Match (30% weight)
- **Exact match**: 0.3 points
- **Similar framework** (same family): 0.15 points
- **No match**: 0.0 points

Framework families:
- Web frontend: React, Vue, Angular, Svelte
- Python web: Django, Flask, FastAPI
- Node.js web: Express, Koa, Hapi
- Java enterprise: Spring, SpringBoot

#### Domain Match (30% weight)
- **Exact match**: 0.3 points
- **Similar domain** (same category): 0.15 points
- **No match**: 0.0 points

Domain categories:
- Web: web, webapp, website, frontend, backend
- AI/ML: ml, ai, machine learning, deep learning
- API: api, rest, graphql, microservice
- Data: data, analytics, etl

### Similarity Examples

```python
# Example 1: Identical projects
Project A: Python, Django, web → Project B: Python, Django, web
Similarity = 0.4 + 0.3 + 0.3 = 1.0 (100%)

# Example 2: Same language, similar framework/domain
Project A: Python, Django, web → Project B: Python, Flask, backend
Similarity = 0.4 + 0.15 + 0.15 = 0.7 (70%)

# Example 3: Same language only
Project A: Python, Django, web → Project B: Python, NumPy, data
Similarity = 0.4 + 0.0 + 0.0 = 0.4 (40%)

# Example 4: Different languages
Project A: Python, Django, web → Project B: JavaScript, React, web
Similarity = 0.0 + 0.0 + 0.15 = 0.15 (15%)
```

## Best Practices

### 1. Pattern Extraction

✅ **DO**:
- Extract patterns from proposals with high confidence (>0.7)
- Use descriptive pattern names
- Include comprehensive descriptions
- Wait for execution completion before extraction

❌ **DON'T**:
- Extract patterns from failed proposals
- Create overly specific patterns
- Extract patterns before testing

### 2. Pattern Application

✅ **DO**:
- Start with high-confidence patterns (>0.7)
- Test patterns thoroughly before applying
- Track outcomes for all applications
- Review patterns before auto-applying

❌ **DON'T**:
- Apply low-confidence patterns without review
- Skip testing after pattern application
- Forget to track outcomes

### 3. Similarity Thresholds

Recommended thresholds based on autonomy level:

```python
if autonomy_level == 1:  # Propose Only
    min_similarity = 0.8  # Very similar projects only
    min_confidence = 0.8  # High confidence required

elif autonomy_level == 2:  # Auto-Commit + PR
    min_similarity = 0.6  # Moderately similar projects
    min_confidence = 0.7  # Good confidence

elif autonomy_level == 3:  # Fully Autonomous
    min_similarity = 0.5  # Broadly similar projects
    min_confidence = 0.6  # Reasonable confidence
```

### 4. Pattern Maintenance

Regular maintenance tasks:

```python
# Remove low-performing patterns
patterns = db.query(LearnedPattern).filter(
    LearnedPattern.confidence < 0.3,
    LearnedPattern.failure_count > LearnedPattern.success_count,
).all()

for pattern in patterns:
    logger.warning(f"Low-performing pattern: {pattern.pattern_name}")
    # Consider archiving or removing

# Consolidate duplicate patterns
# Merge similar patterns with different names
```

## Troubleshooting

### Issue 1: No Patterns Suggested

**Symptoms**: `suggest_patterns_for_project()` returns empty list

**Possible Causes**:
1. No patterns learned yet
2. Similarity threshold too high
3. Confidence threshold too high
4. No patterns for project's language

**Solutions**:
```python
# Lower thresholds
patterns = xp_system.suggest_patterns_for_project(
    project_id=1,
    min_confidence=0.3,  # Lower threshold
    limit=50,
)

# Check if patterns exist
all_patterns = db.query(LearnedPattern).all()
print(f"Total patterns in database: {len(all_patterns)}")

# Check by language
python_patterns = db.query(LearnedPattern).filter(
    LearnedPattern.language == 'python'
).all()
print(f"Python patterns: {len(python_patterns)}")
```

### Issue 2: Low Similarity Scores

**Symptoms**: All projects have similarity < 0.5

**Possible Causes**:
1. Projects use different languages
2. Framework/domain not set on projects
3. Framework/domain names don't match

**Solutions**:
```python
# Check project metadata
project = db.query(Project).filter(Project.project_id == 1).first()
print(f"Language: {project.language}")
print(f"Framework: {project.framework}")
print(f"Domain: {project.domain}")

# Update project metadata if needed
project.framework = "fastapi"  # Standardize names
project.domain = "api"
db.commit()

# Add custom framework/domain families
# Edit _are_frameworks_similar() and _are_domains_similar()
```

### Issue 3: Pattern Confidence Not Updating

**Symptoms**: Pattern confidence remains static

**Possible Causes**:
1. Not calling `track_pattern_outcome()`
2. Database transaction not committed
3. Pattern not found

**Solutions**:
```python
# Verify pattern exists
pattern = db.query(LearnedPattern).filter(
    LearnedPattern.pattern_id == 42
).first()

if pattern:
    print(f"Pattern found: {pattern.pattern_name}")
    print(f"Current confidence: {pattern.confidence}")
    print(f"Success/Failure: {pattern.success_count}/{pattern.failure_count}")
else:
    print("Pattern not found!")

# Track outcome with error handling
try:
    success = xp_system.track_pattern_outcome(
        pattern_id=42,
        success=True,
    )
    print(f"Tracking {'succeeded' if success else 'failed'}")
except Exception as e:
    print(f"Error tracking outcome: {e}")
```

### Issue 4: Database Connection Issues

**Symptoms**: SQLAlchemy errors during operations

**Solutions**:
```python
# Ensure fresh session
db = get_db_session()
xp_system = CrossProjectLearningSystem(db)

try:
    # Your operations
    patterns = xp_system.suggest_patterns_for_project(project_id=1)
except Exception as e:
    logger.error(f"Database error: {e}")
    db.rollback()
finally:
    db.close()
```

## Performance Considerations

### Query Optimization

For large databases with many projects:

```python
# Use pagination for large result sets
def get_all_patterns_paginated(page=1, per_page=100):
    offset = (page - 1) * per_page
    patterns = db.query(LearnedPattern)\
        .order_by(desc(LearnedPattern.confidence))\
        .limit(per_page)\
        .offset(offset)\
        .all()
    return patterns

# Cache similarity calculations
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_similarity(proj1_id, proj2_id):
    return xp_system.calculate_project_similarity(proj1_id, proj2_id)
```

### Batch Operations

Process multiple patterns efficiently:

```python
# Extract patterns in batch
proposals = db.query(Proposal).filter(
    Proposal.status == 'executed',
    Proposal.confidence > 0.7,
).all()

patterns_extracted = []
for proposal in proposals:
    pattern = xp_system.extract_pattern_from_proposal(
        proposal=proposal,
        pattern_name=f"Pattern from {proposal.title}",
        pattern_type="refactoring",
    )
    if pattern:
        patterns_extracted.append(pattern)

print(f"Extracted {len(patterns_extracted)} patterns")
```

## API Reference

See docstrings in `cross_project.py` for complete API documentation:

```python
help(CrossProjectLearningSystem)
help(CrossProjectLearningSystem.extract_pattern_from_proposal)
help(CrossProjectLearningSystem.suggest_patterns_for_project)
# etc.
```

## Future Enhancements

Potential improvements for future versions:

1. **Semantic Similarity**: Use embeddings for more nuanced pattern matching
2. **Pattern Composition**: Combine multiple patterns intelligently
3. **Automated Testing**: Test patterns in sandbox before suggesting
4. **Pattern Versioning**: Track pattern evolution over time
5. **Transfer Learning**: Use ML to predict pattern success
6. **Community Patterns**: Share anonymized patterns across installations

---

For more information, see:
- `cross_project.py` - Full implementation
- `models.py` - Database schema
- `learning_worker.py` - Integration example
