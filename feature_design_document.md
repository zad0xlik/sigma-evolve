# SIGMA Feature Design Document

## Feature 1: Cross-Worker Knowledge Sharing Protocols

### Current State
Workers currently share knowledge indirectly through:
- Database (proposals, patterns, experiments)
- Graphiti knowledge graph (read-only queries)
- DreamerMetaAgent (experiment promotion)

### Design: Direct Worker-to-Worker Knowledge Exchange

#### 1.1 Knowledge Exchange Framework

**Shared Knowledge Graph Layer**
```
┌─────────────────────────────────────────────────┐
│           Shared Knowledge Layer                 │
├─────────────────────────────────────────────────┤
│  • Real-time knowledge propagation              │
│  • Multi-worker context synchronization         │
│  • Conflict resolution strategies               │
│  • Knowledge freshness tracking                 │
└─────────────────────────────────────────────────┘
         ↑           ↑           ↑
    ThinkWorker  LearningWorker  DreamWorker
         ↑           ↑           ↑
    └─────┴─────────┴───────────┴─────┘
                   |
            Graphiti/Neo4j
```

**Protocol Design**

```python
class KnowledgeExchangeProtocol:
    """Direct knowledge sharing between workers"""
    
    def __init__(self, db_session, graphiti_client):
        self.db = db_session
        self.graphiti = graphiti_client
        self.exchange_queue = asyncio.Queue()
        self.worker_topics = {
            'think': ['risk_patterns', 'decision_outcomes'],
            'learning': ['pattern_evolution', 'cross_project_learnings'],
            'analysis': ['issue_patterns', 'complexity_trends'],
            'dream': ['proposal_patterns', 'fix_strategies'],
            'recall': ['context_enrichments', 'retrieval_patterns']
        }
    
    async def broadcast_knowledge(
        self, 
        worker_name: str, 
        knowledge_type: str, 
        payload: Dict,
        urgency: str = "normal"
    ):
        """
        Broadcast knowledge to relevant workers
        
        Args:
            worker_name: Source worker
            knowledge_type: Type of knowledge (e.g., 'risk_pattern', 'successful_fix')
            payload: Knowledge data
            urgency: 'high', 'normal', 'low' - affects propagation speed
        """
        # Store in Graphiti for persistence
        await self._store_in_graphiti(worker_name, knowledge_type, payload)
        
        # Broadcast to interested workers
        interested_workers = self._get_interested_workers(knowledge_type)
        
        for target_worker in interested_workers:
            if target_worker != worker_name:
                await self._notify_worker(
                    target_worker, 
                    worker_name, 
                    knowledge_type, 
                    payload
                )
    
    async def _store_in_graphiti(
        self, 
        worker_name: str, 
        knowledge_type: str, 
        payload: Dict
    ):
        """Store knowledge in Graphiti with metadata"""
        fact_text = self._format_fact_for_graphiti(
            worker_name, knowledge_type, payload
        )
        
        # Add metadata for tracking
        metadata = {
            "source_worker": worker_name,
            "knowledge_type": knowledge_type,
            "timestamp": utc_now(),
            "confidence": payload.get('confidence', 0.5),
            "urgency": payload.get('urgency', 'normal'),
            "workers_exposed": [worker_name]
        }
        
        # Store with metadata
        await self.graphiti.store_fact(
            fact=fact_text,
            metadata=metadata,
            tags=[knowledge_type, worker_name, "worker_exchange"]
        )
    
    def _get_interested_workers(self, knowledge_type: str) -> List[str]:
        """Determine which workers would benefit from this knowledge"""
        interest_map = {
            'risk_pattern': ['think', 'learning'],
            'decision_outcome': ['think', 'learning', 'dream'],
            'successful_fix': ['dream', 'learning', 'analysis'],
            'issue_pattern': ['analysis', 'think'],
            'pattern_evolution': ['learning', 'dream'],
            'context_enrichment': ['recall', 'think', 'dream'],
            'proposal_quality': ['dream', 'think'],
        }
        
        return interest_map.get(knowledge_type, [])
    
    async def _notify_worker(
        self, 
        target_worker: str, 
        source_worker: str, 
        knowledge_type: str, 
        payload: Dict
    ):
        """Notify target worker of new knowledge"""
        notification = {
            "type": "knowledge_update",
            "source": source_worker,
            "knowledge_type": knowledge_type,
            "payload": payload,
            "timestamp": utc_now()
        }
        
        # Store notification in worker-specific queue
        await self.exchange_queue.put((target_worker, notification))
        
        logger.info(
            f"Knowledge broadcast: {source_worker} → {target_worker} "
            f"({knowledge_type})"
        )
    
    async def receive_knowledge(self, worker_name: str) -> Optional[Dict]:
        """Receive knowledge from other workers"""
        try:
            worker, notification = await asyncio.wait_for(
                self.exchange_queue.get(),
                timeout=0.1  # Non-blocking with timeout
            )
            
            if worker == worker_name:
                self.exchange_queue.task_done()
                return notification
            
            # Put back if not for this worker
            await self.exchange_queue.put((worker, notification))
            return None
            
        except asyncio.TimeoutError:
            return None
    
    def _format_fact_for_graphiti(
        self, 
        worker_name: str, 
        knowledge_type: str, 
        payload: Dict
    ) -> str:
        """Format knowledge as Graphiti fact"""
        if knowledge_type == 'risk_pattern':
            return (
                f"Worker {worker_name} identified risk pattern: "
                f"{payload.get('pattern', 'N/A')} "
                f"(severity: {payload.get('severity', 'unknown')}, "
                f"confidence: {payload.get('confidence', 0)})"
            )
        
        elif knowledge_type == 'successful_fix':
            return (
                f"Worker {worker_name} successfully fixed: "
                f"{payload.get('issue_type', 'N/A')} "
                f"(improvement: {payload.get('improvement', 0):.1%}, "
                f"pattern: {payload.get('pattern', 'N/A')})"
            )
        
        elif knowledge_type == 'decision_outcome':
            return (
                f"Worker {worker_name} decision outcome: "
                f"{payload.get('decision', 'N/A')} "
                f"(success: {payload.get('success', False)}, "
                f"learning: {payload.get('learning', 'N/A')})"
            )
        
        else:
            return f"Worker {worker_name} knowledge: {json.dumps(payload, default=str)}"

#### 1.2 Worker Integration

**Enhanced Base Worker with Knowledge Exchange**

```python
class EnhancedBaseWorker(BaseWorker):
    """Base worker with knowledge exchange capabilities"""
    
    def __init__(self, db_session, dreamer, knowledge_protocol=None):
        super().__init__(db_session, dreamer)
        self.knowledge_protocol = knowledge_protocol
        self.received_knowledge = []
        self.knowledge_broadcast_interval = 30  # seconds
    
    def exchange_cycle(self):
        """Exchange knowledge with other workers"""
        if not self.knowledge_protocol:
            return
        
        # 1. Broadcast recent learnings
        self._broadcast_recent_learnings()
        
        # 2. Receive new knowledge
        self._receive_and_process_knowledge()
        
        # 3. Update internal state with shared knowledge
        self._integrate_shared_knowledge()
    
    def _broadcast_recent_learnings(self):
        """Broadcast recent important findings"""
        # Get recent successes from this worker
        recent_successes = self._get_recent_successes(limit=2)
        
        for success in recent_successes:
            asyncio.create_task(
                self.knowledge_protocol.broadcast_knowledge(
                    worker_name=self.worker_name,
                    knowledge_type=self._get_knowledge_type_for_success(success),
                    payload=success,
                    urgency="normal"
                )
            )
    
    def _receive_and_process_knowledge(self):
        """Receive and process knowledge from other workers"""
        while True:
            knowledge = asyncio.run(
                self.knowledge_protocol.receive_knowledge(self.worker_name)
            )
            
            if not knowledge:
                break
            
            # Store for later use
            self.received_knowledge.append(knowledge)
            
            # Process immediately if high urgency
            if knowledge.get('payload', {}).get('urgency') == 'high':
                self._process_high_priority_knowledge(knowledge)
    
    def _process_high_priority_knowledge(self, knowledge: Dict):
        """Process high-priority knowledge immediately"""
        knowledge_type = knowledge['knowledge_type']
        payload = knowledge['payload']
        
        if knowledge_type == 'risk_pattern':
            # Update risk assessment immediately
            self._update_risk_model(payload)
        
        elif knowledge_type == 'critical_issue':
            # Flag for immediate attention
            self._flag_critical_issue(payload)
    
    def _integrate_shared_knowledge(self):
        """Integrate shared knowledge into decision-making"""
        if not self.received_knowledge:
            return
        
        # Group by type
        grouped = {}
        for k in self.received_knowledge:
            ktype = k['knowledge_type']
            if ktype not in grouped:
                grouped[ktype] = []
            grouped[ktype].append(k['payload'])
        
        # Update internal models
        for ktype, knowledge_list in grouped.items():
            if ktype == 'risk_pattern':
                self._update_risk_patterns(knowledge_list)
            elif ktype == 'pattern_evolution':
                self._update_pattern_models(knowledge_list)
            elif ktype == 'context_enrichment':
                self._update_context_models(knowledge_list)

#### 1.3 Knowledge Types and Protocols

**Knowledge Type Registry**

```python
KNOWLEDGE_TYPES = {
    # Risk and Safety Knowledge
    'risk_pattern': {
        'workers': ['think', 'learning'],
        'persistence': 'long',
        'validation': 'required',
        'propagation': 'broadcast'
    },
    
    # Decision and Outcome Knowledge
    'decision_outcome': {
        'workers': ['think', 'learning', 'dream'],
        'persistence': 'medium',
        'validation': 'required',
        'propagation': 'multicast'
    },
    
    # Fix and Solution Knowledge
    'successful_fix': {
        'workers': ['dream', 'learning', 'analysis'],
        'persistence': 'long',
        'validation': 'required',
        'propagation': 'broadcast'
    },
    
    # Issue Pattern Knowledge
    'issue_pattern': {
        'workers': ['analysis', 'think'],
        'persistence': 'medium',
        'validation': 'optional',
        'propagation': 'multicast'
    },
    
    # Pattern Evolution Knowledge
    'pattern_evolution': {
        'workers': ['learning', 'dream'],
        'persistence': 'long',
        'validation': 'required',
        'propagation': 'broadcast'
    },
    
    # Context Enrichment Knowledge
    'context_enrichment': {
        'workers': ['recall', 'think', 'dream'],
        'persistence': 'short',
        'validation': 'optional',
        'propagation': 'multicast'
    },
    
    # Proposal Quality Knowledge
    'proposal_quality': {
        'workers': ['dream', 'think'],
        'persistence': 'medium',
        'validation': 'required',
        'propagation': 'broadcast'
    },
    
    # Experiment Results Knowledge
    'experiment_result': {
        'workers': ['all'],
        'persistence': 'long',
        'validation': 'required',
        'propagation': 'broadcast'
    }
}
```

**Propagation Strategies**

```python
class KnowledgePropagationStrategy:
    """Different strategies for knowledge propagation"""
    
    @staticmethod
    def broadcast(source: str, knowledge_type: str, payload: Dict) -> List[str]:
        """Broadcast to all interested workers"""
        interested = KNOWLEDGE_TYPES[knowledge_type]['workers']
        if 'all' in interested:
            return ['think', 'learning', 'analysis', 'dream', 'recall']
        return interested
    
    @staticmethod
    def multicast(source: str, knowledge_type: str, payload: Dict) -> List[str]:
        """Multicast to subset based on content"""
        interested = []
        
        # Example: Route based on payload content
        if knowledge_type == 'decision_outcome':
            if payload.get('success', False):
                interested = ['learning', 'dream']  # Learning workers want successes
            else:
                interested = ['think']  # Think workers want failures
        
        elif knowledge_type == 'issue_pattern':
            if payload.get('severity') == 'critical':
                interested = ['analysis', 'think', 'dream']  # Everyone needs critical issues
            else:
                interested = ['analysis']  # Only analysis needs non-critical issues
        
        return interested
    
    @staticmethod
    def unicast(source: str, target: str, knowledge_type: str, payload: Dict) -> List[str]:
        """Direct to specific worker"""
        if target in ['think', 'learning', 'analysis', 'dream', 'recall']:
            return [target]
        return []

#### 1.4 Knowledge Freshness and Validation

**Freshness Tracking**

```python
class KnowledgeFreshnessTracker:
    """Track knowledge freshness and relevance"""
    
    def __init__(self):
        self.knowledge_timestamps = {}
        self.relevance_scores = {}
    
    def update_knowledge(
        self, 
        worker_name: str, 
        knowledge_type: str, 
        knowledge_id: str,
        relevance_score: float
    ):
        """Update knowledge freshness"""
        key = f"{worker_name}:{knowledge_type}:{knowledge_id}"
        
        self.knowledge_timestamps[key] = utc_now()
        self.relevance_scores[key] = relevance_score
    
    def get_freshness(
        self, 
        worker_name: str, 
        knowledge_type: str, 
        knowledge_id: str
    ) -> float:
        """Get freshness score (0.0 = stale, 1.0 = fresh)"""
        key = f"{worker_name}:{knowledge_type}:{knowledge_id}"
        
        if key not in self.knowledge_timestamps:
            return 0.0
        
        timestamp = self.knowledge_timestamps[key]
        age_seconds = (datetime.now(timezone.utc) - timestamp).total_seconds()
        
        # Exponential decay: freshness = e^(-age/decay_time)
        decay_time = self._get_decay_time(knowledge_type)
        freshness = math.exp(-age_seconds / decay_time)
        
        return freshness
    
    def _get_decay_time(self, knowledge_type: str) -> float:
        """Get decay time for knowledge type (seconds)"""
        decay_times = {
            'risk_pattern': 86400 * 7,  # 7 days
            'decision_outcome': 86400 * 3,  # 3 days
            'successful_fix': 86400 * 14,  # 14 days
            'issue_pattern': 86400 * 5,  # 5 days
            'pattern_evolution': 86400 * 30,  # 30 days
            'context_enrichment': 3600 * 6,  # 6 hours
            'proposal_quality': 86400 * 7,  # 7 days
            'experiment_result': 86400 * 30,  # 30 days
        }
        return decay_times.get(knowledge_type, 86400)  # Default 1 day

**Knowledge Validation**

```python
class KnowledgeValidator:
    """Validate incoming knowledge"""
    
    @staticmethod
    def validate_knowledge(
        knowledge_type: str, 
        payload: Dict, 
        source_worker: str
    ) -> Tuple[bool, str]:
        """
        Validate knowledge before processing
        
        Returns:
            (is_valid, error_message)
        """
        validators = {
            'risk_pattern': KnowledgeValidator._validate_risk_pattern,
            'decision_outcome': KnowledgeValidator._validate_decision_outcome,
            'successful_fix': KnowledgeValidator._validate_successful_fix,
            'issue_pattern': KnowledgeValidator._validate_issue_pattern,
            'context_enrichment': KnowledgeValidator._validate_context_enrichment,
        }
        
        validator = validators.get(knowledge_type)
        if not validator:
            return True, ""  # No validator for this type
        
        return validator(payload, source_worker)
    
    @staticmethod
    def _validate_risk_pattern(payload: Dict, source_worker: str) -> Tuple[bool, str]:
        """Validate risk pattern knowledge"""
        required = ['pattern', 'severity', 'confidence', 'context']
        missing = [field for field in required if field not in payload]
        
        if missing:
            return False, f"Missing required fields: {missing}"
        
        if not isinstance(payload['severity'], str):
            return False, "Severity must be a string"
        
        if not isinstance(payload['confidence'], (int, float)):
            return False, "Confidence must be numeric"
        
        if not 0 <= payload['confidence'] <= 1:
            return False, "Confidence must be between 0 and 1"
        
        return True, ""
    
    @staticmethod
    def _validate_decision_outcome(payload: Dict, source_worker: str) -> Tuple[bool, str]:
        """Validate decision outcome knowledge"""
        required = ['decision', 'success', 'learning', 'context']
        missing = [field for field in required if field not in payload]
        
        if missing:
            return False, f"Missing required fields: {missing}"
        
        if not isinstance(payload['success'], bool):
            return False, "Success must be a boolean"
        
        return True, ""
    
    @staticmethod
    def _validate_successful_fix(payload: Dict, source_worker: str) -> Tuple[bool, str]:
        """Validate successful fix knowledge"""
        required = ['issue_type', 'improvement', 'pattern', 'fix_details']
        missing = [field for field in required if field not in payload]
        
        if missing:
            return False, f"Missing required fields: {missing}"
        
        if not isinstance(payload['improvement'], (int, float)):
            return False, "Improvement must be numeric"
        
        if not 0 <= payload['improvement'] <= 1:
            return False, "Improvement must be between 0 and 1"
        
        return True, ""
    
    @staticmethod
    def _validate_issue_pattern(payload: Dict, source_worker: str) -> Tuple[bool, str]:
        """Validate issue pattern knowledge"""
        required = ['issue_type', 'severity', 'frequency', 'impact']
        missing = [field for field in required if field not in payload]
        
        if missing:
            return False, f"Missing required fields: {missing}"
        
        if not isinstance(payload['frequency'], (int, float)):
            return False, "Frequency must be numeric"
        
        return True, ""
    
    @staticmethod
    def _validate_context_enrichment(payload: Dict, source_worker: str) -> Tuple[bool, str]:
        """Validate context enrichment knowledge"""
        required = ['context_type', 'enrichment', 'relevance']
        missing = [field for field in required if field not in payload]
        
        if missing:
            return False, f"Missing required fields: {missing}"
        
        if not isinstance(payload['relevance'], (int, float)):
            return False, "Relevance must be numeric"
        
        if not 0 <= payload['relevance'] <= 1:
            return False, "Relevance must be between 0 and 1"
        
        return True, ""

#### 1.5 Integration Points

**Database Schema for Knowledge Exchange**

```sql
-- Knowledge Exchange Registry
CREATE TABLE knowledge_exchange (
    exchange_id SERIAL PRIMARY KEY,
    source_worker VARCHAR(50) NOT NULL,
    target_worker VARCHAR(50),
    knowledge_type VARCHAR(50) NOT NULL,
    knowledge_data JSONB NOT NULL,
    metadata JSONB,
    freshness_score FLOAT,
    validation_status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    INDEX idx_source_worker (source_worker),
    INDEX idx_knowledge_type (knowledge_type),
    INDEX idx_freshness (freshness_score)
);

-- Worker Knowledge State
CREATE TABLE worker_knowledge_state (
    worker_name VARCHAR(50) PRIMARY KEY,
    knowledge_snapshot JSONB,
    last_exchange TIMESTAMP,
    exchange_count INTEGER,
    received_knowledge JSONB,
    broadcast_knowledge JSONB,
    FOREIGN KEY (worker_name) REFERENCES workers(name)
);

-- Knowledge Validation Results
CREATE TABLE knowledge_validation (
    validation_id SERIAL PRIMARY KEY,
    exchange_id INTEGER REFERENCES knowledge_exchange(exchange_id),
    validator_worker VARCHAR(50),
    is_valid BOOLEAN,
    validation_score FLOAT,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**API Endpoints for Knowledge Exchange**

```python
# Backend API endpoints (FastAPI)

@app.post("/api/knowledge/exchange")
async def broadcast_knowledge(
    source_worker: str,
    knowledge_type: str,
    payload: Dict,
    urgency: str = "normal",
    target_workers: Optional[List[str]] = None
):
    """Broadcast knowledge to workers"""
    protocol = get_knowledge_protocol()
    
    if target_workers:
        # Unicast to specific workers
        for target in target_workers:
            await protocol.unicast(
                source_worker, target, knowledge_type, payload
            )
    else:
        # Broadcast to all interested workers
        await protocol.broadcast_knowledge(
            source_worker, knowledge_type, payload, urgency
        )
    
    return {"status": "success", "message": "Knowledge broadcasted"}

@app.get("/api/knowledge/receive/{worker_name}")
async def receive_knowledge(worker_name: str):
    """Receive knowledge for a worker"""
    protocol = get_knowledge_protocol()
    
    knowledge = await protocol.receive_knowledge(worker_name)
    
    return {
        "status": "success",
        "knowledge": knowledge,
        "timestamp": utc_now()
    }

@app.get("/api/knowledge/stats/{worker_name}")
async def get_knowledge_stats(worker_name: str):
    """Get knowledge exchange statistics for a worker"""
    # Query database for stats
    return {
        "worker": worker_name,
        "knowledge_received": 0,
        "knowledge_broadcasted": 0,
        "avg_freshness": 0.0,
        "validation_rate": 0.0
    }
```

### Implementation Plan

**Phase 1: Foundation (Week 1)**
1. Create `KnowledgeExchangeProtocol` class
2. Add knowledge exchange to BaseWorker
3. Implement basic validation framework
4. Create database schema for knowledge exchange
5. Add API endpoints for manual knowledge broadcast

**Phase 2: Integration (Week 2)**
1. Integrate knowledge exchange into ThinkWorker
2. Integrate into LearningWorker
3. Integrate into AnalysisWorker
4. Integrate into DreamWorker
5. Integrate into RecallWorker

**Phase 3: Advanced Features (Week 3)**
1. Implement freshness tracking
2. Add conflict resolution
3. Create knowledge propagation strategies
4. Add real-time notifications (WebSocket)
5. Implement knowledge deduplication

**Phase 4: Optimization (Week 4)**
1. Performance optimization
2. Caching strategies
3. Batch knowledge exchange
4. Compression for large knowledge payloads
5. Monitoring and metrics

---

## Feature 2: Experimental Strategies Leveraging Graphiti

### Current State
Workers use Graphiti for:
- Historical pattern queries (keyword-based)
- Fact retrieval (simple searches)
- Limited multi-hop traversal

### Design: Advanced Graphiti Integration

#### 2.1 Multi-Hop Knowledge Graph Traversal

**Traversal Strategies**

```python
class GraphitiTraversalStrategies:
    """Advanced traversal strategies for Graphiti"""
    
    def __init__(self, graphiti_client):
        self.client = graphiti_client
    
    async def multi_hop_traversal(
        self, 
        start_entity: str, 
        max_hops: int = 3,
        direction: str = "both",
        relationship_types: Optional[List[str]] = None
    ) -> Dict:
        """
        Multi-hop traversal through knowledge graph
        
        Args:
            start_entity: Starting entity/node
            max_hops: Maximum number of hops
            direction: 'outgoing', 'incoming', or 'both'
            relationship_types: Filter by relationship types
        
        Returns:
            Dict with paths, entities, and insights
        """
        # Build traversal query
        query = self._build_multi_hop_query(
            start_entity, max_hops, direction, relationship_types
        )
        
        # Execute traversal
        results = await self.client.traverse(query)
        
        # Analyze results
        analysis = self._analyze_traversal_results(results)
        
        return {
            'paths': results['paths'],
            'entities': results['entities'],
            'relationships': results['relationships'],
            'analysis': analysis,
            'traversal_id': generate_uuid()
        }
    
    def _build_multi_hop_query(
        self, 
        start_entity: str, 
        max_hops: int,
        direction: str,
        relationship_types: Optional[List[str]]
    ) -> str:
        """Build Cypher query for multi-hop traversal"""
        
        # Base traversal pattern
        if direction == "both":
            pattern = f"(start {{name: '{start_entity}'}})-[*1..{max_hops}]-(end)"
        elif direction == "outgoing":
            pattern = f"(start {{name: '{start_entity}'}})-[*1..{max_hops}]->(end)"
        else:  # incoming
            pattern = f"(start {{name: '{start_entity}'}})<-[*1..{max_hops}]-(end)"
        
        # Add relationship type filters
        if relationship_types:
            rel_pattern = "|".join([f":{rt}" for rt in relationship_types])
            pattern = pattern.replace(")-", f"){rel_pattern}-")
        
        # Build full query
        query = f"""
        MATCH {pattern}
        WHERE start.name = '{start_entity}'
        RETURN 
            start, 
            end, 
            relationships(path) as rels,
            nodes(path) as nodes,
            length(path) as hop_count
        ORDER BY hop_count ASC
        """
        
        return query
    
    async def semantic_similarity_search(
        self, 
        query_embedding: List[float], 
        entity_type: Optional[str] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.7
    ) -> Dict:
        """
        Vector similarity search in knowledge graph
        
        Args:
            query_embedding: Embedding vector of query
            entity_type: Filter by entity type
            top_k: Number of results
            similarity_threshold: Minimum similarity score
        
        Returns:
            Similar entities and relationships
        """
        # Build similarity query
        query = self._build_similarity_query(
            query_embedding, entity_type, top_k, similarity_threshold
        )
        
        # Execute similarity search
        results = await self.client.similarity_search(query)
        
        return {
            'similar_entities': results['entities'],
            'similarity_scores': results['scores'],
            'relationships': results['relationships'],
            'search_id': generate_uuid()
        }
    
    def _build_similarity_query(
        self, 
        embedding: List[float], 
        entity_type: Optional[str],
        top_k: int,
        threshold: float
    ) -> str:
        """Build similarity search query"""
        
        # Convert embedding to string for query
        embedding_str = str(embedding)
        
        # Base similarity query
        query = f"""
        CALL db.index.vector.queryNodes(
            'entity_embedding', 
            {top_k}, 
            {embedding_str}
        ) YIELD node, score
        """
        
        # Add entity type filter if specified
        if entity_type:
            query += f"\nWHERE node:type = '{entity_type}'"
        
        # Add similarity threshold
        query += f"\nAND score >= {threshold}"
        
        # Return results
        query += """
        RETURN 
            node.name as entity,
            node.type as type,
            score,
            node.metadata as metadata
        ORDER BY score DESC
        """
        
        return query
    
    async def temporal_pattern_analysis(
        self, 
        entity_name: str, 
        pattern_type: str,
        time_window_days: int = 30
    ) -> Dict:
        """
        Analyze temporal patterns in knowledge graph
        
        Args:
            entity_name: Entity to analyze
            pattern_type: Type of pattern (e.g., 'evolution', 'trend', 'seasonal')
            time_window_days: Time window in days
        
        Returns:
            Temporal analysis results
        """
        query = self._build_temporal_query(
            entity_name, pattern_type, time_window_days
        )
        
        results = await self.client.execute_query(query)
        
        analysis = self._analyze_temporal_patterns(results, pattern_type)
        
        return {
            'entity': entity_name,
            'pattern_type': pattern_type,
            'time_window': time_window_days,
            'temporal_data': results,
            'analysis': analysis,
            'trend': analysis.get('trend', 'unknown')
        }
    
    def _build_temporal_query(
        self, 
        entity_name: str, 
        pattern_type: str, 
        time_window_days: int
    ) -> str:
        """Build temporal analysis query"""
        
        # Calculate timestamp
        timestamp = (datetime.now() - timedelta(days=time_window_days)).isoformat()
        
        if pattern_type == 'evolution':
            query = f"""
            MATCH (e {{name: '{entity_name}'}})-[r]->(related)
            WHERE r.timestamp >= '{timestamp}'
            RETURN 
                e.name as entity,
                type(r) as relationship,
                related.name as related_entity,
                r.timestamp as timestamp,
                r.metadata as metadata
            ORDER BY r.timestamp ASC
            """
        
        elif pattern_type == 'trend':
            query = f"""
            MATCH (e {{name: '{entity_name}'}})-[r]->(related)
            WHERE r.timestamp >= '{timestamp}'
            WITH 
                date(r.timestamp) as day,
                count(r) as count,
                avg(r.score) as avg_score
            RETURN 
                day,
                count,
                avg_score
            ORDER BY day ASC
            """
        
        else:  # seasonal or other patterns
            query = f"""
            MATCH (e {{name: '{entity_name}'}})-[r]->(related)
            WHERE r.timestamp >= '{timestamp}'
            WITH 
                datetime(r.timestamp).month as month,
                datetime(r.timestamp).hour as hour,
                count(r) as frequency
            RETURN 
                month, 
                hour, 
                frequency
            ORDER BY month, hour
            """
        
        return query
    
    def _analyze_traversal_results(self, results: Dict) -> Dict:
        """Analyze multi-hop traversal results"""
        
        paths = results.get('paths', [])
        entities = results.get('entities', [])
        relationships = results.get('relationships', [])
        
        analysis = {
            'total_paths': len(paths),
            'total_entities': len(entities),
            'total_relationships': len(relationships),
            'avg_path_length': 0,
            'most_common_relationships': {},
            'key_insights': []
        }
        
        if paths:
            # Calculate average path length
            total_length = sum(len(p) for p in paths)
            analysis['avg_path_length'] = total_length / len(paths)
        
        # Count relationship types
        rel_counts = {}
        for rel in relationships:
            rel_type = rel.get('type', 'unknown')
            rel_counts[rel_type] = rel_counts.get(rel_type, 0) + 1
        
        analysis['most_common_relationships'] = dict(
            sorted(rel_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        )
        
        # Generate insights
        if len(entities) > 10:
            analysis['key_insights'].append(
                f"Large connected component found with {len(entities)} entities"
            )
        
        if analysis['avg_path_length'] > 2:
            analysis['key_insights'].append(
                f"Complex knowledge structure (avg path length: {analysis['avg_path_length']:.1f})"
            )
        
        return analysis
    
    def _analyze_temporal_patterns(self, results: List, pattern_type: str) -> Dict:
        """Analyze temporal pattern results"""
        
        analysis = {
            'pattern_type': pattern_type,
            'data_points': len(results),
            'trend': 'unknown',
            'seasonality': False,
            'anomalies': []
        }
        
        if not results:
            return analysis
        
        # Extract values for analysis
        if 'count' in results[0]:
            values = [r['count'] for r in results]
        elif 'avg_score' in results[0]:
            values = [r['avg_score'] for r in results]
        else:
            values = [r.get('frequency', 0) for r in results]
        
        # Calculate basic statistics
        if len(values) >= 2:
            # Determine trend
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]
            
            avg_first = sum(first_half) / len(first_half)
            avg_second = sum(second_half) / len(second_half)
            
            if avg_second > avg_first * 1.1:
                analysis['trend'] = 'increasing'
            elif avg_second < avg_first * 0.9:
                analysis['trend'] = 'decreasing'
            else:
                analysis['trend'] = 'stable'
        
        # Detect anomalies (simple z-score)
        if len(values) >= 3:
            mean = sum(values) / len(values)
            std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
            
            for i, v in enumerate(values):
                if std > 0:
                    z_score = abs(v - mean) / std
                    if z_score > 2:  # More than 2 standard deviations
                        analysis['anomalies'].append({
                            'index': i,
                            'value': v,
                            'z_score': z_score
                        })
        
        # Detect seasonality (if hourly/daily data)
        if pattern_type == 'seasonal' and len(values) >= 24:
            # Check for hourly patterns
            hourly_avg = [sum(values[i::24]) / len(values[i::24]) for i in range(24)]
            if max(hourly_avg) - min(hourly_avg) > 0.3:
                analysis['seasonality'] = True
        
        return analysis

#### 2.2 Graphiti-Powered Experimentation Strategies

**Experimental Strategy Registry**

```python
class GraphitiExperimentalStrategies:
    """Collection of experimental strategies using Graphiti"""
    
    def __init__(self, graphiti_client):
        self.client = graphiti_client
        self.strategies = self._initialize_strategies()
    
    def _initialize_strategies(self) -> Dict[str, Dict]:
        """Initialize experimental strategies"""
        return {
            'multi_hop_exploration': {
                'name': 'Multi-Hop Knowledge Exploration',
                'description': 'Explore knowledge graph through multi-hop traversal',
                'workers': ['think', 'recall'],
                'parameters': {
                    'max_hops': 3,
                    'direction': 'both',
                    'relationship_types': None
                },
                'metrics': ['coverage', 'novelty', 'relevance'],
                'risk_level': 'low'
            },
            
            'semantic_similarity_search': {
                'name': 'Semantic Similarity Search',
                'description': 'Find similar entities using vector embeddings',
                'workers': ['think', 'learning', 'dream'],
                'parameters': {
                    'top_k': 10,
                    'similarity_threshold': 0.7
                },
                'metrics': ['precision', 'recall', 'diversity'],
                'risk_level': 'low'
            },
            
            'temporal_evolution_analysis': {
                'name': 'Temporal Pattern Evolution',
                'description': 'Analyze how patterns evolve over time',
                'workers': ['learning', 'analysis'],
                'parameters': {
                    'time_window_days': 30,
                    'pattern_type': 'evolution'
                },
                'metrics': ['trend_accuracy', 'prediction_quality'],
                'risk_level': 'medium'
            },
            
            'cross_domain_transfer': {
                'name': 'Cross-Domain Pattern Transfer',
                'description': 'Transfer patterns from one domain to another',
                'workers': ['learning', 'dream'],
                'parameters': {
                    'source_domain': None,
                    'target_domain': None,
                    'similarity_threshold': 0.8
                },
                'metrics': ['transfer_success', 'adaptation_quality'],
                'risk_level': 'high'
            },
            
            'graph_community_detection': {
                'name': 'Knowledge Graph Community Detection',
                'description': 'Identify communities of related entities',
                'workers': ['analysis', 'think'],
                'parameters': {
                    'algorithm': 'louvain',
                    'min_community_size': 3
                },
                'metrics': ['cohesion', 'separation', 'stability'],
                'risk_level': 'low'
            },
            
            'path_explanation': {
                'name': 'Path Explanation Generation',
                'description': 'Generate natural language explanations for knowledge paths',
                'workers': ['think', 'dream'],
                'parameters': {
                    'max_path_length': 5,
                    'explanation_depth': 2
                },
                'metrics': ['clarity', 'completeness', 'usefulness'],
                'risk_level': 'low'
            },
            
            'anomaly_detection': {
                'name': 'Graph Anomaly Detection',
                'description': 'Detect anomalies and outliers in knowledge graph',
                'workers': ['analysis', 'think'],
                'parameters': {
                    'algorithm': 'isolation_forest',
                    'contamination': 0.1
                },
                'metrics': ['detection_rate', 'false_positive_rate'],
                'risk_level': 'medium'
            }
        }
    
    async def execute_strategy(
        self, 
        strategy_name: str, 
        context: Dict,
        worker_name: str
    ) -> Dict:
        """
        Execute an experimental strategy
        
        Args:
            strategy_name: Name of strategy to execute
            context: Context for strategy execution
            worker_name: Worker executing the strategy
        
        Returns:
            Strategy execution results
        """
        if strategy_name not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        strategy = self.strategies[strategy_name]
        
        # Validate worker can execute this strategy
        if worker_name not in strategy['workers']:
            return {
                'status': 'error',
                'message': f'Worker {worker_name} cannot execute {strategy_name}'
            }
        
        # Prepare parameters
        params = strategy['parameters'].copy()
        params.update(context.get('parameters', {}))
        
        # Execute strategy
        start_time = time.time()
        
        try:
            if strategy_name == 'multi_hop_exploration':
                result = await self._execute_multi_hop_exploration(params)
            elif strategy_name == 'semantic_similarity_search':
                result = await self._execute_semantic_similarity_search(params)
            elif strategy_name == 'temporal_evolution_analysis':
                result = await self._execute_temporal_evolution_analysis(params)
            elif strategy_name == 'cross_domain_transfer':
                result = await self._execute_cross_domain_transfer(params)
            elif strategy_name == 'graph_community_detection':
                result = await self._execute_graph_community_detection(params)
            elif strategy_name == 'path_explanation':
                result = await self._execute_path_explanation(params)
            elif strategy_name == 'anomaly_detection':
                result = await self._execute_anomaly_detection(params)
            else:
                return {'status': 'error', 'message': 'Strategy not implemented'}
            
            elapsed = time.time() - start_time
            
            # Calculate metrics
            metrics = self._calculate_strategy_metrics(
                strategy_name, result, context
            )
            
            return {
                'status': 'success',
                'strategy': strategy_name,
                'result': result,
                'metrics': metrics,
                'execution_time': elapsed,
                'timestamp': utc_now()
            }
            
        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'strategy': strategy_name
            }
    
    async def _execute_multi_hop_exploration(self, params: Dict) -> Dict:
        """Execute multi-hop exploration strategy"""
        traversal = GraphitiTraversalStrategies(self.client)
        
        # Get start entity from context or params
        start_entity = params.get('start_entity')
        if not start_entity:
            return {'error': 'No start entity provided'}
        
        results = await traversal.multi_hop_traversal(
            start_entity=start_entity,
            max_hops=params.get('max_hops', 3),
            direction=params.get('direction', 'both'),
            relationship_types=params.get('relationship_types')
        )
        
        return results
    
    async def _execute_semantic_similarity_search(self, params: Dict) -> Dict:
        """Execute semantic similarity search strategy"""
        traversal = GraphitiTraversalStrategies(self.client)
        
        # Get query embedding
        query_embedding = params.get('query_embedding')
        if not query_embedding:
            return {'error': 'No query embedding provided'}
        
        results = await traversal.semantic_similarity_search(
            query_embedding=query_embedding,
            entity_type=params.get('entity_type'),
            top_k=params.get('top_k', 10),
            similarity_threshold=params.get('similarity_threshold', 0.7)
        )
        
        return results
    
    async def _execute_temporal_evolution_analysis(self, params: Dict) -> Dict:
        """Execute temporal evolution analysis strategy"""
        traversal = GraphitiTraversalStrategies(self.client)
        
        # Get entity and pattern type
        entity_name = params.get('entity_name')
        pattern_type = params.get('pattern_type', 'evolution')
        
        if not entity_name:
            return {'error': 'No entity name provided'}
        
        results = await traversal.temporal_pattern_analysis(
            entity_name=entity_name,
            pattern_type=pattern_type,
            time_window_days=params.get('time_window_days', 30)
        )
        
        return results
    
    async def _execute_cross_domain_transfer(self, params: Dict) -> Dict:
        """Execute cross-domain pattern transfer strategy"""
        # This would require additional logic to identify source and target domains
        source_domain = params.get('source_domain')
        target_domain = params.get('target_domain')
        
        if not source_domain or not target_domain:
            return {'error': 'Source and target domains required'}
        
        # Query for patterns in source domain
        source_query = f"pattern in domain: {source_domain}"
        source_results = await self.client.search_decisions(
            query=source_query, limit=20
        )
        
        # Filter for transferable patterns
        transferable = []
        for result in source_results:
            # Check if pattern can be adapted to target domain
            can_transfer = self._assess_transferability(
                result, source_domain, target_domain
            )
            
            if can_transfer:
                transferable.append({
                    'pattern': result.get('fact'),
                    'source_domain': source_domain,
                    'transferability_score': can_transfer['score'],
                    'adaptation_notes': can_transfer['notes']
                })
        
        return {
            'source_domain': source_domain,
            'target_domain': target_domain,
            'transferable_patterns': transferable,
            'total_found': len(source_results),
            'transferable_count': len(transferable)
        }
    
    def _assess_transferability(self, pattern, source_domain, target_domain):
        """Assess if pattern can be transferred between domains"""
        # Simple heuristic: check for domain-specific keywords
        source_keywords = self._extract_domain_keywords(source_domain)
        target_keywords = self._extract_domain_keywords(target_domain)
        
        pattern_text = pattern.get('fact', '').lower()
        
        # Count source domain keywords in pattern
        source_count = sum(1 for kw in source_keywords if kw in pattern_text)
        
        # Check if target keywords exist
        target_count = sum(1 for kw in target_keywords if kw in pattern_text)
        
        # Calculate transferability score
        if source_count > 0 and target_count == 0:
            # Pattern is domain-specific but not target-specific
            score = min(0.9, 0.5 + (source_count * 0.1))
            notes = f"Pattern appears specific to {source_domain}, may need adaptation"
        elif target_count > 0:
            # Pattern already mentions target domain
            score = 1.0
            notes = f"Pattern already references {target_domain}"
        else:
            # Generic pattern
            score = 0.3
            notes = "Generic pattern, may not be specific enough"
        
        return {'score': score, 'notes': notes}
    
    def _extract_domain_keywords(self, domain: str) -> List[str]:
        """Extract keywords for a domain"""
        domain_keywords = {
            'database': ['database', 'sql', 'schema', 'migration', 'table', 'query'],
            'api': ['api', 'endpoint', 'route', 'request', 'response', 'rest'],
            'security': ['security', 'auth', 'authentication', 'authorization', 'token'],
            'performance': ['performance', 'optimization', 'cache', 'latency', 'throughput'],
            'ui': ['ui', 'frontend', 'render', 'component', 'interface'],
            'backend': ['backend', 'server', 'service', 'controller', 'handler']
        }
        
        return domain_keywords.get(domain, [])
    
    async def _execute_graph_community_detection(self, params: Dict) -> Dict:
        """Execute graph community detection strategy"""
        # Use Graphiti's community detection capabilities
        algorithm = params.get('algorithm', 'louvain')
        min_size = params.get('min_community_size', 3)
        
        query = f"""
        CALL gds.louvain.stream({{
            graphName: 'knowledge_graph',
            relationshipTypes: ['RELATES_TO', 'PART_OF']
        }})
        YIELD nodeId, communityId, intermediateCommunities
        WITH communityId, count(nodeId) as size
        WHERE size >= {min_size}
        RETURN communityId, size
        ORDER BY size DESC
        """
        
        try:
            results = await self.client.execute_query(query)
            
            return {
                'algorithm': algorithm,
                'communities': results,
                'total_communities': len(results),
                'avg_community_size': sum(r['size'] for r in results) / len(results) if results else 0
            }
        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            return {'error': str(e)}
    
    async def _execute_path_explanation(self, params: Dict) -> Dict:
        """Execute path explanation strategy"""
        # This would generate natural language explanations for knowledge paths
        # Using LLM to explain why certain entities are connected
        
        max_path_length = params.get('max_path_length', 5)
        
        # Query for interesting paths
        query = f"""
        MATCH path = (start)-[*1..{max_path_length}]-(end)
        WHERE start:Entity AND end:Entity
        AND length(path) >= 2
        WITH path, relationships(path) as rels
        ORDER BY length(path) DESC
        LIMIT 10
        RETURN 
            start.name as start_entity,
            end.name as end_entity,
            [r IN rels | type(r)] as relationship_types,
            length(path) as path_length
        """
        
        try:
            paths = await self.client.execute_query(query)
            
            # Generate explanations using LLM
            explanations = []
            for path in paths[:3]:  # Limit to top 3
                explanation = await self._generate_path_explanation(path)
                explanations.append({
                    'path': path,
                    'explanation': explanation
                })
            
            return {
                'paths_analyzed': len(paths),
                'explanations': explanations,
                'average_path_length': sum(p['path_length'] for p in paths) / len(paths) if paths else 0
            }
        except Exception as e:
            logger.error(f"Path explanation failed: {e}")
            return {'error': str(e)}
    
    async def _generate_path_explanation(self, path: Dict) -> str:
        """Generate natural language explanation for a path"""
        llm = get_openai_client()
        
        prompt = f"""You are a knowledge graph analyst. Explain why these entities are connected.

Entities:
- Start: {path['start_entity']}
- End: {path['end_entity']}
- Relationship types: {path['relationship_types']}
- Path length: {path['path_length']}

Provide a concise explanation (2-3 sentences) of the logical connection between these entities.
"""
        
        try:
            response = llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate explanation: {e}")
            return "Unable to generate explanation"
    
    async def _execute_anomaly_detection(self, params: Dict) -> Dict:
        """Execute graph anomaly detection strategy"""
        algorithm = params.get('algorithm', 'isolation_forest')
        contamination = params.get('contamination', 0.1)
        
        # Query for entity features
        query = """
        MATCH (e:Entity)
        RETURN 
            e.name as name,
            e.degree as degree,
            e.betweenness as betweenness,
            e.pagerank as pagerank
        """
        
        try:
            entities = await self.client.execute_query(query)
            
            if not entities:
                return {'error': 'No entities found in graph'}
            
            # Extract features for anomaly detection
            features = []
            for entity in entities:
                features.append([
                    entity.get('degree', 0),
                    entity.get('betweenness', 0),
                    entity.get('pagerank', 0)
                ])
            
            # Simple anomaly detection (could use isolation forest)
            anomalies = self._detect_anomalies_simple(features, entities, contamination)
            
            return {
                'algorithm': algorithm,
                'contamination': contamination,
                'total_entities': len(entities),
                'anomalies': anomalies,
                'anomaly_count': len(anomalies)
            }
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return {'error': str(e)}
    
    def _detect_anomalies_simple(self, features, entities, contamination):
        """Simple anomaly detection using statistical methods"""
        if not features:
            return []
        
        # Calculate mean and std for each feature
        num_features = len(features[0])
        means = []
        stds = []
        
        for i in range(num_features):
            values = [f[i] for f in features]
            mean = sum(values) / len(values)
            std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
            means.append(mean)
            stds.append(std)
        
        # Detect anomalies (points with extreme values)
        anomalies = []
        for idx, (entity, feat) in enumerate(zip(entities, features)):
            anomaly_score = 0
            
            for i in range(num_features):
                if stds[i] > 0:
                    z_score = abs(feat[i] - means[i]) / stds[i]
                    if z_score > 2:  # More than 2 standard deviations
                        anomaly_score += 1
            
            # Mark as anomaly if multiple features are extreme
            if anomaly_score >= 2:
                anomalies.append({
                    'entity': entity['name'],
                    'anomaly_score': anomaly_score,
                    'features': {
                        'degree': feat[0],
                        'betweenness': feat[1],
                        'pagerank': feat[2]
                    },
                    'reason': f"Multiple extreme features ({anomaly_score})"
                })
        
        return anomalies
    
    def _calculate_strategy_metrics(
        self, 
        strategy_name: str, 
        result: Dict, 
        context: Dict
    ) -> Dict:
        """Calculate metrics for strategy execution"""
        metrics = {}
        
        if strategy_name == 'multi_hop_exploration':
            # Coverage: percentage of graph explored
            metrics['coverage'] = result.get('analysis', {}).get('total_entities', 0) / 1000  # Normalize
            
            # Novelty: unique entities found
            metrics['novelty'] = len(result.get('entities', [])) / 50  # Target: 50 entities
            
            # Relevance: average path length (shorter = more relevant)
            avg_length = result.get('analysis', {}).get('avg_path_length', 0)
            metrics['relevance'] = max(0, 1 - (avg_length / 10))  # Normalize
        
        elif strategy_name == 'semantic_similarity_search':
            # Precision: high similarity scores
            scores = result.get('similarity_scores', [])
            if scores:
                metrics['precision'] = sum(scores) / len(scores)
            
            # Recall: number of results
            metrics['recall'] = min(len(result.get('similar_entities', [])) / 10, 1.0)
            
            # Diversity: unique result types
            types = set([e.get('type') for e in result.get('similar_entities', [])])
            metrics['diversity'] = len(types) / 5  # Normalize by max types
        
        elif strategy_name == 'temporal_evolution_analysis':
            # Trend accuracy: based on prediction quality
            analysis = result.get('analysis', {})
            if analysis.get('trend') != 'unknown':
                metrics['trend_accuracy'] = 0.8  # Placeholder
            else:
                metrics['trend_accuracy'] = 0.3
            
            # Prediction quality: based on data points
            metrics['prediction_quality'] = min(result.get('data_points', 0) / 20, 1.0)
        
        elif strategy_name == 'cross_domain_transfer':
            # Transfer success: percentage of transferable patterns
            total = result.get('total_found', 0)
            transferable = result.get('transferable_count', 0)
            metrics['transfer_success'] = transferable / total if total > 0 else 0
            
            # Adaptation quality: average transferability score
            patterns = result.get('transferable_patterns', [])
            if patterns:
                avg_score = sum(p.get('transferability_score', 0) for p in patterns) / len(patterns)
                metrics['adaptation_quality'] = avg_score
        
        elif strategy_name == 'graph_community_detection':
            # Cohesion: average community size
            avg_size = result.get('avg_community_size', 0)
            metrics['cohesion'] = min(avg_size / 20, 1.0)  # Normalize
            
            # Separation: number of communities (more = better separation)
            metrics['separation'] = min(result.get('total_communities', 0) / 10, 1.0)
            
            # Stability: communities larger than threshold
            stable = sum(1 for c in result.get('communities', []) if c.get('size', 0) >= 5)
            metrics['stability'] = stable / result.get('total_communities', 1)
        
        elif strategy_name == 'path_explanation':
            # Clarity: would require human evaluation, using placeholder
            metrics['clarity'] = 0.7
            
            # Completeness: percentage of paths explained
            paths_analyzed = result.get('paths_analyzed', 0)
            explanations = len(result.get('explanations', []))
            metrics['completeness'] = explanations / paths_analyzed if paths_analyzed > 0 else 0
            
            # Usefulness: based on explanation count
            metrics['usefulness'] = min(explanations / 3, 1.0)  # Target: 3 explanations
        
        elif strategy_name == 'anomaly_detection':
            # Detection rate: percentage of anomalies found
            metrics['detection_rate'] = result.get('anomaly_count', 0) / result.get('total_entities', 1)
            
            # False positive rate: placeholder (would need ground truth)
            metrics['false_positive_rate'] = 0.2  # Placeholder
        
        return metrics
    
    def get_available_strategies(self, worker_name: str) -> List[Dict]:
        """Get available strategies for a worker"""
        available = []
        
        for name, strategy in self.strategies.items():
            if worker_name in strategy['workers']:
                available.append({
                    'name': name,
                    'description': strategy['description'],
                    'parameters': strategy['parameters'],
                    'metrics': strategy['metrics'],
                    'risk_level': strategy['risk_level']
                })
        
        return available
    
    def recommend_strategy(
        self, 
        worker_name: str, 
        context: Dict
    ) -> Optional[Dict]:
        """Recommend a strategy based on context"""
        available = self.get_available_strategies(worker_name)
        
        if not available:
            return None
        
        # Simple recommendation logic based on context
        context_type = context.get('context_type', '')
        
        # Map context types to strategies
        recommendations = {
            'risk_assessment': 'multi_hop_exploration',
            'pattern_matching': 'semantic_similarity_search',
            'evolution_tracking': 'temporal_evolution_analysis',
            'cross_domain_learning': 'cross_domain_transfer',
            'community_analysis': 'graph_community_detection',
            'knowledge_explanation': 'path_explanation',
            'anomaly_detection': 'anomaly_detection'
        }
        
        recommended_name = recommendations.get(context_type)
        
        if recommended_name:
            for strategy in available:
                if strategy['name'] == recommended_name:
                    return strategy
        
        # Default to first available strategy
        return available[0] if available else None

