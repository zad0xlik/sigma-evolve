"""
SIGMA Agent System API Router

Provides endpoints for monitoring and controlling the SIGMA agent system:
- Dashboard: Worker stats, system health, recent activities
- Proposals: List, review, approve/reject improvement proposals
- Experiments: Track experimental work and results
- Patterns: View learned patterns and cross-project opportunities
- Projects: Manage projects being improved
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    CrossProjectLearning,
    Experiment,
    LearnedPattern,
    Project,
    Proposal,
    WorkerStats,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ===== PYDANTIC SCHEMAS =====

class ProjectResponse(BaseModel):
    project_id: int
    repo_url: str
    branch: str
    language: Optional[str]
    framework: Optional[str]
    domain: Optional[str]
    created_at: datetime
    last_analyzed: Optional[datetime]
    
    class Config:
        from_attributes = True


class ProposalResponse(BaseModel):
    proposal_id: int
    project_id: int
    title: str
    description: Optional[str]
    confidence: float
    critic_score: float
    status: str
    pr_url: Optional[str]
    commit_sha: Optional[str]
    created_at: datetime
    executed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ProposalDetailResponse(ProposalResponse):
    agents_json: Optional[str]
    changes_json: Optional[str]


class ExperimentResponse(BaseModel):
    experiment_id: int
    worker_name: str
    experiment_name: str
    hypothesis: Optional[str]
    approach: Optional[str]
    success: Optional[bool]
    improvement: Optional[float]
    promoted_to_production: bool
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class LearnedPatternResponse(BaseModel):
    pattern_id: int
    pattern_name: str
    pattern_type: str
    description: Optional[str]
    language: str
    framework: Optional[str]
    domain: Optional[str]
    confidence: float
    success_count: int
    failure_count: int
    created_at: datetime
    last_used: Optional[datetime]
    
    class Config:
        from_attributes = True


class WorkerStatsResponse(BaseModel):
    stat_id: int
    worker_name: str
    cycles_run: int
    experiments_run: int
    total_time: float
    errors: int
    last_run: Optional[datetime]
    
    class Config:
        from_attributes = True


class DashboardResponse(BaseModel):
    total_projects: int
    active_proposals: int
    pending_proposals: int
    total_experiments: int
    successful_experiments: int
    promoted_experiments: int
    total_patterns: int
    worker_stats: List[WorkerStatsResponse]
    recent_proposals: List[ProposalResponse]
    recent_experiments: List[ExperimentResponse]


class ApprovalRequest(BaseModel):
    proposal_id: int
    approved: bool = Field(..., description="True to approve, False to reject")
    comment: Optional[str] = Field(None, description="Optional comment for approval/rejection")


class CrossProjectOpportunity(BaseModel):
    learning_id: int
    source_project: ProjectResponse
    target_project: ProjectResponse
    pattern: LearnedPatternResponse
    similarity_score: float
    applied: bool
    created_at: datetime


# ===== DASHBOARD ENDPOINTS =====

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(db: Session = Depends(get_db)):
    """
    Get comprehensive dashboard data for SIGMA agent system.
    
    Returns:
    - Project statistics
    - Proposal counts and statuses
    - Experiment results
    - Worker performance metrics
    - Recent activities
    """
    try:
        # Count statistics
        total_projects = db.query(func.count(Project.project_id)).scalar() or 0
        active_proposals = db.query(func.count(Proposal.proposal_id)).filter(
            Proposal.status != 'rejected'
        ).scalar() or 0
        pending_proposals = db.query(func.count(Proposal.proposal_id)).filter(
            Proposal.status == 'pending'
        ).scalar() or 0
        total_experiments = db.query(func.count(Experiment.experiment_id)).scalar() or 0
        successful_experiments = db.query(func.count(Experiment.experiment_id)).filter(
            Experiment.success == True
        ).scalar() or 0
        promoted_experiments = db.query(func.count(Experiment.experiment_id)).filter(
            Experiment.promoted_to_production == True
        ).scalar() or 0
        total_patterns = db.query(func.count(LearnedPattern.pattern_id)).scalar() or 0
        
        # Worker statistics
        worker_stats = db.query(WorkerStats).all()
        
        # Recent proposals (last 10)
        recent_proposals = db.query(Proposal).order_by(
            desc(Proposal.created_at)
        ).limit(10).all()
        
        # Recent experiments (last 10)
        recent_experiments = db.query(Experiment).order_by(
            desc(Experiment.created_at)
        ).limit(10).all()
        
        return DashboardResponse(
            total_projects=total_projects,
            active_proposals=active_proposals,
            pending_proposals=pending_proposals,
            total_experiments=total_experiments,
            successful_experiments=successful_experiments,
            promoted_experiments=promoted_experiments,
            total_patterns=total_patterns,
            worker_stats=[WorkerStatsResponse.from_orm(ws) for ws in worker_stats],
            recent_proposals=[ProposalResponse.from_orm(p) for p in recent_proposals],
            recent_experiments=[ExperimentResponse.from_orm(e) for e in recent_experiments]
        )
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {str(e)}")


# ===== PROJECT ENDPOINTS =====

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all projects being tracked by SIGMA"""
    projects = db.query(Project).order_by(
        desc(Project.last_analyzed)
    ).offset(skip).limit(limit).all()
    return [ProjectResponse.from_orm(p) for p in projects]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get details for a specific project"""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.from_orm(project)


# ===== PROPOSAL ENDPOINTS =====

@router.get("/proposals", response_model=List[ProposalResponse])
async def list_proposals(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected, executed"),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List code improvement proposals.
    
    Supports filtering by status and project.
    Useful for reviewing and approving proposals at autonomy level 1.
    """
    query = db.query(Proposal)
    
    if status:
        query = query.filter(Proposal.status == status)
    if project_id:
        query = query.filter(Proposal.project_id == project_id)
    
    proposals = query.order_by(desc(Proposal.created_at)).offset(skip).limit(limit).all()
    return [ProposalResponse.from_orm(p) for p in proposals]


