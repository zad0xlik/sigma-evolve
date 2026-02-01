# Phase 2: Knowledge Exchange Integration Plan

## Overview
Integrate the Knowledge Exchange Protocol into all 5 workers (Think, Learning, Analysis, Dream, Recall) with specific knowledge types for each worker.

## Worker-Specific Knowledge Types

### 1. ThinkWorker
**Broadcasts:**
- `decision_outcome` - Results of proposal decisions (execute/reject/defer)
- `risk_pattern` - Risk assessment patterns learned from Graphiti
- `committee_scores` - Multi-agent committee scoring patterns

**Receives:**
- Risk patterns from AnalysisWorker
- Decision outcomes from other ThinkWorkers
- Pattern evolution from LearningWorker

### 2. LearningWorker
**Broadcasts:**
- `pattern_evolution` - How patterns change over time
- `learned_pattern` - New patterns extracted from proposals
- `success_rate` - Success rates of different patterns

**Receives:**
- Execution results from ThinkWorker
- Pattern quality feedback from AnalysisWorker
- Successful fix patterns from DreamWorker

### 3. AnalysisWorker
**Broadcasts:**
- `issue_pattern` - Common issue types and severities
- `complexity_trend` - Complexity evolution over time
- `code_quality_metric` - Quality metrics that improve/degrade

**Receives:**
- Issue resolution patterns from LearningWorker
- Risk patterns affecting code quality from ThinkWorker
- Fix effectiveness from DreamWorker

### 4. DreamWorker
**Broadcasts:**
- `proposal_quality` - Quality metrics of generated proposals
- `successful_fix` - Successful fix patterns (when proposals execute)
- `creativity_pattern` - Novel approaches that work

**Receives:**
- Accepted proposal patterns from ThinkWorker
- Effective patterns from LearningWorker
- Issue patterns from AnalysisWorker

### 5. RecallWorker
**Broadcasts:**
- `context_enrichment` - How context improves decisions
- `knowledge_retrieval` - Retrieval patterns that work
- `cross_project_pattern` - Cross-project knowledge transfers

**Receives:**
- Context relevance feedback from ThinkWorker
- Pattern retrieval success from LearningWorker
- Effective retrieval strategies from other workers

## Implementation Strategy

### 1. Update BaseWorker (Phase 1 complete)
- ✅ KnowledgeExchangeProtocol already integrated
- ✅ Automatic knowledge broadcast methods available
- ✅ Statistics tracking in place

### 2. Worker-Specific Integrations (Phase 2)

#### ThinkWorker Integration
```python
# After _evaluate_proposal(), broadcast decision outcome
def _evaluate_proposal(self, proposal: Proposal) -> Dict:
    decision = self._evaluate_proposal_internal(proposal)
    
    # Broadcast decision outcome
    self._broadcast_knowledge(
        knowledge_type='decision_outcome',
        content={
            'proposal_id': proposal.proposal_id,
            'action': decision['action'],
            'confidence': decision['confidence'],
            'committee_scores': decision['committee_scores'],
            'risk_assessment': decision.get('risk_assessment', {})
        },
        urgency='low'  # Regular learning, not urgent
    )
    
    # Broadcast risk pattern if high risk
    if decision.get('risk_assessment', {}).get('risk_level') == 'high':
        self._broadcast_knowledge(
            knowledge_type='risk_pattern',
            content={
                'proposal_id': proposal.proposal_id,
                'risk_level': 'high',
                'factors': decision['risk_assessment'].get('factors', []),
                'similar_past_decisions': len(decision['risk_assessment'].get('similar_past_decisions', []))
            },
            urgency='medium'
        )
    
    return decision
```

#### LearningWorker Integration
```python
# After extracting pattern, broadcast it
def _extract_and_store_pattern(self, proposal: Proposal) -> bool:
    success = self._evaluate_proposal_success(proposal)
    
    if success and pattern:
        # Broadcast learned pattern
        self._broadcast_knowledge(
            knowledge_type='learned_pattern',
            content={
                'pattern_id': pattern.pattern_id,
                'pattern_name': pattern.pattern_name,
                'pattern_type': pattern.pattern_type,
                'confidence': pattern.confidence,
                'success_rate': pattern.success_count / max(pattern.success_count + pattern.failure_count, 1)
            },
            urgency='low'
        )
        
        # If pattern confidence increased significantly, broadcast evolution
        if enhanced_confidence > pattern.confidence + 0.1:
            self._broadcast_knowledge(
                knowledge_type='pattern_evolution',
                content={
                    'pattern_id': pattern.pattern_id,
                    'improvement': enhanced_confidence - pattern.confidence,
                    'source': 'historical_data_enhancement'
                },
                urgency='low'
            )
```

#### AnalysisWorker Integration
```python
# After analyzing issues, broadcast patterns
def _analyze_codebase(self, workspace: str, language: str) -> Dict:
    snapshot = self._analyze_codebase_internal(workspace, language)
    
    # Broadcast issue patterns if found
    if snapshot['issues_found'] > 0:
        issue_types = {}
        for issue in snapshot.get('issues', []):
            # Extract issue type from message
            message = issue['message'].lower()
            if 'mutable default' in message:
                issue_type = 'mutable_default'
            elif 'bare except' in message:
                issue_type = 'bare_except'
            elif 'type hint' in message:
                issue_type = 'missing_type_hint'
            else:
                issue_type = 'other'
            
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        # Broadcast aggregated issue patterns
        for issue_type, count in issue_types.items():
            if count >= 3:  # Only broadcast common patterns
                self._broadcast_knowledge(
                    knowledge_type='issue_pattern',
                    content={
                        'issue_type': issue_type,
                        'count': count,
                        'severity': issue.get('severity', 'warning'),
                        'files_affected': list(set(i['file'] for i in snapshot['issues']))
                    },
                    urgency='low'
                )
    
    # Broadcast complexity trend if high
    if snapshot['complexity'] > 12:
        self._broadcast_knowledge(
            knowledge_type='complexity_trend',
            content={
                'current_complexity': snapshot['complexity'],
                'threshold': 12,
                'files_analyzed': snapshot['files_analyzed']
            },
            urgency='medium'
        )
    
    return snapshot
```

#### DreamWorker Integration
```python
# After generating proposals, broadcast quality metrics
def _generate_proposals(self, snapshot: CodeSnapshot) -> List[Dict]:
    proposals = self._generate_proposals_internal(snapshot)
    
    # Broadcast proposal quality metrics
    if proposals:
        avg_confidence = sum(p['confidence'] for p in proposals) / len(proposals)
        
        self._broadcast_knowledge(
            knowledge_type='proposal_quality',
            content={
                'proposal_count': len(proposals),
                'avg_confidence': avg_confidence,
                'issue_count': snapshot.issues_found,
                'change_types': list(set(p['changes']['change_type'] for p in proposals))
            },
            urgency='low'
        )
    
    return proposals

# After successful proposal execution, broadcast successful fix
def _after_successful_execution(self, proposal: Proposal):
    """Called when proposal is successfully executed"""
    self._broadcast_knowledge(
        knowledge_type='successful_fix',
        content={
            'proposal_id': proposal.proposal_id,
            'title': proposal.title,
            'change_type': json.loads(proposal.changes_json)['change_type'],
            'confidence': proposal.confidence,
            'executed_at': proposal.executed_at.isoformat() if proposal.executed_at else None
        },
        urgency='medium'
    )
```

#### RecallWorker Integration
```python
# After enriching proposal with context, broadcast enrichment quality
def _enrich_proposal_with_context(self, proposal: Proposal, context: Dict):
    self._enrich_proposal_with_context_internal(proposal, context)
    
    # Broadcast context enrichment quality
    context_quality = {
        'patterns_found': len(context['similar_patterns']),
        'past_proposals_found': len(context['past_proposals']),
        'cross_project_insights': len(context['cross_project_insights']),
        'knowledge_graph_facts': len(context.get('knowledge_graph_context', {}).get('relevant_facts', []))
    }
    
    self._broadcast_knowledge(
        knowledge_type='context_enrichment',
        content={
            'proposal_id': proposal.proposal_id,
            'quality_metrics': context_quality,
            'enrichment_timestamp': context['retrieval_timestamp'].isoformat() if context.get('retrieval_timestamp') else None
        },
        urgency='low'
    )
    
    # Broadcast knowledge retrieval patterns
    if context.get('knowledge_graph_context', {}).get('query_status') == 'success':
        self._broadcast_knowledge(
            knowledge_type='knowledge_retrieval',
            content={
                'query': context['knowledge_graph_context'].get('search_query', ''),
                'results_found': context['knowledge_graph_context'].get('total_results', 0),
                'retrieval_time': 0.5,  # Would track actual time
                'query_status': 'success'
            },
            urgency='low'
        )
```

### 3. Knowledge Exchange Method (BaseWorker)
Each worker will use these methods:

```python
def _broadcast_recent_learnings(self):
    """Override in workers to broadcast specific knowledge"""
    pass

def _update_risk_model(self, new_knowledge: List[Dict]):
    """Update risk assessment models (ThinkWorker)"""
    pass

def _update_pattern_models(self, new_knowledge: List[Dict]):
    """Update pattern extraction models (LearningWorker)"""
    pass

def _update_issue_detection(self, new_knowledge: List[Dict]):
    """Update issue detection rules (AnalysisWorker)"""
    pass

def _update_proposal_generation(self, new_knowledge: List[Dict]):
    """Update proposal generation strategies (DreamWorker)"""
    pass

def _update_context_retrieval(self, new_knowledge: List[Dict]):
    """Update context retrieval strategies (RecallWorker)"""
    pass
```

### 4. Knowledge Reception Methods
Each worker will also receive and process knowledge:

```python
def _process_received_knowledge(self, new_knowledge: List[Dict]):
    """
    Process knowledge received from other workers
    Each worker implements specific logic based on knowledge types
    """
    for knowledge in new_knowledge:
        knowledge_type = knowledge.get('knowledge_type')
        
        if knowledge_type == 'risk_pattern':
            # ThinkWorker: Update risk models
            self._update_risk_model([knowledge])
        
        elif knowledge_type in ['learned_pattern', 'pattern_evolution']:
            # LearningWorker: Update pattern models
            self._update_pattern_models([knowledge])
        
        elif knowledge_type == 'issue_pattern':
            # AnalysisWorker: Update issue detection
            self._update_issue_detection([knowledge])
        
        elif knowledge_type in ['proposal_quality', 'successful_fix']:
            # DreamWorker: Update proposal generation
            self._update_proposal_generation([knowledge])
        
        elif knowledge_type in ['context_enrichment', 'knowledge_retrieval']:
            # RecallWorker: Update context retrieval
            self._update_context_retrieval([knowledge])
```

### 5. Integration Schedule

**Week 1:** ThinkWorker + LearningWorker
- Implement knowledge broadcast for decision outcomes and patterns
- Test knowledge exchange between Think and Learning workers
- Verify database persistence and freshness tracking

**Week 2:** AnalysisWorker + DreamWorker + RecallWorker
- Implement knowledge broadcast for all remaining workers
- Test cross-worker knowledge propagation
- Validate knowledge exchange patterns

**Week 3:** Full Integration & Conflict Resolution
- Implement conflict resolution strategies
- Add knowledge deduplication
- Performance optimization (batch operations, caching)
- Add real-time notifications (WebSocket support)

**Week 4:** Monitoring & Documentation
- Create knowledge exchange dashboard
- Add metrics and alerts
- Complete documentation and deployment guides

## Testing Strategy

### Unit Tests (Per Worker)
1. Knowledge broadcast triggers at correct times
2. Knowledge types are correct
3. Content structure is valid
4. Urgency levels are appropriate

### Integration Tests
1. Cross-worker knowledge propagation
2. Knowledge freshness decay
3. Conflict resolution
4. Performance under load

### End-to-End Tests
1. Complete knowledge exchange cycle
2. Database persistence and retrieval
3. API endpoint functionality
4. Dashboard display of knowledge exchange

## Success Metrics

### Phase 2 Success Criteria
- [ ] Each worker broadcasts knowledge at least once per day
- [ ] Knowledge exchange reduces duplicate work by 20%
- [ ] Workers can access relevant knowledge from other workers
- [ ] Knowledge freshness tracking works correctly
- [ ] No performance degradation in worker cycles
- [ ] 100% test pass rate for new functionality

## Next Steps

1. **Week 1 (Starting Now):**
   - Update ThinkWorker with knowledge broadcast
   - Update LearningWorker with knowledge broadcast
   - Create integration tests for Think + Learning
   - Deploy and monitor knowledge exchange

2. **Week 2:**
   - Update AnalysisWorker, DreamWorker, RecallWorker
   - Create comprehensive integration tests
   - Test knowledge propagation across all workers

3. **Week 3:**
   - Implement conflict resolution
   - Add performance optimizations
   - Test with real workload

4. **Week 4:**
   - Create monitoring dashboard
   - Generate documentation
   - Prepare deployment guides

## Dependencies

### Prerequisites
- ✅ Phase 1 complete (KnowledgeExchangeProtocol, database schema, API endpoints)
- ✅ All workers have access to `self.knowledge_protocol`
- ✅ Knowledge exchange database tables exist

### Required for Phase 2
- Updated BaseWorker methods (in progress)
- Worker-specific integration (to be implemented)
- Integration tests (to be implemented)
- Monitoring and metrics (Phase 3)

## Rollback Plan

If knowledge exchange causes issues:
1. Disable broadcast in worker configs
2. Workers continue with existing logic
3. Knowledge exchange can be re-enabled after fixes

## Notes

- Knowledge exchange is optional - workers can function without it
- All knowledge has timestamps for freshness tracking
- Workers can filter knowledge by type and urgency
- API endpoints available for manual knowledge management
