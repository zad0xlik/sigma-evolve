"""
SIGMA Agent System API Router

Provides endpoints for monitoring and controlling the SIGMA agent system:
- Dashboard: Worker stats, system health, recent activities
- Proposals: List, review, approve/reject improvement proposals
- Experiments: Track experimental work and results
- Patterns: View learned patterns and cross-project opportunities
- Projects: Manage projects being improved
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..database import get_db, get_worker_db
from ..log_broadcaster import get_log_broadcaster
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

class ProjectCreateRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main", description="Branch to analyze")
    workspace_path: Optional[str] = Field(None, description="Optional: Override auto-clone path")
    language: str = Field(..., description="Primary programming language")
    framework: Optional[str] = Field(None, description="Framework used (e.g., fastapi, react)")
    domain: Optional[str] = Field(None, description="Project domain (e.g., web-app, ml)")
    force_reclone: bool = Field(default=False, description="Force re-clone if exists")


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
            worker_stats=[WorkerStatsResponse.model_validate(ws) for ws in worker_stats],
            recent_proposals=[ProposalResponse.model_validate(p) for p in recent_proposals],
            recent_experiments=[ExperimentResponse.model_validate(e) for e in recent_experiments]
        )
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard data: {str(e)}")


# ===== PROJECT ENDPOINTS =====

@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: ProjectCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new project for SIGMA to track and analyze.
    
    **Auto-Clone Behavior:**
    - If workspace_path NOT provided: Clones repo to AGENT_WORKSPACE_ROOT/{repo-name}
    - If workspace_path provided: Uses that path (assumes code already there)
    - If force_reclone=True: Deletes existing clone and re-clones fresh
    
    **Example:**
    ```json
    {
      "repo_url": "https://github.com/zad0xlik/sigma-evolve.git",
      "branch": "main",
      "language": "Python",
      "framework": "crewai"
    }
    ```
    
    → System auto-clones to `/workspace/sigma-evolve/`
    """
    try:
        # Import GitOperations for auto-clone
        from ..utils.git_operations import GitOperations
        import os
        
        # Get workspace root from environment
        workspace_root = os.getenv('AGENT_WORKSPACE_ROOT', '/workspace')
        
        # Determine final workspace path
        if request.workspace_path:
            # User provided explicit path (advanced use case)
            final_workspace_path = request.workspace_path
            repo_name = request.repo_url.rstrip('/').split('/')[-1].replace('.git', '')
            clone_result = {'success': True, 'message': 'Using provided workspace path'}
            logger.info(f"Using provided workspace path: {final_workspace_path}")
        else:
            # Auto-clone to workspace directory
            logger.info(f"Auto-cloning {request.repo_url} to {workspace_root}")
            
            clone_result = GitOperations.clone_repository(
                workspace_root=workspace_root,
                repo_url=request.repo_url,
                branch=request.branch,
                force=request.force_reclone
            )
            
            if not clone_result['success']:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to clone repository: {clone_result.get('message', 'Unknown error')}"
                )
            
            final_workspace_path = clone_result['workspace_path']
            repo_name = clone_result['repo_name']
            
            if clone_result.get('already_existed'):
                logger.info(f"Repository already exists at: {final_workspace_path}")
            else:
                logger.info(f"Successfully cloned {repo_name} to {final_workspace_path}")
        
        # Create project record
        new_project = Project(
            repo_url=request.repo_url,
            branch=request.branch,
            workspace_path=final_workspace_path,
            language=request.language,
            framework=request.framework,
            domain=request.domain,
            created_at=datetime.now(timezone.utc),
            last_analyzed=None
        )
        
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        logger.info(
            f"Created project {new_project.project_id}: {repo_name} " 
            f"(cloned: {not clone_result.get('already_existed', False)})"
        )
        
        return ProjectResponse.model_validate(new_project)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


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
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get details for a specific project"""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.delete("/projects/{project_id}")
async def delete_project(project_id: int, db: Session = Depends(get_db)):
    """
    Delete a project and all associated data.
    
    This will delete:
    - The project record
    - All proposals for this project
    - All code snapshots
    - All worker stats for this project
    - Cross-project learning records (both source and target)
    
    Warning: This action cannot be undone!
    """
    try:
        # Check if project exists
        project = db.query(Project).filter(Project.project_id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Count related records before deletion
        proposals_count = db.query(func.count(Proposal.proposal_id)).filter(
            Proposal.project_id == project_id
        ).scalar() or 0
        
        # Delete related records (cascade)
        # Note: If foreign key constraints are set up with CASCADE, 
        # this will happen automatically. Otherwise, we do it manually.
        
        # Delete proposals
        db.query(Proposal).filter(Proposal.project_id == project_id).delete()
        
        # Delete code snapshots
        from ..models import CodeSnapshot
        db.query(CodeSnapshot).filter(CodeSnapshot.project_id == project_id).delete()
        
        # Note: WorkerStats doesn't have project_id - it tracks global worker performance
        # No need to delete worker stats when deleting a project
        
        # Delete cross-project learning records
        db.query(CrossProjectLearning).filter(
            (CrossProjectLearning.source_project_id == project_id) |
            (CrossProjectLearning.target_project_id == project_id)
        ).delete()
        
        # Finally, delete the project itself
        db.delete(project)
        db.commit()
        
        logger.info(f"Deleted project {project_id} ({project.repo_url}) and {proposals_count} related proposals")
        
        return {
            "success": True,
            "project_id": project_id,
            "message": f"Project '{project.repo_url}' and all related data deleted successfully",
            "deleted_records": {
                "proposals": proposals_count,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")


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
    return [ProposalResponse.model_validate(p) for p in proposals]


@router.get("/proposals/{proposal_id}", response_model=ProposalDetailResponse)
async def get_proposal(proposal_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific proposal"""
    proposal = db.query(Proposal).filter(Proposal.proposal_id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return ProposalDetailResponse.model_validate(proposal)


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
    return [ExperimentResponse.model_validate(e) for e in experiments]


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific experiment"""
    experiment = db.query(Experiment).filter(Experiment.experiment_id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentResponse.model_validate(experiment)


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
    return [LearnedPatternResponse.model_validate(p) for p in patterns]


@router.get("/patterns/{pattern_id}", response_model=LearnedPatternResponse)
async def get_pattern(pattern_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific learned pattern"""
    pattern = db.query(LearnedPattern).filter(LearnedPattern.pattern_id == pattern_id).first()
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return LearnedPatternResponse.model_validate(pattern)


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
                "source_project": ProjectResponse.model_validate(source_project),
                "target_project": ProjectResponse.model_validate(target_project),
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
                source_project=ProjectResponse.model_validate(source_project),
                target_project=ProjectResponse.model_validate(target_project),
                pattern=LearnedPatternResponse.model_validate(pattern),
                similarity_score=opp.similarity_score,
                applied=opp.applied,
                created_at=opp.created_at
            ))
    
    return result


# ===== WORKER CONTROL ENDPOINTS =====

class WorkerStartRequest(BaseModel):
    worker_type: str = Field(..., description="Worker type: analysis, dream, recall, learning, think")
    project_id: int = Field(..., description="Project ID to work on")
    max_iterations: int = Field(default=5, ge=1, le=100, description="Maximum iterations")
    dream_probability: float = Field(default=0.15, ge=0.0, le=1.0, description="Probability of experimental cycles")


class WorkerStartResponse(BaseModel):
    success: bool
    worker_id: str
    worker_type: str
    message: str
    status: str


# Global worker instances - initialized on-demand
_worker_instances = {}
_dreamer_instance = None


def get_or_create_dreamer():
    """Get or create the DreamerMetaAgent singleton"""
    global _dreamer_instance
    if _dreamer_instance is None:
        from ..agents import DreamerMetaAgent
        _dreamer_instance = DreamerMetaAgent()
        logger.info("Created DreamerMetaAgent instance")
    return _dreamer_instance


def get_or_create_worker(worker_type: str, project_id: int, db: Session):
    """Get or create a worker instance"""
    global _worker_instances
    
    worker_key = f"{worker_type}_{project_id}"
    
    if worker_key not in _worker_instances:
        dreamer = get_or_create_dreamer()
        
        from ..agents import (
            AnalysisWorker,
            DreamWorker,
            RecallWorker,
            LearningWorker,
            ThinkWorker
        )
        
        worker_classes = {
            'analysis': AnalysisWorker,
            'dream': DreamWorker,
            'recall': RecallWorker,
            'learning': LearningWorker,
            'think': ThinkWorker
        }
        
        if worker_type not in worker_classes:
            raise ValueError(f"Unknown worker type: {worker_type}")
        
        # Initialize worker with THREAD-LOCAL scoped session (not request-scoped)
        # Workers run in background threads and need persistent sessions
        worker_db = get_worker_db()
        
        # Pass project_id to worker constructor so it knows which project to analyze
        worker = worker_classes[worker_type](worker_db, dreamer, project_id)
        
        _worker_instances[worker_key] = worker
        logger.info(f"Created {worker_type} worker instance for project {project_id}")
    
    return _worker_instances[worker_key]


@router.post("/workers/start", response_model=WorkerStartResponse)
async def start_worker(
    request: WorkerStartRequest,
    db: Session = Depends(get_db)
):
    """
    Start a worker for a specific project.
    
    Workers run in background threads and execute cycles based on their interval.
    Each worker has dual modes: production (main responsibility) and experimental (dreaming).
    
    Args:
        worker_type: Type of worker (analysis, dream, recall, learning, think)
        project_id: Project to work on
        max_iterations: Maximum number of cycles (future enhancement)
        dream_probability: Probability of experimental cycles (future enhancement)
    
    Returns:
        Worker status and identifier
    """
    try:
        # Verify project exists
        project = db.query(Project).filter(Project.project_id == request.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {request.project_id} not found")
        
        # Validate worker type
        valid_workers = ['analysis', 'dream', 'recall', 'learning', 'think']
        if request.worker_type not in valid_workers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid worker type. Must be one of: {', '.join(valid_workers)}"
            )
        
        # Get or create worker
        worker = get_or_create_worker(request.worker_type, request.project_id, db)
        
        # Check if already running
        if worker.is_running():
            return WorkerStartResponse(
                success=True,
                worker_id=f"{request.worker_type}_{request.project_id}",
                worker_type=request.worker_type,
                message=f"{request.worker_type} worker is already running for project {request.project_id}",
                status="already_running"
            )
        
        # Start the worker
        worker.start()
        
        logger.info(f"Started {request.worker_type} worker for project {request.project_id}")
        
        return WorkerStartResponse(
            success=True,
            worker_id=f"{request.worker_type}_{request.project_id}",
            worker_type=request.worker_type,
            message=f"{request.worker_type} worker started successfully for project {request.project_id}",
            status="started"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting worker: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start worker: {str(e)}")


@router.post("/workers/{worker_type}/stop")
async def stop_worker(
    worker_type: str,
    project_id: int = Query(..., description="Project ID"),
    db: Session = Depends(get_db)
):
    """Stop a running worker"""
    try:
        worker_key = f"{worker_type}_{project_id}"
        
        if worker_key not in _worker_instances:
            return {
                "success": False,
                "message": f"Worker {worker_type} for project {project_id} is not running"
            }
        
        worker = _worker_instances[worker_key]
        worker.stop_now()
        
        logger.info(f"Stopped {worker_type} worker for project {project_id}")
        
        return {
            "success": True,
            "message": f"{worker_type} worker stopped successfully"
        }
        
    except Exception as e:
        logger.error(f"Error stopping worker: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop worker: {str(e)}")


@router.get("/workers/status")
async def get_workers_status():
    """Get status of all worker instances"""
    status = {}
    for worker_key, worker in _worker_instances.items():
        status[worker_key] = {
            "running": worker.is_running(),
            "stats": worker.get_stats()
        }
    return status


# ===== WORKER STATS ENDPOINTS =====

@router.get("/workers/stats", response_model=List[WorkerStatsResponse])
async def get_all_worker_stats(db: Session = Depends(get_db)):
    """Get performance statistics for all workers"""
    stats = db.query(WorkerStats).order_by(WorkerStats.worker_name).all()
    return [WorkerStatsResponse.model_validate(s) for s in stats]


@router.get("/workers/{worker_name}/stats", response_model=WorkerStatsResponse)
async def get_worker_stats(worker_name: str, db: Session = Depends(get_db)):
    """Get performance statistics for a specific worker"""
    stats = db.query(WorkerStats).filter(WorkerStats.worker_name == worker_name).first()
    if not stats:
        raise HTTPException(status_code=404, detail=f"No stats found for worker: {worker_name}")
    return WorkerStatsResponse.model_validate(stats)


# ===== GRAPH VISUALIZATION ENDPOINTS =====

@router.get("/graph/project-patterns")
async def get_project_pattern_graph(db: Session = Depends(get_db)):
    """
    Get graph data for Project-Pattern relationships visualization.
    
    Returns nodes and edges for:
    - Projects (sources of patterns)
    - Learned Patterns
    - Cross-project learning opportunities
    """
    try:
        # Get all projects
        projects = db.query(Project).all()
        
        # Get all patterns
        patterns = db.query(LearnedPattern).all()
        
        # Get cross-project learning records
        cross_learning = db.query(CrossProjectLearning).all()
        
        # Build nodes
        nodes = []
        
        # Add project nodes
        for project in projects:
            repo_name = project.repo_url.rstrip('/').split('/')[-1].replace('.git', '')
            nodes.append({
                "id": f"project_{project.project_id}",
                "type": "project",
                "label": repo_name,
                "data": {
                    "project_id": project.project_id,
                    "repo_url": project.repo_url,
                    "language": project.language,
                    "framework": project.framework,
                    "domain": project.domain
                }
            })
        
        # Add pattern nodes
        for pattern in patterns:
            nodes.append({
                "id": f"pattern_{pattern.pattern_id}",
                "type": "pattern",
                "label": pattern.pattern_name,
                "data": {
                    "pattern_id": pattern.pattern_id,
                    "pattern_type": pattern.pattern_type,
                    "confidence": pattern.confidence,
                    "success_count": pattern.success_count,
                    "failure_count": pattern.failure_count,
                    "language": pattern.language,
                    "framework": pattern.framework
                }
            })
        
        # Build edges
        edges = []
        
        # Add edges from projects to patterns they generated
        # (patterns are learned from proposals which belong to projects)
        from ..models import Proposal
        
        for pattern in patterns:
            # Find proposals that created this pattern
            # This is a simplified approach - you may need to add explicit linking
            pattern_proposals = db.query(Proposal).filter(
                Proposal.status == 'executed'
            ).limit(5).all()  # Simplified - real implementation needs pattern->proposal link
            
            for proposal in pattern_proposals:
                edges.append({
                    "source": f"project_{proposal.project_id}",
                    "target": f"pattern_{pattern.pattern_id}",
                    "type": "generates",
                    "data": {
                        "confidence": pattern.confidence
                    }
                })
                break  # One edge per pattern for now
        
        # Add cross-project learning edges
        for learning in cross_learning:
            edges.append({
                "source": f"pattern_{learning.pattern_id}",
                "target": f"project_{learning.target_project_id}",
                "type": "applies_to" if learning.applied else "opportunity",
                "data": {
                    "similarity_score": learning.similarity_score,
                    "applied": learning.applied,
                    "created_at": learning.created_at.isoformat() if learning.created_at else None
                }
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_projects": len(projects),
                "total_patterns": len(patterns),
                "total_connections": len(edges),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating graph data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate graph data: {str(e)}")


# ===== STREAMING LOGS ENDPOINTS =====

@router.get("/logs/stream")
async def stream_worker_logs():
    """
    Stream worker logs in real-time using Server-Sent Events (SSE).
    
    This endpoint establishes a persistent connection and streams worker
    activity logs as they happen. Perfect for live dashboard monitoring.
    
    **Response Format:**
    ```
    data: {"timestamp": "2026-01-18T20:00:00", "worker": "analysis", "level": "info", "message": "...", "metadata": {...}}
    ```
    
    **Usage:**
    ```javascript
    const eventSource = new EventSource('/api/agents/logs/stream');
    eventSource.onmessage = (event) => {
        const log = JSON.parse(event.data);
        console.log(log.worker, log.message);
    };
    ```
    """
    broadcaster = get_log_broadcaster()
    queue = broadcaster.subscribe()
    
    async def event_generator():
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Streaming worker logs', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
            
            # Send recent logs as history
            recent_logs = broadcaster.get_recent_logs(limit=50)
            for log in recent_logs:
                yield f"data: {json.dumps(log)}\n\n"
            
            # Stream new logs as they arrive
            while True:
                try:
                    # Wait for new log event with timeout
                    log_event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(log_event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive ping every 30 seconds
                    yield f": keepalive\n\n"
                except Exception as e:
                    logger.error(f"Error streaming log: {e}")
                    break
        finally:
            # Clean up subscription
            broadcaster.unsubscribe(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/logs/recent")
async def get_recent_logs(
    limit: int = Query(100, ge=1, le=1000, description="Number of recent logs to return")
):
    """
    Get recent worker logs from the buffer.
    
    Returns the most recent logs without establishing a streaming connection.
    Useful for initial page load or polling-based updates.
    """
    broadcaster = get_log_broadcaster()
    logs = broadcaster.get_recent_logs(limit=limit)
    
    return {
        "logs": logs,
        "count": len(logs),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.delete("/logs/clear")
async def clear_log_buffer():
    """
    Clear the log buffer.
    
    Removes all stored logs from memory. Useful for testing or cleanup.
    """
    broadcaster = get_log_broadcaster()
    broadcaster.clear_buffer()
    
    return {
        "success": True,
        "message": "Log buffer cleared successfully",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/logs/stats")
async def get_log_broadcaster_stats():
    """Get statistics about the log broadcaster"""
    broadcaster = get_log_broadcaster()
    stats = broadcaster.get_stats()
    
    return {
        **stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


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
