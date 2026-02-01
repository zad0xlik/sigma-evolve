"""
Cross-Worker Knowledge Exchange Protocol

Direct knowledge sharing between SIGMA agents with validation and freshness tracking.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
import math

from sqlalchemy.orm import Session

from ..models import KnowledgeExchange, WorkerKnowledgeState, KnowledgeValidation
from ..database import get_db

logger = logging.getLogger("sigma.knowledge_exchange")


def utc_now() -> str:
    """Get current UTC timestamp as ISO string"""
    return datetime.now(timezone.utc).isoformat()


class KnowledgeValidator:
    """Validate incoming knowledge before processing"""
    
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
            'pattern_evolution': KnowledgeValidator._validate_pattern_evolution,
            'proposal_quality': KnowledgeValidator._validate_proposal_quality,
            'experiment_result': KnowledgeValidator._validate_experiment_result,
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
        required = ['proposal_id', 'action', 'confidence', 'committee_scores', 'risk_assessment']
        missing = [field for field in required if field not in payload]
        
        if missing:
            return False, f"Missing required fields: {missing}"
        
        if not isinstance(payload['confidence'], (int, float)):
            return False, "Confidence must be numeric"
        
        if not 0 <= payload['confidence'] <= 1:
            return False, "Confidence must be between 0 and 1"
        
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
    
    @staticmethod
    def _validate_pattern_evolution(payload: Dict, source_worker: str) -> Tuple[bool, str]:
        """Validate pattern evolution knowledge"""
        required = ['pattern_name', 'old_pattern', 'new_pattern', 'evolution_type']
        missing = [field for field in required if field not in payload]
        
        if missing:
            return False, f"Missing required fields: {missing}"
        
        if not isinstance(payload['evolution_type'], str):
            return False, "Evolution type must be a string"
        
        return True, ""
    
    @staticmethod
    def _validate_proposal_quality(payload: Dict, source_worker: str) -> Tuple[bool, str]:
        """Validate proposal quality knowledge"""
        required = ['proposal_id', 'quality_score', 'factors']
        missing = [field for field in required if field not in payload]
        
        if missing:
            return False, f"Missing required fields: {missing}"
        
        if not isinstance(payload['quality_score'], (int, float)):
            return False, "Quality score must be numeric"
        
        if not 0 <= payload['quality_score'] <= 1:
            return False, "Quality score must be between 0 and 1"
        
        return True, ""
    
    @staticmethod
    def _validate_experiment_result(payload: Dict, source_worker: str) -> Tuple[bool, str]:
        """Validate experiment result knowledge"""
        required = ['experiment_id', 'metrics', 'success']
        missing = [field for field in required if field not in payload]
        
        if missing:
            return False, f"Missing required fields: {missing}"
        
        if not isinstance(payload['success'], bool):
            return False, "Success must be a boolean"
        
        return True, ""


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
        timestamp_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        age_seconds = (datetime.now(timezone.utc) - timestamp_dt).total_seconds()
        
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


class KnowledgeExchangeProtocol:
    """Direct knowledge sharing between workers"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.exchange_queue = asyncio.Queue()
        self.freshness_tracker = KnowledgeFreshnessTracker()
        self.validator = KnowledgeValidator()
        
        # Knowledge type registry with propagation strategies
        self.knowledge_types = {
            'risk_pattern': {
                'workers': ['think', 'learning'],
                'persistence': 'long',
                'validation': 'required',
                'propagation': 'broadcast'
            },
            'decision_outcome': {
                'workers': ['think', 'learning', 'dream'],
                'persistence': 'medium',
                'validation': 'required',
                'propagation': 'multicast'
            },
            'successful_fix': {
                'workers': ['dream', 'learning', 'analysis'],
                'persistence': 'long',
                'validation': 'required',
                'propagation': 'broadcast'
            },
            'issue_pattern': {
                'workers': ['analysis', 'think'],
                'persistence': 'medium',
                'validation': 'optional',
                'propagation': 'multicast'
            },
            'pattern_evolution': {
                'workers': ['learning', 'dream'],
                'persistence': 'long',
                'validation': 'required',
                'propagation': 'broadcast'
            },
            'context_enrichment': {
                'workers': ['recall', 'think', 'dream'],
                'persistence': 'short',
                'validation': 'optional',
                'propagation': 'multicast'
            },
            'proposal_quality': {
                'workers': ['dream', 'think'],
                'persistence': 'medium',
                'validation': 'required',
                'propagation': 'broadcast'
            },
            'experiment_result': {
                'workers': ['all'],
                'persistence': 'long',
                'validation': 'required',
                'propagation': 'broadcast'
            }
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
        # Store in database for persistence
        await self._store_in_database(worker_name, knowledge_type, payload, urgency)
        
        # Broadcast to interested workers
        interested_workers = self._get_interested_workers(knowledge_type)
        
        for target_worker in interested_workers:
            if target_worker != worker_name:
                await self._notify_worker(
                    target_worker, 
                    worker_name, 
                    knowledge_type, 
                    payload,
                    urgency
                )
    
    async def _store_in_database(
        self, 
        worker_name: str, 
        knowledge_type: str, 
        payload: Dict,
        urgency: str
    ):
        """Store knowledge in database with metadata"""
        
        # Validate knowledge if required
        validation_required = self.knowledge_types.get(knowledge_type, {}).get('validation') == 'required'
        is_valid = True
        
        if validation_required:
            is_valid, error_message = self.validator.validate_knowledge(
                knowledge_type, payload, worker_name
            )
            
            if not is_valid:
                logger.warning(
                    f"Knowledge validation failed for {knowledge_type} from {worker_name}: {error_message}"
                )
        
        # Calculate freshness score
        freshness_score = 1.0  # Fresh by default
        
        if 'confidence' in payload:
            freshness_score = payload['confidence']
        
        if 'relevance' in payload:
            freshness_score = max(freshness_score, payload['relevance'])
        
        # Create metadata
        metadata = {
            "source_worker": worker_name,
            "knowledge_type": knowledge_type,
            "timestamp": utc_now(),
            "confidence": payload.get('confidence', 0.5),
            "urgency": urgency,
            "workers_exposed": [worker_name],
            "is_valid": is_valid,
            "validation_required": validation_required
        }
        
        # Store in database
        try:
            exchange = KnowledgeExchange(
                source_worker=worker_name,
                target_worker=None,  # None = broadcast to all interested workers
                knowledge_type=knowledge_type,
                knowledge_data=payload,
                metadata_=metadata,
                freshness_score=freshness_score,
                validation_status='valid' if is_valid else 'invalid',
                created_at=datetime.now(timezone.utc),
                processed_at=None
            )
            
            self.db.add(exchange)
            self.db.commit()
            
            logger.info(
                f"Stored knowledge exchange: {worker_name} -> {knowledge_type} "
                f"(id: {exchange.exchange_id}, freshness: {freshness_score:.2f})"
            )
            
        except Exception as e:
            logger.error(f"Failed to store knowledge exchange: {e}")
            self.db.rollback()
    
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
            'experiment_result': ['all'],
        }
        
        return interest_map.get(knowledge_type, [])
    
    async def _notify_worker(
        self, 
        target_worker: str, 
        source_worker: str, 
        knowledge_type: str, 
        payload: Dict,
        urgency: str
    ):
        """Notify target worker of new knowledge"""
        notification = {
            "type": "knowledge_update",
            "source": source_worker,
            "knowledge_type": knowledge_type,
            "payload": payload,
            "urgency": urgency,
            "timestamp": utc_now()
        }
        
        # Store notification in worker-specific queue
        await self.exchange_queue.put((target_worker, notification))
        
        logger.info(
            f"Knowledge broadcast: {source_worker} → {target_worker} "
            f"({knowledge_type}, urgency: {urgency})"
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
    
    async def query_knowledge(
        self,
        worker_name: str,
        knowledge_type: Optional[str] = None,
        limit: int = 10,
        min_freshness: float = 0.0
    ) -> List[Dict]:
        """Query knowledge from database"""
        try:
            query = self.db.query(KnowledgeExchange)
            
            # Filter by worker if specified
            if worker_name:
                # Get knowledge targeting this worker or broadcast to all
                query = query.filter(
                    (KnowledgeExchange.target_worker == worker_name) |
                    (KnowledgeExchange.target_worker == None)
                )
            
            # Filter by knowledge type
            if knowledge_type:
                query = query.filter(KnowledgeExchange.knowledge_type == knowledge_type)
            
            # Filter by freshness
            if min_freshness > 0:
                query = query.filter(KnowledgeExchange.freshness_score >= min_freshness)
            
            # Order by freshness and recency
            query = query.order_by(
                KnowledgeExchange.freshness_score.desc(),
                KnowledgeExchange.created_at.desc()
            )
            
            # Limit results
            exchanges = query.limit(limit).all()
            
            # Format results
            results = []
            for exchange in exchanges:
                result = {
                    "exchange_id": exchange.exchange_id,
                    "source_worker": exchange.source_worker,
                    "knowledge_type": exchange.knowledge_type,
                    "payload": exchange.knowledge_data,
                    "freshness_score": exchange.freshness_score,
                    "metadata": exchange.metadata_,
                    "created_at": exchange.created_at.isoformat() if exchange.created_at else None,
                    "processed_at": exchange.processed_at.isoformat() if exchange.processed_at else None
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to query knowledge: {e}")
            return []
    
    async def validate_received_knowledge(
        self,
        exchange_id: int,
        validator_worker: str,
        is_valid: bool,
        validation_score: float,
        feedback: Optional[str] = None
    ):
        """Validate received knowledge and store validation result"""
        try:
            # Get exchange
            exchange = self.db.query(KnowledgeExchange).get(exchange_id)
            if not exchange:
                logger.warning(f"Exchange {exchange_id} not found")
                return
            
            # Store validation
            validation = KnowledgeValidation(
                exchange_id=exchange_id,
                validator_worker=validator_worker,
                is_valid=is_valid,
                validation_score=validation_score,
                feedback=feedback,
                created_at=datetime.now(timezone.utc)
            )
            
            self.db.add(validation)
            
            # Update exchange validation status
            if is_valid:
                exchange.validation_status = 'validated'
            else:
                exchange.validation_status = 'invalid'
            
            self.db.commit()
            
            logger.info(
                f"Knowledge validated by {validator_worker}: "
                f"exchange_id={exchange_id}, valid={is_valid}, score={validation_score:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Failed to validate knowledge: {e}")
            self.db.rollback()
    
    async def update_worker_knowledge_state(
        self,
        worker_name: str,
        received_knowledge: Optional[List[Dict]] = None,
        broadcast_knowledge: Optional[List[Dict]] = None
    ):
        """Update worker's knowledge state"""
        try:
            # Get or create worker state
            state = self.db.query(WorkerKnowledgeState).get(worker_name)
            
            if not state:
                state = WorkerKnowledgeState(
                    worker_name=worker_name,
                    knowledge_snapshot={},
                    exchange_count=0,
                    received_knowledge=[],
                    broadcast_knowledge=[],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                self.db.add(state)
            
            # Update state
            state.last_exchange = datetime.now(timezone.utc)
            state.exchange_count += 1
            
            if received_knowledge:
                current = state.received_knowledge or []
                state.received_knowledge = current + received_knowledge[-10:]  # Keep last 10
            
            if broadcast_knowledge:
                current = state.broadcast_knowledge or []
                state.broadcast_knowledge = current + broadcast_knowledge[-10:]  # Keep last 10
            
            state.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            
            logger.debug(f"Updated knowledge state for {worker_name}")
            
        except Exception as e:
            logger.error(f"Failed to update worker knowledge state: {e}")
            self.db.rollback()
    
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
