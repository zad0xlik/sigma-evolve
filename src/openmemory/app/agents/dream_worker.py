"""
Dream Worker - Generates creative code improvement proposals.

Production Mode: LLM-powered proposals based on analysis results
Experimental Mode: Novel proposal generation strategies, multi-agent reasoning
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import logging

from .base_worker import BaseWorker
from ..agent_config import get_agent_config
from ..models import Project, CodeSnapshot, Proposal
from ..database import get_db

logger = logging.getLogger(__name__)


class DreamWorker(BaseWorker):
    """Generates creative proposals for code improvements."""
    
    def __init__(self, db_session, dreamer):
        super().__init__(db_session, dreamer)
        self.config = get_agent_config()
        self.current_strategy = "single_agent_proposals"
    
    def get_interval(self) -> int:
        """Dream runs every 4 minutes by default"""
        return self.config.workers.dream_interval
    
    def _production_cycle(self):
        """
        Production Mode: Generate proposals based on recent analysis
        
        Steps:
        1. Get latest code snapshot from Analysis Worker
        2. If issues found, generate improvement proposals using LLM
        3. Score proposals using confidence metrics
        4. Store proposals in DB with status='pending'
        5. Later, Think Worker will decide which to execute
        """
        try:
            # Check for promoted strategies
            self._check_for_promoted_strategies()
            
            # Get latest analysis results
            latest_snapshot = self._get_latest_snapshot()
            if not latest_snapshot:
                logger.info("No analysis results available for dreaming")
                return
            
            # Skip if no issues found
            if latest_snapshot.issues_found == 0:
                logger.info("No issues found in latest analysis, skipping proposals")
                return
            
            logger.info(f"Generating proposals for {latest_snapshot.issues_found} issues")
            
            # Generate proposals using LLM
            proposals = self._generate_proposals(latest_snapshot)
            
            # Store proposals
            for proposal_data in proposals:
                self._store_proposal(latest_snapshot.project_id, proposal_data)
            
            logger.info(f"Generated {len(proposals)} proposals")
            
        except Exception as e:
            logger.error(f"Production dreaming failed: {e}")
            raise
    
    def _experimental_cycle(self):
        """
        Experimental Mode: Try novel proposal generation strategies
        
        Experiments:
        - Multi-agent reasoning (architect + reviewer consensus)
        - Chain-of-thought prompting
        - Few-shot learning with successful past proposals
        - Temperature/creativity variations
        - Structured vs freeform proposal formats
        
        Metrics tracked:
        - Proposal quality (acceptance rate by Think Worker)
        - Execution success rate
        - Innovation score (novelty of approach)
        - Confidence calibration
        """
        try:
            latest_snapshot = self._get_latest_snapshot()
            if not latest_snapshot or latest_snapshot.issues_found == 0:
                return
            
            # Get baseline performance
            context = self._get_current_performance()
            
            # Ask DreamerMetaAgent for experimental approach
            experiment = self.dreamer.propose_experiment("dream", context)
            
            if not experiment:
                logger.info("No suitable experiment proposed")
                return
            
            logger.info(f"🧪 Starting experiment: {experiment['experiment_name']}")
            
            # Record experiment start
            exp_id = self.dreamer.record_experiment_start(
                worker_name="dream",
                experiment_name=experiment["experiment_name"],
                hypothesis=experiment["hypothesis"],
                approach=experiment["approach"]
            )
            
            # Execute experimental approach
            start_time = time.time()
            result = self._try_experimental_approach(
                latest_snapshot,
                experiment["approach"]
            )
            elapsed = time.time() - start_time
            
            # Calculate improvement vs baseline
            improvement = self._calculate_improvement(result, context)
            
            # Record outcome
            self.dreamer.record_outcome(
                experiment_id=exp_id,
                success=improvement > 0,
                improvement=improvement,
                details={
                    "result_metrics": result,
                    "baseline_metrics": context,
                    "elapsed_time": elapsed
                }
            )
            
            logger.info(f"Experiment complete: improvement={improvement:.2%}")
            
        except Exception as e:
            logger.error(f"Experimental dreaming failed: {e}")
    
    def _get_latest_snapshot(self) -> Optional[CodeSnapshot]:
        """Get the most recent code analysis snapshot"""
        return self.db.query(CodeSnapshot)\
            .order_by(CodeSnapshot.created_at.desc())\
            .first()
    
    def _generate_proposals(self, snapshot: CodeSnapshot) -> List[Dict]:
        """
        Generate code improvement proposals using LLM
        
        Returns list of proposals, each containing:
            {
                'title': str,
                'description': str,
                'agents': Dict,  # Multi-agent committee scores
                'changes': Dict,  # Proposed code changes
                'confidence': float,
                'critic_score': float
            }
        """
        # Parse issues from snapshot metrics
        metrics = json.loads(snapshot.metrics_json)
        issues = metrics.get('issues', [])
        
        if not issues:
            return []
        
        proposals = []
        
        # Group issues by severity
        error_issues = [i for i in issues if i.get('severity') == 'error']
        warning_issues = [i for i in issues if i.get('severity') == 'warning']
        
        # Generate proposals for errors (high priority)
        if error_issues:
            proposal = self._generate_error_fix_proposal(error_issues, snapshot)
            if proposal:
                proposals.append(proposal)
        
        # Generate proposals for warnings (lower priority)
        if warning_issues and len(warning_issues) <= 10:  # Batch small warning sets
            proposal = self._generate_warning_fix_proposal(warning_issues, snapshot)
            if proposal:
                proposals.append(proposal)
        
        # Generate refactoring proposals if complexity is high
        if snapshot.complexity > 10:
            proposal = self._generate_refactoring_proposal(snapshot)
            if proposal:
                proposals.append(proposal)
        
        return proposals
    
    def _generate_error_fix_proposal(self, issues: List[Dict], snapshot: CodeSnapshot) -> Optional[Dict]:
        """Generate proposal to fix error-level issues"""
        # In a real implementation, this would call an LLM
        # For now, create a structured proposal
        
        issue_summary = "\n".join([
            f"- {issue['file']}:{issue['line']}: {issue['message']}"
            for issue in issues[:5]  # Limit to first 5
        ])
        
        return {
            'title': f"Fix {len(issues)} Critical Error(s)",
            'description': f"Resolve the following critical errors:\n{issue_summary}",
            'agents': {
                'architect': 0.85,
                'reviewer': 0.80,
                'tester': 0.90,
                'security': 0.75,
                'optimizer': 0.70
            },
            'changes': {
                'files_affected': list(set(i['file'] for i in issues)),
                'change_type': 'bug_fix',
                'estimated_lines': len(issues) * 3  # Rough estimate
            },
            'confidence': 0.85,
            'critic_score': 0.80
        }
    
    def _generate_warning_fix_proposal(self, issues: List[Dict], snapshot: CodeSnapshot) -> Optional[Dict]:
        """Generate proposal to fix warning-level issues"""
        issue_summary = "\n".join([
            f"- {issue['file']}:{issue['line']}: {issue['message']}"
            for issue in issues[:5]
        ])
        
        return {
            'title': f"Address {len(issues)} Code Warning(s)",
            'description': f"Improve code quality by addressing:\n{issue_summary}",
            'agents': {
                'architect': 0.70,
                'reviewer': 0.85,
                'tester': 0.75,
                'security': 0.65,
                'optimizer': 0.80
            },
            'changes': {
                'files_affected': list(set(i['file'] for i in issues)),
                'change_type': 'code_quality',
                'estimated_lines': len(issues) * 2
            },
            'confidence': 0.75,
            'critic_score': 0.70
        }
    
    def _generate_refactoring_proposal(self, snapshot: CodeSnapshot) -> Optional[Dict]:
        """Generate proposal to refactor complex code"""
        return {
            'title': f"Refactor High Complexity Code",
            'description': f"Current average complexity: {snapshot.complexity:.2f}. "
                          f"Refactor to reduce complexity and improve maintainability.",
            'agents': {
                'architect': 0.90,
                'reviewer': 0.75,
                'tester': 0.80,
                'security': 0.70,
                'optimizer': 0.95
            },
            'changes': {
                'files_affected': [],  # Would be determined from analysis
                'change_type': 'refactoring',
                'estimated_lines': 50
            },
            'confidence': 0.70,
            'critic_score': 0.75
        }
    
    def _store_proposal(self, project_id: int, proposal_data: Dict):
        """Store proposal in database"""
        # Calculate weighted confidence from agent committee
        agents = proposal_data['agents']
        committee_config = self.config.committee
        
        weighted_confidence = (
            agents['architect'] * committee_config.architect_weight +
            agents['reviewer'] * committee_config.reviewer_weight +
            agents['tester'] * committee_config.tester_weight +
            agents['security'] * committee_config.security_weight +
            agents['optimizer'] * committee_config.optimizer_weight
        )
        
        proposal = Proposal(
            project_id=project_id,
            title=proposal_data['title'],
            description=proposal_data['description'],
            agents_json=json.dumps(proposal_data['agents']),
            changes_json=json.dumps(proposal_data['changes']),
            confidence=weighted_confidence,
            critic_score=proposal_data['critic_score'],
            status='pending',
            created_at=datetime.now()
        )
        
        self.db.add(proposal)
        self.db.commit()
        
        logger.info(f"Stored proposal: '{proposal.title}' (confidence={weighted_confidence:.2f})")
    
    def _get_current_performance(self) -> Dict:
        """Get recent performance metrics for experiment baseline"""
        # Get recent proposals
        recent_proposals = self.db.query(Proposal)\
            .order_by(Proposal.created_at.desc())\
            .limit(20)\
            .all()
        
        if not recent_proposals:
            return {
                'avg_confidence': 0.75,
                'acceptance_rate': 0.60,
                'execution_success_rate': 0.70,
                'avg_proposals_per_run': 2.0,
                'current_strategy': self.current_strategy
            }
        
        # Calculate metrics
        executed = [p for p in recent_proposals if p.status == 'executed']
        approved = [p for p in recent_proposals if p.status in ['approved', 'executed']]
        
        return {
            'avg_confidence': sum(p.confidence for p in recent_proposals) / len(recent_proposals),
            'acceptance_rate': len(approved) / len(recent_proposals) if recent_proposals else 0.0,
            'execution_success_rate': len(executed) / max(len(approved), 1),
            'avg_proposals_per_run': len(recent_proposals) / 10,  # Last 10 runs
            'current_strategy': self.current_strategy
        }
    
    def _try_experimental_approach(self, snapshot: CodeSnapshot, approach: str) -> Dict:
        """
        Execute experimental proposal generation approach
        
        Could try:
        - Different prompting strategies
        - Multi-agent reasoning
        - Few-shot learning
        - Different LLM models/temperatures
        """
        # For now, just run standard generation
        proposals = self._generate_proposals(snapshot)
        
        return {
            'proposals_generated': len(proposals),
            'avg_confidence': sum(p['confidence'] for p in proposals) / max(len(proposals), 1),
            'proposal_quality_score': 0.75  # Would be determined by Think Worker acceptance
        }
    
    def _calculate_improvement(self, result: Dict, baseline: Dict) -> float:
        """
        Calculate improvement percentage over baseline
        
        Factors:
        - Higher confidence proposals = better
        - More proposals generated = better (up to a point)
        - Better acceptance rate = better (requires tracking)
        """
        result_confidence = result.get('avg_confidence', 0.75)
        baseline_confidence = baseline.get('avg_confidence', 0.75)
        
        confidence_improvement = (result_confidence - baseline_confidence) / max(baseline_confidence, 0.1)
        
        # Bonus for generating more proposals (but diminishing returns)
        result_count = result.get('proposals_generated', 2)
        baseline_count = baseline.get('avg_proposals_per_run', 2)
        count_improvement = (result_count - baseline_count) / max(baseline_count, 1)
        count_improvement = min(count_improvement, 0.5)  # Cap at 50% bonus
        
        total_improvement = confidence_improvement * 0.7 + count_improvement * 0.3
        
        return total_improvement
    
    def _check_for_promoted_strategies(self):
        """Check if any experiments have been promoted to production"""
        promoted = self.dreamer.get_promoted_experiments("dream")
        
        if promoted and promoted[0].experiment_name != self.current_strategy:
            logger.info(f"🎉 Adopting promoted strategy: {promoted[0].experiment_name}")
            self.current_strategy = promoted[0].experiment_name
            # TODO: Actually implement strategy switching
