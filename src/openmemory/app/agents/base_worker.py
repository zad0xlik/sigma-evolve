"""
Base Worker Class

Foundation for all SIGMA agent workers with built-in dreaming capability.
Inspired by kgdreaminvest worker pattern.
"""
import json
import logging
import random
import threading
import time
import traceback
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from sqlalchemy import text

from ..agent_config import get_agent_config
from ..database import get_worker_db, remove_worker_db
from ..log_broadcaster import broadcast_worker_log
from ..utils.knowledge_exchange import KnowledgeExchangeProtocol
from ..utils.conflict_resolver import ConflictResolver, ConflictAnalysis, ResolutionStrategy, AutoConflictManager
from typing import List, Dict, Any, Optional


logger = logging.getLogger("sigma.workers")


def utc_now() -> str:
    """Get current UTC timestamp as ISO string"""
    return datetime.now(timezone.utc).isoformat()


def jitter_sleep(base_seconds: int, stop_event: threading.Event):
    """Sleep with jitter (±10%) and stop event checking"""
    jitter = random.uniform(0.9, 1.1)
    sleep_time = base_seconds * jitter
    
    # Check stop event every second
    for _ in range(int(sleep_time)):
        if stop_event.is_set():
            return
        time.sleep(1)
    
    # Handle fractional second
    remainder = sleep_time - int(sleep_time)
    if remainder > 0 and not stop_event.is_set():
        time.sleep(remainder)


