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
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from ..agent_config import get_agent_config
from ..database import get_db


logger = logging.getLogger("sigma.workers")


def utc_now() -> str:
    """Get current UTC timestamp as ISO string"""
    return datetime.utcnow().isoformat()


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
    
    def __init__(self, name: str, dreamer: "DreamerMetaAgent"):
        """
        Initialize worker.
        
        Args:
            name: Worker name (e.g., "analysis", "dream", "recall")
            dreamer: Reference to DreamerMetaAgent for experimentation
        """
        self.name = name
        self.dreamer = dreamer
        self.config = get_agent_config()
        
        # Thread management
        self.running = False
        self.stop = threading.Event()
        self.thread: Optional[threading.Thread] = None
        
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
        self._log_event("start", f"{self.name} worker started")
    
    def stop_now(self):
        """Stop the worker thread"""
        self.running = False
        self.stop.set()
        logger.info(f"{self.name} worker stop signaled")
        self._log_event("stop", f"{self.name} worker stopped")
    
    def _loop(self):
        """Main worker loop"""
        while self.running and not self.stop.is_set():
            start_time = time.time()
            
            try:
                # Decide: production or experimental cycle?
                if self.dreamer.should_experiment():
                    self._experimental_cycle()
                    self.stats["experiments_run"] += 1
                    action = "experiment"
                else:
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
                
                # Persist statistics periodically (every 10 cycles)
                if self.stats["cycles_run"] % 10 == 0:
                    self._persist_stats()
                
            except Exception as e:
                self.stats["error_count"] += 1
                self.stats["last_error"] = str(e)
                logger.error(f"{self.name} worker error: {e}")
                logger.debug(traceback.format_exc())
                self._log_event("error", f"Error: {e}")
            
            # Sleep until next cycle
            jitter_sleep(self.get_interval(), self.stop)
    
    def _log_event(self, event_type: str, details: str):
        """Log event to database"""
        try:
            db = next(get_db())
            db.execute(
                "INSERT INTO event_log (ts, worker, event, details) VALUES (?, ?, ?, ?)",
                (utc_now(), self.name, event_type, details)
            )
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log event: {e}")
    
    def _persist_stats(self):
        """Persist worker statistics to database"""
        try:
            db = next(get_db())
            
            # Get current project_id if available
            project_id = None
            if hasattr(self, 'current_project_id'):
                project_id = self.current_project_id
            
            db.execute("""
                INSERT INTO worker_stats (
                    worker_name, project_id, ts, cycles_run, experiments_run, 
                    experiments_successful, avg_cycle_time, last_cycle_time,
                    error_count, metrics_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.name,
                project_id,
                utc_now(),
                self.stats["cycles_run"],
                self.stats["experiments_run"],
                self.stats["experiments_successful"],
                self.stats["avg_cycle_time"],
                self.stats["last_cycle_time"],
                self.stats["error_count"],
                json.dumps(self.stats)
            ))
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to persist stats: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current worker statistics"""
        return self.stats.copy()
    
    def is_running(self) -> bool:
        """Check if worker is running"""
        return self.running and self.thread and self.thread.is_alive()


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
