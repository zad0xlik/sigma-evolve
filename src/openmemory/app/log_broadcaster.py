"""
Log Broadcaster - Real-time streaming of worker logs via SSE

Provides a centralized log broadcasting system for streaming worker activity
to connected clients via Server-Sent Events (SSE).
"""
import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from threading import Lock

logger = logging.getLogger(__name__)


class LogBroadcaster:
    """
    Thread-safe log broadcaster for real-time worker activity streaming.
    
    Features:
    - In-memory circular buffer (last 1000 logs)
    - Multiple concurrent SSE subscribers
    - Thread-safe log broadcasting from worker threads
    - Automatic cleanup of disconnected clients
    """
    
    def __init__(self, max_buffer_size: int = 1000):
        self.max_buffer_size = max_buffer_size
        self.buffer: deque = deque(maxlen=max_buffer_size)
        self.buffer_lock = Lock()
        self.subscribers: List[asyncio.Queue] = []
        self.subscribers_lock = Lock()
    
    def broadcast_log(
        self,
        worker_name: str,
        level: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast a log event to all subscribers.
        
        Thread-safe - can be called from worker threads.
        
        Args:
            worker_name: Name of worker generating the log
            level: Log level (info, warning, error, debug, experiment)
            message: Log message
            metadata: Optional additional data (project_id, metrics, etc.)
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        log_event = {
            "timestamp": timestamp,
            "worker": worker_name,
            "level": level,
            "message": message,
            "metadata": metadata or {}
        }
        
        # Add to buffer (thread-safe)
        with self.buffer_lock:
            self.buffer.append(log_event)
        
        # Broadcast to all subscribers (thread-safe)
        with self.subscribers_lock:
            # Remove queues that are full (disconnected clients)
            active_subscribers = []
            for queue in self.subscribers:
                try:
                    # Try to put without blocking - if full, skip (client disconnected)
                    if queue.qsize() < 100:  # Max queue size per client
                        queue.put_nowait(log_event)
                        active_subscribers.append(queue)
                except asyncio.QueueFull:
                    logger.debug(f"Subscriber queue full, removing")
                except Exception as e:
                    logger.error(f"Error broadcasting to subscriber: {e}")
            
            self.subscribers = active_subscribers
    
    def subscribe(self) -> asyncio.Queue:
        """
        Subscribe to log stream.
        
        Returns:
            asyncio.Queue that will receive log events
        """
        queue = asyncio.Queue()
        
        with self.subscribers_lock:
            self.subscribers.append(queue)
        
        logger.info(f"New subscriber added (total: {len(self.subscribers)})")
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from log stream"""
        with self.subscribers_lock:
            if queue in self.subscribers:
                self.subscribers.remove(queue)
                logger.info(f"Subscriber removed (total: {len(self.subscribers)})")
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent logs from buffer.
        
        Args:
            limit: Maximum number of logs to return
        
        Returns:
            List of recent log events (newest first)
        """
        with self.buffer_lock:
            logs = list(self.buffer)
        
        # Return most recent logs
        return list(reversed(logs[-limit:]))
    
    def clear_buffer(self):
        """Clear the log buffer"""
        with self.buffer_lock:
            self.buffer.clear()
        logger.info("Log buffer cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get broadcaster statistics"""
        with self.buffer_lock:
            buffer_size = len(self.buffer)
        
        with self.subscribers_lock:
            subscriber_count = len(self.subscribers)
        
        return {
            "buffer_size": buffer_size,
            "max_buffer_size": self.max_buffer_size,
            "active_subscribers": subscriber_count
        }


# Global broadcaster instance
_broadcaster: Optional[LogBroadcaster] = None
_broadcaster_lock = Lock()


def get_log_broadcaster() -> LogBroadcaster:
    """Get or create the global log broadcaster instance"""
    global _broadcaster
    
    if _broadcaster is None:
        with _broadcaster_lock:
            if _broadcaster is None:  # Double-check locking
                _broadcaster = LogBroadcaster()
                logger.info("Log broadcaster initialized")
    
    return _broadcaster


def broadcast_worker_log(
    worker_name: str,
    level: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Convenience function to broadcast a worker log.
    
    Thread-safe - can be called from any worker thread.
    
    Example:
        broadcast_worker_log("analysis", "info", "Starting analysis", {"project_id": 1})
        broadcast_worker_log("dreamer", "experiment", "🧪 New experiment", {"name": "test"})
    """
    broadcaster = get_log_broadcaster()
    broadcaster.broadcast_log(worker_name, level, message, metadata)