@router.get("/proposals/{proposal_id}", response_model=ProposalDetailResponse)
async def get_proposal(proposal_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific proposal"""
    proposal = db.query(Proposal).filter(Proposal.proposal_id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return ProposalDetailResponse.from_orm(proposal)


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: int,
    request: ApprovalRequest,
    db: Session = Depends(get_db)
):
    """
    Approve or reject a proposal (for autonomy level 1).
    
    When approved:
    - Status changes to 'approved'
    - Think Worker will execute the proposal
    - Git operations will create PR or commit
    
    When rejected:
    - Status changes to 'rejected'
    - Learning Worker may analyze why it was rejected
    """
    proposal = db.query(Proposal).filter(Proposal.proposal_id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if proposal.status != 'pending':
        raise HTTPException(
            status_code=400,
            detail=f"Proposal is already {proposal.status}, cannot approve/reject"
        )
    
    # Update status
    proposal.status = 'approved' if request.approved else 'rejected'
    
    # Add approval metadata
    if not proposal.agents_json:
        proposal.agents_json = "{}"
    
    import json
    try:
        agents_data = json.loads(proposal.agents_json)
    except:
        agents_data = {}
    
    agents_data['approval'] = {
        'approved': request.approved,
        'comment': request.comment,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    proposal.agents_json = json.dumps(agents_data)
    
    db.commit()
    db.refresh(proposal)
    
    action = "approved" if request.approved else "rejected"
    logger.info(f"Proposal {proposal_id} has been {action}")
    
    return {
        "success": True,
        "proposal_id": proposal_id,
        "status": proposal.status,
        "message": f"Proposal {action} successfully"
    }


# ===== EXPERIMENT ENDPOINTS =====

@router.get("/experiments", response_model=List[ExperimentResponse])
async def list_experiments(
    worker_name: Optional[str] = Query(None, description="Filter by worker name"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    promoted: Optional[bool] = Query(None, description="Filter by promotion status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List experiments conducted by DreamerMetaAgent.
    
    Shows experimental approaches, their results, and promotion status.
    Experiments with >20% improvement are auto-promoted to production.
    """
    query = db.query(Experiment)
    
    if worker_name:
        query = query.filter(Experiment.worker_name == worker_name)
    if success is not None:
        query = query.filter(Experiment.success == success)
    if promoted is not None:
        query = query.filter(Experiment.promoted_to_production == promoted)
    
    experiments = query.order_by(desc(Experiment.created_at)).offset(skip).limit(limit).all()
    return [ExperimentResponse.from_orm(e) for e in experiments]


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific experiment"""
    experiment = db.query(Experiment).filter(Experiment.experiment_id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentResponse.from_orm(experiment)


@router.get("/experiments/worker/{worker_name}/stats")
async def get_worker_experiment_stats(worker_name: str, db: Session = Depends(get_db)):
    """Get experiment statistics for a specific worker"""
    total = db.query(func.count(Experiment.experiment_id)).filter(
        Experiment.worker_name == worker_name
    ).scalar() or 0
    
    successful = db.query(func.count(Experiment.experiment_id)).filter(
        Experiment.worker_name == worker_name,
        Experiment.success == True
    ).scalar() or 0
    
    promoted = db.query(func.count(Experiment.experiment_id)).filter(
        Experiment.worker_name == worker_name,
        Experiment.promoted_to_production == True
    ).scalar() or 0
    
    avg_improvement = db.query(func.avg(Experiment.improvement)).filter(
        Experiment.worker_name == worker_name,
        Experiment.success == True
    ).scalar() or 0.0
    
    return {
        "worker_name": worker_name,
        "total_experiments": total,
        "successful_experiments": successful,
        "promoted_experiments": promoted,
        "success_rate": (successful / total * 100) if total > 0 else 0,
        "promotion_rate": (promoted / total * 100) if total > 0 else 0,
        "avg_improvement": float(avg_improvement)
    }


# ===== PATTERN ENDPOINTS =====

@router.get("/patterns", response_model=List[LearnedPatternResponse])
async def list_patterns(
    pattern_type: Optional[str] = Query(None, description="Filter by type: refactoring, optimization, bug_fix, etc."),
    language: Optional[str] = Query(None, description="Filter by programming language"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List learned patterns from successful proposals.
    
    These patterns are extracted by Learning Worker and can be applied
    to similar projects through cross-project learning.
    """
    query = db.query(LearnedPattern).filter(LearnedPattern.confidence >= min_confidence)
    
    if pattern_type:
        query = query.filter(LearnedPattern.pattern_type == pattern_type)
    if language:
        query = query.filter(LearnedPattern.language == language)
    
    patterns = query.order_by(desc(LearnedPattern.confidence)).offset(skip).limit(limit).all()
    return [LearnedPatternResponse.from_orm(p) for p in patterns]


@router.get("/patterns/{pattern_id}", response_model=LearnedPatternResponse)
async def get_pattern(pattern_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific learned pattern"""
    pattern = db.query(LearnedPattern).filter(LearnedPattern.pattern_id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return LearnedPatternResponse.from_orm(pattern)


@router.get("/patterns/{pattern_id}/applications")
async def get_pattern_applications(pattern_id: int, db: Session = Depends(get_db)):
    """Get cross-project applications of a specific pattern"""
    applications = db.query(CrossProjectLearning).filter(
        CrossProjectLearning.pattern_id == pattern_id
    ).all()
    
    result = []
    for app in applications:
        source_project = db.query(Project).filter(
            Project.project_id == app.source_project_id
        ).first()
        target_project = db.query(Project).filter(
            Project.project_id == app.target_project_id
        ).first()
        
        if source_project and target_project:
            result.append({
                "learning_id": app.learning_id,
                "source_project": ProjectResponse.from_orm(source_project),
                "target_project": ProjectResponse.from_orm(target_project),
                "similarity_score": app.similarity_score,
                "applied": app.applied,
                "created_at": app.created_at,
                "applied_at": app.applied_at
            })
    
    return result


# ===== CROSS-PROJECT LEARNING ENDPOINTS =====

@router.get("/cross-project/opportunities", response_model=List[CrossProjectOpportunity])
async def get_cross_project_opportunities(
    applied: Optional[bool] = Query(None, description="Filter by application status"),
    min_similarity: float = Query(0.5, ge=0.0, le=1.0, description="Minimum similarity score"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List cross-project learning opportunities.
    
    Shows patterns that could be applied from one project to similar projects.
    """
    query = db.query(CrossProjectLearning).filter(
        CrossProjectLearning.similarity_score >= min_similarity
    )
    
    if applied is not None:
        query = query.filter(CrossProjectLearning.applied == applied)
    
    opportunities = query.order_by(
        desc(CrossProjectLearning.similarity_score)
    ).offset(skip).limit(limit).all()
    
    result = []
    for opp in opportunities:
        source_project = db.query(Project).filter(
            Project.project_id == opp.source_project_id
        ).first()
        target_project = db.query(Project).filter(
            Project.project_id == opp.target_project_id
        ).first()
        pattern = db.query(LearnedPattern).filter(
            LearnedPattern.pattern_id == opp.pattern_id
        ).first()
        
        if source_project and target_project and pattern:
            result.append(CrossProjectOpportunity(
                learning_id=opp.learning_id,
                source_project=ProjectResponse.from_orm(source_project),
                target_project=ProjectResponse.from_orm(target_project),
                pattern=LearnedPatternResponse.from_orm(pattern),
                similarity_score=opp.similarity_score,
                applied=opp.applied,
                created_at=opp.created_at
            ))
    
    return result


# ===== WORKER STATS ENDPOINTS =====

@router.get("/workers/stats", response_model=List[WorkerStatsResponse])
async def get_all_worker_stats(db: Session = Depends(get_db)):
    """Get performance statistics for all workers"""
    stats = db.query(WorkerStats).order_by(WorkerStats.worker_name).all()
    return [WorkerStatsResponse.from_orm(s) for s in stats]


@router.get("/workers/{worker_name}/stats", response_model=WorkerStatsResponse)
async def get_worker_stats(worker_name: str, db: Session = Depends(get_db)):
    """Get performance statistics for a specific worker"""
    stats = db.query(WorkerStats).filter(WorkerStats.worker_name == worker_name).first()
    if not stats:
        raise HTTPException(status_code=404, detail=f"No stats found for worker: {worker_name}")
    return WorkerStatsResponse.from_orm(stats)


# ===== SYSTEM HEALTH ENDPOINTS =====

@router.get("/health")
async def agent_system_health(db: Session = Depends(get_db)):
    """
    Check health of the SIGMA agent system.
    
    Returns:
    - System status
    - Recent activity
    - Worker health
    - Pending actions
    """
    try:
        # Check recent activity
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        recent_proposals = db.query(func.count(Proposal.proposal_id)).filter(
            Proposal.created_at >= one_hour_ago
        ).scalar() or 0
        
        recent_experiments = db.query(func.count(Experiment.experiment_id)).filter(
            Experiment.created_at >= one_hour_ago
        ).scalar() or 0
        
        # Check pending actions
        pending_proposals = db.query(func.count(Proposal.proposal_id)).filter(
            Proposal.status == 'pending'
        ).scalar() or 0
        
        # Check worker health
        worker_stats = db.query(WorkerStats).all()
        workers_with_errors = sum(1 for w in worker_stats if w.errors > 0)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "activity": {
                "recent_proposals": recent_proposals,
                "recent_experiments": recent_experiments,
                "pending_proposals": pending_proposals
            },
            "workers": {
                "total": len(worker_stats),
                "with_errors": workers_with_errors,
                "healthy": len(worker_stats) - workers_with_errors
            }
        }
    except Exception as e:
        logger.error(f"Error checking system health: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }
