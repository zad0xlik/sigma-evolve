# SIGMA Agent Dashboard

Beautiful, modern web dashboard for monitoring and controlling the SIGMA multi-agent system.

## Overview

The SIGMA Dashboard provides real-time visibility into your autonomous agent system's operations:

- **Real-time Monitoring**: View worker status, proposals, experiments, and patterns
- **Manual Approval Workflow**: Review and approve/reject proposals (for autonomy level 1)
- **Performance Metrics**: Track success rates, experiments, and learning progress
- **Pattern Visualization**: View learned patterns and cross-project opportunities
- **Auto-refresh**: Updates every 30 seconds automatically

## Accessing the Dashboard

Once the FastAPI server is running, access the dashboard at:

```
http://localhost:8000/dashboard
```

## Dashboard Sections

### 1. Overview Statistics (Top Cards)

Four key metrics displayed prominently:

- **Total Projects**: Number of projects being tracked
- **Pending Proposals**: Proposals awaiting approval (autonomy level 1)
- **Success Rate**: Percentage of successful experiments
- **Learned Patterns**: Total patterns extracted from successful proposals

### 2. Proposals Tab

**Purpose**: Review and manage code improvement proposals

**Features**:
- View all proposals with status badges (pending, approved, rejected, executed)
- Confidence and critic score visualization with progress bars
- Approve/reject buttons for pending proposals (autonomy level 1)
- Direct links to GitHub PRs
- Detailed view of proposal changes and metadata

**Workflow** (Autonomy Level 1):
1. Dream Worker creates proposals → Status: `pending`
2. Review in dashboard → Click "Approve" or "Reject"
3. Approved proposals → Think Worker executes → Status: `executed`
4. Rejected proposals → Learning Worker analyzes for improvement

### 3. Experiments Tab

**Purpose**: Track experimental approaches by DreamerMetaAgent

**Features**:
- Color-coded cards:
  - Green: Successful experiments
  - Red: Failed experiments
  - Gradient: Promoted experiments (>20% improvement)
- Shows worker name, hypothesis, and improvement percentage
- Tracks which experiments were auto-promoted to production

**Key Insight**: Experiments with >20% improvement are automatically promoted, allowing workers to evolve their strategies autonomously.

### 4. Workers Tab

**Purpose**: Monitor performance of all 5 SIGMA workers

**Features**:
- Health indicators (green = healthy, yellow = warnings)
- Performance metrics:
  - **Cycles Run**: Total execution cycles
  - **Experiments**: Experimental approaches tested
  - **Total Time**: Cumulative execution time
  - **Errors**: Error count (impacts health status)
- Last run timestamp for each worker

**Workers Monitored**:
- Analysis Worker (code analysis & metrics)
- Dream Worker (proposal generation)
- Recall Worker (context & history)
- Learning Worker (pattern extraction)
- Think Worker (execution & validation)

### 5. Patterns Tab

**Purpose**: View learned patterns from successful proposals

**Features**:
- Pattern metadata: name, type, description
- Technical details: language, framework, domain
- Confidence score with visual progress bar
- Success/failure statistics
- Pattern types:
  - refactoring
  - optimization
  - bug_fix
  - testing
  - documentation
  - security
  - architecture

**Use Case**: These patterns can be applied to similar projects through cross-project learning.

### 6. Projects Tab

**Purpose**: View all projects tracked by SIGMA

**Features**:
- Repository URL and branch
- Language, framework, and domain classification
- Creation and last analyzed timestamps
- Enables cross-project learning by comparing similar projects

## API Endpoints Used

The dashboard communicates with these FastAPI endpoints:

```
GET  /api/agents/dashboard          # Overview statistics
GET  /api/agents/proposals           # List proposals
POST /api/agents/proposals/{id}/approve  # Approve/reject
GET  /api/agents/experiments         # List experiments
GET  /api/agents/workers/stats       # Worker statistics
GET  /api/agents/patterns            # Learned patterns
GET  /api/agents/projects            # Tracked projects
```

## Auto-Refresh

The dashboard automatically refreshes every 30 seconds to show the latest data. You can also manually refresh using the circular button in the bottom-right corner.

## Responsive Design

The dashboard is fully responsive and works on:
- Desktop (1400px+ optimal)
- Tablets (768px - 1400px)
- Mobile devices (< 768px)

