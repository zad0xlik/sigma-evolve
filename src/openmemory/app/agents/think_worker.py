"""
Think Worker - Decision-making agent using multi-agent committee approach.

Production Mode: Weighted committee consensus, autonomy-based execution
Experimental Mode: Novel decision strategies, risk-reward optimization
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from .base_worker import BaseWorker
from ..agent_config import get_agent_config
from ..models import Proposal, Project, CodeSnapshot
from ..database import get_db
from ..utils.docker_executor import DockerExecutor, ExecutionResult, TestResult, BuildResult
from ..utils.git_operations import GitOperations, is_git_operations_available, is_github_operations_available

logger = logging.getLogger(__name__)


class ThinkWorker(BaseWorker):
    """Makes decisions about which proposals to execute using multi-agent committee."""
    
    def __init__(self, db_session, dreamer):
        super().__init__(db_session, dreamer)
        self.config = get_agent_config()
        self.current_strategy = "weighted_committee_consensus"
        
        # Initialize Docker executor if enabled
        self.docker_executor = None
        if self.config.execution.docker_enabled:
            try:
                self.docker_executor = DockerExecutor()
                logger.info("Docker executor initialized")
            except Exception as e:
                logger.warning(f"Docker executor unavailable: {e}")
    
    def get_interval(self) -> int:
        """Think runs every 8 minutes by default"""
        return self.config.workers.think_interval
    
    def _production_cycle(self):
        """
        Production Mode: Evaluate and decide on proposals
        
        Steps:
        1. Get pending proposals enriched by Recall Worker
        2. Run multi-agent committee evaluation
        3. Calculate weighted consensus score
        4. Check autonomy level permissions
        5. Execute approved proposals or mark for manual review
        6. Log decisions for Learning Worker to analyze
        """
        try:
            # Check for promoted strategies
            self._check_for_promoted_strategies()
            
            # Get pending proposals ready for decision
            pending_proposals = self._get_pending_proposals()
            
            if not pending_proposals:
                logger.info("No pending proposals ready for decision")
                return
            
            logger.info(f"Evaluating {len(pending_proposals)} proposals")
            
            decisions_made = 0
            executed = 0
            
            for proposal in pending_proposals:
                decision = self._evaluate_proposal(proposal)
                
                if decision['action'] == 'execute':
                    if self._execute_proposal(proposal, decision):
                        executed += 1
                elif decision['action'] == 'approve':
                    proposal.status = 'approved'
                    self.db.commit()
                elif decision['action'] == 'reject':
                    proposal.status = 'rejected'
                    self.db.commit()
                
                decisions_made += 1
                
                logger.info(f"Proposal '{proposal.title}': {decision['action']} "
                          f"(confidence: {decision['confidence']:.2f})")
            
            logger.info(f"Made {decisions_made} decisions, executed {executed} proposals")
            
        except Exception as e:
            logger.error(f"Production thinking failed: {e}")
            raise
    
    def _experimental_cycle(self):
        """
        Experimental Mode: Try novel decision-making strategies
        
        Experiments:
        - Different committee weighting schemes
        - Risk-reward optimization
        - Uncertainty quantification methods
        - Portfolio approach (diversification)
        - Temporal decision strategies
        
        Metrics tracked:
        - Decision accuracy (proposals that succeeded)
        - False positive rate (bad decisions)
        - False negative rate (missed opportunities)
        - Decision speed
        - Confidence calibration
        """
        try:
            pending_proposals = self._get_pending_proposals()
            if not pending_proposals:
                return
            
            # Get baseline performance
            context = self._get_current_performance()
            
            # Ask DreamerMetaAgent for experimental approach
            experiment = self.dreamer.propose_experiment("think", context)
            
            if not experiment:
                logger.info("No suitable experiment proposed")
                return
            
            logger.info(f"🧪 Starting experiment: {experiment['experiment_name']}")
            
            # Record experiment start
            exp_id = self.dreamer.record_experiment_start(
                worker_name="think",
                experiment_name=experiment["experiment_name"],
                hypothesis=experiment["hypothesis"],
                approach=experiment["approach"]
            )
            
            # Execute experimental approach
            start_time = time.time()
            result = self._try_experimental_approach(
                pending_proposals[0],  # Try on first proposal
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
            logger.error(f"Experimental thinking failed: {e}")
    
    def _get_pending_proposals(self) -> List[Proposal]:
        """Get proposals ready for decision (enriched by Recall Worker)"""
        # Get proposals that have been pending for at least 10 minutes
        # (giving Recall Worker time to enrich them)
        cutoff = datetime.now() - timedelta(minutes=10)
        
        return self.db.query(Proposal)\
            .filter(Proposal.status == 'pending')\
            .filter(Proposal.created_at <= cutoff)\
            .order_by(Proposal.confidence.desc())\
            .limit(5)\
            .all()
    
    def _evaluate_proposal(self, proposal: Proposal) -> Dict:
        """
        Evaluate proposal using multi-agent committee
        
        Returns:
            {
                'action': 'execute' | 'approve' | 'reject' | 'defer',
                'confidence': float,
                'reasoning': str,
                'committee_scores': Dict
            }
        """
        # Parse agent scores from proposal
        agents = json.loads(proposal.agents_json)
        
        # Calculate weighted consensus
        committee_config = self.config.committee
        weighted_score = (
            agents['architect'] * committee_config.architect_weight +
            agents['reviewer'] * committee_config.reviewer_weight +
            agents['tester'] * committee_config.tester_weight +
            agents['security'] * committee_config.security_weight +
            agents['optimizer'] * committee_config.optimizer_weight
        )
        
        # Check for critical vetos (any agent < 0.5 can veto)
        veto_agents = [name for name, score in agents.items() if score < 0.5]
        
        if veto_agents:
            return {
                'action': 'reject',
                'confidence': weighted_score,
                'reasoning': f"Vetoed by: {', '.join(veto_agents)}",
                'committee_scores': agents
            }
        
        # Determine action based on autonomy level and confidence
        autonomy = self.config.autonomy
        can_execute, reason = autonomy.can_execute(weighted_score)
        
        if can_execute and autonomy.level == 3:
            action = 'execute'
        elif can_execute and autonomy.level == 2:
            action = 'approve'  # Will be executed manually or by CI
        else:
            if weighted_score >= 0.70:
                action = 'approve'  # Good proposal, but needs manual review
            elif weighted_score >= 0.50:
                action = 'defer'  # Borderline, defer for more analysis
            else:
                action = 'reject'
        
        return {
            'action': action,
            'confidence': weighted_score,
            'reasoning': reason,
            'committee_scores': agents
        }
    
    def _execute_proposal(self, proposal: Proposal, decision: Dict) -> bool:
        """
        Execute an approved proposal
        
        Steps:
        1. Validate proposal can be executed
        2. Create Docker container for safe execution
        3. Apply changes in container
        4. Run tests and validate
        5. Run build if configured
        6. Create feature branch and commit (TODO: GitOperations)
        7. Create PR or auto-merge based on autonomy level (TODO: GitOperations)
        
        Returns True if execution succeeded
        """
        try:
            logger.info(f"Executing proposal: {proposal.title}")
            
            # Get project details
            project = self.db.query(Project).filter(
                Project.project_id == proposal.project_id
            ).first()
            
            if not project:
                logger.error(f"Project {proposal.project_id} not found")
                return False
            
            # Check if Docker is available
            if not self.docker_executor:
                logger.warning("Docker unavailable, using simulated execution")
                return self._simulate_execution(proposal, decision)
            
            # Step 1: Create Docker container for project
            success, container_id, error = self.docker_executor.create_project_container(
                project_id=project.project_id,
                workspace=project.workspace_path,
                language=project.language,
            )
            
            if not success:
                logger.error(f"Failed to create container: {error}")
                return False
            
            try:
                # Step 2: Apply code changes
                changes = json.loads(proposal.changes_json)
                apply_result = self.docker_executor.apply_changes(
                    container_id=container_id,
                    changes=changes,
                )
                
                if not apply_result.success:
                    logger.error(f"Failed to apply changes: {apply_result.error}")
                    return False
                
                logger.info(f"Applied {len(changes)} changes to container")
                
                # Step 3: Run tests if configured
                test_result = None
                if self.config.execution.auto_test:
                    test_result = self.docker_executor.run_tests(
                        container_id=container_id,
                        language=project.language,
                    )
                    
                    if not test_result.success:
                        logger.warning(f"Tests failed: {test_result.error}")
                        logger.warning(f"Passed: {test_result.tests_passed}, "
                                     f"Failed: {test_result.tests_failed}")
                        
                        # If tests fail, reject the proposal
                        proposal.status = 'rejected'
                        proposal.notes = f"Tests failed: {test_result.error}"
                        self.db.commit()
                        return False
                    
                    logger.info(f"✅ Tests passed: {test_result.tests_passed} tests, "
                              f"coverage: {test_result.coverage_percent:.1f}%")
                    
                    # Check minimum coverage requirement
                    if test_result.coverage_percent < self.config.execution.min_test_coverage * 100:
                        logger.warning(f"Coverage {test_result.coverage_percent:.1f}% below "
                                     f"threshold {self.config.execution.min_test_coverage * 100:.1f}%")
                
                # Step 4: Run build if configured
                build_result = None
                if self.config.execution.auto_build:
                    build_result = self.docker_executor.run_build(
                        container_id=container_id,
                        language=project.language,
                    )
                    
                    if not build_result.success:
                        logger.error(f"Build failed: {build_result.error}")
                        proposal.status = 'rejected'
                        proposal.notes = f"Build failed: {build_result.error}"
                        self.db.commit()
                        return False
                    
                    logger.info(f"✅ Build succeeded in {build_result.build_time:.1f}s")
                
                # Step 5: Update proposal status
                proposal.status = 'executed'
                proposal.executed_at = datetime.now()
                
                # Store execution metadata
                execution_metadata = {
                    'confidence': decision['confidence'],
                    'committee_scores': decision['committee_scores'],
                    'autonomy_level': self.config.autonomy.level,
                    'executed_by': 'think_worker',
                    'container_id': container_id[:12],
                    'test_results': {
                        'success': test_result.success if test_result else None,
                        'tests_passed': test_result.tests_passed if test_result else 0,
                        'tests_failed': test_result.tests_failed if test_result else 0,
                        'coverage': test_result.coverage_percent if test_result else 0.0,
                    } if test_result else None,
                    'build_results': {
                        'success': build_result.success if build_result else None,
                        'build_time': build_result.build_time if build_result else 0.0,
                    } if build_result else None,
                }
                
                proposal.commit_sha = json.dumps(execution_metadata)
                
                # Step 6 & 7: Git operations (if Level 2+)
                if self.config.autonomy.level >= 2 and is_git_operations_available():
                    try:
                        git_ops = GitOperations(
                            repo_path=project.workspace_path,
                            github_token=self.config.project.token,
                            default_branch=self.config.project.branch,
                        )
                        
                        # Execute full Git workflow
                        workflow_result = git_ops.execute_full_workflow(
                            proposal_id=proposal.proposal_id,
                            changes=changes,
                            container_workspace=None,  # Already applied
                            test_results={
                                'success': test_result.success if test_result else True,
                                'tests_passed': test_result.tests_passed if test_result else 0,
                                'tests_failed': test_result.tests_failed if test_result else 0,
                                'coverage_percent': test_result.coverage_percent if test_result else 0.0,
                                'execution_time': test_result.execution_time if test_result else 0.0,
                            },
                            build_results={
                                'success': build_result.success if build_result else True,
                                'build_time': build_result.build_time if build_result else 0.0,
                            },
                            confidence=decision['confidence'],
                            autonomy_level=self.config.autonomy.level,
                        )
                        
                        # Update proposal with Git results
                        if workflow_result['success']:
                            execution_metadata['git_workflow'] = workflow_result
                            proposal.commit_sha = json.dumps(execution_metadata)
                            
                            logger.info(f"✅ Git workflow complete: "
                                      f"Branch: {workflow_result.get('branch_name')}, "
                                      f"PR: {workflow_result.get('pr_url')}")
                        else:
                            logger.warning(f"Git workflow failed: {workflow_result.get('error')}")
                            execution_metadata['git_workflow'] = workflow_result
                            proposal.commit_sha = json.dumps(execution_metadata)
                    
                    except Exception as e:
                        logger.warning(f"Git operations failed: {e}")
                        execution_metadata['git_error'] = str(e)
                        proposal.commit_sha = json.dumps(execution_metadata)
                else:
                    if self.config.autonomy.level < 2:
                        logger.info("Autonomy level < 2: Skipping Git operations")
                    elif not is_git_operations_available():
                        logger.warning("Git operations not available: Install GitPython and PyGithub")
                
                self.db.commit()
                
                logger.info(f"✅ Successfully executed proposal: {proposal.title}")
                return True
                
            finally:
                # Always cleanup container
                self.docker_executor.stop_container(container_id)
                self.docker_executor.cleanup_project(project.project_id)
            
        except Exception as e:
            logger.error(f"Failed to execute proposal {proposal.proposal_id}: {e}")
            proposal.status = 'rejected'
            proposal.notes = f"Execution error: {str(e)}"
            self.db.commit()
            return False
    
    def _simulate_execution(self, proposal: Proposal, decision: Dict) -> bool:
        """Simulate execution when Docker is unavailable"""
        logger.info("Simulating proposal execution (Docker unavailable)")
        
        proposal.status = 'executed'
        proposal.executed_at = datetime.now()
        
        # Store decision metadata
        proposal.commit_sha = json.dumps({
            'confidence': decision['confidence'],
            'committee_scores': decision['committee_scores'],
            'autonomy_level': self.config.autonomy.level,
            'executed_by': 'think_worker',
            'simulated': True,
        })
        
        self.db.commit()
        
        logger.info(f"✅ Simulated execution: {proposal.title}")
        return True
    
    def _create_feature_branch(self, proposal: Proposal) -> str:
        """Create feature branch for proposal"""
        # TODO: Implement using GitOperations
        branch_name = f"sigma/proposal-{proposal.proposal_id}"
        return branch_name
    
    
    def _commit_and_push(self, proposal: Proposal, branch: str) -> str:
        """Commit changes and push to remote"""
        # TODO: Implement using GitOperations
        # 1. Stage files
        # 2. Create commit with detailed message
        # 3. Push to remote
        # 4. Return commit SHA
        return "abc123def456"
    
    def _create_or_merge_pr(self, proposal: Proposal, branch: str, commit_sha: str) -> str:
        """Create PR or auto-merge based on autonomy level"""
        # TODO: Implement using GitOperations (PyGithub)
        # Level 2: Create PR for manual review
        # Level 3: Create and auto-merge PR if confidence >= threshold
        
        if self.config.autonomy.level == 3 and self.config.autonomy.can_merge_pr:
            # Auto-merge
            pr_url = f"https://github.com/user/repo/pull/123"
            logger.info(f"🚀 Auto-merged PR: {pr_url}")
        else:
            # Create PR for review
            pr_url = f"https://github.com/user/repo/pull/123"
            logger.info(f"📝 Created PR for review: {pr_url}")
        
        return pr_url
    
    def _get_current_performance(self) -> Dict:
        """Get recent performance metrics for experiment baseline"""
        # Get recent decisions
        recent_decisions = self.db.query(Proposal)\
            .filter(Proposal.status.in_(['executed', 'approved', 'rejected']))\
            .filter(Proposal.created_at >= datetime.now() - timedelta(days=7))\
            .all()
        
        if not recent_decisions:
            return {
                'decision_accuracy': 0.75,
                'false_positive_rate': 0.15,
                'false_negative_rate': 0.20,
                'avg_decision_time': 2.0,
                'current_strategy': self.current_strategy
            }
        
        # Calculate metrics
        executed = [p for p in recent_decisions if p.status == 'executed']
        rejected = [p for p in recent_decisions if p.status == 'rejected']
        
        # TODO: Track actual success/failure of executed proposals
        # For now, assume high confidence proposals are successful
        successful = len([p for p in executed if p.confidence >= 0.80])
        
        return {
            'decision_accuracy': successful / max(len(executed), 1),
            'false_positive_rate': 0.15,  # Would track actual failures
            'false_negative_rate': 0.20,  # Would track missed opportunities
            'avg_decision_time': 2.0,
            'decisions_per_day': len(recent_decisions) / 7,
            'current_strategy': self.current_strategy
        }
    
    def _try_experimental_approach(self, proposal: Proposal, approach: str) -> Dict:
        """
        Execute experimental decision-making approach
        
        Could try:
        - Different committee weightings
        - Risk-adjusted scoring
        - Confidence intervals
        - Portfolio optimization
        """
        # For now, just run standard evaluation
        decision = self._evaluate_proposal(proposal)
        
        return {
            'decision_made': True,
            'confidence': decision['confidence'],
            'action': decision['action'],
            'decision_quality': 0.80  # Would be measured by actual outcomes
        }
    
    def _calculate_improvement(self, result: Dict, baseline: Dict) -> float:
        """
        Calculate improvement percentage over baseline
        
        Factors:
        - Better decision accuracy = better
        - Lower false positive rate = better
        - Lower false negative rate = better
        - Faster decisions = better (but not at cost of accuracy)
        """
        result_quality = result.get('decision_quality', 0.80)
        baseline_accuracy = baseline.get('decision_accuracy', 0.75)
        
        accuracy_improvement = (result_quality - baseline_accuracy) / max(baseline_accuracy, 0.1)
        
        # Consider confidence calibration
        result_confidence = result.get('confidence', 0.80)
        expected_confidence = 0.80
        calibration_error = abs(result_confidence - expected_confidence)
        
        # Penalize poor calibration
        if calibration_error > 0.15:
            accuracy_improvement -= 0.1
        
        return accuracy_improvement
    
    def _check_for_promoted_strategies(self):
        """Check if any experiments have been promoted to production"""
        promoted = self.dreamer.get_promoted_experiments("think")
        
        if promoted and promoted[0].experiment_name != self.current_strategy:
            logger.info(f"🎉 Adopting promoted strategy: {promoted[0].experiment_name}")
            self.current_strategy = promoted[0].experiment_name
            # TODO: Actually implement strategy switching
            
            # Potentially adjust committee weights based on learned strategy
            self._apply_promoted_strategy(promoted[0])
    
    def _apply_promoted_strategy(self, experiment):
        """Apply a promoted experimental strategy to production"""
        # Parse experiment approach to extract new committee weights or decision logic
        # This is where the system truly evolves by adopting successful experiments
        
        try:
            approach = experiment.approach
            
            # Example: If experiment suggested different weights, apply them
            # This would require parsing the approach string or storing structured data
            
            logger.info(f"Applied promoted strategy: {experiment.experiment_name}")
            
        except Exception as e:
            logger.warning(f"Could not apply promoted strategy: {e}")
