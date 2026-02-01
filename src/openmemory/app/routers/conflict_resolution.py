"""
Conflict Resolution API Router

Provides endpoints for conflict detection, resolution, and monitoring.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.conflict_resolver import (
    ConflictResolver,
    ConflictAnalysis,
    ResolutionStrategy,
    AutoConflictManager,
)
from app.agents.base_worker import get_worker_controller

router = APIRouter(prefix="/conflict", tags=["conflict-resolution"])


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_conflict_dashboard(
    session: Session = Depends(get_db),
    worker_name: Optional[str] = Query(None, description="Filter by specific worker")
):
    """
    Get conflict resolution dashboard data.
    
    Returns statistics and resolution data for conflicts in the system.
    """
    try:
        # Get global conflict resolver
        resolver = ConflictResolver()
        
        # Get worker-specific stats if requested
        if worker_name:
            worker_controller = get_worker_controller()
            if worker_name in worker_controller.workers:
                worker = worker_controller.workers[worker_name]
                if worker.conflict_manager:
                    return worker.get_conflict_dashboard()
        
        # Return global dashboard
        summary = resolver.get_conflict_summary()
        
        # Add system-wide metrics
        dashboard = {
            **summary,
            "system_status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_workers": len(get_worker_controller().workers),
        }
        
        return dashboard
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")


@router.get("/detect/{worker_id}", response_model=List[Dict[str, Any]])
async def detect_conflicts_for_worker(
    worker_id: str,
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_db)
):
    """
    Detect conflicts for a specific worker.
    
    Analyzes the worker's knowledge against others to find potential conflicts.
    """
    try:
        resolver = ConflictResolver()
        conflicts = resolver.detect_conflicts_for_worker(worker_id, limit=limit)
        
        # Convert to dict for JSON response
        return [
            {
                "conflict_id": conflict.conflict_id,
                "conflict_type": conflict.conflict_type.value,
                "severity": conflict.severity,
                "similarity_score": conflict.similarity_score,
                "contradiction_score": conflict.contradiction_score,
                "overlap_score": conflict.overlap_score,
                "summary": conflict.summary,
                "recommended_strategy": conflict.recommended_strategy.value,
                "confidence": conflict.confidence,
                "knowledge_a_id": conflict.knowledge_a_id,
                "knowledge_b_id": conflict.knowledge_b_id,
            }
            for conflict in conflicts
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect conflicts: {str(e)}")


@router.post("/resolve", response_model=Dict[str, Any])
async def resolve_conflict(
    conflict_data: Dict[str, Any],
    strategy: Optional[str] = Query(None, description="Resolution strategy (merge, select_newer, select_higher_quality, keep_both, mark_as_resolved)"),
    session: Session = Depends(get_db)
):
    """
    Resolve a specific conflict.
    
    Args:
        conflict_data: Conflict analysis data (from detect endpoint)
        strategy: Optional resolution strategy override
    """
    try:
        from app.utils.conflict_resolver import ConflictType
        
        # Parse conflict data
        conflict_id = conflict_data.get("conflict_id")
        knowledge_a_id = conflict_data.get("knowledge_a_id")
        knowledge_b_id = conflict_data.get("knowledge_b_id")
        conflict_type = ConflictType(conflict_data.get("conflict_type"))
        
        # Create analysis object
        analysis = ConflictAnalysis(
            conflict_id=conflict_id,
            knowledge_a_id=knowledge_a_id,
            knowledge_b_id=knowledge_b_id,
            conflict_type=conflict_type,
            similarity_score=conflict_data.get("similarity_score"),
            contradiction_score=conflict_data.get("contradiction_score"),
            overlap_score=conflict_data.get("overlap_score"),
            severity=conflict_data.get("severity", "medium"),
            summary=conflict_data.get("summary", ""),
            recommended_strategy=ResolutionStrategy(conflict_data.get("recommended_strategy", "merge")),
            confidence=conflict_data.get("confidence", 0.8),
        )
        
        # Resolve conflict
        resolver = ConflictResolver()
        resolution_strategy = ResolutionStrategy(strategy) if strategy else None
        resolution = resolver.resolve_conflict(analysis, resolution_strategy)
        
        return {
            "resolution_id": resolution.resolution_id,
            "conflict_id": resolution.conflict_id,
            "strategy": resolution.strategy.value,
            "selected_knowledge_id": resolution.selected_knowledge_id,
            "merged_knowledge": resolution.merged_knowledge,
            "resolution_notes": resolution.resolution_notes,
            "resolution_confidence": resolution.resolution_confidence,
            "resolved_at": resolution.resolved_at.isoformat(),
            "success": True,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve conflict: {str(e)}")


@router.get("/auto-detect", response_model=Dict[str, Any])
async def run_auto_conflict_detection(
    auto_resolve: bool = Query(False, description="Automatically resolve detected conflicts"),
    min_confidence: float = Query(0.8, ge=0.0, le=1.0, description="Minimum confidence threshold for auto-resolution"),
    session: Session = Depends(get_db)
):
    """
    Run automatic conflict detection cycle.
    
    Args:
        auto_resolve: If True, automatically resolve detected conflicts
        min_confidence: Minimum confidence threshold for auto-resolution
    """
    try:
        manager = AutoConflictManager(auto_resolve=auto_resolve, min_confidence=min_confidence)
        result = manager.run_cycle()
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run auto-detection: {str(e)}")


@router.post("/worker/{worker_name}/enable-auto-resolve", response_model=Dict[str, Any])
async def enable_worker_auto_conflict_resolution(
    worker_name: str,
    min_confidence: float = Query(0.8, ge=0.0, le=1.0),
):
    """
    Enable automatic conflict resolution for a specific worker.
    """
    try:
        worker_controller = get_worker_controller()
        
        if worker_name not in worker_controller.workers:
            raise HTTPException(status_code=404, detail=f"Worker '{worker_name}' not found")
        
        worker = worker_controller.workers[worker_name]
        worker.enable_auto_conflict_resolution(min_confidence)
        
        return {
            "success": True,
            "worker": worker_name,
            "auto_resolve_enabled": True,
            "min_confidence": min_confidence,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable auto-resolve: {str(e)}")


@router.post("/worker/{worker_name}/disable-auto-resolve", response_model=Dict[str, Any])
async def disable_worker_auto_conflict_resolution(
    worker_name: str,
):
    """
    Disable automatic conflict resolution for a specific worker.
    """
    try:
        worker_controller = get_worker_controller()
        
        if worker_name not in worker_controller.workers:
            raise HTTPException(status_code=404, detail=f"Worker '{worker_name}' not found")
        
        worker = worker_controller.workers[worker_name]
        worker.disable_auto_conflict_resolution()
        
        return {
            "success": True,
            "worker": worker_name,
            "auto_resolve_enabled": False,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable auto-resolve: {str(e)}")


@router.get("/worker/{worker_name}/conflict-cycle", response_model=Dict[str, Any])
async def run_worker_conflict_cycle(
    worker_name: str,
):
    """
    Run conflict detection cycle for a specific worker.
    """
    try:
        worker_controller = get_worker_controller()
        
        if worker_name not in worker_controller.workers:
            raise HTTPException(status_code=404, detail=f"Worker '{worker_name}' not found")
        
        worker = worker_controller.workers[worker_name]
        result = worker.run_conflict_detection_cycle()
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run conflict cycle: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_conflict_stats(
    session: Session = Depends(get_db)
):
    """
    Get comprehensive conflict statistics.
    """
    try:
        from app.models import ConflictResolutions, ConflictMetrics
        
        # Get basic counts
        total_resolutions = session.query(ConflictResolutions).count()
        recent_resolutions = session.query(ConflictResolutions).filter(
            ConflictResolutions.resolved_at >= datetime.now(timezone.utc).replace(day=datetime.now(timezone.utc).day - 7)
        ).count()
        
        # Get conflict type distribution
        type_distribution = session.query(
            ConflictResolutions.conflict_type,
            ConflictResolutions.severity,
            session.func.count().label('count')
        ).group_by(
            ConflictResolutions.conflict_type,
            ConflictResolutions.severity
        ).all()
        
        # Get average confidence
        avg_confidence_query = session.query(
            session.func.avg(ConflictResolutions.confidence).label('avg_confidence'),
            session.func.avg(ConflictResolutions.resolution_confidence).label('avg_resolution_confidence')
        ).first()
        
        return {
            "total_resolutions": total_resolutions,
            "recent_resolutions_last_7_days": recent_resolutions,
            "type_distribution": [
                {"type": r[0], "severity": r[1], "count": r[2]}
                for r in type_distribution
            ],
            "average_confidence": float(avg_confidence_query.avg_confidence or 0),
            "average_resolution_confidence": float(avg_confidence_query.avg_resolution_confidence or 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/recent", response_model=List[Dict[str, Any]])
async def get_recent_conflicts(
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_db)
):
    """
    Get recently resolved conflicts.
    """
    try:
        from app.models import ConflictResolutions
        
        recent = session.query(ConflictResolutions).order_by(
            ConflictResolutions.resolved_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": r.id,
                "conflict_id": r.conflict_id,
                "conflict_type": r.conflict_type,
                "severity": r.severity,
                "confidence": r.confidence,
                "resolution_strategy": r.resolution_strategy,
                "resolution_confidence": r.resolution_confidence,
                "resolved_at": r.resolved_at.isoformat(),
                "resolution_notes": r.resolution_notes,
            }
            for r in recent
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent conflicts: {str(e)}")


@router.get("/audit", response_model=Dict[str, Any])
async def get_conflict_audit(
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_db)
):
    """
    Get conflict audit trail.
    """
    try:
        from app.models import ConflictAudit
        
        audit_entries = session.query(ConflictAudit).order_by(
            ConflictAudit.conflict_check_timestamp.desc()
        ).limit(limit).all()
        
        return {
            "audit_entries": [
                {
                    "id": entry.id,
                    "worker_id": entry.worker_id,
                    "timestamp": entry.conflict_check_timestamp.isoformat(),
                    "knowledge_checked": entry.knowledge_checked_count,
                    "conflicts_detected": entry.conflicts_detected_count,
                    "resolutions_made": entry.resolutions_made_count,
                    "auto_resolve_enabled": entry.auto_resolve_enabled,
                    "confidence": entry.detection_confidence,
                    "duration_ms": entry.cycle_duration_ms,
                    "health_status": entry.health_status,
                }
                for entry in audit_entries
            ],
            "total_entries": len(audit_entries),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audit: {str(e)}")