## Color Scheme

- **Primary**: Purple gradient (#667eea → #764ba2)
- **Success**: Green (#28a745)
- **Warning**: Yellow (#ffc107)
- **Error**: Red (#dc3545)

## Customization

To customize the dashboard, edit `/src/openmemory/static/dashboard.html`:

- **Styles**: Modify the `<style>` section
- **Functionality**: Update the `<script>` section
- **Layout**: Change the HTML structure

## Troubleshooting

### Dashboard shows "No data found"

**Cause**: No data in database yet
**Solution**: Run the agent system to generate proposals, experiments, and patterns

### API errors in console

**Cause**: FastAPI server not running or database not configured
**Solution**: 
```bash
cd src/openmemory
uvicorn main:app --reload
```

### Static files not loading

**Cause**: Static directory not mounted
**Solution**: Ensure `static` directory exists in `/src/openmemory/` and contains `dashboard.html`

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (Dashboard)                     │
│  - Real-time UI updates every 30s                           │
│  - Approve/reject proposals                                 │
│  - View worker stats & patterns                             │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/JSON
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  FastAPI Server (main.py)                   │
│  - /dashboard → Serve HTML                                  │
│  - /api/agents/* → Agent router                             │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Agent Router (routers/agents.py)               │
│  - 20+ endpoints for monitoring                             │
│  - Pydantic schemas for validation                          │
│  - Query filtering & pagination                             │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│               PostgreSQL Database (models.py)               │
│  - Projects, Proposals, Experiments                         │
│  - LearnedPatterns, WorkerStats                            │
│  - CrossProjectLearning                                     │
└─────────────────────────────────────────────────────────────┘
```

## Usage Examples

### Example 1: Reviewing a Proposal (Autonomy Level 1)

1. Navigate to Proposals tab
2. See pending proposal: "Optimize database queries"
3. Review confidence (85%) and critic score (78%)
4. Click "View Details" to see proposed changes
5. Click "Approve" to execute the proposal
6. Think Worker creates branch, commits, and opens PR
7. Refresh to see status change to "executed"

### Example 2: Monitoring Experiments

1. Navigate to Experiments tab
2. See experiment: "Alternative recall strategy using semantic search"
3. Worker: RecallWorker
4. Improvement: 23% (shown in green with PROMOTED badge)
5. This experiment was automatically promoted to production
6. Future recall operations will use this improved strategy

### Example 3: Exploring Learned Patterns

1. Navigate to Patterns tab
2. Filter by language: "Python"
3. See pattern: "Database Connection Pooling"
4. Confidence: 87% (based on 12 successes, 1 failure)
5. Can be applied to similar Python projects automatically

## Security Considerations

The dashboard currently has no authentication. For production use:

1. Add authentication middleware to FastAPI
2. Implement role-based access control (RBAC)
3. Use HTTPS for all communications
4. Rate limit API endpoints
5. Add CSRF protection for POST requests

## Performance Tips

- The dashboard fetches up to 20 items per tab by default
- Use API filtering parameters for large datasets:
  ```javascript
  /api/agents/proposals?status=pending&limit=50
  /api/agents/experiments?worker_name=AnalysisWorker
  /api/agents/patterns?language=python&min_confidence=0.7
  ```

## Future Enhancements

Planned improvements:

1. **Real-time Updates**: WebSocket support for instant notifications
2. **Advanced Filtering**: Multi-select filters, date ranges
3. **Visualizations**: Charts for trends over time
4. **Detailed Views**: Modal dialogs for in-depth information
5. **Configuration**: Adjust autonomy levels from dashboard
6. **Logs**: View worker logs and error traces
7. **Manual Triggers**: Start worker cycles on demand

## Related Documentation

- **API Reference**: See `/api/docs` (FastAPI Swagger UI)
- **Agent System**: See `/memory-bank/systemPatterns.md`
- **Cross-Project Learning**: See `/src/openmemory/app/utils/README_CROSS_PROJECT.md`
- **Docker Executor**: See `/src/openmemory/app/utils/README_DOCKER_EXECUTOR.md`
- **Git Operations**: See `/src/openmemory/app/utils/README_GIT_OPERATIONS.md`