#### 2.3 Worker-Specific Experimentation Enhancements

**ThinkWorker Experiments**

```python
class EnhancedThinkWorker(ThinkWorker):
    """ThinkWorker with enhanced Graphiti experiments"""
    
    def __init__(self, db_session, dreamer):
        super().__init__(db_session, dreamer)
        self.graphiti_strategies = GraphitiExperimentalStrategies(
            get_graphiti_client_sync()
        )
        self.current_experiment = None
    
    def _experimental_cycle(self):
        """Enhanced experimental cycle with Graphiti strategies"""
        try:
            # Get baseline performance
            context = self._get_current_performance()
            
            # Get available Graphiti strategies
            available = self.graphiti_strategies.get_available_strategies('think')
            
            if not available:
                logger.info("No Graphiti strategies available")
                super()._experimental_cycle()
                return
            
            # Recommend strategy
            strategy = self.graphiti_strategies.recommend_strategy('think', context)
            
            if not strategy:
                logger.info("No suitable Graphiti strategy recommended")
                super()._experimental_cycle()
                return
            
            logger.info(f"🧪 Starting Graphiti experiment: {strategy['name']}")
            
            # Execute strategy
            start_time = time.time()
            
            result = asyncio.run(
                self.graphiti_strategies.execute_strategy(
                    strategy['name'], context, 'think'
                )
            )
            
            elapsed = time.time() - start_time
            
            # Record experiment
            exp_id = self.dreamer.record_experiment_start(
                worker_name="think",
                experiment_name=f"Graphiti: {strategy['name']}",
                hypothesis=strategy['description'],
                approach=f"Execute Graphiti strategy: {strategy['name']}",
                project_id=self.project_id
            )
            
            # Calculate improvement
            improvement = self._calculate_graphiti_improvement(result, context)
            
            # Record outcome
            self.dreamer.record_outcome(
                experiment_id=exp_id,
                outcome={
                    "success": improvement > 0,
                    "improvement": improvement,
                    "result_metrics": result.get('metrics', {}),
                    "baseline_metrics": context,
                    "elapsed_time": elapsed,
                    "strategy": strategy['name']
                }
            )
            
            logger.info(f"Graphiti experiment complete: improvement={improvement:.2%}")
            
            # If successful, update decision-making with new insights
            if improvement > 0.1:  # 10% improvement
                self._integrate_graphiti_insights(result)
            
        except Exception as e:
            logger.error(f"Enhanced experimental cycle failed: {e}")
            # Fall back to standard experimental cycle
            super()._experimental_cycle()
    
    def _calculate_graphiti_improvement(self, result: Dict, baseline: Dict) -> float:
        """Calculate improvement from Graphiti experiment"""
        if result.get('status') != 'success':
            return -0.1  # Penalty for failure
        
        metrics = result.get('metrics', {})
        
        if not metrics:
            return 0.0
        
        # Weighted improvement calculation
        improvement = 0.0
        
        # Coverage improvement
        if 'coverage' in metrics:
            improvement += metrics['coverage'] * 0.3
        
        # Relevance improvement
        if 'relevance' in metrics:
            improvement += metrics['relevance'] * 0.3
        
        # Novelty improvement
        if 'novelty' in metrics:
            improvement += metrics['novelty'] * 0.2
        
        # Precision/recall
        if 'precision' in metrics:
            improvement += metrics['precision'] * 0.2
        
        return min(improvement, 1.0)
    
    def _integrate_graphiti_insights(self, result: Dict):
        """Integrate Graphiti insights into decision-making"""
        if 'result' not in result:
            return
        
        result_data = result['result']
        
        # Store insights for future use
        if 'entities' in result_data:
            # Extract key entities
            entities = result_data['entities']
            
            # Update internal knowledge base
            if hasattr(self, 'graphiti_knowledge'):
                for entity in entities:
                    self.graphiti_knowledge.add(entity)
        
        if 'analysis' in result_data:
            # Extract key insights
            analysis = result_data['analysis']
            
            if 'key_insights' in analysis:
                for insight in analysis['key_insights']:
                    logger.info(f"Graphiti Insight: {insight}")
                    
                    # Store for decision-making
                    if hasattr(self, 'insight_cache'):
                        self.insight_cache.append({
                            'insight': insight,
                            'source': 'graphiti',
                            'timestamp': utc_now()
                        })
        
        logger.info(f"Integrated {len(result_data.get('entities', []))} Graphiti insights")

**LearningWorker Experiments**

```python
class EnhancedLearningWorker(LearningWorker):
    """LearningWorker with enhanced Graphiti experiments"""
    
    def __init__(self, db_session, dreamer):
        super().__init__(db_session, dreamer)
        self.graphiti_strategies = GraphitiExperimentalStrategies(
            get_graphiti_client_sync()
        )
        self.pattern_evolution_tracker = PatternEvolutionTracker()
    
    def _experimental_cycle(self):
        """Enhanced experimental cycle for pattern learning"""
        try:
            # Get context
            context = self._get_current_performance()
            
            # Try temporal evolution analysis
            strategy_name = 'temporal_evolution_analysis'
            
            # Get representative entity (e.g., most frequent pattern)
            pattern_entity = self._get_most_frequent_pattern()
            
            if not pattern_entity:
                logger.info("No pattern entity found for analysis")
                super()._experimental_cycle()
                return
            
            logger.info(f"🧪 Starting pattern evolution analysis for: {pattern_entity}")
            
            # Execute strategy
            result = asyncio.run(
                self.graphiti_strategies.execute_strategy(
                    strategy_name, 
                    {'entity_name': pattern_entity, 'pattern_type': 'evolution'},
                    'learning'
                )
            )
            
            # Record experiment
            exp_id = self.dreamer.record_experiment_start(
                worker_name="learning",
                experiment_name=f"Pattern Evolution: {pattern_entity}",
                hypothesis=f"Pattern {pattern_entity} shows evolution over time",
                approach="Temporal analysis of pattern usage",
                project_id=self.project_id
            )
            
            # Calculate improvement
            improvement = self._calculate_evolution_improvement(result, context)
            
            # Record outcome
            self.dreamer.record_outcome(
                experiment_id=exp_id,
                outcome={
                    "success": improvement > 0,
                    "improvement": improvement,
                    "result_metrics": result.get('metrics', {}),
                    "pattern_entity": pattern_entity,
                    "trend": result.get('result', {}).get('analysis', {}).get('trend', 'unknown')
                }
            )
            
            # Update pattern evolution tracker
            if result.get('status') == 'success':
                self.pattern_evolution_tracker.update(
                    pattern_entity,
                    result['result']['analysis']
                )
            
            logger.info(f"Pattern evolution analysis complete: improvement={improvement:.2%}")
            
        except Exception as e:
            logger.error(f"Enhanced learning experiment failed: {e}")
            super()._experimental_cycle()
    
    def _get_most_frequent_pattern(self) -> Optional[str]:
        """Get the most frequent pattern from learned patterns"""
        try:
            patterns = self.db.query(LearnedPattern)\
                .order_by(LearnedPattern.success_count.desc())\
                .limit(10)\
                .all()
            
            if patterns:
                # Return pattern name (as entity)
                return patterns[0].pattern_name
        except Exception as e:
            logger.error(f"Failed to get most frequent pattern: {e}")
        
        return None
    
    def _calculate_evolution_improvement(self, result: Dict, baseline: Dict) -> float:
        """Calculate improvement from evolution analysis"""
        if result.get('status') != 'success':
            return -0.1
        
        analysis = result.get('result', {}).get('analysis', {})
        
        improvement = 0.0
        
        # Trend accuracy
        trend = analysis.get('trend', 'unknown')
        if trend in ['increasing', 'decreasing', 'stable']:
            improvement += 0.5  # Successfully identified trend
        
        # Data points (more data = better)
        data_points = analysis.get('data_points', 0)
        improvement += min(data_points / 20, 0.3)  # Normalize
        
        # Anomalies detected (anomalies are interesting)
        anomalies = analysis.get('anomalies', [])
        if anomalies:
            improvement += min(len(anomalies) / 10, 0.2)
        
        return min(improvement, 1.0)

class PatternEvolutionTracker:
    """Track pattern evolution over time"""
    
    def __init__(self):
        self.evolution_history = {}
    
    def update(self, pattern_name: str, analysis: Dict):
        """Update evolution tracking for a pattern"""
        if pattern_name not in self.evolution_history:
            self.evolution_history[pattern_name] = []
        
        self.evolution_history[pattern_name].append({
            'timestamp': utc_now(),
            'trend': analysis.get('trend', 'unknown'),
            'data_points': analysis.get('data_points', 0),
            'anomalies': len(analysis.get('anomalies', [])),
            'seasonality': analysis.get('seasonality', False)
        })
        
        # Keep only recent history
        if len(self.evaluation_history[pattern_name]) > 10:
            self.evaluation_history[pattern_name] = self.evaluation_history[pattern_name][-10:]
    
    def get_evolution_trend(self, pattern_name: str) -> Dict:
        """Get evolution trend for a pattern"""
        history = self.evaluation_history.get(pattern_name, [])
        
        if not history:
            return {'trend': 'unknown', 'confidence': 0.0}
        
        # Analyze trend over time
        trends = [h['trend'] for h in history]
        increasing = trends.count('increasing')
        decreasing = trends.count('decreasing')
        stable = trends.count('stable')
        
        total = len(trends)
        
        if increasing / total > 0.6:
            return {'trend': 'increasing', 'confidence': increasing / total}
        elif decreasing / total > 0.6:
            return {'trend': 'decreasing', 'confidence': decreasing / total}
        elif stable / total > 0.6:
            return {'trend': 'stable', 'confidence': stable / total}
        else:
            return {'trend': 'volatile', 'confidence': 0.5}

#### 2.4 Real-Time Knowledge Graph Updates

**Real-Time Update System**

```python
class RealTimeGraphitiUpdater:
    """Real-time knowledge graph update system"""
    
    def __init__(self, graphiti_client):
        self.client = graphiti_client
        self.update_queue = asyncio.Queue()
        self.batch_size = 10
        self.batch_timeout = 5.0  # seconds
    
    async def start(self):
        """Start the real-time updater"""
        logger.info("Starting real-time Graphiti updater")
        
        while True:
            try:
                # Wait for batch or timeout
                batch = await self._collect_batch()
                
                if batch:
                    await self._process_batch(batch)
                
                await asyncio.sleep(0.1)  # Prevent CPU spinning
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Real-time updater error: {e}")
                await asyncio.sleep(1)  # Back off on error
    
    async def _collect_batch(self) -> List[Dict]:
        """Collect batch of updates"""
        batch = []
        start_time = time.time()
        
        while len(batch) < self.batch_size:
            remaining_time = self.batch_timeout - (time.time() - start_time)
            
            if remaining_time <= 0:
                break
            
            try:
                update = await asyncio.wait_for(
                    self.update_queue.get(),
                    timeout=remaining_time
                )
                batch.append(update)
                self.update_queue.task_done()
            except asyncio.TimeoutError:
                break
        
        return batch
    
    async def _process_batch(self, batch: List[Dict]):
        """Process batch of updates"""
        if not batch:
            return
        
        logger.info(f"Processing batch of {len(batch)} updates")
        
        # Group by type for efficient processing
        grouped = {}
        for update in batch:
            update_type = update.get('type', 'unknown')
            if update_type not in grouped:
                grouped[update_type] = []
            grouped[update_type].append(update)
        
        # Process each group
        for update_type, updates in grouped.items():
            try:
                if update_type == 'fact_insert':
                    await self._batch_insert_facts(updates)
                elif update_type == 'fact_update':
                    await self._batch_update_facts(updates)
                elif update_type == 'relationship_insert':
                    await self._batch_insert_relationships(updates)
                else:
                    logger.warning(f"Unknown update type: {update_type}")
            except Exception as e:
                logger.error(f"Failed to process {update_type} updates: {e}")
    
    async def queue_update(self, update: Dict):
        """Queue an update for processing"""
        await self.update_queue.put(update)
    
    async def _batch_insert_facts(self, updates: List[Dict]):
        """Batch insert facts into Graphiti"""
        facts = []
        for update in updates:
            fact = update.get('fact')
            if fact:
                facts.append(fact)
        
        if not facts:
            return
        
        # Use batch insert if available
        try:
            await self.client.batch_insert_facts(facts)
            logger.info(f"Inserted {len(facts)} facts")
        except Exception as e:
            logger.error(f"Batch insert failed: {e}")
            # Fall back to individual inserts
            for fact in facts:
                try:
                    await self.client.insert_fact(fact)
                except Exception as e:
                    logger.error(f"Failed to insert fact: {e}")
    
    async def _batch_update_facts(self, updates: List[Dict]):
        """Batch update facts in Graphiti"""
        for update in updates:
            fact_id = update.get('fact_id')
            new_fact = update.get('fact')
            
            if fact_id and new_fact:
                try:
                    await self.client.update_fact(fact_id, new_fact)
                except Exception as e:
                    logger.error(f"Failed to update fact {fact_id}: {e}")
    
    async def _batch_insert_relationships(self, updates: List[Dict]):
        """Batch insert relationships into Graphiti"""
        relationships = []
        for update in updates:
            rel = update.get('relationship')
            if rel:
                relationships.append(rel)
        
        if not relationships:
            return
        
        try:
            await self.client.batch_insert_relationships(relationships)
            logger.info(f"Inserted {len(relationships)} relationships")
        except Exception as e:
            logger.error(f"Batch insert failed: {e}")

#### 2.5 Experimentation Dashboard

**Backend API for Experimentation**

```python
# Backend API endpoints for Graphiti experiments

@app.get("/api/graphiti/strategies/{worker_name}")
async def get_strategies(worker_name: str):
    """Get available Graphiti strategies for a worker"""
    strategies = GraphitiExperimentalStrategies(get_graphiti_client_sync())
    available = strategies.get_available_strategies(worker_name)
    
    return {
        "worker": worker_name,
        "strategies": available,
        "count": len(available)
    }

@app.post("/api/graphiti/strategies/{worker_name}/execute")
async def execute_strategy(
    worker_name: str,
    strategy_name: str,
    parameters: Dict
):
    """Execute a Graphiti strategy"""
    strategies = GraphitiExperimentalStrategies(get_graphiti_client_sync())
    
    result = await strategies.execute_strategy(
        strategy_name, parameters, worker_name
    )
    
    return result

@app.get("/api/graphiti/experiments")
async def get_experiments():
    """Get Graphiti experiment history"""
    # Query experiments table for Graphiti experiments
    db = next(get_db())
    
    experiments = db.execute(text("""
        SELECT * FROM experiments 
        WHERE experiment_name LIKE 'Graphiti: %'
        ORDER BY started_at DESC
        LIMIT 50
    """)).fetchall()
    
    return {
        "experiments": [
            {
                "id": exp["experiment_id"],
                "name": exp["experiment_name"],
                "worker": exp["worker_name"],
                "status": exp["status"],
                "success": exp["success"],
                "improvement": exp["improvement"],
                "started_at": exp["started_at"],
                "completed_at": exp["completed_at"]
            }
            for exp in experiments
        ],
        "count": len(experiments)
    }

@app.get("/api/graphiti/stats")
async def get_graphiti_stats():
    """Get Graphiti statistics"""
    try:
        client = get_graphiti_client_sync()
        
        # Query basic stats
        stats = await client.get_stats()
        
        return {
            "status": "success",
            "stats": stats,
            "timestamp": utc_now()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": utc_now()
        }

@app.post("/api/graphiti/query")
async def query_graphiti(query: str, limit: int = 10):
    """Query Graphiti knowledge graph"""
    try:
        client = get_graphiti_client_sync()
        
        results = await client.search_decisions(query=query, limit=limit)
        
        return {
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
```

**Frontend Components for Experimentation**

```typescript
// Frontend React components for Graphiti experimentation

// Strategy Selection Component
interface Strategy {
  name: string;
  description: string;
  parameters: Record<string, any>;
  metrics: string[];
  risk_level: string;
}

interface StrategySelectorProps {
  workerName: string;
  onSelect: (strategy: Strategy) => void;
}

const StrategySelector: React.FC<StrategySelectorProps> = ({ workerName, onSelect }) => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchStrategies();
  }, [workerName]);
  
  const fetchStrategies = async () => {
    try {
      const response = await fetch(`/api/graphiti/strategies/${workerName}`);
      const data = await response.json();
      setStrategies(data.strategies || []);
    } catch (error) {
      console.error("Failed to fetch strategies:", error);
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return <div>Loading strategies...</div>;
  }
  
  return (
    <div className="strategy-selector">
      <h3>Available Graphiti Strategies for {workerName}</h3>
      <div className="strategy-grid">
        {strategies.map((strategy) => (
          <div 
            key={strategy.name} 
            className="strategy-card"
            onClick={() => onSelect(strategy)}
          >
            <h4>{strategy.name}</h4>
            <p>{strategy.description}</p>
            <div className="strategy-meta">
              <span className={`risk-level ${strategy.risk_level}`}>
                Risk: {strategy.risk_level}
              </span>
              <span>Metrics: {strategy.metrics.join(", ")}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Strategy Parameters Component
interface StrategyParametersProps {
  strategy: Strategy;
  onExecute: (parameters: Record<string, any>) => void;
}

const StrategyParameters: React.FC<StrategyParametersProps> = ({ strategy, onExecute }) => {
  const [parameters, setParameters] = useState<Record<string, any>>({});
  
  useEffect(() => {
    // Initialize parameters with defaults
    const defaults = { ...strategy.parameters };
    setParameters(defaults);
  }, [strategy]);
  
  const handleParameterChange = (key: string, value: any) => {
    setParameters(prev => ({ ...prev, [key]: value }));
  };
  
  const executeStrategy = () => {
    onExecute(parameters);
  };
  
  return (
    <div className="strategy-parameters">
      <h4>Strategy Parameters: {strategy.name}</h4>
      <div className="parameters-form">
        {Object.entries(strategy.parameters).map(([key, defaultValue]) => (
          <div key={key} className="parameter-group">
            <label>{key}</label>
            <input
              type="text"
              defaultValue={defaultValue}
              onChange={(e) => handleParameterChange(key, e.target.value)}
              placeholder={`Enter ${key}...`}
            />
          </div>
        ))}
      </div>
      <button onClick={executeStrategy} className="execute-btn">
        Execute Strategy
      </button>
    </div>
  );
};

// Experiment Results Component
interface ExperimentResultsProps {
  results: any;
  onRerun?: () => void;
  onSave?: () => void;
}

const ExperimentResults: React.FC<ExperimentResultsProps> = ({ results, onRerun, onSave }) => {
  const [activeTab, setActiveTab] = useState<'summary' | 'details' | 'metrics'>('summary');
  
  if (!results) {
    return <div>No results to display</div>;
  }
  
  return (
    <div className="experiment-results">
      <div className="results-header">
        <h3>Experiment Results</h3>
        <div className="results-actions">
          {onRerun && <button onClick={onRerun}>Rerun</button>}
          {onSave && <button onClick={onSave}>Save</button>}
        </div>
      </div>
      
      <div className="results-tabs">
        <button 
          className={activeTab === 'summary' ? 'active' : ''}
          onClick={() => setActiveTab('summary')}
        >
          Summary
        </button>
        <button 
          className={activeTab === 'details' ? 'active' : ''}
          onClick={() => setActiveTab('details')}
        >
          Details
        </button>
        <button 
          className={activeTab === 'metrics' ? 'active' : ''}
          onClick={() => setActiveTab('metrics')}
        >
          Metrics
        </button>
      </div>
      
      <div className="results-content">
        {activeTab === 'summary' && (
          <div className="summary-view">
            <div className="status-indicator">
              <span className={`status ${results.status}`}>
                {results.status.toUpperCase()}
              </span>
            </div>
            <div className="results-metrics">
              {results.metrics && Object.entries(results.metrics).map(([key, value]) => (
                <div key={key} className="metric">
                  <span className="metric-name">{key}</span>
                  <span className="metric-value">
                    {typeof value === 'number' ? value.toFixed(3) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {activeTab === 'details' && (
          <div className="details-view">
            <pre>{JSON.stringify(results, null, 2)}</pre>
          </div>
        )}
        
        {activeTab === 'metrics' && results.metrics && (
          <div className="metrics-view">
            <div className="metrics-chart">
              {Object.entries(results.metrics).map(([key, value]) => (
                <div key={key} className="metric-bar">
                  <div className="bar-label">{key}</div>
                  <div className="bar-container">
                    <div 
                      className="bar-fill"
                      style={{ width: `${Math.min(value * 100, 100)}%` }}
                    />
                  </div>
                  <div className="bar-value">{(value * 100).toFixed(1)}%</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Graphiti Dashboard Component
const GraphitiDashboard: React.FC = () => {
  const [selectedWorker, setSelectedWorker] = useState<string>('think');
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [parameters, setParameters] = useState<Record<string, any> | null>(null);
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [experiments, setExperiments] = useState<any[]>([]);
  
  const handleExecuteStrategy = async (params: Record<string, any>) => {
    if (!selectedStrategy) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/graphiti/strategies/${selectedWorker}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strategy_name: selectedStrategy.name,
          parameters: params
        })
      });
      
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error("Execution failed:", error);
      setResults({ status: 'error', message: String(error) });
    } finally {
      setLoading(false);
    }
  };
  
  const fetchExperiments = async () => {
    try {
      const response = await fetch('/api/graphiti/experiments');
      const data = await response.json();
      setExperiments(data.experiments || []);
    } catch (error) {
      console.error("Failed to fetch experiments:", error);
    }
  };
  
  useEffect(() => {
    fetchExperiments();
    const interval = setInterval(fetchExperiments, 30000);
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="graphiti-dashboard">
      <h2>Graphiti Experimentation Dashboard</h2>
      
      <div className="dashboard-grid">
        <div className="dashboard-panel">
          <h3>1. Select Worker & Strategy</h3>
          <div className="worker-selector">
            <label>Worker:</label>
            <select 
              value={selectedWorker} 
              onChange={(e) => setSelectedWorker(e.target.value)}
            >
              <option value="think">Think Worker</option>
              <option value="learning">Learning Worker</option>
              <option value="analysis">Analysis Worker</option>
              <option value="dream">Dream Worker</option>
              <option value="recall">Recall Worker</option>
            </select>
          </div>
          <StrategySelector 
            workerName={selectedWorker} 
            onSelect={setSelectedStrategy} 
          />
        </div>
        
        {selectedStrategy && (
          <div className="dashboard-panel">
            <h3>2. Configure Parameters</h3>
            <StrategyParameters 
              strategy={selectedStrategy} 
              onExecute={handleExecuteStrategy} 
            />
          </div>
        )}
        
        {results && (
          <div className="dashboard-panel">
            <h3>3. View Results</h3>
            <ExperimentResults results={results} />
          </div>
        )}
        
        <div className="dashboard-panel">
          <h3>Recent Experiments</h3>
          <div className="experiments-list">
            {experiments.length === 0 ? (
              <p>No experiments yet</p>
            ) : (
              experiments.slice(0, 10).map((exp: any) => (
                <div key={exp.id} className="experiment-item">
                  <div className="experiment-info">
                    <span className="experiment-name">{exp.name}</span>
                    <span className="experiment-worker">({exp.worker})</span>
                  </div>
                  <div className="experiment-status">
                    <span className={`status ${exp.status}`}>
                      {exp.status}
                    </span>
                    {exp.improvement !== null && (
                      <span className="improvement">
                        {exp.improvement > 0 ? '+' : ''}{(exp.improvement * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
```

### Implementation Plan

**Phase 1: Core Graphiti Enhancements (Week 1-2)**
1. Create `GraphitiTraversalStrategies` class
2. Implement multi-hop traversal
3. Add semantic similarity search
4. Create temporal analysis
5. Add basic experimental strategies

**Phase 2: Worker Integration (Week 2-3)**
1. Integrate into ThinkWorker
2. Integrate into LearningWorker
3. Add to AnalysisWorker
4. Enhance DreamWorker
5. Update RecallWorker

**Phase 3: Advanced Features (Week 3-4)**
1. Real-time Graphiti updates
2. Cross-domain pattern transfer
3. Community detection
4. Path explanations
5. Anomaly detection

**Phase 4: UI and Experimentation (Week 4-5)**
1. Backend API endpoints
2. Frontend components
3. Experimentation dashboard
4. Results visualization
5. Strategy recommendation

**Phase 5: Optimization (Week 5-6)**
1. Performance optimization
2. Caching strategies
3. Batch operations
4. Monitoring and metrics
5. Documentation

---

## Feature 3: Worker Prompts Extraction to UI

### Current State
Prompts are hardcoded in worker classes:
- ThinkWorker: Committee scoring prompts
- LearningWorker: Pattern quality prompts
- AnalysisWorker: Issue severity prompts
- DreamWorker: Proposal generation prompts
- RecallWorker: Query building prompts

### Design: Centralized Prompt Management

#### 3.1 Database Schema for Prompts

```sql
-- Prompt Templates Table
CREATE TABLE prompt_templates (
    template_id SERIAL PRIMARY KEY,
    worker_name VARCHAR(50) NOT NULL,
    prompt_type VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    system_prompt TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL,
    parameters JSONB,  -- Expected parameters for template
    metadata JSONB,  -- Additional metadata (tags, categories, etc.)
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    FOREIGN KEY (worker_name) REFERENCES workers(name),
    UNIQUE(worker_name, prompt_type, name, version)
);

-- Prompt Usage History
CREATE TABLE prompt_usage (
    usage_id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES prompt_templates(template_id),
    worker_name VARCHAR(50) NOT NULL,
    execution_id VARCHAR(100),
    context JSONB,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost DECIMAL(10, 6),  -- in USD
    latency_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_template_usage (template_id, created_at),
    INDEX idx_worker_usage (worker_name, created_at)
);

-- Prompt Versions History
CREATE TABLE prompt_versions (
    version_id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES prompt_templates(template_id),
    version INTEGER NOT NULL,
    system_prompt TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL,
    parameters JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    change_notes TEXT,
    INDEX idx_template_versions (template_id, version)
);

-- Prompt Tests
CREATE TABLE prompt_tests (
    test_id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES prompt_templates(template_id),
    name VARCHAR(200) NOT NULL,
    test_input JSONB NOT NULL,
    expected_output JSONB,
    expected_error TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_template_tests (template_id)
);

-- Prompt Validation Results
CREATE TABLE prompt_validations (
    validation_id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES prompt_templates(template_id),
    test_id INTEGER REFERENCES prompt_tests(test_id),
    execution_id VARCHAR(100),
    status VARCHAR(20) CHECK (status IN ('passed', 'failed', 'skipped')),
    actual_output JSONB,
    error_message TEXT,
    validation_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_template_validations (template_id, created_at)
);

-- Prompt Usage Analytics
CREATE TABLE prompt_analytics (
    analytics_id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES prompt_templates(template_id),
    date DATE NOT NULL,
    usage_count INTEGER DEFAULT 0,
    avg_latency_ms INTEGER,
    success_rate DECIMAL(5, 4),
    avg_cost DECIMAL(10, 6),
    total_cost DECIMAL(12, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(template_id, date)
);
```

#### 3.2 Prompt Template Model

```python
# src/openmemory/app/models.py additions

from sqlalchemy import Column, Integer, String, Text, Boolean, Float, JSON, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class PromptTemplate(Base):
    """Prompt template for AI agents"""
    __tablename__ = 'prompt_templates'
    
    template_id = Column(Integer, primary_key=True, index=True)
    worker_name = Column(String(50), nullable=False, index=True)
    prompt_type = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)
    parameters = Column(JSON, default=dict)  # Expected parameters
    metadata = Column(JSON, default=dict)  # Tags, categories, etc.
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))
    updated_by = Column(String(100))
    
    # Relationships
    versions = relationship("PromptVersion", back_populates="template", cascade="all, delete-orphan")
    tests = relationship("PromptTest", back_populates="template", cascade="all, delete-orphan")
    usages = relationship("PromptUsage", back_populates="template", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('worker_name', 'prompt_type', 'name', 'version', name='uix_worker_prompt_version'),
    )
    
    def render_user_prompt(self, **kwargs) -> str:
        """Render user prompt template with parameters"""
        try:
            return self.user_prompt_template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required parameter: {e}")
    
    def validate_parameters(self, provided_params: Dict) -> Tuple[bool, List[str]]:
        """Validate provided parameters against template requirements"""
        if not self.parameters:
            return True, []
        
        required = self.parameters.get('required', [])
        optional = self.parameters.get('optional', [])
        
        missing = [param for param in required if param not in provided_params]
        
        return len(missing) == 0, missing
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            'template_id': self.template_id,
            'worker_name': self.worker_name,
            'prompt_type': self.prompt_type,
            'name': self.name,
            'description': self.description,
            'system_prompt': self.system_prompt,
            'user_prompt_template': self.user_prompt_template,
            'parameters': self.parameters,
            'metadata': self.metadata,
            'version': self.version,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
        }


class PromptUsage(Base):
    """Track prompt usage for analytics and cost tracking"""
    __tablename__ = 'prompt_usage'
    
    usage_id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey('prompt_templates.template_id'), nullable=False, index=True)
    worker_name = Column(String(50), nullable=False, index=True)
    execution_id = Column(String(100))
    context = Column(JSON, default=dict)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)  # in USD
    latency_ms = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    template = relationship("PromptTemplate", back_populates="usages")
    
    def to_dict(self) -> Dict:
        return {
            'usage_id': self.usage_id,
            'template_id': self.template_id,
            'worker_name': self.worker_name,
            'execution_id': self.execution_id,
            'context': self.context,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'cost': self.cost,
            'latency_ms': self.latency_ms,
            'success': self.success,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class PromptVersion(Base):
    """Version history for prompt templates"""
    __tablename__ = 'prompt_versions'
    
    version_id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey('prompt_templates.template_id'), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text, nullable=False)
    parameters = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100))
    change_notes = Column(Text)
    
    # Relationships
    template = relationship("PromptTemplate", back_populates="versions")
    
    def to_dict(self) -> Dict:
        return {
            'version_id': self.version_id,
            'template_id': self.template_id,
            'version': self.version,
            'system_prompt': self.system_prompt,
            'user_prompt_template': self.user_prompt_template,
            'parameters': self.parameters,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'change_notes': self.change_notes,
        }


class PromptTest(Base):
    """Test cases for prompt templates"""
    __tablename__ = 'prompt_tests'
    
    test_id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey('prompt_templates.template_id'), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    test_input = Column(JSON, nullable=False)
    expected_output = Column(JSON)
    expected_error = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    template = relationship("PromptTemplate", back_populates="tests")
    
    def to_dict(self) -> Dict:
        return {
            'test_id': self.test_id,
            'template_id': self.template_id,
            'name': self.name,
            'test_input': self.test_input,
            'expected_output': self.expected_output,
            'expected_error': self.expected_error,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PromptValidation(Base):
    """Validation results for prompt tests"""
    __tablename__ = 'prompt_validations'
    
    validation_id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey('prompt_templates.template_id'), nullable=False, index=True)
    test_id = Column(Integer, ForeignKey('prompt_tests.test_id'))
    execution_id = Column(String(100))
    status = Column(String(20), nullable=False)  # passed, failed, skipped
    actual_output = Column(JSON)
    error_message = Column(Text)
    validation_time_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            'validation_id': self.validation_id,
            'template_id': self.template_id,
            'test_id': self.test_id,
            'execution_id': self.execution_id,
            'status': self.status,
            'actual_output': self.actual_output,
            'error_message': self.error_message,
            'validation_time_ms': self.validation_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class PromptAnalytics(Base):
    """Daily analytics for prompt templates"""
    __tablename__ = 'prompt_analytics'
    
    analytics_id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey('prompt_templates.template_id'), nullable=False, index=True)
    date = Column(Date, nullable=False)
    usage_count = Column(Integer, default=0)
    avg_latency_ms = Column(Integer)
    success_rate = Column(Float)
    avg_cost = Column(Float)
    total_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('template_id', 'date', name='uix_template_date'),
    )
    
    def to_dict(self) -> Dict:
        return {
            'analytics_id': self.analytics_id,
            'template_id': self.template_id,
            'date': self.date.isoformat(),
            'usage_count': self.usage_count,
            'avg_latency_ms': self.avg_latency_ms,
            'success_rate': self.success_rate,
            'avg_cost': self.avg_cost,
            'total_cost': self.total_cost,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
```

#### 3.3 Prompt Management Service

```python
# src/openmemory/app/services/prompt_service.py

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..models import (
    PromptTemplate,
    PromptUsage,
    PromptVersion,
    PromptTest,
    PromptValidation,
    PromptAnalytics
)
from ..database import get_db

logger = logging.getLogger(__name__)


class PromptService:
    """Service for managing prompt templates and usage"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or next(get_db())
    
    # ==================== TEMPLATE MANAGEMENT ====================
    
    def create_template(
        self,
        worker_name: str,
        prompt_type: str,
        name: str,
        system_prompt: str,
        user_prompt_template: str,
        description: Optional[str] = None,
        parameters: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        created_by: Optional[str] = None,
        is_default: bool = False
    ) -> PromptTemplate:
        """Create a new prompt template"""
        
        # Check if template already exists (same name/type/version 1)
        existing = self.db.query(PromptTemplate).filter(
            PromptTemplate.worker_name == worker_name,
            PromptTemplate.prompt_type == prompt_type,
            PromptTemplate.name == name,
            PromptTemplate.version == 1
        ).first()
        
        if existing:
            raise ValueError(
                f"Template '{name}' already exists for worker '{worker_name}'"
            )
        
        template = PromptTemplate(
            worker_name=worker_name,
            prompt_type=prompt_type,
            name=name,
            description=description,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            parameters=parameters or {},
            metadata=metadata or {},
            version=1,
            is_active=True,
            is_default=is_default,
            created_by=created_by
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        logger.info(f"Created prompt template: {template.template_id} - {name}")
        return template
    
    def update_template(
        self,
        template_id: int,
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        updated_by: Optional[str] = None,
        change_notes: Optional[str] = None,
        create_new_version: bool = True
    ) -> PromptTemplate:
        """Update a prompt template (creates new version if specified)"""
        
        template = self.db.query(PromptTemplate).get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        if create_new_version:
            # Create new version
            new_version = template.version + 1
            
            new_template = PromptTemplate(
                worker_name=template.worker_name,
                prompt_type=template.prompt_type,
                name=template.name,
                description=description or template.description,
                system_prompt=system_prompt or template.system_prompt,
                user_prompt_template=user_prompt_template or template.user_prompt_template,
                parameters=parameters or template.parameters,
                metadata=metadata or template.metadata,
                version=new_version,
                is_active=True,
                is_default=False,
                created_by=updated_by
            )
            
            self.db.add(new_template)
            
            # Archive old default if making new default
            if new_template.is_default:
                old_default = self.db.query(PromptTemplate).filter(
                    PromptTemplate.worker_name == template.worker_name,
                    PromptTemplate.prompt_type == template.prompt_type,
                    PromptTemplate.name == template.name,
                    PromptTemplate.is_default == True
                ).first()
                
                if old_default:
                    old_default.is_default = False
            
            # Save version history
            version = PromptVersion(
                template_id=new_template.template_id,
                version=new_template.version,
                system_prompt=new_template.system_prompt,
                user_prompt_template=new_template.user_prompt_template,
                parameters=new_template.parameters,
                created_by=updated_by,
                change_notes=change_notes
            )
            
            self.db.add(version)
            
            self.db.commit()
            self.db.refresh(new_template)
            
            logger.info(f"Created new version {new_version} of template {template_id}")
            return new_template
        
        else:
            # Update existing template
            if system_prompt is not None:
                template.system_prompt = system_prompt
            if user_prompt_template is not None:
                template.user_prompt_template = user_prompt_template
            if description is not None:
                template.description = description
            if parameters is not None:
                template.parameters = parameters
            if metadata is not None:
                template.metadata = metadata
            if updated_by is not None:
                template.updated_by = updated_by
            
            template.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(template)
            
            logger.info(f"Updated template {template_id}")
            return template
    
    def get_template(
        self,
        template_id: int
    ) -> Optional[PromptTemplate]:
        """Get a prompt template by ID"""
        return self.db.query(PromptTemplate).get(template_id)
    
    def get_templates(
        self,
        worker_name: Optional[str] = None,
        prompt_type: Optional[str] = None,
        name: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_default: Optional[bool] = None
    ) -> List[PromptTemplate]:
        """Get prompt templates with optional filters"""
        query = self.db.query(PromptTemplate)
        
        if worker_name:
            query = query.filter(PromptTemplate.worker_name == worker_name)
        if prompt_type:
            query = query.filter(PromptTemplate.prompt_type == prompt_type)
        if name:
            query = query.filter(PromptTemplate.name == name)
        if is_active is not None:
            query = query.filter(PromptTemplate.is_active == is_active)
        if is_default is not None:
            query = query.filter(PromptTemplate.is_default == is_default)
        
        return query.order_by(PromptTemplate.name, PromptTemplate.version.desc()).all()
    
    def get_default_template(
        self,
        worker_name: str,
        prompt_type: str
    ) -> Optional[PromptTemplate]:
        """Get the default template for a worker and type"""
        return self.db.query(PromptTemplate).filter(
            PromptTemplate.worker_name == worker_name,
            PromptTemplate.prompt_type == prompt_type,
            PromptTemplate.is_default == True,
            PromptTemplate.is_active == True
        ).first()
    
    def set_default_template(self, template_id: int) -> PromptTemplate:
        """Set a template as default (unsets others of same name/type)"""
        template = self.db.query(PromptTemplate).get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Unset other defaults
        old_defaults = self.db.query(PromptTemplate).filter(
            PromptTemplate.worker_name == template.worker_name,
            PromptTemplate.prompt_type == template.prompt_type,
            PromptTemplate.name == template.name,
            PromptTemplate.is_default == True
        ).all()
        
        for old in old_defaults:
            old.is_default = False
        
        # Set new default
        template.is_default = True
        self.db.commit()
        self.db.refresh(template)
        
        logger.info(f"Set template {template_id} as default")
        return template
    
    def archive_template(self, template_id: int) -> bool:
        """Archive a prompt template (soft delete)"""
        template = self.db.query(PromptTemplate).get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        template.is_active = False
        template.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Archived template {template_id}")
        return True
    
    def delete_template(self, template_id: int) -> bool:
        """Permanently delete a prompt template"""
        template = self.db.query(PromptTemplate).get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Delete associated data
        self.db.query(PromptVersion).filter(
            PromptVersion.template_id == template_id
        ).delete()
        
        self.db.query(PromptTest).filter(
            PromptTest.template_id == template_id
        ).delete()
        
        self.db.query(PromptUsage).filter(
            PromptUsage.template_id == template_id
        ).delete()
        
        self.db.query(PromptAnalytics).filter(
            PromptAnalytics.template_id == template_id
        ).delete()
        
        # Delete template
        self.db.delete(template)
        self.db.commit()
        
        logger.info(f"Deleted template {template_id}")
        return True
    
    # ==================== TEMPLATE RENDERING ====================
    
    def render_template(
        self,
        template: PromptTemplate,
        **kwargs
    ) -> Tuple[str, str, Dict]:
        """
        Render a prompt template with parameters
        
        Returns:
            Tuple of (system_prompt, user_prompt, rendered_params)
        """
        # Validate parameters
        is_valid, missing = template.validate_parameters(kwargs)
        
        if not is_valid:
            raise ValueError(f"Missing required parameters: {missing}")
        
        # Render user prompt
        try:
            user_prompt = template.render_user_prompt(**kwargs)
        except Exception as e:
            raise ValueError(f"Failed to render user prompt: {e}")
        
        # Collect rendered parameters for logging
        rendered_params = {
            **kwargs,
            'rendered_at': datetime.utcnow().isoformat()
        }
        
        return template.system_prompt, user_prompt, rendered_params
    
    def render_template_by_id(
        self,
        template_id: int,
        **kwargs
    ) -> Tuple[str, str, Dict]:
        """Render a template by ID"""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        return self.render_template(template, **kwargs)
    
    def render_default_template(
        self,
        worker_name: str,
        prompt_type: str,
        **kwargs
    ) -> Tuple[str, str, Dict, PromptTemplate]:
        """Render the default template for a worker and type"""
        template = self.get_default_template(worker_name, prompt_type)
        if not template:
            raise ValueError(
                f"No default template found for worker '{worker_name}', type '{prompt_type}'"
            )
        
        system, user, params = self.render_template(template, **kwargs)
        return system, user, params, template
    
    # ==================== USAGE TRACKING ====================
    
    def track_usage(
        self,
        template_id: int,
        worker_name: str,
        context: Dict,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        latency_ms: int = 0,
        success: bool = True,
        error_message: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> PromptUsage:
        """Track prompt usage for analytics"""
        
        usage = PromptUsage(
            template_id=template_id,
            worker_name=worker_name,
            context=context,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            execution_id=execution_id
        )
        
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        
        # Update analytics
        self._update_daily_analytics(template_id)
        
        return usage
    
    def get_usage_stats(
        self,
        template_id: Optional[int] = None,
        worker_name: Optional[str] = None,
        days: int = 7
    ) -> Dict:
        """Get usage statistics for templates"""
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(
            PromptUsage.template_id,
            PromptUsage.worker_name,
            func.count(PromptUsage.usage_id).label('usage_count'),
            func.avg(PromptUsage.latency_ms).label('avg_latency'),
            func.avg(PromptUsage.success).label('success_rate'),
            func.avg(PromptUsage.cost).label('avg_cost'),
            func.sum(PromptUsage.cost).label('total_cost'),
            func.sum(PromptUsage.input_tokens).label('total_input_tokens'),
            func.sum(PromptUsage.output_tokens).label('total_output_tokens')
        ).filter(PromptUsage.created_at >= cutoff)
        
        if template_id:
            query = query.filter(PromptUsage.template_id == template_id)
        if worker_name:
            query = query.filter(PromptUsage.worker_name == worker_name)
        
        query = query.group_by(PromptUsage.template_id, PromptUsage.worker_name)
        
        results = query.all()
        
        stats = []
        for row in results:
            stats.append({
                'template_id': row.template_id,
                'worker_name': row.worker_name,
                'usage_count': row.usage_count,
                'avg_latency': float(row.avg_latency) if row.avg_latency else 0,
                'success_rate': float(row.success_rate) if row.success_rate else 0,
                'avg_cost': float(row.avg_cost) if row.avg_cost else 0,
                'total_cost': float(row.total_cost) if row.total_cost else 0,
                'total_input_tokens': row.total_input_tokens or 0,
                'total_output_tokens': row.total_output_tokens or 0
            })
        
        return {
            'period_days': days,
            'stats': stats,
            'summary': {
                'total_usage': sum(s['usage_count'] for s in stats),
                'total_cost': sum(s['total_cost'] for s in stats),
                'avg_success_rate': sum(s['success_rate'] for s in stats) / len(stats) if stats else 0
            }
        }
    
    def _update_daily_analytics(self, template_id: int):
        """Update daily analytics for a template"""
        today = datetime.utcnow().date()
        
        # Get stats for today
        query = self.db.query(
            func.count(PromptUsage.usage_id).label('usage_count'),
            func.avg(PromptUsage.latency_ms).label('avg_latency'),
            func.avg(PromptUsage.success).label('success_rate'),
            func.avg(PromptUsage.cost).label('avg_cost'),
            func.sum(PromptUsage.cost).label('total_cost')
        ).filter(
            PromptUsage.template_id == template_id,
            func.date(PromptUsage.created_at) == today
        )
        
        result = query.first()
        
        if result:
            # Check if analytics for today already exists
            existing = self.db.query(PromptAnalytics).filter(
                PromptAnalytics.template_id == template_id,
                PromptAnalytics.date == today
            ).first()
            
            if existing:
                # Update existing
                existing.usage_count = result.usage_count or 0
                existing.avg_latency_ms = int(result.avg_latency) if result.avg_latency else None
                existing.success_rate = float(result.success_rate) if result.success_rate else None
                existing.avg_cost = float(result.avg_cost) if result.avg_cost else None
                existing.total_cost = float(result.total_cost) if result.total_cost else 0
                existing.created_at = datetime.utcnow()
            else:
                # Create new
                analytics = PromptAnalytics(
                    template_id=template_id,
                    date=today,
                    usage_count=result.usage_count or 0,
                    avg_latency_ms=int(result.avg_latency) if result.avg_latency else None,
                    success_rate=float(result.success_rate) if result.success_rate else None,
                    avg_cost=float(result.avg_cost) if result.avg_cost else None,
                    total_cost=float(result.total_cost) if result.total_cost else 0
                )
                self.db.add(analytics)
            
            self.db.commit()
    
    # ==================== TESTING & VALIDATION ====================
    
    def create_test(
        self,
        template_id: int,
        name: str,
        test_input: Dict,
        expected_output: Optional[Dict] = None,
        expected_error: Optional[str] = None
    ) -> PromptTest:
        """Create a test case for a template"""
        
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        test = PromptTest(
            template_id=template_id,
            name=name,
            test_input=test_input,
            expected_output=expected_output,
            expected_error=expected_error
        )
        
        self.db.add(test)
        self.db.commit()
        self.db.refresh(test)
        
        logger.info(f"Created test {test.test_id} for template {template_id}")
        return test
    
    def get_tests(self, template_id: int) -> List[PromptTest]:
        """Get all tests for a template"""
        return self.db.query(PromptTest).filter(
            PromptTest.template_id == template_id,
            PromptTest.is_active == True
        ).all()
    
    def run_test(
        self,
        test_id: int,
        template_id: Optional[int] = None
    ) -> PromptValidation:
        """Run a test case and validate the result"""
        
        test = self.db.query(PromptTest).get(test_id)
        if not test:
            raise ValueError(f"Test {test_id} not found")
        
        template = test.template if template_id is None else self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found")
        
        # Render template with test input
        try:
            start_time = datetime.utcnow()
            
            # This would call the actual LLM in production
            # For testing, we simulate the result
            actual_output = {
                'status': 'simulated',
                'message': 'This is a simulated test result',
                'input': test.test_input
            }
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Validate result
            status = 'passed'
            error_message = None
            
            if test.expected_output:
                # Simple validation - would need more sophisticated logic
                if actual_output.get('status') != test.expected_output.get('status'):
                    status = 'failed'
                    error_message = f"Status mismatch: {actual_output.get('status')} != {test.expected_output.get('status')}"
            
            if test.expected_error and status == 'passed':
                # Should have errored but didn't
                status = 'failed'
                error_message = f"Expected error: {test.expected_error}"
            
            # Create validation record
            validation = PromptValidation(
                template_id=template.template_id,
                test_id=test_id,
                execution_id=f"test_{test_id}_{int(datetime.utcnow().timestamp())}",
                status=status,
                actual_output=actual_output,
                error_message=error_message,
                validation_time_ms=latency_ms
            )
            
            self.db.add(validation)
            self.db.commit()
            self.db.refresh(validation)
            
            logger.info(f"Test {test_id} executed: {status}")
            return validation
            
        except Exception as e:
            # Create failed validation
            validation = PromptValidation(
                template_id=template.template_id,
                test_id=test_id,
                execution_id=f"test_{test_id}_{int(datetime.utcnow().timestamp())}",
                status='failed',
                error_message=str(e),
                validation_time_ms=0
            )
            
            self.db.add(validation)
            self.db.commit()
            self.db.refresh(validation)
            
            logger.error(f"Test {test_id} failed: {e}")
            return validation
    
    def run_all_tests(self, template_id: int) -> List[PromptValidation]:
        """Run all active tests for a template"""
        tests = self.get_tests(template_id)
        results = []
        
        for test in tests:
            try:
                result = self.run_test(test.test_id, template_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to run test {test.test_id}: {e}")
        
        return results
    
    def get_test_results(self, template_id: int) -> Dict:
        """Get test results for a template"""
        results = self.db.query(PromptValidation).filter(
            PromptValidation.template_id == template_id
        ).order_by(PromptValidation.created_at.desc()).limit(50).all()
        
        passed = sum(1 for r in results if r.status == 'passed')
        failed = sum(1 for r in results if r.status == 'failed')
        skipped = sum(1 for r in results if r.status == 'skipped')
        
        return {
            'total': len(results),
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'pass_rate': passed / len(results) if results else 0,
            'results': [r.to_dict() for r in results]
        }
    
    # ==================== VERSION MANAGEMENT ====================
    
    def get_versions(self, template_id: int) -> List[PromptVersion]:
        """Get all versions of a template"""
        return self.db.query(PromptVersion).filter(
            PromptVersion.template_id == template_id
        ).order_by(PromptVersion.version.desc()).all()
    
    def get_version(self, template_id: int, version: int) -> Optional[PromptVersion]:
        """Get a specific version of a template"""
        return self.db.query(PromptVersion).filter(
            PromptVersion.template_id == template_id,
            PromptVersion.version == version
        ).first()
    
    def rollback_to_version(
        self,
        template_id: int,
        version: int
    ) -> PromptTemplate:
        """Rollback to a previous version"""
        target_version = self.get_version(template_id, version)
        if not target_version:
            raise ValueError(f"Version {version} not found for template {template_id}")
        
        # Create new template from version
        template = self.db.query(PromptTemplate).get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Create new version with rolled back content
        new_template = PromptTemplate(
            worker_name=template.worker_name,
            prompt_type=template.prompt_type,
            name=template.name,
            description=template.description,
            system_prompt=target_version.system_prompt,
            user_prompt_template=target_version.user_prompt_template,
            parameters=target_version.parameters,
            metadata=template.metadata,
            version=template.version + 1,
            is_active=True,
            is_default=False,
            created_by=f"rollback_to_v{version}"
        )
        
        self.db.add(new_template)
        
        # Save version history
        version_record = PromptVersion(
            template_id=new_template.template_id,
            version=new_template.version,
            system_prompt=new_template.system_prompt,
            user_prompt_template=new_template.user_prompt_template,
            parameters=new_template.parameters,
            created_by=f"rollback_to_v{version}",
            change_notes=f"Rolled back from version {template.version} to version {version}"
        )
        
        self.db.add(version_record)
        self.db.commit()
        self.db.refresh(new_template)
        
        logger.info(f"Rolled back template {template_id} to version {version}")
        return new_template
    
    # ==================== SEARCH & FILTERING ====================
    
    def search_templates(
        self,
        query: str,
        worker_name: Optional[str] = None,
        prompt_type: Optional[str] = None,
        limit: int = 20
    ) -> List[PromptTemplate]:
        """Search templates by keyword"""
        search_pattern = f"%{query}%"
        
        q = self.db.query(PromptTemplate).filter(
            or_(
                PromptTemplate.name.ilike(search_pattern),
                PromptTemplate.description.ilike(search_pattern),
                PromptTemplate.system_prompt.ilike(search_pattern),
                PromptTemplate.user_prompt_template.ilike(search_pattern)
            )
        )
        
        if worker_name:
            q = q.filter(PromptTemplate.worker_name == worker_name)
        if prompt_type:
            q = q.filter(PromptTemplate.prompt_type == prompt_type)
        
        return q.order_by(PromptTemplate.name).limit(limit).all()
    
    def get_workers(self) -> List[str]:
        """Get all workers that have templates"""
        results = self.db.query(PromptTemplate.worker_name).distinct().all()
        return [r.worker_name for r in results]
    
    def get_prompt_types(self, worker_name: Optional[str] = None) -> List[str]:
        """Get all prompt types"""
        query = self.db.query(PromptTemplate.prompt_type).distinct()
        
        if worker_name:
            query = query.filter(PromptTemplate.worker_name == worker_name)
        
        results = query.all()
        return [r.prompt_type for r in results]
    
    def get_template_stats(self) -> Dict:
        """Get overall statistics for all templates"""
        total_templates = self.db.query(PromptTemplate).count()
        active_templates = self.db.query(PromptTemplate).filter(
            PromptTemplate.is_active == True
        ).count()
        
        workers = self.get_workers()
        prompt_types = self.get_prompt_types()
        
        # Get usage stats
        usage_stats = self.get_usage_stats(days=7)
        
        return {
            'total_templates': total_templates,
            'active_templates': active_templates,
            'workers': workers,
            'prompt_types': prompt_types,
            'recent_usage': usage_stats['summary']
        }

#### 3.4 Prompt Service Initialization

```python
# src/openmemory/app/services/__init__.py

from .prompt_service import PromptService

__all__ = ['PromptService']
```

#### 3.5 Prompt Service Integration

```python
# src/openmemory/app/utils/prompts.py

from typing import Dict, List, Optional, Tuple
import logging

from ..services.prompt_service import PromptService
from ..models import PromptTemplate

logger = logging.getLogger(__name__)


class PromptManager:
    """Manager for prompt templates with database persistence"""
    
    def __init__(self):
        self.service = PromptService()
    
    def render_template(
        self,
        worker_name: str,
        prompt_type: str,
        **kwargs
    ) -> Tuple[str, str, PromptTemplate]:
        """
        Render a prompt template
        
        Args:
            worker_name: Name of the worker
            prompt_type: Type of prompt
            **kwargs: Template parameters
        
        Returns:
            Tuple of (system_prompt, user_prompt, template)
        """
        try:
            system, user, params, template = self.service.render_default_template(
                worker_name, prompt_type, **kwargs
            )
            
            # Track usage (async to not block)
            import asyncio
            asyncio.create_task(
                self._track_usage_async(template, worker_name, params)
            )
            
            return system, user, template
            
        except ValueError as e:
            # Template not found, fall back to hardcoded
            logger.warning(f"Template not found, using hardcoded: {e}")
            return self._get_hardcoded_template(worker_name, prompt_type, **kwargs)
    
    async def _track_usage_async(
        self,
        template: PromptTemplate,
        worker_name: str,
        context: Dict
    ):
        """Async usage tracking"""
        try:
            # In production, would get actual token counts and costs
            # For now, use placeholders
            input_tokens = len(context.get('input', '')) // 4  # Rough estimate
            output_tokens = 0  # Would be from LLM response
            
            self.service.track_usage(
                template_id=template.template_id,
                worker_name=worker_name,
                context=context,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=0.0,  # Would calculate based on model
                latency_ms=0,  # Would measure actual latency
                success=True
            )
        except Exception as e:
            logger.error(f"Failed to track usage: {e}")
    
    def _get_hardcoded_template(
        self,
        worker_name: str,
        prompt_type: str,
        **kwargs
    ) -> Tuple[str, str, PromptTemplate]:
        """Get hardcoded template (fallback when DB template not found)"""
        
        templates = {
            ('think', 'committee_scoring'): (
                """You are an expert committee member. Score the proposal 0-1 considering:
- Technical feasibility
- Risk level
- Business value
- Implementation complexity
- Test coverage

Return JSON: {"score": 0.85, "confidence": 0.90, "risks": ["...", "..."]}""",
                """Proposal: {proposal}
Description: {description}
Changes: {changes}

Score this proposal considering the factors above."""
            ),
            ('think', 'risk_assessment'): (
                """You are a risk assessment expert. Analyze risks in the following proposal.

Respond with JSON:
{
  "risk_level": "low|medium|high",
  "risks": ["risk1", "risk2"],
  "confidence": 0.0-1.0,
  "mitigation_suggestions": ["...", "..."]
}""",
                """Proposal: {proposal}
Description: {description}
Change type: {change_type}

Assess the risks."""
            ),
            ('learning', 'pattern_extraction'): (
                """You are a pattern extraction expert. Extract patterns from successful proposals.

Respond with JSON:
{
  "pattern_name": "descriptive name",
  "pattern_type": "type",
  "description": "pattern description",
  "confidence": 0.0-1.0,
  "code_template": "template code",
  "applicability": "when to use this pattern"
}""",
                """Proposal: {proposal}
Description: {description}
Changes: {changes}
Success rate: {success_rate}

Extract the pattern."""
            ),
            ('dream', 'error_fix'): (
                """You are an expert software engineer specialized in fixing code issues.

Respond with JSON:
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
  "testing_strategy": "How to verify",
  "historical_lessons": "What was learned"
}""",
                """Issues to fix:
{issues}

File contents:
{file_contents}

Generate specific code fixes."""
            ),
            ('analysis', 'issue_assessment'): (
                """You are a code analysis expert. Assess issue severity.

Respond with JSON:
{
  "severity": "info|warning|error",
  "confidence": 0.0-1.0,
  "suggested_fix": "fix description",
  "priority": 1-5
}""",
                """Issue: {issue}
File: {file}
Line: {line}
Context: {context}

Assess the severity."""
            ),
            ('recall', 'context_retrieval'): (
                """You are a context retrieval expert. Find relevant context for the query.

Respond with JSON:
{
  "relevant_context": ["context1", "context2"],
  "sources": ["source1", "source2"],
  "relevance_score": 0.0-1.0
}""",
                """Query: {query}
Available context: {context}

Find relevant context."""
            ),
            ('dreamer', 'experiment_generation'): (
                """You are the Dreamer for the {worker_name} worker in SIGMA.
Your role is to propose novel experimental approaches.

Respond in JSON format:
{{
  "experiment_name": "descriptive name",
  "hypothesis": "what you think will happen",
  "approach": "detailed implementation steps",
  "metrics": ["metric1", "metric2"],
  "risk_level": "low|medium|high",
  "rollback_plan": "how to undo if it fails",
  "confidence": 0.0-1.0
}}""",
                """Worker: {worker_name}
Context: {context}

Propose an experiment."""
            ),
        }
        
        key = (worker_name, prompt_type)
        if key in templates:
            system, user = templates[key]
            
            # Create a temporary template object
            template = PromptTemplate(
                worker_name=worker_name,
                prompt_type=prompt_type,
                name=f"hardcoded_{prompt_type}",
                system_prompt=system,
                user_prompt_template=user,
                parameters={},
                metadata={'hardcoded': True},
                version=1,
                is_active=True,
                is_default=False
            )
            
            # Render user prompt
            try:
                user_prompt = user.format(**kwargs)
            except KeyError as e:
                user_prompt = user  # Return as-is if formatting fails
            
            return system, user_prompt, template
        
        raise ValueError(
            f"No hardcoded template found for worker '{worker_name}', type '{prompt_type}'"
        )


# Global prompt manager instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get the global prompt manager instance"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
```

#### 3.6 Worker Integration with Prompt Manager

**Enhanced Base Worker**

```python
class EnhancedBaseWorkerWithPrompts(BaseWorker):
    """Base worker with prompt management"""
    
    def __init__(self, db_session, dreamer):
        super().__init__(db_session, dreamer)
        self.prompt_manager = get_prompt_manager()
        self.local_prompt_cache = {}  # Cache for frequently used prompts
    
    def get_prompt(
        self,
        prompt_type: str,
        **kwargs
    ) -> Tuple[str, str]:
        """Get a prompt with caching"""
        cache_key = f"{self.worker_name}:{prompt_type}:{str(kwargs)}"
        
        if cache_key in self.local_prompt_cache:
            logger.debug(f"Using cached prompt for {prompt_type}")
            return self.local_prompt_cache[cache_key]
        
        try:
            system, user, template = self.prompt_manager.render_template(
                self.worker_name, prompt_type, **kwargs
            )
            
            # Cache the result
            self.local_prompt_cache[cache_key] = (system, user)
            
            # Limit cache size
            if len(self.local_prompt_cache) > 100:
                self.local_prompt_cache.pop(next(iter(self.local_prompt_cache)))
            
            return system, user
            
        except Exception as e:
            logger.error(f"Failed to get prompt {prompt_type}: {e}")
            raise
    
    def clear_prompt_cache(self):
        """Clear local prompt cache"""
        self.local_prompt_cache.clear()
        logger.info(f"Cleared prompt cache for {self.worker_name}")

**Enhanced ThinkWorker with Prompts**

```python
class ThinkWorkerWithPrompts(ThinkWorker):
    """ThinkWorker with prompt management"""
    
    def __init__(self, db_session, dreamer):
        super().__init__(db_session, dreamer)
        self.prompt_manager = get_prompt_manager()
    
    def _score_proposal_with_committee(self, proposal: Proposal) -> Dict:
        """Score proposal using committee with managed prompts"""
        changes = json.loads(proposal.changes_json)
        
        # Get committee members
        committee_members = [
            'architect', 'reviewer', 'tester', 'security', 'optimizer'
        ]
        
        agent_scores = {}
        
        for member in committee_members:
            try:
                # Get prompt for this committee member
                system, user = self.prompt_manager.render_template(
                    worker_name='think',
                    prompt_type='committee_scoring',
                    member=member,
                    proposal=proposal.title,
                    description=proposal.description,
                    changes=changes
                )
                
                # Call LLM (simplified - would use actual LLM client)
                score, confidence, risks = self._call_llm_for_scoring(
                    system, user, member
                )
                
                agent_scores[member] = {
                    'score': score,
                    'confidence': confidence,
                    'risks': risks
                }
                
            except Exception as e:
                logger.error(f"Failed to score with {member}: {e}")
                # Default score on error
                agent_scores[member] = {
                    'score': 0.5,
                    'confidence': 0.5,
                    'risks': ['Failed to score']
                }
        
        # Calculate weighted score
        weights = self.config.committee.weights
        weighted_score = (
            agent_scores['architect']['score'] * weights.architect +
            agent_scores['reviewer']['score'] * weights.reviewer +
            agent_scores['tester']['score'] * weights.tester +
            agent_scores['security']['score'] * weights.security +
            agent_scores['optimizer']['score'] * weights.optimizer
        )
        
        return {
            'agent_scores': agent_scores,
            'weighted_score': weighted_score,
            'committee_config': weights.__dict__
        }

**Enhanced DreamWorker with Prompts**

```python
class DreamWorkerWithPrompts(DreamWorker):
    """DreamWorker with prompt management"""
    
    def __init__(self, db_session, dreamer):
        super().__init__(db_session, dreamer)
        self.prompt_manager = get_prompt_manager()
    
    def _generate_error_fix_proposal(self, issues: List[Dict], snapshot: CodeSnapshot) -> Optional[Dict]:
        """Generate error fix proposal with managed prompts"""
        project = self.db.query(Project).filter(Project.project_id == snapshot.project_id).first()
        
        # Prepare context
        file_contents = self._read_affected_files(
            project.workspace_path, issues[:5]
        )
        
        # Get historical context
        historical_context = self._query_historical_fix_patterns(issues[:5])
        
        # Build prompt parameters
        prompt_params = {
            'issues': issues[:5],
            'file_contents': file_contents,
            'historical_context': historical_context
        }
        
        # Get prompt
        try:
            system, user = self.prompt_manager.render_template(
                worker_name='dream',
                prompt_type='error_fix',
                **prompt_params
            )
            
            # Call LLM
            llm = get_openai_client()
            model = os.getenv("MODEL", "gpt-4o-mini")
            
            response = llm.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=0.3,
                max_tokens=2500
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            # Track usage
            self._track_prompt_usage(
                template_id=None,  # Would get from template
                worker_name='dream',
                context=prompt_params,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens
            )
            
            # Build proposal
            agents = {
                'architect': 0.85,
                'reviewer': 0.80,
                'tester': 0.90,
                'security': 0.75,
                'optimizer': 0.70
            }
            
            return {
                'title': result.get('title', f"Fix {len(issues)} Critical Error(s)"),
                'description': result.get('description', ''),
                'agents': agents,
                'changes': {
                    'files_affected': list(set(i['file'] for i in issues[:5])),
                    'change_type': 'bug_fix',
                    'code_changes': result.get('changes', []),
                    'testing_strategy': result.get('testing_strategy', ''),
                    'historical_lessons': result.get('historical_lessons', '')
                },
                'confidence': float(result.get('confidence', 0.85)),
                'critic_score': 0.80
            }
            
        except Exception as e:
            logger.error(f"Failed to generate proposal: {e}")
            # Fall back to hardcoded
            return super()._generate_error_fix_proposal(issues, snapshot)
    
    def _track_prompt_usage(
        self,
        template_id: Optional[int],
        worker_name: str,
        context: Dict,
        input_tokens: int,
        output_tokens: int
    ):
        """Track prompt usage for analytics"""
        try:
            self.prompt_manager.service.track_usage(
                template_id=template_id,
                worker_name=worker_name,
                context=context,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=self._calculate_cost(input_tokens, output_tokens),
                success=True
            )
        except Exception as e:
            logger.error(f"Failed to track prompt usage: {e}")
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost (simplified)"""
        # GPT-4o-mini pricing: $0.15 per 1M input tokens, $0.60 per 1M output tokens
        input_cost = (input_tokens / 1_000_000) * 0.15
        output_cost = (output_tokens / 1_000_000) * 0.60
        return input_cost + output_cost
```

#### 3.7 Backend API for Prompt Management

```python
# src/openmemory/app/routers/prompts.py

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
import logging

from ..services.prompt_service import PromptService
from ..models import PromptTemplate
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

def get_prompt_service() -> PromptService:
    """Dependency to get prompt service"""
    return PromptService()


# ==================== TEMPLATE MANAGEMENT ====================

@router.post("/templates", response_model=Dict[str, Any])
async def create_template(
    worker_name: str,
    prompt_type: str,
    name: str,
    system_prompt: str,
    user_prompt_template: str,
    description: Optional[str] = None,
    parameters: Optional[Dict] = None,
    metadata: Optional[Dict] = None,
    created_by: Optional[str] = None,
    is_default: bool = False,
    service: PromptService = Depends(get_prompt_service)
):
    """Create a new prompt template"""
    try:
        template = service.create_template(
            worker_name=worker_name,
            prompt_type=prompt_type,
            name=name,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            description=description,
            parameters=parameters,
            metadata=metadata,
            created_by=created_by,
            is_default=is_default
        )
        
        return {
            "status": "success",
            "template": template.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=Dict[str, Any])
async def get_templates(
    worker_name: Optional[str] = None,
    prompt_type: Optional[str] = None,
    name: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_default: Optional[bool] = None,
    service: PromptService = Depends(get_prompt_service)
):
    """Get prompt templates with optional filters"""
    try:
        templates = service.get_templates(
            worker_name=worker_name,
            prompt_type=prompt_type,
            name=name,
            is_active=is_active,
            is_default=is_default
        )
        
        return {
            "status": "success",
            "templates": [t.to_dict() for t in templates],
            "count": len(templates)
        }
        
    except Exception as e:
        logger.error(f"Failed to get templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}", response_model=Dict[str, Any])
async def get_template(
    template_id: int,
    service: PromptService = Depends(get_prompt_service)
):
    """Get a specific prompt template"""
    template = service.get_template(template_id)
    
    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Template {template_id} not found"
        )
    
    return {
        "status": "success",
        "template": template.to_dict()
    }


@router.put("/templates/{template_id}", response_model=Dict[str, Any])
async def update_template(
    template_id: int,
    system_prompt: Optional[str] = None,
    user_prompt_template: Optional[str] = None,
    description: Optional[str] = None,
    parameters: Optional[Dict] = None,
    metadata: Optional[Dict] = None,
    updated_by: Optional[str] = None,
    change_notes: Optional[str] = None,
    create_new_version: bool = True,
    service: PromptService = Depends(get_prompt_service)
):
    """Update a prompt template"""
    try:
        template = service.update_template(
            template_id=template_id,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            description=description,
            parameters=parameters,
            metadata=metadata,
            updated_by=updated_by,
            change_notes=change_notes,
            create_new_version=create_new_version
        )
        
        return {
            "status": "success",
            "template": template.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/templates/{template_id}/default", response_model=Dict[str, Any])
async def set_default_template(
    template_id: int,
    service: PromptService = Depends(get_prompt_service)
):
    """Set a template as default"""
    try:
        template = service.set_default_template(template_id)
        
        return {
            "status": "success",
            "template": template.to_dict(),
            "message": "Template set as default"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set default template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/templates/{template_id}", response_model=Dict[str, Any])
async def delete_template(
    template_id: int,
    permanent: bool = False,
    service: PromptService = Depends(get_prompt_service)
):
    """Delete a prompt template"""
    try:
        if permanent:
            success = service.delete_template(template_id)
            message = "Template permanently deleted"
        else:
            success = service.archive_template(template_id)
            message = "Template archived"
        
        return {
            "status": "success",
            "message": message
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TEMPLATE RENDERING ====================

@router.post("/templates/{template_id}/render", response_model=Dict[str, Any])
async def render_template(
    template_id: int,
    parameters: Dict[str, Any],
    service: PromptService = Depends(get_prompt_service)
):
    """Render a template with parameters"""
    try:
        template = service.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        system, user, rendered_params = service.render_template(template, **parameters)
        
        return {
            "status": "success",
            "system_prompt": system,
            "user_prompt": user,
            "rendered_params": rendered_params,
            "template": template.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to render template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/render/default", response_model=Dict[str, Any])
async def render_default_template(
    worker_name: str,
    prompt_type: str,
    parameters: Dict[str, Any],
    service: PromptService = Depends(get_prompt_service)
):
    """Render the default template for a worker and type"""
    try:
        system, user, rendered_params, template = service.render_default_template(
            worker_name, prompt_type, **parameters
        )
        
        return {
            "status": "success",
            "system_prompt": system,
            "user_prompt": user,
            "rendered_params": rendered_params,
            "template": template.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to render default template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== USAGE & ANALYTICS ====================

@router.get("/usage/stats", response_model=Dict[str, Any])
async def get_usage_stats(
    template_id: Optional[int] = None,
    worker_name: Optional[str] = None,
    days: int = 7,
    service: PromptService = Depends(get_prompt_service)
):
    """Get usage statistics for templates"""
    try:
        stats = service.get_usage_stats(
            template_id=template_id,
            worker_name=worker_name,
            days=days
        )
        
        return {
            "status": "success",
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=Dict[str, Any])
async def get_template_stats(
    service: PromptService = Depends(get_prompt_service)
):
    """Get overall statistics for all templates"""
    try:
        stats = service.get_template_stats()
        
        return {
            "status": "success",
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get template stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TESTING & VALIDATION ====================

@router.post("/templates/{template_id}/tests", response_model=Dict[str, Any])
async def create_test(
    template_id: int,
    name: str,
    test_input: Dict[str, Any],
    expected_output: Optional[Dict[str, Any]] = None,
    expected_error: Optional[str] = None,
    service: PromptService = Depends(get_prompt_service)
):
    """Create a test case for a template"""
    try:
        test = service.create_test(
            template_id=template_id,
            name=name,
            test_input=test_input,
            expected_output=expected_output,
            expected_error=expected_error
        )
        
        return {
            "status": "success",
            "test": test.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create test: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}/tests", response_model=Dict[str, Any])
async def get_tests(
    template_id: int,
    service: PromptService = Depends(get_prompt_service)
):
    """Get all tests for a template"""
    try:
        tests = service.get_tests(template_id)
        
        return {
            "status": "success",
            "tests": [t.to_dict() for t in tests],
            "count": len(tests)
        }
        
    except Exception as e:
        logger.error(f"Failed to get tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tests/{test_id}/run", response_model=Dict[str, Any])
async def run_test(
    test_id: int,
    template_id: Optional[int] = None,
    service: PromptService = Depends(get_prompt_service)
):
    """Run a test case"""
    try:
        validation = service.run_test(test_id, template_id)
        
        return {
            "status": "success",
            "validation": validation.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to run test: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/{template_id}/tests/run-all", response_model=Dict[str, Any])
async def run_all_tests(
    template_id: int,
    service: PromptService = Depends(get_prompt_service)
):
    """Run all active tests for a template"""
    try:
        results = service.run_all_tests(template_id)
        
        return {
            "status": "success",
            "results": [r.to_dict() for r in results],
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to run tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}/test-results", response_model=Dict[str, Any])
async def get_test_results(
    template_id: int,
    service: PromptService = Depends(get_prompt_service)
):
    """Get test results for a template"""
    try:
        results = service.get_test_results(template_id)
        
        return {
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Failed to get test results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== VERSION MANAGEMENT ====================

@router.get("/templates/{template_id}/versions", response_model=Dict[str, Any])
async def get_versions(
    template_id: int,
    service: PromptService = Depends(get_prompt_service)
):
    """Get all versions of a template"""
    try:
        versions = service.get_versions(template_id)
        
        return {
            "status": "success",
            "versions": [v.to_dict() for v in versions],
            "count": len(versions)
        }
        
    except Exception as e:
        logger.error(f"Failed to get versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}/versions/{version}", response_model=Dict[str, Any])
async def get_version(
    template_id: int,
    version: int,
    service: PromptService = Depends(get_prompt_service)
):
    """Get a specific version of a template"""
    try:
        version_obj = service.get_version(template_id, version)
        
        if not version_obj:
            raise ValueError(f"Version {version} not found")
        
        return {
            "status": "success",
            "version": version_obj.to_dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/{template_id}/rollback", response_model=Dict[str, Any])
async def rollback_to_version(
    template_id: int,
    version: int,
    service: PromptService = Depends(get_prompt_service)
):
    """Rollback a template to a previous version"""
    try:
        new_template = service.rollback_to_version(template_id, version)
        
        return {
            "status": "success",
            "template": new_template.to_dict(),
            "message": f"Rolled back to version {version}"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to rollback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SEARCH & FILTERING ====================

@router.get("/search", response_model=Dict[str, Any])
async def search_templates(
    query: str,
    worker_name: Optional[str] = None,
    prompt_type: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    service: PromptService = Depends(get_prompt_service)
):
    """Search templates by keyword"""
    try:
        templates = service.search_templates(
            query=query,
            worker_name=worker_name,
            prompt_type=prompt_type,
            limit=limit
        )
        
        return {
            "status": "success",
            "templates": [t.to_dict() for t in templates],
            "count": len(templates)
        }
        
    except Exception as e:
        logger.error(f"Failed to search templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workers", response_model=Dict[str, Any])
async def get_workers(
    service: PromptService = Depends(get_prompt_service)
):
    """Get all workers that have templates"""
    try:
        workers = service.get_workers()
        
        return {
            "status": "success",
            "workers": workers,
            "count": len(workers)
        }
        
    except Exception as e:
        logger.error(f"Failed to get workers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompt-types", response_model=Dict[str, Any])
async def get_prompt_types(
    worker_name: Optional[str] = None,
    service: PromptService = Depends(get_prompt_service)
):
    """Get all prompt types"""
    try:
        types = service.get_prompt_types(worker_name)
        
        return {
            "status": "success",
            "prompt_types": types,
            "count": len(types)
        }
        
    except Exception as e:
        logger.error(f"Failed to get prompt types: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

#### 3.8 Frontend UI Components for Prompt Management

```typescript
// Frontend React components for prompt management

// Template List Component
interface TemplateListProps {
  onSelectTemplate: (templateId: number) => void;
  onRefresh: () => void;
}

const TemplateList: React.FC<TemplateListProps> = ({ onSelectTemplate, onRefresh }) => {
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    workerName: '',
    promptType: '',
    name: '',
    isActive: true,
    isDefault: false
  });
  
  useEffect(() => {
    fetchTemplates();
  }, [filters]);
  
  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.workerName) params.append('worker_name', filters.workerName);
      if (filters.promptType) params.append('prompt_type', filters.promptType);
      if (filters.name) params.append('name', filters.name);
      if (filters.isActive !== null) params.append('is_active', filters.isActive.toString());
      if (filters.isDefault !== null) params.append('is_default', filters.isDefault.toString());
      
      const response = await fetch(`/api/prompts/templates?${params}`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setTemplates(data.templates);
      }
    } catch (error) {
      console.error("Failed to fetch templates:", error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleSearch = (field: string, value: string | boolean) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };
  
  const handleClearFilters = () => {
    setFilters({
      workerName: '',
      promptType: '',
      name: '',
      isActive: true,
      isDefault: false
    });
  };
  
  if (loading) {
    return <div className="loading">Loading templates...</div>;
  }
  
  return (
    <div className="template-list">
      <div className="list-header">
        <h3>Prompt Templates ({templates.length})</h3>
        <div className="header-actions">
          <button onClick={onRefresh} className="refresh-btn">Refresh</button>
          <button onClick={handleClearFilters} className="clear-btn">Clear Filters</button>
        </div>
      </div>
      
      <div className="filters">
        <div className="filter-group">
          <label>Worker:</label>
          <input
            type="text"
            value={filters.workerName}
            onChange={(e) => handleSearch('workerName', e.target.value)}
            placeholder="Filter by worker..."
          />
        </div>
        <div className="filter-group">
          <label>Prompt Type:</label>
          <input
            type="text"
            value={filters.promptType}
            onChange={(e) => handleSearch('promptType', e.target.value)}
            placeholder="Filter by type..."
          />
        </div>
        <div className="filter-group">
          <label>Name:</label>
          <input
            type="text"
            value={filters.name}
            onChange={(e) => handleSearch('name', e.target.value)}
            placeholder="Filter by name..."
          />
        </div>
      </div>
      
      <div className="templates-grid">
        {templates.map((template) => (
          <div 
            key={template.template_id} 
            className="template-card"
            onClick={() => onSelectTemplate(template.template_id)}
          >
            <div className="template-header">
              <h4>{template.name}</h4>
              <div className="template-meta">
                <span className="badge worker">{template.worker_name}</span>
                <span className="badge type">{template.prompt_type}</span>
                {template.is_default && <span className="badge default">Default</span>}
                {!template.is_active && <span className="badge inactive">Inactive</span>}
              </div>
            </div>
            <div className="template-info">
              <div className="info-row">
                <span className="label">Version:</span>
                <span className="value">{template.version}</span>
              </div>
              <div className="info-row">
                <span className="label">Updated:</span>
                <span className="value">
                  {template.updated_at ? new Date(template.updated_at).toLocaleDateString() : 'N/A'}
                </span>
              </div>
              {template.description && (
                <p className="description">{template.description}</p>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {templates.length === 0 && (
        <div className="empty-state">
          <p>No templates found. Try adjusting your filters.</p>
        </div>
      )}
    </div>
  );
};

// Template Editor Component
interface TemplateEditorProps {
  templateId?: number;
  onSave?: () => void;
  onCancel?: () => void;
}

const TemplateEditor: React.FC<TemplateEditorProps> = ({ templateId, onSave, onCancel }) => {
  const [template, setTemplate] = useState<any>(null);
  const [formData, setFormData] = useState({
    worker_name: '',
    prompt_type: '',
    name: '',
    description: '',
    system_prompt: '',
    user_prompt_template: '',
    parameters: {},
    metadata: {},
    is_default: false,
    change_notes: ''
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  useEffect(() => {
    if (templateId) {
      fetchTemplate();
    }
  }, [templateId]);
  
  const fetchTemplate = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/prompts/templates/${templateId}`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setTemplate(data.template);
        setFormData({
          worker_name: data.template.worker_name,
          prompt_type: data.template.prompt_type,
          name: data.template.name,
          description: data.template.description || '',
          system_prompt: data.template.system_prompt,
          user_prompt_template: data.template.user_prompt_template,
          parameters: data.template.parameters || {},
          metadata: data.template.metadata || {},
          is_default: data.template.is_default,
          change_notes: ''
        });
      }
    } catch (error) {
      console.error("Failed to fetch template:", error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };
  
  const handleJsonChange = (field: string, value: string) => {
    try {
      const parsed = JSON.parse(value);
      handleInputChange(field, parsed);
    } catch (e) {
      // Keep as string, don't update
    }
  };
  
  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.worker_name.trim()) {
      newErrors.worker_name = 'Worker name is required';
    }
    if (!formData.prompt_type.trim()) {
      newErrors.prompt_type = 'Prompt type is required';
    }
    if (!formData.name.trim()) {
      newErrors.name = 'Template name is required';
    }
    if (!formData.system_prompt.trim()) {
      newErrors.system_prompt = 'System prompt is required';
    }
    if (!formData.user_prompt_template.trim()) {
      newErrors.user_prompt_template = 'User prompt template is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  const handleSave = async () => {
    if (!validateForm()) {
      return;
    }
    
    setLoading(true);
    try {
      const url = templateId 
        ? `/api/prompts/templates/${templateId}`
        : '/api/prompts/templates';
      
      const method = templateId ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          create_new_version: true
        })
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        if (onSave) onSave();
      } else {
        throw new Error(data.message || 'Save failed');
      }
    } catch (error) {
      console.error("Failed to save template:", error);
      setErrors({ submit: String(error) });
    } finally {
      setLoading(false);
    }
  };
  
  const handleRenderTest = async () => {
    try {
      const response = await fetch(`/api/prompts/templates/${templateId}/render`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})  // Empty params for testing
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        alert(`System Prompt:\n${data.system_prompt}\n\nUser Prompt:\n${data.user_prompt}`);
      }
    } catch (error) {
      console.error("Failed to render template:", error);
    }
  };
  
  if (loading && !template) {
    return <div className="loading">Loading template...</div>;
  }
  
  return (
    <div className="template-editor">
      <div className="editor-header">
        <h3>{templateId ? 'Edit Template' : 'Create Template'}</h3>
        <div className="editor-actions">
          {templateId && (
            <button onClick={handleRenderTest} className="test-btn">
              Test Render
            </button>
          )}
          <button onClick={onCancel} className="cancel-btn">
            Cancel
          </button>
          <button onClick={handleSave} className="save-btn" disabled={loading}>
            {loading ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
      
      {errors.submit && (
        <div className="error-banner">{errors.submit}</div>
      )}
      
      <div className="form-grid">
        <div className="form-group">
          <label>Worker Name *</label>
          <input
            type="text"
            value={formData.worker_name}
            onChange={(e) => handleInputChange('worker_name', e.target.value)}
            disabled={!!templateId}
            className={errors.worker_name ? 'error' : ''}
            placeholder="e.g., think, learning, dream"
          />
          {errors.worker_name && <span className="error-text">{errors.worker_name}</span>}
        </div>
        
        <div className="form-group">
          <label>Prompt Type *</label>
          <input
            type="text"
            value={formData.prompt_type}
            onChange={(e) => handleInputChange('prompt_type', e.target.value)}
            disabled={!!templateId}
            className={errors.prompt_type ? 'error' : ''}
            placeholder="e.g., committee_scoring, risk_assessment"
          />
          {errors.prompt_type && <span className="error-text">{errors.prompt_type}</span>}
        </div>
        
        <div className="form-group full-width">
          <label>Template Name *</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleInputChange('name', e.target.value)}
            className={errors.name ? 'error' : ''}
            placeholder="e.g., Multi-Agent Committee Scoring"
          />
          {errors.name && <span className="error-text">{errors.name}</span>}
        </div>
        
        <div className="form-group full-width">
          <label>Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => handleInputChange('description', e.target.value)}
            placeholder="Brief description of this prompt template..."
            rows={2}
          />
        </div>
        
        <div className="form-group full-width">
          <label>System Prompt *</label>
          <textarea
            value={formData.system_prompt}
            onChange={(e) => handleInputChange('system_prompt', e.target.value)}
            className={errors.system_prompt ? 'error' : ''}
            placeholder="System instruction for the AI..."
            rows={6}
          />
          {errors.system_prompt && <span className="error-text">{errors.system_prompt}</span>}
        </div>
        
        <div className="form-group full-width">
          <label>User Prompt Template *</label>
          <textarea
            value={formData.user_prompt_template}
            onChange={(e) => handleInputChange('user_prompt_template', e.target.value)}
            className={errors.user_prompt_template ? 'error' : ''}
            placeholder="User prompt template with {parameters}..."
            rows={6}
          />
          {errors.user_prompt_template && <span className="error-text">{errors.user_prompt_template}</span>}
        </div>
        
        <div className="form-group full-width">
          <label>Parameters (JSON)</label>
          <textarea
            value={JSON.stringify(formData.parameters, null, 2)}
            onChange={(e) => handleJsonChange('parameters', e.target.value)}
            placeholder='{"required": ["param1", "param2"], "optional": ["param3"]}'
            rows={4}
          />
        </div>
        
        <div className="form-group full-width">
          <label>Metadata (JSON)</label>
          <textarea
            value={JSON.stringify(formData.metadata, null, 2)}
            onChange={(e) => handleJsonChange('metadata', e.target.value)}
            placeholder='{"tags": ["tag1", "tag2"], "category": "scoring"}'
            rows={3}
          />
        </div>
        
        <div className="form-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={formData.is_default}
              onChange={(e) => handleInputChange('is_default', e.target.checked)}
            />
            Set as Default
          </label>
        </div>
        
        {templateId && (
          <div className="form-group full-width">
            <label>Change Notes</label>
            <textarea
              value={formData.change_notes}
              onChange={(e) => handleInputChange('change_notes', e.target.value)}
              placeholder="Describe what changed in this version..."
              rows={2}
            />
          </div>
        )}
      </div>
    </div>
  );
};

// Template Viewer Component
interface TemplateViewerProps {
  templateId: number;
  onClose: () => void;
}

const TemplateViewer: React.FC<TemplateViewerProps> = ({ templateId, onClose }) => {
  const [template, setTemplate] = useState<any>(null);
  const [versions, setVersions] = useState<any[]>([]);
  const [tests, setTests] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'details' | 'versions' | 'tests' | 'analytics'>('details');
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchTemplate();
    fetchVersions();
    fetchTests();
    fetchStats();
  }, [templateId]);
  
  const fetchTemplate = async () => {
    try {
      const response = await fetch(`/api/prompts/templates/${templateId}`);
      const data = await response.json();
      if (data.status === 'success') {
        setTemplate(data.template);
      }
    } catch (error) {
      console.error("Failed to fetch template:", error);
    }
  };
  
  const fetchVersions = async () => {
    try {
      const response = await fetch(`/api/prompts/templates/${templateId}/versions`);
      const data = await response.json();
      if (data.status === 'success') {
        setVersions(data.versions);
      }
    } catch (error) {
      console.error("Failed to fetch versions:", error);
    }
  };
  
  const fetchTests = async () => {
    try {
      const response = await fetch(`/api/prompts/templates/${templateId}/tests`);
      const data = await response.json();
      if (data.status === 'success') {
        setTests(data.tests);
      }
    } catch (error) {
      console.error("Failed to fetch tests:", error);
    }
  };
  
  const fetchStats = async () => {
    try {
      const response = await fetch(`/api/prompts/usage/stats?template_id=${templateId}&days=30`);
      const data = await response.json();
      if (data.status === 'success') {
        setStats(data.stats);
      }
    } catch (error) {
      console.error("Failed to fetch stats:", error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleRunAllTests = async () => {
    if (!templateId) return;
    
    try {
      const response = await fetch(`/api/prompts/templates/${templateId}/tests/run-all`, {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        alert(`Tests completed: ${data.count} results`);
        fetchTests();
      }
    } catch (error) {
      console.error("Failed to run tests:", error);
    }
  };
  
  const handleSetDefault = async () => {
    try {
      const response = await fetch(`/api/prompts/templates/${templateId}/default`, {
        method: 'PUT'
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        alert('Template set as default');
        fetchTemplate();
      }
    } catch (error) {
      console.error("Failed to set default:", error);
    }
  };
  
  if (loading) {
    return <div className="loading">Loading template viewer...</div>;
  }
  
  if (!template) {
    return <div className="error">Template not found</div>;
  }
  
  return (
    <div className="template-viewer">
      <div className="viewer-header">
        <h3>{template.name}</h3>
        <div className="viewer-meta">
          <span className="badge worker">{template.worker_name}</span>
          <span className="badge type">{template.prompt_type}</span>
          <span className="badge version">v{template.version}</span>
          {template.is_default && <span className="badge default">Default</span>}
          {!template.is_active && <span className="badge inactive">Inactive</span>}
        </div>
        <div className="viewer-actions">
          <button onClick={handleSetDefault} className="btn-default">Set as Default</button>
          <button onClick={onClose} className="btn-close">Close</button>
        </div>
      </div>
      
      <div className="viewer-tabs">
        <button 
          className={activeTab === 'details' ? 'active' : ''}
          onClick={() => setActiveTab('details')}
        >
          Details
        </button>
        <button 
          className={activeTab === 'versions' ? 'active' : ''}
          onClick={() => setActiveTab('versions')}
        >
          Versions ({versions.length})
        </button>
        <button 
          className={activeTab === 'tests' ? 'active' : ''}
          onClick={() => setActiveTab('tests')}
        >
          Tests ({tests.length})
        </button>
        <button 
          className={activeTab === 'analytics' ? 'active' : ''}
          onClick={() => setActiveTab('analytics')}
        >
          Analytics
        </button>
      </div>
      
      <div className="viewer-content">
        {activeTab === 'details' && (
          <div className="details-tab">
            <div className="section">
              <h4>System Prompt</h4>
              <pre className="prompt-display">{template.system_prompt}</pre>
            </div>
            
            <div className="section">
              <h4>User Prompt Template</h4>
              <pre className="prompt-display">{template.user_prompt_template}</pre>
            </div>
            
            <div className="section">
              <h4>Parameters</h4>
              <pre className="prompt-display">{JSON.stringify(template.parameters, null, 2)}</pre>
            </div>
            
            <div className="section">
              <h4>Metadata</h4>
              <pre className="prompt-display">{JSON.stringify(template.metadata, null, 2)}</pre>
            </div>
            
            {template.description && (
              <div className="section">
                <h4>Description</h4>
                <p>{template.description}</p>
              </div>
            )}
          </div>
        )}
        
        {activeTab === 'versions' && (
          <div className="versions-tab">
            <div className="versions-list">
              {versions.map((version) => (
                <div key={version.version_id} className="version-item">
                  <div className="version-header">
                    <h4>Version {version.version}</h4>
                    <span className="date">
                      {version.created_at ? new Date(version.created_at).toLocaleString() : 'N/A'}
                    </span>
                  </div>
                  {version.change_notes && (
                    <div className="version-notes">
                      <strong>Notes:</strong> {version.change_notes}
                    </div>
                  )}
                  <div className="version-preview">
                    <div className="preview-section">
                      <strong>System:</strong>
                      <p>{version.system_prompt.substring(0, 100)}...</p>
                    </div>
                    <div className="preview-section">
                      <strong>User:</strong>
                      <p>{version.user_prompt_template.substring(0, 100)}...</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {activeTab === 'tests' && (
          <div className="tests-tab">
            <div className="tests-header">
              <h4>Test Cases</h4>
              <button onClick={handleRunAllTests} className="btn-run-all">
                Run All Tests
              </button>
            </div>
            
            <div className="tests-list">
              {tests.length === 0 ? (
                <p>No test cases yet.</p>
              ) : (
                tests.map((test) => (
                  <div key={test.test_id} className="test-item">
                    <div className="test-header">
                      <h5>{test.name}</h5>
                      <span className="test-status">{test.is_active ? 'Active' : 'Inactive'}</span>
                    </div>
                    <div className="test-input">
                      <strong>Input:</strong>
                      <pre>{JSON.stringify(test.test_input, null, 2)}</pre>
                    </div>
                    {test.expected_output && (
                      <div className="test-expected">
                        <strong>Expected Output:</strong>
                        <pre>{JSON.stringify(test.expected_output, null, 2)}</pre>
                      </div>
                    )}
                    {test.expected_error && (
                      <div className="test-expected-error">
                        <strong>Expected Error:</strong> {test.expected_error}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
        
        {activeTab === 'analytics' && (
          <div className="analytics-tab">
            {stats && stats.stats && stats.stats.length > 0 ? (
              <div className="analytics-overview">
                <div className="analytics-summary">
                  <div className="stat-card">
                    <h5>Total Usage</h5>
                    <div className="stat-value">{stats.stats.summary.total_usage}</div>
                  </div>
                  <div className="stat-card">
                    <h5>Total Cost</h5>
                    <div className="stat-value">${stats.stats.summary.total_cost.toFixed(6)}</div>
                  </div>
                  <div className="stat-card">
                    <h5>Success Rate</h5>
                    <div className="stat-value">{(stats.stats.summary.avg_success_rate * 100).toFixed(1)}%</div>
                  </div>
                </div>
                
                <div className="usage-breakdown">
                  <h5>Usage Breakdown</h5>
                  {stats.stats.stats.map((stat: any, idx: number) => (
                    <div key={idx} className="usage-row">
                      <span className="worker-name">{stat.worker_name}</span>
                      <span className="usage-count">{stat.usage_count} uses</span>
                      <span className="cost">${stat.total_cost.toFixed(6)}</span>
                      <span className="success-rate">{(stat.success_rate * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="empty-analytics">
                <p>No usage data available yet.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Prompt Dashboard Main Component
const PromptDashboard: React.FC = () => {
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'editor' | 'viewer'>('list');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  
  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };
  
  const handleCreateNew = () => {
    setEditingId(null);
    setViewMode('editor');
  };
  
  const handleEdit = (templateId: number) => {
    setEditingId(templateId);
    setViewMode('editor');
  };
  
  const handleView = (templateId: number) => {
    setSelectedTemplateId(templateId);
    setViewMode('viewer');
  };
  
  const handleSave = () => {
    setViewMode('list');
    handleRefresh();
  };
  
  const handleCancel = () => {
    setViewMode('list');
  };
  
  const handleDelete = async (templateId: number) => {
    if (!confirm('Are you sure you want to delete this template?')) {
      return;
    }
    
    try {
      const response = await fetch(`/api/prompts/templates/${templateId}`, {
        method: 'DELETE'
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        alert('Template deleted');
        handleRefresh();
      }
    } catch (error) {
      console.error("Failed to delete template:", error);
    }
  };
  
  return (
    <div className="prompt-dashboard">
      <div className="dashboard-header">
        <h2>Prompt Management Dashboard</h2>
        {viewMode === 'list' && (
          <div className="header-actions">
            <button onClick={handleCreateNew} className="btn-primary">
              Create Template
            </button>
          </div>
        )}
      </div>
      
      {viewMode === 'list' && (
        <TemplateList
          key={refreshKey}
          onSelectTemplate={handleView}
          onRefresh={handleRefresh}
        />
      )}
      
      {viewMode === 'editor' && (
        <TemplateEditor
          templateId={editingId}
          onSave={handleSave}
          onCancel={handleCancel}
        />
      )}
      
      {viewMode === 'viewer' && selectedTemplateId && (
        <TemplateViewer
          templateId={selectedTemplateId}
          onClose={() => setViewMode('list')}
        />
      )}
    </div>
  );
};
```

#### 3.9 UI Integration with Existing Dashboard

```typescript
// src/openmemory/static/js/dashboard.js additions

// Add prompt management tab to dashboard
const PROMPT_TAB = {
  id: 'prompts',
  label: 'Prompts',
  icon: '📝',
  component: PromptDashboard  // React component
};

// Register the new tab
if (window.dashboardTabs) {
  window.dashboardTabs.registerTab(PROMPT_TAB);
} else {
  // Fallback if dashboard tabs not initialized yet
  window.addEventListener('dashboardReady', () => {
    window.dashboardTabs.registerTab(PROMPT_TAB);
  });
}

// Add prompt management to main menu
const PROMPT_MENU_ITEM = {
  id: 'prompt-management',
  label: 'Prompt Management',
  icon: '📝',
  onClick: () => {
    // Navigate to prompts page or open modal
    window.location.hash = '#/prompts';
  }
};

if (window.mainMenu) {
  window.mainMenu.registerMenuItem(PROMPT_MENU_ITEM);
}
```

#### 3.10 Migration Script for Existing Prompts

```python
# src/openmemory/alembic/versions/add_prompt_templates.py

"""Add prompt templates table

Revision ID: add_prompt_templates
Revises: fix_cross_project_learnings_schema
Create Date: 2026-01-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json

# revision identifiers, used by Alembic.
revision = 'add_prompt_templates'
down_revision = 'fix_cross_project_learnings_schema'
branch_labels = None
depends_on = None

def upgrade():
    # Create prompt_templates table
    op.create_table(
        'prompt_templates',
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('worker_name', sa.String(length=50), nullable=False),
        sa.Column('prompt_type', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('user_prompt_template', sa.Text(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('template_id'),
        sa.UniqueConstraint('worker_name', 'prompt_type', 'name', 'version', name='uix_worker_prompt_version')
    )
    op.create_index('idx_prompt_templates_worker', 'prompt_templates', ['worker_name'])
    op.create_index('idx_prompt_templates_type', 'prompt_templates', ['prompt_type'])
    op.create_index('idx_prompt_templates_active', 'prompt_templates', ['is_active'])
    
    # Create prompt_usage table
    op.create_table(
        'prompt_usage',
        sa.Column('usage_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('worker_name', sa.String(length=50), nullable=False),
        sa.Column('execution_id', sa.String(length=100), nullable=True),
        sa.Column('context', postgresql.JSONB(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.template_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('usage_id')
    )
    op.create_index('idx_prompt_usage_template', 'prompt_usage', ['template_id'])
    op.create_index('idx_prompt_usage_worker', 'prompt_usage', ['worker_name'])
    op.create_index('idx_prompt_usage_created', 'prompt_usage', ['created_at'])
    
    # Create prompt_versions table
    op.create_table(
        'prompt_versions',
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('user_prompt_template', sa.Text(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('change_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.template_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('version_id')
    )
    op.create_index('idx_prompt_versions_template', 'prompt_versions', ['template_id'])
    op.create_index('idx_prompt_versions_version', 'prompt_versions', ['version'])
    
    # Create prompt_tests table
    op.create_table(
        'prompt_tests',
        sa.Column('test_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('test_input', postgresql.JSONB(), nullable=False),
        sa.Column('expected_output', postgresql.JSONB(), nullable=True),
        sa.Column('expected_error', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.template_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('test_id')
    )
    op.create_index('idx_prompt_tests_template', 'prompt_tests', ['template_id'])
    
    # Create prompt_validations table
    op.create_table(
        'prompt_validations',
        sa.Column('validation_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('test_id', sa.Integer(), nullable=True),
        sa.Column('execution_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('actual_output', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('validation_time_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.template_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['test_id'], ['prompt_tests.test_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('validation_id')
    )
    op.create_index('idx_prompt_validations_template', 'prompt_validations', ['template_id'])
    op.create_index('idx_prompt_validations_created', 'prompt_validations', ['created_at'])
    
    # Create prompt_analytics table
    op.create_table(
        'prompt_analytics',
        sa.Column('analytics_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_latency_ms', sa.Integer(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('avg_cost', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.template_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('analytics_id'),
        sa.UniqueConstraint('template_id', 'date', name='uix_template_date')
    )
    op.create_index('idx_prompt_analytics_template', 'prompt_analytics', ['template_id'])
    op.create_index('idx_prompt_analytics_date', 'prompt_analytics', ['date'])
    
    # Seed with existing hardcoded prompts
    # This would migrate existing hardcoded prompts to the database
    
    # Add prompt templates for each worker
    # ThinkWorker templates
    op.execute("""
        INSERT INTO prompt_templates (
            worker_name, prompt_type, name, description,
            system_prompt, user_prompt_template, parameters,
            is_default, version
        ) VALUES 
        (
            'think', 'committee_scoring', 'Multi-Agent Committee Scoring',
            'Scoring proposal using multi-agent committee with weighted average',
            'You are an expert committee member. Score the proposal 0-1 considering:
- Technical feasibility
- Risk level
- Business value
- Implementation complexity
- Test coverage

Return JSON: {{"score": 0.85, "confidence": 0.90, "risks": ["...", "..."]}}',
            'Proposal: {{proposal}}
Description: {{description}}
Changes: {{changes}}

Score this proposal considering the factors above.',
            '{{"required": ["proposal", "description", "changes"], "optional": []}}',
            true, 1
        ),
        (
            'think', 'risk_assessment', 'Risk Assessment',
            'Assess risks in proposed changes',
            'You are a risk assessment expert. Analyze risks in the following proposal.

Respond with JSON:
{{
  "risk_level": "low|medium|high",
  "risks": ["risk1", "risk2"],
  "confidence": 0.0-1.0,
  "mitigation_suggestions": ["...", "..."]
}}',
            'Proposal: {{proposal}}
Description: {{description}}
Change type: {{change_type}}

Assess the risks.',
            '{{"required": ["proposal", "description", "change_type"], "optional": []}}',
            true, 1
        );
    """)
    
    # DreamWorker templates
    op.execute("""
        INSERT INTO prompt_templates (
            worker_name, prompt_type, name, description,
            system_prompt, user_prompt_template, parameters,
            is_default, version
        ) VALUES 
        (
            'dream', 'error_fix', 'Error Fix Generation',
            'Generate code fixes for identified errors',
            'You are an expert software engineer specialized in fixing code issues.

Respond with JSON:
{{
  "title": "Brief title",
  "description": "Detailed explanation",
  "confidence": 0.0-1.0,
  "changes": [
    {{
      "file": "path/to/file.py",
      "original": "code to replace",
      "fixed": "corrected code",
      "explanation": "why this fixes it"
    }}
  ],
  "testing_strategy": "How to verify",
  "historical_lessons": "What was learned"
}}',
            'Issues to fix:
{{issues}}

File contents:
{{file_contents}}

Generate specific code fixes.',
            '{{"required": ["issues", "file_contents"], "optional": ["historical_context"]}}',
            true, 1
        );
    """)
    
    # LearningWorker templates
    op.execute("""
        INSERT INTO prompt_templates (
            worker_name, prompt_type, name, description,
            system_prompt, user_prompt_template, parameters,
            is_default, version
        ) VALUES 
        (
            'learning', 'pattern_extraction', 'Pattern Extraction',
            'Extract patterns from successful proposals',
            'You are a pattern extraction expert. Extract patterns from successful proposals.

Respond with JSON:
{{
  "pattern_name": "descriptive name",
  "pattern_type": "type",
  "description": "pattern description",
  "confidence": 0.0-1.0,
  "code_template": "template code",
  "applicability": "when to use this pattern"
}}',
            'Proposal: {{proposal}}
Description: {{description}}
Changes: {{changes}}
Success rate: {{success_rate}}

Extract the pattern.',
            '{{"required": ["proposal", "description", "changes", "success_rate"], "optional": []}}',
            true, 1
        );
    """)
    
    # AnalysisWorker templates
    op.execute("""
        INSERT INTO prompt_templates (
            worker_name, prompt_type, name, description,
            system_prompt, user_prompt_template, parameters,
            is_default, version
        ) VALUES 
        (
            'analysis', 'issue_assessment', 'Issue Severity Assessment',
            'Assess severity of code issues',
            'You are a code analysis expert. Assess issue severity.

Respond with JSON:
{{
  "severity": "info|warning|error",
  "confidence": 0.0-1.0,
  "suggested_fix": "fix description",
  "priority": 1-5
}}',
            'Issue: {{issue}}
File: {{file}}
Line: {{line}}
Context: {{context}}

Assess the severity.',
            '{{"required": ["issue", "file", "line", "context"], "optional": []}}',
            true, 1
        );
    """)
    
    # RecallWorker templates
    op.execute("""
        INSERT INTO prompt_templates (
            worker_name, prompt_type, name, description,
            system_prompt, user_prompt_template, parameters,
            is_default, version
        ) VALUES 
        (
            'recall', 'context_retrieval', 'Context Retrieval',
            'Retrieve relevant context for queries',
            'You are a context retrieval expert. Find relevant context for the query.

Respond with JSON:
{{
  "relevant_context": ["context1", "context2"],
  "sources": ["source1", "source2"],
  "relevance_score": 0.0-1.0
}}',
            'Query: {{query}}
Available context: {{context}}

Find relevant context.',
            '{{"required": ["query", "context"], "optional": []}}',
            true, 1
        );
    """)
    
    # DreamerMetaAgent templates
    op.execute("""
        INSERT INTO prompt_templates (
            worker_name, prompt_type, name, description,
            system_prompt, user_prompt_template, parameters,
            is_default, version
        ) VALUES 
        (
            'dreamer', 'experiment_generation', 'Experiment Generation',
            'Generate experimental approaches',
            'You are the Dreamer for the {{worker_name}} worker in SIGMA.
Your role is to propose novel experimental approaches.

Respond in JSON format:
{{
  "experiment_name": "descriptive name",
  "hypothesis": "what you think will happen",
  "approach": "detailed implementation steps",
  "metrics": ["metric1", "metric2"],
  "risk_level": "low|medium|high",
  "rollback_plan": "how to undo if it fails",
  "confidence": 0.0-1.0
}}',
            'Worker: {{worker_name}}
Context: {{context}}

Propose an experiment.',
            '{{"required": ["worker_name", "context"], "optional": []}}',
            true, 1
        );
    """)

def downgrade():
    # Drop tables in reverse order
    op.drop_index('idx_prompt_analytics_date', table_name='prompt_analytics')
    op.drop_index('idx_prompt_analytics_template', table_name='prompt_analytics')
    op.drop_table('prompt_analytics')
    
    op.drop_index('idx_prompt_validations_created', table_name='prompt_validations')
    op.drop_index('idx_prompt_validations_template', table_name='prompt_validations')
    op.drop_table('prompt_validations')
    
    op.drop_index('idx_prompt_tests_template', table_name='prompt_tests')
    op.drop_table('prompt_tests')
    
    op.drop_index('idx_prompt_versions_version', table_name='prompt_versions')
    op.drop_index('idx_prompt_versions_template', table_name='prompt_versions')
    op.drop_table('prompt_versions')
    
    op.drop_index('idx_prompt_usage_created', table_name='prompt_usage')
    op.drop_index('idx_prompt_usage_worker', table_name='prompt_usage')
    op.drop_index('idx_prompt_usage_template', table_name='prompt_usage')
    op.drop_table('prompt_usage')
    
    op.drop_index('idx_prompt_templates_active', table_name='prompt_templates')
    op.drop_index('idx_prompt_templates_type', table_name='prompt_templates')
    op.drop_index('idx_prompt_templates_worker', table_name='prompt_templates')
    op.drop_table('prompt_templates')
```

#### 3.11 Database Migration for New Tables

```python
# src/openmemory/alembic/versions/add_prompt_templates.py

"""Add prompt templates table

Revision ID: add_prompt_templates
Revises: fix_cross_project_learnings_schema
Create Date: 2026-01-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json

# revision identifiers, used by Alembic.
revision = 'add_prompt_templates'
down_revision = 'fix_cross_project_learnings_schema'
branch_labels = None
depends_on = None

def upgrade():
    # Create prompt_templates table
    op.create_table(
        'prompt_templates',
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('worker_name', sa.String(length=50), nullable=False),
        sa.Column('prompt_type', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('user_prompt_template', sa.Text(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('template_id'),
        sa.UniqueConstraint('worker_name', 'prompt_type', 'name', 'version', name='uix_worker_prompt_version')
    )
    op.create_index('idx_prompt_templates_worker', 'prompt_templates', ['worker_name'])
    op.create_index('idx_prompt_templates_type', 'prompt_templates', ['prompt_type'])
    op.create_index('idx_prompt_templates_active', 'prompt_templates', ['is_active'])
    
    # Create prompt_usage table
    op.create_table(
        'prompt_usage',
        sa.Column('usage_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('worker_name', sa.String(length=50), nullable=False),
        sa.Column('execution_id', sa.String(length=100), nullable=True),
        sa.Column('context', postgresql.JSONB(), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.template_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('usage_id')
    )
    op.create_index('idx_prompt_usage_template', 'prompt_usage', ['template_id'])
    op.create_index('idx_prompt_usage_worker', 'prompt_usage', ['worker_name'])
    op.create_index('idx_prompt_usage_created', 'prompt_usage', ['created_at'])
    
    # Create prompt_versions table
    op.create_table(
        'prompt_versions',
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('user_prompt_template', sa.Text(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('change_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.template_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('version_id')
    )
    op.create_index('idx_prompt_versions_template', 'prompt_versions', ['template_id'])
    op.create_index('idx_prompt_versions_version', 'prompt_versions', ['version'])
    
    # Create prompt_tests table
    op.create_table(
        'prompt_tests',
        sa.Column('test_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('test_input', postgresql.JSONB(), nullable=False),
        sa.Column('expected_output', postgresql.JSONB(), nullable=True),
        sa.Column('expected_error', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.template_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('test_id')
    )
    op.create_index('idx_prompt_tests_template', 'prompt_tests', ['template_id'])
    
    # Create prompt_validations table
    op.create_table(
        'prompt_validations',
        sa.Column('validation_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('test_id', sa.Integer(), nullable=True),
        sa.Column('execution_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('actual_output', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('validation_time_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.template_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['test_id'], ['prompt_tests.test_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('validation_id')
    )
    op.create_index('idx_prompt_validations_template', 'prompt_validations', ['template_id'])
    op.create_index('idx_prompt_validations_created', 'prompt_validations', ['created_at'])
    
    # Create prompt_analytics table
    op.create_table(
        'prompt_analytics',
        sa.Column('analytics_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('avg_latency_ms', sa.Integer(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('avg_cost', sa.Float(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.template_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('analytics_id'),
        sa.UniqueConstraint('template_id', 'date', name='uix_template_date')
    )
    op.create_index('idx_prompt_analytics_template', 'prompt_analytics', ['template_id'])
    op.create_index('idx_prompt_analytics_date', 'prompt_analytics', ['date'])
    
    # Seed with existing hardcoded prompts
    # This would migrate existing hardcoded prompts to the database
    
    # Add prompt templates for each worker
    # ThinkWorker templates
    op.execute("""
        INSERT INTO prompt_templates (
            worker_name, prompt_type, name, description,
            system_prompt, user_prompt_template, parameters,
            is_default, version
        ) VALUES 
        (
            'think', 'committee_scoring', 'Multi-Agent Committee Scoring',
            'Scoring proposal using multi-agent committee with weighted average',
            'You are an expert committee member. Score the proposal 0-1 considering:
- Technical feasibility
- Risk level
- Business value
- Implementation complexity
- Test coverage

Return JSON: {{"score": 0.85, "confidence": 0.90, "risks": ["...", "..."]}}',
            'Proposal: {{proposal}}
Description: {{description}}
Changes: {{changes}}

Score this proposal considering the factors above.',
            '{{"required": ["proposal", "description", "changes"], "optional": []}}',
            true, 1
        ),
        (
            'think', 'risk_assessment', 'Risk Assessment',
            'Assess risks in proposed changes',
            'You are a risk assessment expert. Analyze risks in the following proposal.

Respond with JSON:
{{
  "risk_level": "low|medium|high",
  "risks": ["risk1", "risk2"],
  "confidence": 0.0-1.0,
  "mitigation_suggestions": ["...", "..."]
}}',
            'Proposal: {{proposal}}
Description: {{description}}
Change type: {{change_type}}

Assess the risks.',
            '{{"required": ["proposal", "description", "change_type"], "optional": []}}',
            true, 1
        );
    """)
    
    # DreamWorker templates
    op.execute("""
        INSERT INTO prompt_templates (
            worker_name, prompt_type, name, description,
            system_prompt, user_prompt_template, parameters,
            is_default, version
        ) VALUES 
        (
            'dream', 'error_fix', 'Error Fix Generation',
            'Generate code fixes for identified errors',
            'You are an expert software engineer specialized in fixing code issues.

Respond with JSON:
{{
  "title": "Brief title",
  "description": "Detailed explanation",
  "confidence": 0.0-1.0,
  "changes": [
    {{
      "file": "path/to/file.py",
      "original": "code to replace",
      "fixed": "corrected code",
      "explanation": "why this fixes it"
    }}
  ],
  "testing_strategy": "How to verify",
  "historical_lessons": "What was learned"
}}',
            'Issues to fix:
{{issues}}

File contents:
{{file_contents}}

Generate specific code fixes.',
            '{{"required": ["issues", "file_contents"], "optional": ["historical_context"]}}',
            true, 1
        );
    """)
    
    # LearningWorker templates
    op.execute("""
        INSERT INTO prompt_templates (
            worker_name, prompt_type, name, description,
            system_prompt, user_prompt_template, parameters,
            is_default, version
        ) VALUES 
        (
            'learning', 'pattern_extraction', 'Pattern Extraction',
            'Extract patterns from successful proposals',
            'You are a pattern extraction expert. Extract patterns from successful proposals.

Respond with JSON:
{{
  "pattern_name": "descriptive name",
  "pattern_type": "type",
  "description": "pattern description",
  "confidence": 0.0-1.0,
  "code_template": "template code",
  "applicability": "when to use this pattern"
}}',
            'Proposal: {{proposal}}
Description: {{description}}
Changes: {{changes}}
Success rate: {{success_rate}}

Extract the pattern.',
            '{{"required": ["proposal", "description", "changes", "success_rate"], "optional": []}}',
            true, 1
        );
    """)
    
    # AnalysisWorker templates
    op.execute("""
        INSERT INTO prompt_templates (
            worker_name, prompt_type, name, description,
            system_prompt, user_prompt_template, parameters,
            is_default, version
        ) VALUES 
        (
            'analysis', 'issue_assessment', 'Issue Severity Assessment',
            'Assess severity of code issues',
            'You are a code analysis expert. Assess issue severity.

Respond with JSON:
{{
  "severity": "info|warning|error",
  "confidence": 0.0-1.0,
  "suggested_fix": "fix description",
  "priority": 1-5
}}',
            'Issue: {{issue}}
File: {{file}}
Line: {{line}}
Context: {{context}}

Assess the severity.',
            '{{"required": ["issue", "file", "line", "context"], "optional": []}}',
            true, 1
        );
    """)
    
    # RecallWorker templates
    op.execute("""
        INSERT INTO prompt_templates (
            worker_name, prompt_type, name, description,
            system_prompt, user_prompt_template, parameters,
            is_default, version
        ) VALUES 
        (
            'recall', 'context_retrieval', 'Context Retrieval',
            'Retrieve relevant context for queries',
            'You are a context retrieval expert. Find relevant context for the query.

Respond with JSON:
{{
  "relevant_context": ["context1", "context2"],
  "sources": ["source1", "source2"],
  "relevance_score": 0.0-1.0
}}',
            'Query: {{query}}
Available context: {{context}}

Find relevant context.',
            '{{"required": ["query", "context"], "optional": []}}',
            true, 1
        );
    """)
    
    # DreamerMetaAgent templates
    op.execute("""
        INSERT INTO prompt_templates (
            worker_name, prompt_type, name, description,
            system_prompt, user_prompt_template, parameters,
            is_default, version
        ) VALUES 
        (
            'dreamer', 'experiment_generation', 'Experiment Generation',
            'Generate experimental approaches',
            'You are the Dreamer for the {{worker_name}} worker in SIGMA.
Your role is to propose novel experimental approaches.

Respond in JSON format:
{{
  "experiment_name": "descriptive name",
  "hypothesis": "what you think will happen",
  "approach": "detailed implementation steps",
  "metrics": ["metric1", "metric2"],
  "risk_level": "low|medium|high",
  "rollback_plan": "how to undo if it fails",
  "confidence": 0.0-1.0
}}',
            'Worker: {{worker_name}}
Context: {{context}}

Propose an experiment.',
            '{{"required": ["worker_name", "context"], "optional": []}}',
            true, 1
        );
    """)

def downgrade():
    # Drop tables in reverse order
    op.drop_index('idx_prompt_analytics_date', table_name='prompt_analytics')
    op.drop_index('idx_prompt_analytics_template', table_name='prompt_analytics')
    op.drop_table('prompt_analytics')
    
    op.drop_index('idx_prompt_validations_created', table_name='prompt_validations')
    op.drop_index('idx_prompt_validations_template', table_name='prompt_validations')
    op.drop_table('prompt_validations')
    
    op.drop_index('idx_prompt_tests_template', table_name='prompt_tests')
    op.drop_table('prompt_tests')
    
    op.drop_index('idx_prompt_versions_version', table_name='prompt_versions')
    op.drop_index('idx_prompt_versions_template', table_name='prompt_versions')
    op.drop_table('prompt_versions')
    
    op.drop_index('idx_prompt_usage_created', table_name='prompt_usage')
    op.drop_index('idx_prompt_usage_worker', table_name='prompt_usage')
    op.drop_index('idx_prompt_usage_template', table_name='prompt_usage')
    op.drop_table('prompt_usage')
    
    op.drop_index('idx_prompt_templates_active', table_name='prompt_templates')
    op.drop_index('idx_prompt_templates_type', table_name='prompt_templates')
    op.drop_index('idx_prompt_templates_worker', table_name='prompt_templates')
    op.drop_table('prompt_templates')
```

#### 3.12 Integration with Main Application

```python
# src/openmemory/main.py additions

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .app.database import init_db, get_db
from .app.routers import prompts
from .app.services.prompt_service import PromptService

app = FastAPI(
    title="SIGMA Memory Server",
    description="Self-Improving Generative Memory & Agents",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    
    # Initialize prompt service and migrate existing prompts
    service = PromptService()
    
    # Check if any templates exist
    existing = service.get_templates(limit=1)
    
    if not existing:
        logger.info("No prompt templates found. Migrating from hardcoded prompts...")
        # This would call the migration script or create default templates
        # For now, templates are seeded during migration
        logger.info("Prompt templates initialized")
    
    logger.info("SIGMA Memory Server started")

# Include routers
app.include_router(prompts.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SIGMA Memory Server",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

# API info endpoint
@app.get("/")
async def root():
    """API information"""
    return {
        "name": "SIGMA Memory Server",
        "version": "2.0.0",
        "description": "Self-Improving Generative Memory & Agents",
        "endpoints": {
            "prompt_management": "/api/prompts",
            "agents": "/api/agents",
            "dashboard": "/static/dashboard.html"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "src.openmemory.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
```

### Implementation Plan

**Phase 1: Database Schema and Models (Week 1)**
1. Create prompt template models
2. Create usage tracking models
3. Create version history models
4. Create test and validation models
5. Create analytics models
6. Run migration script

**Phase 2: Service Layer (Week 2)**
1. Implement PromptService class
2. Add template CRUD operations
3. Add rendering logic with parameter validation
4. Add usage tracking
5. Add testing framework
6. Add version management
7. Add search and filtering

**Phase 3: Backend API (Week 3)**
1. Create FastAPI router for prompts
2. Implement all CRUD endpoints
3. Implement rendering endpoints
4. Implement analytics endpoints
5. Implement testing endpoints
6. Implement search endpoints
7. Add OpenAPI documentation

**Phase 4: Worker Integration (Week 3-4)**
1. Create PromptManager utility
2. Integrate into BaseWorker
3. Integrate into ThinkWorker
4. Integrate into DreamWorker
5. Integrate into LearningWorker
6. Integrate into AnalysisWorker
7. Integrate into RecallWorker
8. Add fallback to hardcoded prompts

**Phase 5: Frontend UI (Week 4-5)**
1. Create TemplateList component
2. Create TemplateEditor component
3. Create TemplateViewer component
4. Create PromptDashboard main component
5. Integrate with existing dashboard
6. Add navigation and routing
7. Add styling and theming

**Phase 6: Testing and Validation (Week 5)**
1. Create test cases for all templates
2. Validate rendering logic
3. Test worker integration
4. Test API endpoints
5. Test UI components
6. Performance testing
7. Load testing

**Phase 7: Documentation and Deployment (Week 6)**
1. API documentation
2. User guide for UI
3. Developer guide for integration
4. Deployment scripts
5. Monitoring setup
6. Backup and recovery procedures

---

## Testing Plan

### Cross-Worker Knowledge Sharing Tests

**Unit Tests**
- [ ] KnowledgeExchangeProtocol broadcast/receive
- [ ] KnowledgeValidator validation logic
- [ ] KnowledgeFreshnessTracker decay calculations
- [ ] Worker integration with knowledge exchange
- [ ] Conflict resolution strategies

**Integration Tests**
- [ ] Multi-worker knowledge propagation
- [ ] Graphiti knowledge storage
- [ ] Real-time knowledge updates
- [ ] Knowledge freshness monitoring
- [ ] Cross-worker context enrichment

**End-to-End Tests**
- [ ] Complete knowledge sharing workflow
- [ ] Failure recovery scenarios
- [ ] Performance under load
- [ ] Memory usage patterns
- [ ] Network latency handling

### Graphiti Experimentation Tests

**Unit Tests**
- [ ] Multi-hop traversal strategies
- [ ] Semantic similarity search
- [ ] Temporal analysis algorithms
- [ ] Community detection
- [ ] Anomaly detection
- [ ] Path explanation generation

**Integration Tests**
- [ ] Strategy execution workflows
- [ ] Graphiti client integration
- [ ] Experiment result tracking
- [ ] Metric calculations
- [ ] Error handling

**End-to-End Tests**
- [ ] Complete experimentation workflow
- [ ] UI interaction tests
- [ ] API endpoint tests
- [ ] Performance benchmarks
- [ ] Scalability tests

### Prompt Management Tests

**Unit Tests**
- [ ] Template CRUD operations
- [ ] Parameter validation
- [ ] Prompt rendering
- [ ] Version management
- [ ] Test execution
- [ ] Usage tracking
- [ ] Analytics calculations

**Integration Tests**
- [ ] Database operations
- [ ] API endpoints
- [ ] Worker integration
- [ ] Fallback to hardcoded prompts
- [ ] Error recovery

**End-to-End Tests**
- [ ] Complete prompt lifecycle
- [ ] UI component tests
- [ ] API workflow tests
- [ ] Performance tests
- [ ] Security tests

---

## Summary

This comprehensive design document provides:

### Feature 1: Cross-Worker Knowledge Sharing Protocols
- **Direct knowledge exchange** between workers via message queue
- **Knowledge type registry** with validation and propagation strategies
- **Freshness tracking** with decay functions
- **Conflict resolution** for overlapping knowledge
- **Real-time notifications** via WebSocket
- **Database schema** for persistence and analytics

### Feature 2: Experimental Strategies Leveraging Graphiti
- **Multi-hop traversal** for deep knowledge exploration
- **Semantic similarity search** using vector embeddings
- **Temporal pattern analysis** for evolution tracking
- **Cross-domain transfer** for pattern adaptation
- **Community detection** for knowledge organization
- **Anomaly detection** for identifying outliers
- **Path explanations** for natural language insights
- **Real-time updates** for immediate graph evolution
- **Experimentation dashboard** with strategy selection and monitoring

### Feature 3: Worker Prompts Extraction to UI
- **Centralized prompt management** with database storage
- **Version control** for tracking prompt changes
- **Testing framework** for validation
- **Usage analytics** for cost and performance tracking
- **Parameter validation** and rendering
- **Backend API** with full CRUD operations
- **Frontend UI** with list, editor, viewer components
- **Integration** with existing workers and dashboard
- **Migration** from hardcoded to database prompts

### Key Benefits
1. **Operational Control**: Manage prompts without code changes
2. **Experimentation**: Test new strategies safely via UI
3. **Knowledge Sharing**: Workers learn from each other in real-time
4. **Cost Tracking**: Monitor LLM usage and costs
5. **Performance Metrics**: Track prompt effectiveness
6. **Version Control**: Rollback to previous prompt versions
7. **Testing**: Validate prompts before deployment
8. **Scalability**: Support for multiple workers and projects

### Estimated Timeline
- **Cross-Worker Knowledge Sharing**: 4 weeks
- **Graphiti Experimentation**: 6 weeks
- **Prompt Management UI**: 6 weeks
- **Testing & Optimization**: 2 weeks
- **Total**: ~18 weeks for full implementation

This design provides a solid foundation for building a production-ready system with enhanced capabilities for self-improvement, knowledge sharing, and operational control.
