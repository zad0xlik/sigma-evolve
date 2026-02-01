"""
API endpoints for cross-worker knowledge exchange
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
import logging

from ..utils.knowledge_exchange import KnowledgeExchangeProtocol
from ..database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge_exchange"])


def get_knowledge_protocol(db: Session = Depends(get_db)) -> KnowledgeExchangeProtocol:
    """Get knowledge exchange protocol instance"""
    return KnowledgeExchangeProtocol(db)


# ==================== KNOWLEDGE BROADCAST ====================

@router.post("/broadcast", response_model=Dict[str, Any])
async def broadcast_knowledge(
    source_worker: str,
    knowledge_type: str,
    payload: Dict[str, Any],
    urgency: str = "normal",
    target_workers: Optional[List[str]] = None,
    protocol: KnowledgeExchangeProtocol = Depends(get_knowledge_protocol)
):
    """Broadcast knowledge to workers"""
    try:
        if target_workers:
            # Unicast to specific workers
            for target in target_workers:
                await protocol.broadcast_knowledge(
                    source_worker=source_worker,
                    knowledge_type=knowledge_type,
                    payload=payload,
                    urgency=urgency
                )
        else:
            # Broadcast to all interested workers
            await protocol.broadcast_knowledge(
                source_worker=source_worker,
                knowledge_type=knowledge_type,
                payload=payload,
                urgency=urgency
            )
        
        return {
            "status": "success",
            "message": "Knowledge broadcasted",
            "source_worker": source_worker,
            "knowledge_type": knowledge_type,
            "urgency": urgency,
            "target_workers": target_workers or "all interested workers"
        }
        
    except Exception as e:
        logger.error(f"Failed to broadcast knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/receive/{worker_name}", response_model=Dict[str, Any])
async def receive_knowledge(
    worker_name: str,
    protocol: KnowledgeExchangeProtocol = Depends(get_knowledge_protocol)
):
    """Receive knowledge for a worker"""
    try:
        knowledge = await protocol.receive_knowledge(worker_name)
        
        return {
            "status": "success",
            "knowledge": knowledge,
            "timestamp": protocol.freshness_tracker.utc_now()
        }
        
    except Exception as e:
        logger.error(f"Failed to receive knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== KNOWLEDGE QUERY ====================

@router.get("/query", response_model=Dict[str, Any])
async def query_knowledge(
    worker_name: Optional[str] = None,
    knowledge_type: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    min_freshness: float = Query(0.0, ge=0.0, le=1.0),
    protocol: KnowledgeExchangeProtocol = Depends(get_knowledge_protocol)
):
    """Query knowledge from database"""
    try:
        results = await protocol.query_knowledge(
            worker_name=worker_name,
            knowledge_type=knowledge_type,
            limit=limit,
            min_freshness=min_freshness
        )
        
        return {
            "status": "success",
            "results": results,
            "count": len(results),
            "filters": {
                "worker_name": worker_name,
                "knowledge_type": knowledge_type,
                "min_freshness": min_freshness
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to query knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== KNOWLEDGE VALIDATION ====================

@router.post("/validate", response_model=Dict[str, Any])
async def validate_knowledge(
    exchange_id: int,
    validator_worker: str,
    is_valid: bool,
    validation_score: float,
    feedback: Optional[str] = None,
    protocol: KnowledgeExchangeProtocol = Depends(get_knowledge_protocol)
):
    """Validate received knowledge"""
    try:
        await protocol.validate_received_knowledge(
            exchange_id=exchange_id,
            validator_worker=validator_worker,
            is_valid=is_valid,
            validation_score=validation_score,
            feedback=feedback
        )
        
        return {
            "status": "success",
            "message": "Knowledge validated",
            "exchange_id": exchange_id,
            "validator_worker": validator_worker,
            "is_valid": is_valid,
            "validation_score": validation_score
        }
        
    except Exception as e:
        logger.error(f"Failed to validate knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WORKER KNOWLEDGE STATE ====================

@router.get("/state/{worker_name}", response_model=Dict[str, Any])
async def get_worker_knowledge_state(
    worker_name: str,
    protocol: KnowledgeExchangeProtocol = Depends(get_knowledge_protocol)
):
    """Get knowledge state for a worker"""
    try:
        from ..models import WorkerKnowledgeState
        
        state = protocol.db.query(WorkerKnowledgeState).get(worker_name)
        
        if not state:
            return {
                "status": "success",
                "worker": worker_name,
                "state": None,
                "message": "No knowledge state found"
            }
        
        return {
            "status": "success",
            "worker": worker_name,
            "state": {
                "worker_name": state.worker_name,
                "last_exchange": state.last_exchange.isoformat() if state.last_exchange else None,
                "exchange_count": state.exchange_count,
                "received_knowledge_count": len(state.received_knowledge or []),
                "broadcast_knowledge_count": len(state.broadcast_knowledge or []),
                "created_at": state.created_at.isoformat() if state.created_at else None,
                "updated_at": state.updated_at.isoformat() if state.updated_at else None,
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get worker knowledge state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/state/{worker_name}/clear", response_model=Dict[str, Any])
async def clear_worker_knowledge_state(
    worker_name: str,
    protocol: KnowledgeExchangeProtocol = Depends(get_knowledge_protocol)
):
    """Clear knowledge state for a worker"""
    try:
        from ..models import WorkerKnowledgeState
        
        state = protocol.db.query(WorkerKnowledgeState).get(worker_name)
        
        if state:
            state.received_knowledge = []
            state.broadcast_knowledge = []
            state.exchange_count = 0
            state.updated_at = protocol.freshness_tracker.utc_now()
            protocol.db.commit()
        
        return {
            "status": "success",
            "worker": worker_name,
            "message": "Knowledge state cleared"
        }
        
    except Exception as e:
        logger.error(f"Failed to clear worker knowledge state: {e}")
        protocol.db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EXCHANGE STATISTICS ====================

@router.get("/stats", response_model=Dict[str, Any])
async def get_exchange_stats(
    protocol: KnowledgeExchangeProtocol = Depends(get_knowledge_protocol)
):
    """Get knowledge exchange statistics"""
    try:
        from ..models import KnowledgeExchange, KnowledgeValidation
        from sqlalchemy import func, and_
        
        # Total exchanges
        total_exchanges = protocol.db.query(KnowledgeExchange).count()
        
        # Exchanges by type
        by_type = protocol.db.query(
            KnowledgeExchange.knowledge_type,
            func.count(KnowledgeExchange.exchange_id).label('count')
        ).group_by(KnowledgeExchange.knowledge_type).all()
        
        # Exchanges by source worker
        by_source = protocol.db.query(
            KnowledgeExchange.source_worker,
            func.count(KnowledgeExchange.exchange_id).label('count')
        ).group_by(KnowledgeExchange.source_worker).all()
        
        # Validation statistics
        total_validations = protocol.db.query(KnowledgeValidation).count()
        valid_count = protocol.db.query(KnowledgeValidation).filter(
            KnowledgeValidation.is_valid == True
        ).count()
        
        # Recent exchanges (last 24 hours)
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=24)
        recent_exchanges = protocol.db.query(KnowledgeExchange).filter(
            KnowledgeExchange.created_at >= cutoff
        ).count()
        
        return {
            "status": "success",
            "stats": {
                "total_exchanges": total_exchanges,
                "recent_exchanges_24h": recent_exchanges,
                "exchanges_by_type": {row[0]: row[1] for row in by_type},
                "exchanges_by_source": {row[0]: row[1] for row in by_source},
                "validations": {
                    "total": total_validations,
                    "valid": valid_count,
                    "invalid": total_validations - valid_count if total_validations > 0 else 0,
                    "validation_rate": valid_count / total_validations if total_validations > 0 else 0.0
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get exchange stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== KNOWLEDGE TYPES ====================

@router.get("/types", response_model=Dict[str, Any])
async def get_knowledge_types(
    protocol: KnowledgeExchangeProtocol = Depends(get_knowledge_protocol)
):
    """Get available knowledge types and their metadata"""
    try:
        knowledge_types = {}
        
        for ktype, metadata in protocol.knowledge_types.items():
            knowledge_types[ktype] = {
                "workers": metadata['workers'],
                "persistence": metadata['persistence'],
                "validation": metadata['validation'],
                "propagation": metadata['propagation']
            }
        
        return {
            "status": "success",
            "knowledge_types": knowledge_types,
            "count": len(knowledge_types)
        }
        
    except Exception as e:
        logger.error(f"Failed to get knowledge types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BULK OPERATIONS ====================

@router.post("/broadcast/bulk", response_model=Dict[str, Any])
async def bulk_broadcast(
    broadcasts: List[Dict[str, Any]],
    protocol: KnowledgeExchangeProtocol = Depends(get_knowledge_protocol)
):
    """Broadcast multiple knowledge items in bulk"""
    try:
        results = []
        
        for broadcast in broadcasts:
            try:
                await protocol.broadcast_knowledge(
                    source_worker=broadcast['source_worker'],
                    knowledge_type=broadcast['knowledge_type'],
                    payload=broadcast['payload'],
                    urgency=broadcast.get('urgency', 'normal')
                )
                
                results.append({
                    "status": "success",
                    "source_worker": broadcast['source_worker'],
                    "knowledge_type": broadcast['knowledge_type']
                })
                
            except Exception as e:
                results.append({
                    "status": "error",
                    "source_worker": broadcast.get('source_worker', 'unknown'),
                    "knowledge_type": broadcast.get('knowledge_type', 'unknown'),
                    "error": str(e)
                })
        
        return {
            "status": "partial_success" if any(r['status'] == 'error' for r in results) else "success",
            "results": results,
            "total": len(broadcasts),
            "successful": sum(1 for r in results if r['status'] == 'success'),
            "failed": sum(1 for r in results if r['status'] == 'error')
        }
        
    except Exception as e:
        logger.error(f"Failed to bulk broadcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))
