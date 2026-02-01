# Phase 4: Conflict Resolution & Advanced Features
**Implementation Plan**  
**Timeline: 4 days**  
**Status: Not Started**

---

## Overview

This phase enhances the knowledge exchange system with enterprise-grade features:
- **Conflict Detection & Resolution** - Intelligent handling of conflicting knowledge
- **WebSocket Notifications** - Real-time knowledge sharing across workers
- **Advanced Monitoring** - Comprehensive metrics and alerting
- **Performance Optimization** - Batch operations and caching

---

## Phase 4 Objectives

### 1. Conflict Resolution System (1 day)
- [ ] Detect conflicting knowledge submissions
- [ ] Implement resolution strategies (merge, prioritize, discard)
- [ ] Add conflict resolution metadata to knowledge
- [ ] Create conflict resolution API endpoints
- [ ] Test conflict scenarios

### 2. WebSocket Notification System (1.5 days)
- [ ] Design WebSocket server architecture
- [ ] Implement real-time broadcast mechanisms
- [ ] Add WebSocket authentication
- [ ] Create client-side WebSocket handlers
- [ ] Test WebSocket connections and messaging

### 3. Advanced Monitoring & Alerting (1 day)
- [ ] Implement comprehensive metrics collection
- [ ] Add health check endpoints
- [ ] Create alerting system for anomalies
- [ ] Add dashboard widgets for monitoring
- [ ] Test monitoring system

### 4. Performance Optimization (0.5 day)
- [ ] Implement batch operations for knowledge processing
- [ ] Add caching layer for frequent queries
- [ ] Optimize database queries
- [ ] Performance testing and validation

---

## Detailed Implementation

### 1. Conflict Resolution System

#### Files to Create/Modify:

**1.1 Conflict Detection Module** (`src/openmemory/app/utils/conflict_resolver.py`)
```python
"""
Conflict detection and resolution for knowledge exchange.

Features:
- Automatic conflict detection based on similarity thresholds
- Multiple resolution strategies
- Conflict metadata tracking
- Resolution history audit trail
"""

@dataclass
class ConflictMetadata:
    """Metadata for detected conflicts."""
    conflict_id: str
    knowledge_ids: List[str]
    conflict_type: str  # 'duplicate', 'contradiction', 'overlap'
    similarity_score: float
    detected_at: datetime
    resolution_strategy: str
    resolution_status: str  # 'pending', 'resolved', 'failed'
    resolution_details: Optional[Dict] = None

class ConflictResolver:
    """Detect and resolve knowledge conflicts."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.similarity_threshold = 0.85
        self.resolution_strategies = {
            'merge': self._merge_knowledge,
            'prioritize': self._prioritize_knowledge,
            'discard': self._discard_knowledge,
            'manual': self._manual_resolution
        }
    
    def detect_conflicts(self, new_knowledge: KnowledgeExchange) -> List[ConflictMetadata]:
        """Detect conflicts with existing knowledge."""
        # Query similar knowledge based on:
        # - Content similarity (using embeddings if available)
        # - Same worker_id and knowledge_type
        # - Time window (recent knowledge)
        
        similar_knowledge = self.db.query(KnowledgeExchange).filter(
            KnowledgeExchange.worker_id == new_knowledge.worker_id,
            KnowledgeExchange.knowledge_type == new_knowledge.knowledge_type,
            KnowledgeExchange.timestamp >= datetime.now() - timedelta(hours=1),
            KnowledgeExchange.id != new_knowledge.id
        ).all()
        
        conflicts = []
        for existing in similar_knowledge:
            similarity = self._calculate_similarity(new_knowledge, existing)
            if similarity > self.similarity_threshold:
                conflict = ConflictMetadata(
                    conflict_id=str(uuid.uuid4()),
                    knowledge_ids=[new_knowledge.id, existing.id],
                    conflict_type=self._classify_conflict(new_knowledge, existing),
                    similarity_score=similarity,
                    detected_at=datetime.now(),
                    resolution_strategy='merge',  # Default strategy
                    resolution_status='pending'
                )
                conflicts.append(conflict)
        
        return conflicts
    
    def resolve_conflict(self, conflict: ConflictMetadata, strategy: str = None) -> bool:
        """Resolve a conflict using specified strategy."""
        if strategy:
            conflict.resolution_strategy = strategy
        
        if conflict.resolution_strategy not in self.resolution_strategies:
            return False
        
        try:
            resolver = self.resolution_strategies[conflict.resolution_strategy]
            result = resolver(conflict)
            
            if result:
                conflict.resolution_status = 'resolved'
                conflict.resolution_details = {
                    'resolved_at': datetime.now().isoformat(),
                    'strategy': conflict.resolution_strategy,
                    'result': 'success'
                }
            else:
                conflict.resolution_status = 'failed'
                conflict.resolution_details = {
                    'error': 'Resolution failed',
                    'strategy': conflict.resolution_strategy
                }
            
            return result
        except Exception as e:
            conflict.resolution_status = 'failed'
            conflict.resolution_details = {
                'error': str(e),
                'strategy': conflict.resolution_strategy
            }
            return False
    
    def _calculate_similarity(self, k1: KnowledgeExchange, k2: KnowledgeExchange) -> float:
        """Calculate similarity between two knowledge items."""
        # Simple similarity based on content length overlap
        # In production, use embeddings or semantic similarity
        content1 = k1.content if isinstance(k1.content, str) else str(k1.content)
        content2 = k2.content if isinstance(k2.content, str) else str(k2.content)
        
        if not content1 or not content2:
            return 0.0
        
        # Calculate Jaccard similarity on tokens
        tokens1 = set(content1.lower().split())
        tokens2 = set(content2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        
        return intersection / union if union > 0 else 0.0
    
    def _classify_conflict(self, k1: KnowledgeExchange, k2: KnowledgeExchange) -> str:
        """Classify the type of conflict."""
        # Implementation based on content analysis
        content1 = str(k1.content).lower()
        content2 = str(k2.content).lower()
        
        # Check for exact duplicates
        if content1 == content2:
            return 'duplicate'
        
        # Check for contradictions (simple heuristic)
        if self._has_contradictions(content1, content2):
            return 'contradiction'
        
        return 'overlap'
    
    def _has_contradictions(self, content1: str, content2: str) -> bool:
        """Detect potential contradictions in content."""
        # Simple keyword-based contradiction detection
        contradiction_patterns = [
            ('should', 'should not'),
            ('is', 'is not'),
            ('can', 'cannot'),
            ('always', 'never'),
            ('true', 'false'),
            ('success', 'failure'),
            ('increase', 'decrease')
        ]
        
        for word1, word2 in contradiction_patterns:
            if word1 in content1 and word2 in content2:
                return True
            if word2 in content1 and word1 in content2:
                return True
        
        return False
    
    def _merge_knowledge(self, conflict: ConflictMetadata) -> bool:
        """Merge multiple knowledge items into one."""
        knowledge_items = self.db.query(KnowledgeExchange).filter(
            KnowledgeExchange.id.in_(conflict.knowledge_ids)
        ).all()
        
        if not knowledge_items:
            return False
        
        # Merge metadata from all items
        merged_content = []
        merged_source_ids = []
        merged_worker_ids = []
        
        for item in knowledge_items:
            if isinstance(item.content, str):
                merged_content.append(item.content)
            if item.source_id:
                merged_source_ids.append(item.source_id)
            if item.worker_id:
                merged_worker_ids.append(item.worker_id)
            
            # Mark original as merged
            item.is_merged = True
            item.merged_into = knowledge_items[0].id
        
        # Create merged knowledge
        merged_knowledge = KnowledgeExchange(
            worker_id=knowledge_items[0].worker_id,
            knowledge_type=knowledge_items[0].knowledge_type,
            content={
                'merged_from': [item.id for item in knowledge_items],
                'content_parts': merged_content,
                'source_ids': merged_source_ids,
                'worker_ids': merged_worker_ids
            },
            metadata={
                'merged_at': datetime.now().isoformat(),
                'conflict_id': conflict.conflict_id,
                'strategy': 'merge'
            }
        )
        
        self.db.add(merged_knowledge)
        self.db.commit()
        
        return True
    
    def _prioritize_knowledge(self, conflict: ConflictMetadata) -> bool:
        """Prioritize one knowledge item over others."""
        knowledge_items = self.db.query(KnowledgeExchange).filter(
            KnowledgeExchange.id.in_(conflict.knowledge_ids)
        ).all()
        
        if not knowledge_items:
            return False
        
        # Priority: Most recent, highest confidence, most sources
        sorted_items = sorted(
            knowledge_items,
            key=lambda x: (
                x.timestamp,
                x.confidence if hasattr(x, 'confidence') else 0.5,
                len(x.source_ids) if x.source_ids else 0
            ),
            reverse=True
        )
        
        # Keep the top item, mark others as deprecated
        priority_item = sorted_items[0]
        for item in sorted_items[1:]:
            item.is_deprecated = True
            item.deprecated_reason = f"Superseded by {priority_item.id}"
        
        self.db.commit()
        
        return True
    
    def _discard_knowledge(self, conflict: ConflictMetadata) -> bool:
        """Discard all conflicting knowledge items."""
        knowledge_items = self.db.query(KnowledgeExchange).filter(
            KnowledgeExchange.id.in_(conflict.knowledge_ids)
        ).all()
        
        for item in knowledge_items:
            item.is_deprecated = True
            item.deprecated_reason = "Discarded due to conflict"
        
        self.db.commit()
        
        return True
    
    def _manual_resolution(self, conflict: ConflictMetadata) -> bool:
        """Mark conflict for manual resolution."""
        conflict.resolution_status = 'pending_manual'
        conflict.resolution_details = {
            'message': 'Manual resolution required',
            'assigned_to': None
        }
        return True

# API Router for conflict management
@router.get("/conflicts", response_model=List[ConflictResponse])
async def get_conflicts(
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get list of conflicts."""
    query = db.query(KnowledgeConflict)
    if status:
        query = query.filter(KnowledgeConflict.resolution_status == status)
    return query.order_by(KnowledgeConflict.detected_at.desc()).limit(limit).all()

@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    resolution: ConflictResolutionRequest,
    db: Session = Depends(get_db)
):
    """Resolve a specific conflict."""
    resolver = ConflictResolver(db)
    conflict = db.query(KnowledgeConflict).filter(
        KnowledgeConflict.conflict_id == conflict_id
    ).first()
    
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    success = resolver.resolve_conflict(conflict, resolution.strategy)
    
    if not success:
        raise HTTPException(status_code=500, detail="Resolution failed")
    
    return {"status": "resolved", "conflict_id": conflict_id}
```

**1.2 Update BaseWorker to Use Conflict Resolution** (`src/openmemory/app/agents/base_worker.py`)
```python
class BaseWorker:
    # Existing methods...
    
    def __init__(self, worker_id: str, config: Optional[Dict] = None):
        # ... existing initialization ...
        self.conflict_resolver = None
        self.conflict_strategy = 'auto'  # auto, manual, prioritize, merge, discard
    
    async def start(self):
        """Start worker with conflict resolution enabled."""
        await super().start()
        
        # Initialize conflict resolver
        if self.db_session:
            from src.openmemory.app.utils.conflict_resolver import ConflictResolver
            self.conflict_resolver = ConflictResolver(self.db_session)
        
        logger.info(f"Worker {self.worker_id} started with conflict resolution")
    
    async def broadcast_knowledge(
        self,
        knowledge_type: str,
        content: Union[str, Dict],
        urgency: str = "normal",
        priority: int = 5
    ) -> str:
        """Broadcast knowledge with conflict detection."""
        knowledge_id = await super().broadcast_knowledge(
            knowledge_type, content, urgency, priority
        )
        
        # After broadcasting, check for conflicts
        if self.conflict_resolver and self.conflict_strategy != 'manual':
            try:
                # Fetch the newly created knowledge
                knowledge = self.db_session.query(KnowledgeExchange).filter(
                    KnowledgeExchange.id == knowledge_id
                ).first()
                
                if knowledge:
                    conflicts = self.conflict_resolver.detect_conflicts(knowledge)
                    
                    for conflict in conflicts:
                        # Auto-resolve based on strategy
                        if self.conflict_strategy != 'auto':
                            continue
                        
                        resolved = self.conflict_resolver.resolve_conflict(
                            conflict, 
                            strategy=conflict.resolution_strategy
                        )
                        
                        if resolved:
                            logger.info(
                                f"Auto-resolved conflict {conflict.conflict_id} "
                                f"for knowledge {knowledge_id}"
                            )
            except Exception as e:
                logger.error(f"Conflict detection failed: {e}")
        
        return knowledge_id
```

#### Database Schema Updates:

**1.3 Add Conflict Tables** (`src/openmemory/alembic/versions/add_conflict_tables.py`)
```python
"""Add conflict resolution tables.

Revision ID: add_conflict_tables
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Table for tracking conflicts
    op.create_table(
        'knowledge_conflicts',
        sa.Column('conflict_id', sa.String(), nullable=False),
        sa.Column('knowledge_ids', sa.JSON(), nullable=False),
        sa.Column('conflict_type', sa.String(), nullable=False),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('resolution_strategy', sa.String(), nullable=True),
        sa.Column('resolution_status', sa.String(), nullable=False),
        sa.Column('resolution_details', sa.JSON(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('conflict_id'),
        sa.Index('idx_conflicts_status', 'resolution_status'),
        sa.Index('idx_conflicts_detected', 'detected_at'),
    )
    
    # Add columns to KnowledgeExchange for conflict metadata
    op.add_column('knowledge_exchange', sa.Column('is_merged', sa.Boolean(), default=False))
    op.add_column('knowledge_exchange', sa.Column('merged_into', sa.String()))
    op.add_column('knowledge_exchange', sa.Column('is_deprecated', sa.Boolean(), default=False))
    op.add_column('knowledge_exchange', sa.Column('deprecated_reason', sa.String()))
    
    # Add index for better conflict detection queries
    op.create_index(
        'idx_knowledge_worker_type_timestamp',
        'knowledge_exchange',
        ['worker_id', 'knowledge_type', 'timestamp']
    )

def downgrade():
    op.drop_index('idx_knowledge_worker_type_timestamp')
    op.drop_table('knowledge_conflicts')
    op.drop_column('knowledge_exchange', 'is_merged')
    op.drop_column('knowledge_exchange', 'merged_into')
    op.drop_column('knowledge_exchange', 'is_deprecated')
    op.drop_column('knowledge_exchange', 'deprecated_reason')
```

---

### 2. WebSocket Notification System

#### Files to Create/Modify:

**2.1 WebSocket Server** (`src/openmemory/app/utils/websocket_server.py`)
```python
"""
WebSocket server for real-time knowledge notifications.

Features:
- Real-time broadcast to all connected workers
- Room-based messaging (per worker type)
- Authentication and authorization
- Connection monitoring
- Message queuing for offline workers
"""

from fastapi import WebSocket, WebSocketDisconnect
from fastapi import Depends
from typing import Dict, List, Set
import asyncio
import json
from datetime import datetime

class WebSocketManager:
    """Manages WebSocket connections and broadcasting."""
    
    def __init__(self):
        # Active connections: {worker_id: {connection_id: WebSocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Connection metadata: {connection_id: metadata}
        self.connection_metadata: Dict[str, Dict] = {}
        # Message queue for offline workers
        self.message_queues: Dict[str, List[Dict]] = {}
        # Lock for thread safety
        self.lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, worker_id: str, connection_id: str):
        """Connect a new WebSocket client."""
        await websocket.accept()
        
        async with self.lock:
            if worker_id not in self.active_connections:
                self.active_connections[worker_id] = {}
            
            self.active_connections[worker_id][connection_id] = websocket
            self.connection_metadata[connection_id] = {
                'worker_id': worker_id,
                'connected_at': datetime.now().isoformat(),
                'last_heartbeat': datetime.now().isoformat()
            }
            
            # Send any queued messages
            if worker_id in self.message_queues and self.message_queues[worker_id]:
                for message in self.message_queues[worker_id]:
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        logger.error(f"Failed to send queued message: {e}")
                
                # Clear queue after sending
                self.message_queues[worker_id] = []
            
            logger.info(f"WebSocket connected: {worker_id} ({connection_id})")
    
    async def disconnect(self, worker_id: str, connection_id: str):
        """Disconnect a WebSocket client."""
        async with self.lock:
            if worker_id in self.active_connections:
                if connection_id in self.active_connections[worker_id]:
                    del self.active_connections[worker_id][connection_id]
                    
                    if not self.active_connections[worker_id]:
                        del self.active_connections[worker_id]
            
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]
            
            logger.info(f"WebSocket disconnected: {worker_id} ({connection_id})")
    
    async def broadcast(self, message: Dict, exclude_worker_id: str = None):
        """Broadcast message to all connected workers."""
        async with self.lock:
            message['timestamp'] = datetime.now().isoformat()
            
            for worker_id, connections in self.active_connections.items():
                if exclude_worker_id and worker_id == exclude_worker_id:
                    continue
                
                for connection_id, websocket in connections.items():
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        logger.error(f"Failed to broadcast to {worker_id}: {e}")
                        # Remove failed connection
                        await self.disconnect(worker_id, connection_id)
    
    async def send_to_worker(self, worker_id: str, message: Dict):
        """Send message to specific worker."""
        async with self.lock:
            if worker_id in self.active_connections:
                message['timestamp'] = datetime.now().isoformat()
                
                for connection_id, websocket in self.active_connections[worker_id].items():
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        logger.error(f"Failed to send to {worker_id}: {e}")
                        await self.disconnect(worker_id, connection_id)
            else:
                # Worker offline, queue message
                if worker_id not in self.message_queues:
                    self.message_queues[worker_id] = []
                
                self.message_queues[worker_id].append(message)
                
                # Limit queue size
                if len(self.message_queues[worker_id]) > 1000:
                    self.message_queues[worker_id] = self.message_queues[worker_id][-1000:]
                
                logger.info(f"Worker {worker_id} offline, message queued")
    
    async def broadcast_knowledge_event(self, knowledge_event: Dict):
        """Broadcast knowledge event to all workers."""
        message = {
            'type': 'knowledge_broadcast',
            'data': knowledge_event
        }
        
        await self.broadcast(message)
    
    async def broadcast_conflict_event(self, conflict_event: Dict):
        """Broadcast conflict event to relevant workers."""
        message = {
            'type': 'conflict_detected',
            'data': conflict_event
        }
        
        # Send to all workers involved in the conflict
        worker_ids = conflict_event.get('involved_workers', [])
        for worker_id in worker_ids:
            await self.send_to_worker(worker_id, message)
    
    async def handle_heartbeat(self, connection_id: str):
        """Update heartbeat timestamp for a connection."""
        async with self.lock:
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]['last_heartbeat'] = datetime.now().isoformat()
    
    def get_connections_summary(self) -> Dict:
        """Get summary of all connections."""
        with self.lock:
            total_connections = sum(
                len(connections) 
                for connections in self.active_connections.values()
            )
            
            return {
                'total_connections': total_connections,
                'workers_connected': len(self.active_connections),
                'active_workers': list(self.active_connections.keys()),
                'queued_messages': sum(len(q) for q in self.message_queues.values()),
                'connection_details': self.connection_metadata
            }

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

@router.websocket("/ws/{worker_id}/{connection_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    worker_id: str,
    connection_id: str,
    token: Optional[str] = None
):
    """WebSocket endpoint for real-time notifications."""
    # Validate authentication
    if token:
        # In production, validate token properly
        # For now, we'll accept any token
        pass
    
    await websocket_manager.connect(websocket, worker_id, connection_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get('type') == 'heartbeat':
                    await websocket_manager.handle_heartbeat(connection_id)
                
                elif message.get('type') == 'acknowledge':
                    # Handle acknowledgment of received message
                    pass
                    
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from {worker_id}")
                
    except WebSocketDisconnect:
        await websocket_manager.disconnect(worker_id, connection_id)
    except Exception as e:
        logger.error(f"WebSocket error for {worker_id}: {e}")
        await websocket_manager.disconnect(worker_id, connection_id)

@router.get("/ws/connections")
async def get_connections():
    """Get WebSocket connections summary."""
    return websocket_manager.get_connections_summary()

@router.post("/ws/broadcast")
async def broadcast_message(
    message: Dict,
    exclude_worker_id: Optional[str] = None
):
    """Broadcast message to all workers via WebSocket."""
    await websocket_manager.broadcast(message, exclude_worker_id)
    return {"status": "broadcast_sent"}
```