class BaseWorker(ABC):
    """
    Base class for all SIGMA workers with dreaming capability.
    
    Each worker has two modes:
    1. Production Mode: Execute primary responsibility efficiently
    2. Dream Mode: Experiment with novel approaches (15% of cycles by default)
    
    Workers self-report statistics and can be monitored/controlled.
    """
    
    def __init__(self, db_session, dreamer: "DreamerMetaAgent", project_id: Optional[int] = None):
        """
        Initialize worker.
        
        Args:
            db_session: SQLAlchemy database session
            dreamer: Reference to DreamerMetaAgent for experimentation
            project_id: ID of project this worker is analyzing (optional)
        """
        self.db = db_session
        self.name = self.__class__.__name__.replace('Worker', '').lower()
        self.dreamer = dreamer
        self.config = get_agent_config()
        self.project_id = project_id  # Track which project worker is analyzing
        
        # Thread management
        self.running = False
        self.stop = threading.Event()
        self.thread: Optional[threading.Thread] = None
        
        # Knowledge exchange
        self.knowledge_protocol: Optional[KnowledgeExchangeProtocol] = None
        self.received_knowledge: List[Dict] = []
        self.knowledge_broadcast_interval = 30  # seconds
        
        # Conflict resolution
        self.conflict_resolver: Optional[ConflictResolver] = None
        self.conflict_manager: Optional[AutoConflictManager] = None
        self.auto_resolve_conflicts: bool = False
        self.min_confidence_for_auto_resolve: float = 0.8
        
        # Statistics
        self.stats = {
            "cycles_run": 0,
            "experiments_run": 0,
            "experiments_successful": 0,
            "avg_cycle_time": 0.0,
            "last_cycle_time": 0.0,
            "error_count": 0,
            "last_error": None,
            "last_ts": None,
            "last_action": None,
            "knowledge_exchanges": 0,
        }
        
        logger.info(f"{self.name} worker initialized")
    
    @abstractmethod
    def get_interval(self) -> int:
        """Get worker cycle interval in seconds"""
        pass
    
    @abstractmethod
    def _production_cycle(self):
        """Execute one production cycle (main responsibility)"""
        pass
    
    @abstractmethod
    def _experimental_cycle(self):
        """Execute one experimental cycle (dreaming)"""
        pass
    
    @abstractmethod
    def _get_experiment_context(self) -> Dict[str, Any]:
        """Get context for experiment proposal"""
        pass
    
    def start(self):
        """Start the worker thread"""
        if self.thread and self.thread.is_alive():
            logger.warning(f"{self.name} worker already running")
            return
        
        self.running = True
        self.stop.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True, name=f"worker-{self.name}")
        self.thread.start()
        
        logger.info(f"{self.name} worker started")
        broadcast_worker_log(self.name, "info", f"✅ {self.name.capitalize()} worker started")
        
        # Initialize knowledge exchange protocol
        if self.knowledge_protocol is None:
            try:
                from ..utils.knowledge_exchange import KnowledgeExchangeProtocol
                self.knowledge_protocol = KnowledgeExchangeProtocol(self.db)
                logger.info(f"Knowledge exchange protocol initialized for {self.name}")
            except Exception as e:
                logger.warning(f"Failed to initialize knowledge exchange for {self.name}: {e}")
        
        # Initialize conflict resolution system
        if self.conflict_resolver is None:
            try:
                self.conflict_resolver = ConflictResolver()
                self.conflict_manager = AutoConflictManager(
                    auto_resolve=self.auto_resolve_conflicts,
                    min_confidence=self.min_confidence_for_auto_resolve
                )
                logger.info(f"Conflict resolution system initialized for {self.name}")
            except Exception as e:
                logger.warning(f"Failed to initialize conflict resolution for {self.name}: {e}")
    
    def stop_now(self):
        """Stop the worker thread"""
        self.running = False
        self.stop.set()
        logger.info(f"{self.name} worker stop signaled")
        broadcast_worker_log(self.name, "info", f"🛑 {self.name.capitalize()} worker stopped")
    
    def _loop(self):
        """Main worker loop"""
        cycle_count = 0
        while self.running and not self.stop.is_set():
            start_time = time.time()
            
            try:
                # Exchange knowledge with other workers
                if self.knowledge_protocol:
                    interval = max(1, self.get_interval())
                    broadcast_mod = max(1, self.knowledge_broadcast_interval // interval)
                    if cycle_count % broadcast_mod == 0:
                        self._exchange_knowledge()
                
                # Decide: production or experimental cycle?
                if self.dreamer.should_experiment():
                    broadcast_worker_log(
                        self.name,
                        "experiment",
                        f"🧪 Starting experimental cycle",
                        {"cycle": self.stats["cycles_run"] + 1}
                    )
                    self._experimental_cycle()
                    self.stats["experiments_run"] += 1
                    action = "experiment"
                else:
                    broadcast_worker_log(
                        self.name,
                        "info",
                        f"🔄 Starting production cycle",
                        {"cycle": self.stats["cycles_run"] + 1}
                    )
                    self._production_cycle()
                    action = "production"
                
                # Update statistics
                cycle_time = time.time() - start_time
                self.stats["cycles_run"] += 1
                self.stats["last_cycle_time"] = cycle_time
                self.stats["avg_cycle_time"] = (
                    (self.stats["avg_cycle_time"] * (self.stats["cycles_run"] - 1) + cycle_time)
                    / self.stats["cycles_run"]
                )
                self.stats["last_ts"] = utc_now()
                self.stats["last_action"] = action
                
                # Broadcast completion
                broadcast_worker_log(
                    self.name,
                    "debug",
                    f"Cycle {self.stats['cycles_run']} complete ({action})",
                    {
                        "cycle_time": f"{cycle_time:.2f}s",
                        "action": action,
                        "total_cycles": self.stats["cycles_run"]
                    }
                )
                
                # Persist statistics periodically (every 10 cycles)
                if self.stats["cycles_run"] % 10 == 0:
                    self._persist_stats()
                
            except Exception as e:
                self.stats["error_count"] += 1
                self.stats["last_error"] = str(e)
                
                # Rollback database session to prevent 'prepared' state errors
                try:
                    self.db.rollback()
                except Exception as rollback_error:
                    logger.warning(f"Failed to rollback session: {rollback_error}")
                
                logger.error(f"{self.name} worker error: {e}")
                logger.debug(traceback.format_exc())
                broadcast_worker_log(
                    self.name,
                    "error",
                    f"❌ Error: {str(e)}",
                    {"error_count": self.stats["error_count"]}
                )
            
            # Sleep until next cycle
            jitter_sleep(self.get_interval(), self.stop)
            cycle_count += 1
    
    def _persist_stats(self):
        """
        Persist worker statistics to database.
        
        Updates or creates WorkerStats record for this worker.
        """
        try:
            from ..models import WorkerStats
            from sqlalchemy import update
            
            # Check if stats record exists for this worker
            existing_stats = self.db.query(WorkerStats).filter(
                WorkerStats.worker_name == self.name
            ).first()
            
            if existing_stats:
                # Update existing record
                existing_stats.cycles_run = self.stats["cycles_run"]
                existing_stats.experiments_run = self.stats["experiments_run"]
                existing_stats.total_time += self.stats["last_cycle_time"]
                existing_stats.errors = self.stats["error_count"]
                existing_stats.last_run = datetime.now(timezone.utc)
            else:
                # Create new record
                new_stats = WorkerStats(
                    worker_name=self.name,
                    cycles_run=self.stats["cycles_run"],
                    experiments_run=self.stats["experiments_run"],
                    total_time=self.stats.get("avg_cycle_time", 0) * self.stats["cycles_run"],
                    errors=self.stats["error_count"],
                    last_run=datetime.now(timezone.utc)
                )
                self.db.add(new_stats)
            
            self.db.commit()
            logger.debug(f"Persisted stats for {self.name} worker")
            
        except Exception as e:
            logger.error(f"Failed to persist stats for {self.name}: {e}")
            try:
                self.db.rollback()
            except:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current worker statistics"""
        return self.stats.copy()
    
    def is_running(self) -> bool:
        """Check if worker is running"""
        return self.running and self.thread and self.thread.is_alive()
    
    def _exchange_knowledge(self):
        """Exchange knowledge with other workers"""
        if not self.knowledge_protocol:
            return
        
        try:
            # Receive knowledge from other workers
            while True:
                knowledge = asyncio.run(self.knowledge_protocol.receive_knowledge(self.name))
                
                if not knowledge:
                    break
                
                # Store for later use
                self.received_knowledge.append(knowledge)
                self.stats["knowledge_exchanges"] += 1
                
                # Process immediately if high urgency
                if knowledge.get('payload', {}).get('urgency') == 'high':
                    self._process_high_priority_knowledge(knowledge)
            
            # Detect and resolve conflicts in received knowledge
            if self.received_knowledge:
                self._detect_and_resolve_conflicts()
            
            # Update knowledge state
            if self.received_knowledge:
                asyncio.run(
                    self.knowledge_protocol.update_worker_knowledge_state(
                        worker_name=self.name,
                        received_knowledge=self.received_knowledge
                    )
                )
            
            # Broadcast recent learnings
            self._broadcast_recent_learnings()
            
        except Exception as e:
            logger.error(f"Failed to exchange knowledge: {e}")
    
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
        
        logger.info(f"Processed high-priority {knowledge_type} from {knowledge['source']}")
    
    def _broadcast_recent_learnings(self):
        """Broadcast recent learnings to other workers"""
        if not self.knowledge_protocol:
            return
        
        # Get recent successes from this worker
        recent_successes = self._get_recent_successes(limit=2)
        
        for success in recent_successes:
            knowledge_type = self._get_knowledge_type_for_success(success)
            
            asyncio.run(
                self.knowledge_protocol.broadcast_knowledge(
                    worker_name=self.name,
                    knowledge_type=knowledge_type,
                    payload=success,
                    urgency="normal"
                )
            )
    
    def _get_recent_successes(self, limit: int = 2) -> List[Dict]:
        """Get recent successful operations from this worker"""
        # This should be overridden by specific workers
        # For now, return empty list
        return []
    
    def _get_knowledge_type_for_success(self, success: Dict) -> str:
        """Determine knowledge type for a success"""
        # This should be overridden by specific workers
        return "decision_outcome"
    
    def _update_risk_model(self, payload: Dict):
        """Update risk model with new knowledge"""
        # This should be overridden by specific workers
        pass
    
    def _flag_critical_issue(self, payload: Dict):
        """Flag critical issue for attention"""
        # This should be overridden by specific workers
        pass
    
    def _broadcast_knowledge(self, knowledge_type: str, content: Dict, urgency: str = "normal"):
        """
        Broadcast knowledge to other workers.
        
        Args:
            knowledge_type: Type of knowledge being broadcast
            content: The knowledge content
            urgency: Urgency level ('low', 'normal', 'high', 'critical')
        """
        if not self.knowledge_protocol:
            return
        
        try:
            asyncio.run(
                self.knowledge_protocol.broadcast_knowledge(
                    worker_name=self.name,
                    knowledge_type=knowledge_type,
                    payload=content,
                    urgency=urgency
                )
            )
            logger.debug(f"{self.name} broadcasted {knowledge_type} knowledge")
        except Exception as e:
            logger.error(f"{self.name} failed to broadcast knowledge: {e}")
    
    # ============================================================================
    # Knowledge Reception Methods (Phase 3)
    # ============================================================================
    
    def process_received_knowledge(self, knowledge_list: List[Dict]) -> None:
        """
        Process knowledge received from other workers.
        
        Each worker implements specific logic based on knowledge types
        they care about. Knowledge is filtered and processed accordingly.
        
        Args:
            knowledge_list: List of knowledge dictionaries received
        """
        if not knowledge_list:
            return
        
        logger.info(f"{self.name} processing {len(knowledge_list)} knowledge items")
        
        for knowledge in knowledge_list:
            try:
                knowledge_type = knowledge.get('knowledge_type')
                source = knowledge.get('source')
                payload = knowledge.get('payload', {})
                
                # Update statistics
                self.stats['knowledge_received'] = self.stats.get('knowledge_received', 0) + 1
                
                # Route knowledge to appropriate handler
                if knowledge_type == 'risk_pattern':
                    self._update_risk_model(payload)
                    logger.debug(f"{self.name} updated risk model from {source}")
                
                elif knowledge_type in ['learned_pattern', 'pattern_evolution']:
                    self._update_pattern_models([knowledge])
                    logger.debug(f"{self.name} updated pattern models from {source}")
                
                elif knowledge_type == 'issue_pattern':
                    self._update_issue_detection([knowledge])
                    logger.debug(f"{self.name} updated issue detection from {source}")
                
                elif knowledge_type in ['proposal_quality', 'successful_fix']:
                    self._update_proposal_generation([knowledge])
                    logger.debug(f"{self.name} updated proposal generation from {source}")
                
                elif knowledge_type in ['context_enrichment', 'knowledge_retrieval']:
                    self._update_context_retrieval([knowledge])
                    logger.debug(f"{self.name} updated context retrieval from {source}")
                
                elif knowledge_type == 'decision_outcome':
                    self._update_decision_making([knowledge])
                    logger.debug(f"{self.name} updated decision making from {source}")
                
                elif knowledge_type == 'complexity_trend':
                    self._update_complexity_analysis([knowledge])
                    logger.debug(f"{self.name} updated complexity analysis from {source}")
                
                else:
                    logger.warning(f"{self.name} received unknown knowledge type: {knowledge_type}")
                
            except Exception as e:
                logger.error(f"{self.name} failed to process knowledge {knowledge_type}: {e}")
                continue
        
        # Detect and resolve conflicts in received knowledge
        if self.received_knowledge:
            self._detect_and_resolve_conflicts()
        
        # Persist knowledge state
        if self.received_knowledge:
            self._persist_knowledge_state()
    
    def query_knowledge(
        self,
        knowledge_types: Optional[List[str]] = None,
        min_freshness: Optional[float] = None,
        urgency: Optional[str] = None,
        limit: int = 10,
        worker_name: Optional[str] = None,
    ) -> List[Dict]:
        """
        Query for relevant knowledge from the knowledge exchange system.
        
        Args:
            knowledge_types: Filter by specific knowledge types
            min_freshness: Minimum freshness score (0.0 to 1.0)
            urgency: Filter by urgency level ('low', 'normal', 'high', 'critical')
            limit: Maximum number of results
            worker_name: Filter by source worker name
        
        Returns:
            List of knowledge dictionaries matching the query
        """
        if not self.knowledge_protocol:
            logger.warning(f"{self.name} knowledge protocol not available")
            return []
        
        try:
            # Build query parameters
            query_params = {
                'target_worker': self.name,
                'limit': limit,
            }
            
            if knowledge_types:
                query_params['knowledge_types'] = knowledge_types
            
            if min_freshness is not None:
                query_params['min_freshness'] = min_freshness
            
            if urgency:
                query_params['urgency'] = urgency
            
            if worker_name:
                query_params['source_worker'] = worker_name
            
            # Execute query
            knowledge = asyncio.run(
                self.knowledge_protocol.query_knowledge(**query_params)
            )
            
            logger.debug(f"{self.name} queried {len(knowledge)} knowledge items")
            return knowledge
            
        except Exception as e:
            logger.error(f"{self.name} failed to query knowledge: {e}")
            return []
    
    def get_relevant_knowledge(self) -> List[Dict]:
        """
        Get knowledge relevant to this worker's type.
        
        Each worker type implements specific logic to retrieve
        knowledge that can improve its performance.
        
        Returns:
            List of relevant knowledge items
        """
        return []
    
    def _update_pattern_models(self, knowledge_list: List[Dict]) -> None:
        """
        Update pattern recognition models with new knowledge.
        
        Args:
            knowledge_list: List of pattern-related knowledge
        """
        pass
    
    def _update_issue_detection(self, knowledge_list: List[Dict]) -> None:
        """
        Update issue detection rules with new knowledge.
        
        Args:
            knowledge_list: List of issue-related knowledge
        """
        pass
    
    def _update_proposal_generation(self, knowledge_list: List[Dict]) -> None:
        """
        Update proposal generation heuristics with new knowledge.
        
        Args:
            knowledge_list: List of proposal-related knowledge
        """
        pass
    
    def _update_context_retrieval(self, knowledge_list: List[Dict]) -> None:
        """
        Update context retrieval strategies with new knowledge.
        
        Args:
            knowledge_list: List of context-related knowledge
        """
        pass
    
    def _update_decision_making(self, knowledge_list: List[Dict]) -> None:
        """
        Update decision-making models with new knowledge.
        
        Args:
            knowledge_list: List of decision-related knowledge
        """
        pass
    
    def _update_complexity_analysis(self, knowledge_list: List[Dict]) -> None:
        """
        Update complexity analysis with new knowledge.
        
        Args:
            knowledge_list: List of complexity-related knowledge
        """
        pass
    
    def _persist_knowledge_state(self) -> None:
        """
        Persist knowledge state to database.
        
        Updates the worker's knowledge state record with
        the list of received knowledge items.
        """
        if not self.knowledge_protocol:
            return
        
        try:
            asyncio.run(
                self.knowledge_protocol.update_worker_knowledge_state(
                    worker_name=self.name,
                    received_knowledge=self.received_knowledge
                )
            )
            logger.debug(f"{self.name} persisted knowledge state")
        except Exception as e:
            logger.error(f"{self.name} failed to persist knowledge state: {e}")
    
    def _detect_and_resolve_conflicts(self):
        """
        Detect and resolve conflicts in received knowledge.
        
        Uses conflict resolution system to identify and handle
        duplicate, contradictory, or overlapping knowledge.
        """
        if not self.conflict_resolver or not self.conflict_manager:
            return
        
        try:
            # Get recent knowledge from database for comparison
            from ..database import get_session
            from ..models import KnowledgeExchange
            
            session = get_session()
            try:
                # Get knowledge from other workers (excluding self)
                other_knowledge = session.query(KnowledgeExchange).filter(
                    KnowledgeExchange.source_worker != self.name
                ).order_by(KnowledgeExchange.created_at.desc()).limit(20).all()
                
                # Check for conflicts with each received knowledge
                for received_kw in self.received_knowledge:
                    for db_kw in other_knowledge:
                        # Analyze conflict
                        conflict = self.conflict_resolver.analyze_conflicts(
                            received_kw, db_kw
                        )
                        
                        # Check if conflict needs resolution
                        if conflict.confidence >= self.min_confidence_for_auto_resolve and conflict.severity in ["medium", "high", "critical"]:
                            logger.warning(f"Conflict detected: {conflict.summary}")
                            
                            # Auto-resolve if enabled
                            if self.auto_resolve_conflicts:
                                resolution = self.conflict_resolver.resolve_conflict(conflict)
                                logger.info(f"Auto-resolved conflict using {resolution.strategy.value}")
            
            finally:
                session.close()
            
            # Update conflict statistics
            self.stats['conflicts_detected'] = self.stats.get('conflicts_detected', 0) + 1
            
        except Exception as e:
            logger.error(f"{self.name} failed to detect/resolve conflicts: {e}")
    
    def enable_auto_conflict_resolution(self, min_confidence: float = 0.8):
        """
        Enable automatic conflict resolution.
        
        Args:
            min_confidence: Minimum confidence threshold for auto-resolution (0.0 to 1.0)
        """
        self.auto_resolve_conflicts = True
        self.min_confidence_for_auto_resolve = min_confidence
        
        if self.conflict_manager:
            self.conflict_manager.auto_resolve = True
            self.conflict_manager.min_confidence = min_confidence
        
        logger.info(f"{self.name} enabled auto-conflict resolution (min_confidence={min_confidence})")
    
    def disable_auto_conflict_resolution(self):
        """Disable automatic conflict resolution"""
        self.auto_resolve_conflicts = False
        
        if self.conflict_manager:
            self.conflict_manager.auto_resolve = False
        
        logger.info(f"{self.name} disabled auto-conflict resolution")
    
    def get_conflict_dashboard(self) -> Dict[str, Any]:
        """
        Get conflict resolution dashboard data.
        
        Returns:
            Dictionary with conflict statistics and resolution data
        """
        if not self.conflict_manager:
            return {"error": "Conflict manager not initialized"}
        
        try:
            return self.conflict_manager.get_conflict_dashboard()
        except Exception as e:
            return {"error": str(e)}
    
    def run_conflict_detection_cycle(self) -> Dict[str, Any]:
        """
        Run a manual conflict detection and resolution cycle.
        
        Returns:
            Cycle summary
        """
        if not self.conflict_manager:
            return {"error": "Conflict manager not initialized"}
        
        try:
            result = self.conflict_manager.run_cycle()
            logger.info(f"Conflict cycle complete: {result['conflicts_detected']} conflicts detected, {result['resolutions_made']} resolved")
            return result
        except Exception as e:
            logger.error(f"Conflict detection cycle failed: {e}")
            return {"error": str(e)}


class WorkerController:
    """
    Controller for managing all workers.
    
    Provides centralized control and monitoring of all agent workers.
    """
    
    def __init__(self):
        self.workers: Dict[str, BaseWorker] = {}
    
    def register_worker(self, worker: BaseWorker):
        """Register a worker with the controller"""
        self.workers[worker.name] = worker
        logger.info(f"Registered worker: {worker.name}")
    
    def start_all(self):
        """Start all registered workers"""
        for worker in self.workers.values():
            worker.start()
        logger.info(f"Started {len(self.workers)} workers")
    
    def stop_all(self):
        """Stop all registered workers"""
        for worker in self.workers.values():
            worker.stop_now()
        logger.info("Stopped all workers")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all workers"""
        return {
            name: {
                "running": worker.is_running(),
                "stats": worker.get_stats(),
            }
            for name, worker in self.workers.items()
        }
    
    def start_worker(self, name: str):
        """Start a specific worker"""
        if name in self.workers:
            self.workers[name].start()
        else:
            raise ValueError(f"Unknown worker: {name}")
    
    def stop_worker(self, name: str):
        """Stop a specific worker"""
        if name in self.workers:
            self.workers[name].stop_now()
        else:
            raise ValueError(f"Unknown worker: {name}")


# Global worker controller instance
_controller: Optional[WorkerController] = None


def get_worker_controller() -> WorkerController:
    """Get the global worker controller"""
    global _controller
    if _controller is None:
        _controller = WorkerController()
    return _controller