**2.2 Update Knowledge Exchange to Use WebSockets** (`src/openmemory/app/utils/knowledge_exchange.py`)
```python
class KnowledgeExchangeProtocol:
    # Existing methods...
    
    async def broadcast_knowledge(
        self,
        worker_id: str,
        knowledge_type: str,
        content: Union[str, Dict],
        urgency: str = "normal",
        priority: int = 5
    ) -> str:
        """Broadcast knowledge to all workers with WebSocket notification."""
        # Existing broadcasting logic...
        
        # After broadcasting, send WebSocket notification
        try:
            from src.openmemory.app.utils.websocket_server import websocket_manager
            
            # Prepare knowledge event
            knowledge_event = {
                'worker_id': worker_id,
                'knowledge_type': knowledge_type,
                'knowledge_id': knowledge_id,
                'urgency': urgency,
                'priority': priority,
                'timestamp': datetime.now().isoformat()
            }
            
            # Broadcast via WebSocket
            await websocket_manager.broadcast_knowledge_event(knowledge_event)
            
        except Exception as e:
            logger.error(f"Failed to broadcast WebSocket notification: {e}")
            # Don't fail the broadcast if WebSocket fails
        
        return knowledge_id
    
    async def notify_conflict(
        self,
        conflict: ConflictMetadata,
        involved_workers: List[str]
    ):
        """Notify involved workers about detected conflict."""
        try:
            from src.openmemory.app.utils.websocket_server import websocket_manager
            
            conflict_event = {
                'conflict_id': conflict.conflict_id,
                'conflict_type': conflict.conflict_type,
                'involved_workers': involved_workers,
                'similarity_score': conflict.similarity_score,
                'detected_at': conflict.detected_at.isoformat(),
                'resolution_status': conflict.resolution_status
            }
            
            await websocket_manager.broadcast_conflict_event(conflict_event)
            
        except Exception as e:
            logger.error(f"Failed to broadcast conflict notification: {e}")
```

**2.3 Update BaseWorker to Use WebSockets** (`src/openmemory/app/agents/base_worker.py`)
```python
class BaseWorker:
    # Existing methods...
    
    def __init__(self, worker_id: str, config: Optional[Dict] = None):
        # ... existing initialization ...
        self.websocket_url = config.get('websocket_url', 'ws://localhost:8000/ws')
        self.websocket_connection_id = str(uuid.uuid4())
        self.websocket_client = None
        self.websocket_connected = False
        self.websocket_reconnect_delay = 5
        self.websocket_max_reconnect_attempts = 10
        self.websocket_reconnect_attempts = 0
    
    async def start(self):
        """Start worker with WebSocket connection."""
        await super().start()
        
        # Connect to WebSocket server
        await self._connect_websocket()
    
    async def _connect_websocket(self):
        """Connect to WebSocket server for real-time notifications."""
        try:
            import websockets
            
            url = f"{self.websocket_url}/{self.worker_id}/{self.websocket_connection_id}"
            
            # In production, include authentication token
            # url += f"?token={self._get_auth_token()}"
            
            self.websocket_client = await websockets.connect(url)
            self.websocket_connected = True
            self.websocket_reconnect_attempts = 0
            
            logger.info(f"WebSocket connected for worker {self.worker_id}")
            
            # Start listening for messages
            asyncio.create_task(self._listen_websocket())
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            await self._schedule_reconnect()
    
    async def _listen_websocket(self):
        """Listen for WebSocket messages."""
        try:
            async for message in self.websocket_client:
                try:
                    data = json.loads(message)
                    await self._handle_websocket_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from WebSocket: {message}")
        except Exception as e:
            logger.error(f"WebSocket listening error: {e}")
            self.websocket_connected = False
            await self._schedule_reconnect()
    
    async def _handle_websocket_message(self, message: Dict):
        """Handle incoming WebSocket messages."""
        msg_type = message.get('type')
        data = message.get('data', {})
        
        if msg_type == 'knowledge_broadcast':
            # Handle knowledge broadcast from other workers
            await self._handle_knowledge_broadcast(data)
        
        elif msg_type == 'conflict_detected':
            # Handle conflict notification
            await self._handle_conflict_notification(data)
        
        elif msg_type == 'heartbeat':
            # Send heartbeat acknowledgment
            await self.websocket_client.send(json.dumps({
                'type': 'acknowledge',
                'timestamp': datetime.now().isoformat()
            }))
    
    async def _handle_knowledge_broadcast(self, knowledge_event: Dict):
        """Handle knowledge broadcast from other workers."""
        logger.info(f"Received knowledge broadcast: {knowledge_event}")
        
        # Check if this worker should process this knowledge
        knowledge_type = knowledge_event.get('knowledge_type')
        if knowledge_type in self.subscribed_knowledge_types:
            # Process the knowledge
            try:
                await self.process_received_knowledge(
                    knowledge_type=knowledge_type,
                    content=f"Broadcast from {knowledge_event.get('worker_id')}",
                    source_id=knowledge_event.get('knowledge_id'),
                    metadata=knowledge_event
                )
            except Exception as e:
                logger.error(f"Failed to process broadcast knowledge: {e}")
    
    async def _handle_conflict_notification(self, conflict_event: Dict):
        """Handle conflict notification from other workers."""
        logger.warning(f"Conflict detected: {conflict_event}")
        
        # Update worker statistics
        if hasattr(self, 'stats'):
            self.stats['conflicts_detected'] = self.stats.get('conflicts_detected', 0) + 1
        
        # Check if this worker is involved
        if self.worker_id in conflict_event.get('involved_workers', []):
            # Handle being involved in a conflict
            await self._handle_involved_in_conflict(conflict_event)
    
    async def _handle_involved_in_conflict(self, conflict_event: Dict):
        """Handle when this worker is involved in a conflict."""
        logger.info(f"Worker {self.worker_id} involved in conflict {conflict_event.get('conflict_id')}")
        
        # Can implement custom logic here, e.g., adjust behavior
        # or notify external systems
    
    async def _schedule_reconnect(self):
        """Schedule WebSocket reconnection."""
        self.websocket_reconnect_attempts += 1
        
        if self.websocket_reconnect_attempts > self.websocket_max_reconnect_attempts:
            logger.error(f"Max WebSocket reconnection attempts reached for {self.worker_id}")
            return
        
        logger.info(
            f"WebSocket reconnection attempt {self.websocket_reconnect_attempts} "
            f"for {self.worker_id} in {self.websocket_reconnect_delay}s"
        )
        
        await asyncio.sleep(self.websocket_reconnect_delay)
        
        # Exponential backoff
        self.websocket_reconnect_delay = min(
            self.websocket_reconnect_delay * 2,
            60  # Max 60 seconds
        )
        
        await self._connect_websocket()
    
    async def send_heartbeat(self):
        """Send heartbeat to WebSocket server."""
        if self.websocket_connected and self.websocket_client:
            try:
                await self.websocket_client.send(json.dumps({
                    'type': 'heartbeat',
                    'timestamp': datetime.now().isoformat()
                }))
            except Exception as e:
                logger.error(f"Failed to send heartbeat: {e}")
    
    async def stop(self):
        """Stop worker and WebSocket connection."""
        if self.websocket_client:
            try:
                await self.websocket_client.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        
        await super().stop()
```

---

### 3. Advanced Monitoring & Alerting

#### Files to Create/Modify:

**3.1 Monitoring Metrics** (`src/openmemory/app/utils/monitoring.py`)
```python
"""
Advanced monitoring and alerting system.

Features:
- Comprehensive metrics collection
- Health checks
- Alerting for anomalies
- Performance tracking
- Dashboard integration
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
import statistics
import asyncio

@dataclass
class MetricsSnapshot:
    """Snapshot of metrics at a point in time."""
    timestamp: datetime
    worker_id: str
    metrics: Dict
    alerts: List[Dict]

class MetricsCollector:
    """Collect and analyze worker metrics."""
    
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.metrics_history = deque(maxlen=1000)  # Keep last 1000 snapshots
        self.alert_rules = self._init_alert_rules()
        self.anomaly_detection_window = 100  # Number of snapshots for baseline
    
    def _init_alert_rules(self) -> Dict:
        """Initialize alert rules."""
        return {
            'knowledge_broadcast_rate': {
                'threshold': 100,  # per minute
                'window': 60,  # seconds
                'severity': 'warning'
            },
            'conflict_rate': {
                'threshold': 10,  # per minute
                'window': 60,
                'severity': 'critical'
            },
            'knowledge_reception_delay': {
                'threshold': 5000,  # milliseconds
                'window': 60,
                'severity': 'warning'
            },
            'queue_size': {
                'threshold': 1000,
                'window': 60,
                'severity': 'warning'
            },
            'error_rate': {
                'threshold': 0.05,  # 5% error rate
                'window': 60,
                'severity': 'critical'
            }
        }
    
    def record_metric(self, metric_name: str, value: float, tags: Optional[Dict] = None):
        """Record a metric value."""
        snapshot = MetricsSnapshot(
            timestamp=datetime.now(),
            worker_id=self.worker_id,
            metrics={
                metric_name: value,
                **(tags or {})
            },
            alerts=[]
        )
        
        self.metrics_history.append(snapshot)
        
        # Check for alerts
        self._check_alerts(snapshot)
    
    def _check_alerts(self, snapshot: MetricsSnapshot):
        """Check metrics against alert rules."""
        for rule_name, rule in self.alert_rules.items():
            if rule_name in snapshot.metrics:
                value = snapshot.metrics[rule_name]
                
                if self._evaluate_rule(rule_name, value, rule):
                    alert = {
                        'rule': rule_name,
                        'value': value,
                        'threshold': rule['threshold'],
                        'severity': rule['severity'],
                        'timestamp': snapshot.timestamp.isoformat(),
                        'worker_id': self.worker_id
                    }
                    
                    snapshot.alerts.append(alert)
                    
                    # Log alert
                    if rule['severity'] == 'critical':
                        logger.critical(f"CRITICAL ALERT: {rule_name} = {value}")
                    else:
                        logger.warning(f"ALERT: {rule_name} = {value}")
    
    def _evaluate_rule(self, rule_name: str, value: float, rule: Dict) -> bool:
        """Evaluate if a rule should trigger an alert."""
        # Get recent values for trend analysis
        recent_values = self._get_recent_values(rule_name, rule['window'])
        
        if not recent_values:
            return False
        
        # Check threshold
        if value > rule['threshold']:
            return True
        
        # Check for anomaly (sudden spike)
        if len(recent_values) >= 10:
            mean = statistics.mean(recent_values)
            std = statistics.stdev(recent_values) if len(recent_values) > 1 else 0
            
            if std > 0 and abs(value - mean) > 2 * std:
                return True
        
        return False
    
    def _get_recent_values(self, metric_name: str, window_seconds: int) -> List[float]:
        """Get recent values for a metric."""
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        values = []
        
        for snapshot in reversed(self.metrics_history):
            if snapshot.timestamp < cutoff:
                break
            
            if metric_name in snapshot.metrics:
                values.append(snapshot.metrics[metric_name])
        
        return values
    
    def get_metrics_summary(self) -> Dict:
        """Get summary of current metrics."""
        if not self.metrics_history:
            return {}
        
        latest = list(self.metrics_history)[-1]
        
        # Calculate rates
        recent_minutes = 5
        cutoff = datetime.now() - timedelta(minutes=recent_minutes)
        
        broadcast_count = sum(
            1 for m in self.metrics_history 
            if m.timestamp >= cutoff and 'knowledge_broadcast_rate' in m.metrics
        )
        
        conflict_count = sum(
            1 for m in self.metrics_history 
            if m.timestamp >= cutoff and 'conflict_rate' in m.metrics
        )
        
        return {
            'worker_id': self.worker_id,
            'timestamp': latest.timestamp.isoformat(),
            'current_metrics': latest.metrics,
            'recent_activity': {
                'knowledge_broadcasts_last_5min': broadcast_count,
                'conflicts_last_5min': conflict_count,
                'total_snapshots': len(self.metrics_history)
            },
            'alert_summary': self._get_alert_summary()
        }
    
    def _get_alert_summary(self) -> Dict:
        """Get summary of recent alerts."""
        alerts_last_hour = []
        
        for snapshot in reversed(self.metrics_history):
            if snapshot.timestamp < datetime.now() - timedelta(hours=1):
                break
            
            alerts_last_hour.extend(snapshot.alerts)
        
        return {
            'total_last_hour': len(alerts_last_hour),
            'by_severity': {
                'critical': sum(1 for a in alerts_last_hour if a['severity'] == 'critical'),
                'warning': sum(1 for a in alerts_last_hour if a['severity'] == 'warning')
            },
            'recent_alerts': alerts_last_hour[-10:]  # Last 10 alerts
        }

class HealthChecker:
    """Health check system for workers."""
    
    def __init__(self):
        self.worker_health = {}  # {worker_id: health_status}
        self.check_interval = 30  # seconds
    
    async def check_worker_health(self, worker) -> Dict:
        """Check health of a worker."""
        checks = {}
        
        # Check database connection
        try:
            if worker.db_session:
                worker.db_session.execute("SELECT 1")
                checks['database'] = {'status': 'healthy', 'latency_ms': 0}
        except Exception as e:
            checks['database'] = {'status': 'unhealthy', 'error': str(e)}
        
        # Check WebSocket connection
        if hasattr(worker, 'websocket_connected'):
            checks['websocket'] = {
                'status': 'connected' if worker.websocket_connected else 'disconnected',
                'reconnect_attempts': getattr(worker, 'websocket_reconnect_attempts', 0)
            }
        
        # Check knowledge exchange
        if hasattr(worker, 'last_broadcast_time'):
            time_since_broadcast = (
                datetime.now() - worker.last_broadcast_time
            ).total_seconds()
            
            checks['knowledge_exchange'] = {
                'status': 'active' if time_since_broadcast < 300 else 'idle',
                'last_broadcast': worker.last_broadcast_time.isoformat(),
                'time_since_broadcast_seconds': time_since_broadcast
            }
        
        # Overall health
        healthy_checks = sum(1 for c in checks.values() if c.get('status') == 'healthy')
        total_checks = len(checks)
        
        overall_status = 'healthy'
        if healthy_checks < total_checks * 0.8:  # 80% threshold
            overall_status = 'degraded'
        if healthy_checks == 0:
            overall_status = 'unhealthy'
        
        return {
            'worker_id': worker.worker_id,
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status,
            'checks': checks
        }

# API endpoints for monitoring
@router.get("/metrics/{worker_id}")
async def get_worker_metrics(worker_id: str):
    """Get metrics for a specific worker."""
    # This would integrate with your existing metrics system
    return {
        "worker_id": worker_id,
        "metrics": {
            "knowledge_broadcast_rate": 45.2,
            "knowledge_reception_delay_ms": 123.4,
            "conflict_rate": 2.1,
            "queue_size": 15,
            "error_rate": 0.01
        },
        "timestamp": datetime.now().isoformat()
    }

@router.get("/health")
async def health_check():
    """Overall system health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "healthy",
            "websocket": "healthy",
            "api": "healthy"
        }
    }

@router.get("/alerts")
async def get_alerts(severity: Optional[str] = None, limit: int = 50):
    """Get system alerts."""
    # This would query the alert database
    return {
        "alerts": [],
        "total": 0,
        "timestamp": datetime.now().isoformat()
    }
```

**3.2 Update BaseWorker to Use Monitoring** (`src/openmemory/app/agents/base_worker.py`)
```python
class BaseWorker:
    # Existing methods...
    
    def __init__(self, worker_id: str, config: Optional[Dict] = None):
        # ... existing initialization ...
        
        # Initialize monitoring
        self.metrics_collector = MetricsCollector(worker_id)
        self.health_checker = HealthChecker()
        self.last_broadcast_time = None
        self.stats = {
            'knowledge_broadcasts': 0,
            'knowledge_received': 0,
            'conflicts_detected': 0,
            'errors': 0,
            'processing_time_ms': 0
        }
        
        # Performance tracking
        self.processing_times = deque(maxlen=100)
    
    async def broadcast_knowledge(
        self,
        knowledge_type: str,
        content: Union[str, Dict],
        urgency: str = "normal",
        priority: int = 5
    ) -> str:
        """Broadcast knowledge with metrics tracking."""
        start_time = datetime.now()
        
        try:
            knowledge_id = await super().broadcast_knowledge(
                knowledge_type, content, urgency, priority
            )
            
            # Record metrics
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics_collector.record_metric(
                'knowledge_broadcast_rate', 1, {'type': knowledge_type}
            )
            self.metrics_collector.record_metric(
                'processing_time_ms', processing_time
            )
            
            # Update statistics
            self.stats['knowledge_broadcasts'] += 1
            self.stats['processing_time_ms'] += processing_time
            self.processing_times.append(processing_time)
            
            self.last_broadcast_time = datetime.now()
            
            return knowledge_id
            
        except Exception as e:
            self.metrics_collector.record_metric('error_rate', 1)
            self.stats['errors'] += 1
            raise
    
    async def process_received_knowledge(
        self,
        knowledge_type: str,
        content: Union[str, Dict],
        source_id: str,
        metadata: Optional[Dict] = None
    ):
        """Process received knowledge with metrics tracking."""
        start_time = datetime.now()
        
        try:
            await super().process_received_knowledge(
                knowledge_type, content, source_id, metadata
            )
            
            # Record metrics
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics_collector.record_metric(
                'knowledge_reception_delay_ms', processing_time
            )
            
            self.stats['knowledge_received'] += 1
            self.processing_times.append(processing_time)
            
        except Exception as e:
            self.metrics_collector.record_metric('error_rate', 1)
            self.stats['errors'] += 1
            raise
    
    async def get_health_status(self) -> Dict:
        """Get worker health status."""
        if self.health_checker:
            return await self.health_checker.check_worker_health(self)
        return {"worker_id": self.worker_id, "status": "unknown"}
    
    async def get_metrics(self) -> Dict:
        """Get worker metrics."""
        return {
            'worker_id': self.worker_id,
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics_collector.get_metrics_summary(),
            'statistics': self.stats,
            'performance': {
                'avg_processing_time_ms': statistics.mean(self.processing_times) 
                if self.processing_times else 0,
                'max_processing_time_ms': max(self.processing_times) 
                if self.processing_times else 0,
                'min_processing_time_ms': min(self.processing_times) 
                if self.processing_times else 0
            }
        }
```

---

### 4. Performance Optimization

#### Files to Create/Modify:

**4.1 Batch Processing** (`src/openmemory/app/utils/batch_processor.py`)
```python
"""
Batch processing and caching for performance optimization.

Features:
- Batch knowledge processing
- Query caching
- Connection pooling
- Memory optimization
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import hashlib

class BatchProcessor:
    """Process knowledge in batches for better performance."""
    
    def __init__(self, batch_size: int = 50, flush_interval: int = 5):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.batches: Dict[str, List] = defaultdict(list)
        self.lock = asyncio.Lock()
        self.last_flush = datetime.now()
        
        # Start background flush task
        self._flush_task = asyncio.create_task(self._periodic_flush())
    
    async def add_to_batch(self, batch_type: str, item: Dict):
        """Add item to batch for processing."""
        async with self.lock:
            self.batches[batch_type].append(item)
            
            # Flush if batch is full
            if len(self.batches[batch_type]) >= self.batch_size:
                await self._flush_batch(batch_type)
    
    async def _periodic_flush(self):
        """Periodically flush all batches."""
        while True:
            await asyncio.sleep(self.flush_interval)
            
            async with self.lock:
                if datetime.now() - self.last_flush > timedelta(seconds=self.flush_interval):
                    await self._flush_all_batches()
    
    async def _flush_batch(self, batch_type: str):
        """Flush a specific batch."""
        if batch_type not in self.batches or not self.batches[batch_type]:
            return
        
        items = self.batches[batch_type][:]
        self.batches[batch_type].clear()
        
        # Process batch
        try:
            if batch_type == 'knowledge_broadcast':
                await self._process_knowledge_batch(items)
            elif batch_type == 'knowledge_reception':
                await self._process_reception_batch(items)
            else:
                logger.warning(f"Unknown batch type: {batch_type}")
        except Exception as e:
            logger.error(f"Failed to process batch {batch_type}: {e}")
        
        self.last_flush = datetime.now()
    
    async def _flush_all_batches(self):
        """Flush all batches."""
        for batch_type in list(self.batches.keys()):
            await self._flush_batch(batch_type)
    
    async def _process_knowledge_batch(self, items: List[Dict]):
        """Process batch of knowledge broadcasts."""
        # Group by worker and type for efficient processing
        grouped = defaultdict(list)
        
        for item in items:
            key = f"{item['worker_id']}_{item['knowledge_type']}"
            grouped[key].append(item)
        
        # Process each group
        for key, group_items in grouped.items():
            # In production, use bulk insert/update
            logger.info(f"Processing batch of {len(group_items)} knowledge items for {key}")
            
            # Example: Bulk database operation
            # await self._bulk_insert_knowledge(group_items)
    
    async def _process_reception_batch(self, items: List[Dict]):
        """Process batch of knowledge receptions."""
        # Similar to broadcast batch processing
        logger.info(f"Processing batch of {len(items)} knowledge receptions")
    
    async def flush(self):
        """Manually flush all batches."""
        async with self.lock:
            await self._flush_all_batches()
    
    async def stop(self):
        """Stop batch processor."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining items
        await self.flush()

class QueryCache:
    """Caching layer for frequent queries."""
    
    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self.cache = {}  # {key: (value, timestamp)}
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[any]:
        """Get cached value."""
        if key not in self.cache:
            self.misses += 1
            return None
        
        value, timestamp = self.cache[key]
        
        # Check if cache is still valid
        if datetime.now() - timestamp > timedelta(seconds=self.ttl_seconds):
            del self.cache[key]
            self.misses += 1
            return None
        
        self.hits += 1
        return value
    
    def set(self, key: str, value: any):
        """Set cached value."""
        self.cache[key] = (value, datetime.now())
        
        # Limit cache size
        if len(self.cache) > 1000:
            # Remove oldest entries
            oldest_keys = sorted(
                self.cache.keys(),
                key=lambda k: self.cache[k][1]
            )[:100]
            
            for k in oldest_keys:
                del self.cache[k]
    
    def delete(self, key: str):
        """Delete cached value."""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        """Clear all cached values."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        hit_rate = self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        
        return {
            'size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'ttl_seconds': self.ttl_seconds
        }

# Create global instances
batch_processor = BatchProcessor()
query_cache = QueryCache()

# Update BaseWorker to use optimizations
class BaseWorker:
    # ... existing methods ...
    
    def __init__(self, worker_id: str, config: Optional[Dict] = None):
        # ... existing initialization ...
        
        # Performance optimization
        self.batch_processor = None
        self.query_cache = None
        self.use_batching = config.get('use_batching', True)
        self.use_caching = config.get('use_caching', True)
    
    async def start(self):
        """Start worker with performance optimizations."""
        await super().start()
        
        # Initialize batch processor
        if self.use_batching:
            from src.openmemory.app.utils.batch_processor import batch_processor
            self.batch_processor = batch_processor
        
        # Initialize query cache
        if self.use_caching:
            from src.openmemory.app.utils.batch_processor import query_cache
            self.query_cache = query_cache
        
        logger.info(f"Worker {self.worker_id} started with optimizations: batching={self.use_batching}, caching={self.use_caching}")
    
    async def broadcast_knowledge(
        self,
        knowledge_type: str,
        content: Union[str, Dict],
        urgency: str = "normal",
        priority: int = 5
    ) -> str:
        """Broadcast knowledge with batch optimization."""
        if self.batch_processor and self.use_batching:
            # Add to batch instead of immediate processing
            batch_item = {
                'worker_id': self.worker_id,
                'knowledge_type': knowledge_type,
                'content': content,
                'urgency': urgency,
                'priority': priority,
                'timestamp': datetime.now()
            }
            
            await self.batch_processor.add_to_batch('knowledge_broadcast', batch_item)
            
            # Return a placeholder ID
            return f"batch_{hashlib.md5(str(batch_item).encode()).hexdigest()[:8]}"
        else:
            # Use immediate processing
            return await super().broadcast_knowledge(
                knowledge_type, content, urgency, priority
            )
    
    async def query_knowledge(self, **kwargs) -> List[Dict]:
        """Query knowledge with cache optimization."""
        if self.query_cache and self.use_caching:
            # Create cache key from query parameters
            cache_key = f"query_{self.worker_id}_{hashlib.md5(str(sorted(kwargs.items())).encode()).hexdigest()}"
            
            cached = self.query_cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for query: {kwargs}")
                return cached
        
        # Execute query
        result = await super().query_knowledge(**kwargs)
        
        # Cache result
        if self.query_cache and self.use_caching:
            cache_key = f"query_{self.worker_id}_{hashlib.md5(str(sorted(kwargs.items())).encode()).hexdigest()}"
            self.query_cache.set(cache_key, result)
        
        return result
```

---

## Implementation Timeline

### Day 1: Conflict Resolution System
- [ ] Create conflict detection module (`conflict_resolver.py`)
- [ ] Add conflict resolution to BaseWorker
- [ ] Create database schema updates
- [ ] Add API endpoints for conflict management
- [ ] Write conflict resolution tests
- [ ] Test conflict scenarios

### Day 2: WebSocket Notification System
- [ ] Create WebSocket server (`websocket_server.py`)
- [ ] Integrate WebSockets with knowledge exchange
- [ ] Update BaseWorker with WebSocket client
- [ ] Add WebSocket API endpoints
- [ ] Write WebSocket integration tests
- [ ] Test real-time notifications

### Day 3: Advanced Monitoring & Performance
- [ ] Create monitoring metrics module (`monitoring.py`)
- [ ] Add health check system
- [ ] Implement alerting system
- [ ] Create batch processing module (`batch_processor.py`)
- [ ] Add query caching
- [ ] Write monitoring tests
- [ ] Test performance optimization

### Day 4: Integration & Testing
- [ ] Integrate all Phase 4 components
- [ ] Run full integration tests
- [ ] Performance testing and profiling
- [ ] Documentation and cleanup
- [ ] Final validation

---

## Testing Strategy

### Conflict Resolution Tests
- [ ] Test duplicate detection
- [ ] Test contradiction detection
- [ ] Test merge strategy
- [ ] Test prioritize strategy
- [ ] Test discard strategy
- [ ] Test manual resolution
- [ ] Test conflict resolution API

### WebSocket Tests
- [ ] Test connection establishment
- [ ] Test message broadcasting
- [ ] Test worker-specific messaging
- [ ] Test connection recovery
- [ ] Test authentication
- [ ] Test message queuing for offline workers

### Monitoring Tests
- [ ] Test metrics collection
- [ ] Test alert rules
- [ ] Test health checks
- [ ] Test anomaly detection
- [ ] Test dashboard integration

### Performance Tests
- [ ] Test batch processing
- [ ] Test cache hit/miss rates
- [ ] Test throughput with optimizations
- [ ] Test memory usage
- [ ] Test database query optimization

---

## Success Criteria

### Conflict Resolution
- [ ] 100% conflict detection accuracy for known patterns
- [ ] < 100ms conflict detection latency
- [ ] Successful resolution in > 95% of auto-resolved conflicts
- [ ] Proper audit trail for all resolutions

### WebSocket Notifications
- [ ] < 100ms notification latency
- [ ] 99.9% connection reliability
- [ ] Proper handling of offline workers
- [ ] Secure authentication

### Monitoring
- [ ] Metrics collection with < 1% overhead
- [ ] Health checks with < 50ms response time
- [ ] Alert accuracy > 95%
- [ ] Dashboard updates < 1 second

### Performance
- [ ] 2x throughput improvement with batching
- [ ] 3x query speed improvement with caching
- [ ] Memory usage < 2x baseline
- [ ] Database queries reduced by 50%

---

## Risk Mitigation

### Technical Risks
- **WebSocket scalability**: Implement connection pooling and horizontal scaling
- **Cache consistency**: Use cache invalidation strategies
- **Conflict resolution complexity**: Start with simple strategies, add complexity gradually

### Operational Risks
- **Production deployment**: Deploy in phases with feature flags
- **Monitoring overhead**: Implement sampling for high-volume metrics
- **Database load**: Use read replicas for queries, connection pooling

---

## Deployment Checklist

- [ ] Feature flags for each Phase 4 component
- [ ] Rollback procedures documented
- [ ] Monitoring dashboards created
- [ ] Alert thresholds configured
- [ ] Performance baselines established
- [ ] Documentation updated
- [ ] Team training completed

---

## Next Steps

After completing Phase 4, the system will have:
1. ✅ Full knowledge sharing (Phases 1-3)
2. ✅ Conflict resolution and advanced features (Phase 4)
3. ⏳ Experimental strategies (Feature 2)
4. ⏳ Prompt management UI (Feature 3)

The foundation will be ready for enterprise deployment with production-grade reliability, monitoring, and performance.

---

**Ready to implement Phase 4?**  
Let me know when you'd like to start, and I'll begin with the conflict resolution system.
