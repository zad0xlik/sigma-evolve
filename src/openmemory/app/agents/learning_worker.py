"""
Learning Worker - Extracts patterns from executed proposals and stores learnings.

Production Mode: Pattern extraction, cross-project learning
Experimental Mode: Novel pattern recognition, meta-learning strategies
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from .base_worker import BaseWorker
from ..agent_config import get_agent_config
from ..models import (
    Project, Proposal, LearnedPattern, CrossProjectLearning,
    CodeSnapshot
)
from ..database import get_db
from ..utils.cross_project import CrossProjectLearningSystem

logger = logging.getLogger(__name__)


class LearningWorker(BaseWorker):
    """Extracts and stores patterns from successful and failed proposals."""
    
    def __init__(self, db_session, dreamer):
        super().__init__(db_session, dreamer)
        self.config = get_agent_config()
        self.current_strategy = "success_pattern_extraction"
        self.xp_system = CrossProjectLearningSystem(db_session)
    
    def get_interval(self) -> int:
        """Learning runs every 6 minutes by default"""
        return self.config.workers.learning_interval
    
    def _production_cycle(self):
        """
        Production Mode: Learn from executed proposals
        
        Steps:
        1. Get recently executed proposals
        2. Compare before/after metrics to determine success
        3. Extract patterns from successful proposals
        4. Update pattern confidence scores based on outcomes
        5. Identify cross-project learning opportunities
        6. Store learned patterns for future use
        """
        try:
            # Check for promoted strategies
            self._check_for_promoted_strategies()
            
            # Get recently executed proposals
            executed_proposals = self._get_recent_executed_proposals()
            
            if not executed_proposals:
                logger.info("No recently executed proposals to learn from")
                return
            
            logger.info(f"Learning from {len(executed_proposals)} executed proposals")
            
            patterns_learned = 0
            for proposal in executed_proposals:
                if self._extract_and_store_pattern(proposal):
                    patterns_learned += 1
            
            # Update cross-project learnings if enabled
            if self.config.cross_project.enabled:
                self._identify_cross_project_opportunities()
            
            logger.info(f"Extracted {patterns_learned} new patterns")
            
        except Exception as e:
            logger.error(f"Production learning failed: {e}")
            raise
    
    def _experimental_cycle(self):
        """
        Experimental Mode: Try novel learning strategies
        
        Experiments:
        - Different pattern extraction algorithms
        - Meta-learning from failed proposals
        - Temporal pattern evolution tracking
        - Ensemble pattern recognition
        - Transfer learning heuristics
        
        Metrics tracked:
        - Pattern quality (reuse success rate)
        - Pattern generalization (cross-project applicability)
        - Learning speed (patterns per proposal)
        - Confidence calibration accuracy
        """
        try:
            executed_proposals = self._get_recent_executed_proposals()
            if not executed_proposals:
                return
            
            # Get baseline performance
            context = self._get_current_performance()
            
            # Ask DreamerMetaAgent for experimental approach
            experiment = self.dreamer.propose_experiment("learning", context)
            
            if not experiment:
                logger.info("No suitable experiment proposed")
                return
            
            logger.info(f"🧪 Starting experiment: {experiment['experiment_name']}")
            
            # Record experiment start
            exp_id = self.dreamer.record_experiment_start(
                worker_name="learning",
                experiment_name=experiment["experiment_name"],
                hypothesis=experiment["hypothesis"],
                approach=experiment["approach"]
            )
            
            # Execute experimental approach
            start_time = time.time()
            result = self._try_experimental_approach(
                executed_proposals[0],  # Try on first proposal
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
            logger.error(f"Experimental learning failed: {e}")
    
    def _get_recent_executed_proposals(self) -> List[Proposal]:
        """Get proposals executed in the last hour"""
        cutoff = datetime.now() - timedelta(hours=1)
        
        return self.db.query(Proposal)\
            .filter(Proposal.status == 'executed')\
            .filter(Proposal.executed_at >= cutoff)\
            .order_by(Proposal.executed_at.desc())\
            .limit(10)\
            .all()
    
    def _extract_and_store_pattern(self, proposal: Proposal) -> bool:
        """
        Extract pattern from executed proposal using CrossProjectLearningSystem
        
        Returns True if a new pattern was stored
        """
        # Determine if proposal was successful
        success = self._evaluate_proposal_success(proposal)
        
        if not success:
            # Don't extract patterns from failed proposals
            logger.debug(f"Skipping pattern extraction from failed proposal {proposal.proposal_id}")
            return False
        
        # Parse proposal details
        changes = json.loads(proposal.changes_json) if proposal.changes_json else {}
        change_type = changes.get('change_type', 'unknown')
        
        # Get project context
        project = self.db.query(Project).get(proposal.project_id)
        if not project:
            return False
        
        # Use CrossProjectLearningSystem to extract pattern
        pattern_name = self._generate_pattern_name(proposal, change_type)
        
        pattern = self.xp_system.extract_pattern_from_proposal(
            proposal=proposal,
            pattern_name=pattern_name,
            pattern_type=change_type,
            description=proposal.description[:500] if proposal.description else None,
        )
        
        if pattern:
            logger.info(f"✅ Extracted pattern: {pattern.pattern_name} "
                       f"(confidence: {pattern.confidence:.2f})")
            
            # Track outcome for the pattern
            self.xp_system.track_pattern_outcome(
                pattern_id=pattern.pattern_id,
                success=success,
            )
            
            return True
        
        return False
    
    def _evaluate_proposal_success(self, proposal: Proposal) -> bool:
        """
        Evaluate if a proposal execution was successful
        
        For now, use simple heuristics. In production:
        - Check if tests pass
        - Compare before/after metrics
        - Monitor runtime errors
        - User feedback
        """
        # Get snapshots before and after proposal execution
        before_snapshot = self.db.query(CodeSnapshot)\
            .filter(CodeSnapshot.project_id == proposal.project_id)\
            .filter(CodeSnapshot.created_at < proposal.executed_at)\
            .order_by(CodeSnapshot.created_at.desc())\
            .first()
        
        after_snapshot = self.db.query(CodeSnapshot)\
            .filter(CodeSnapshot.project_id == proposal.project_id)\
            .filter(CodeSnapshot.created_at > proposal.executed_at)\
            .order_by(CodeSnapshot.created_at.asc())\
            .first()
        
        # If no before/after snapshots, use confidence as proxy
        if not before_snapshot or not after_snapshot:
            return proposal.confidence >= 0.75
        
        # Compare metrics
        improvements = 0
        regressions = 0
        
        # Check complexity
        if after_snapshot.complexity < before_snapshot.complexity:
            improvements += 1
        elif after_snapshot.complexity > before_snapshot.complexity * 1.2:
            regressions += 1
        
        # Check issues
        if after_snapshot.issues_found < before_snapshot.issues_found:
            improvements += 1
        elif after_snapshot.issues_found > before_snapshot.issues_found:
            regressions += 1
        
        # Check test coverage
        if after_snapshot.test_coverage > before_snapshot.test_coverage:
            improvements += 1
        
        # Success if more improvements than regressions
        return improvements > regressions
    
    def _generate_pattern_name(self, proposal: Proposal, change_type: str) -> str:
        """Generate descriptive pattern name"""
        # Extract key words from title
        words = proposal.title.split()[:5]
        base_name = " ".join(words)
        
        return f"{change_type.replace('_', ' ').title()}: {base_name}"
    
    def _extract_code_template(self, proposal: Proposal) -> str:
        """
        Extract code template from proposal
        
        In production, this would:
        - Parse actual code changes from commits
        - Abstract variable names
        - Identify core pattern structure
        """
        # TODO: Integrate with git to extract actual changes
        changes = json.loads(proposal.changes_json)
        
        # For now, return a placeholder template
        template = f"""
# Pattern Type: {changes.get('change_type', 'unknown')}
# Files Affected: {len(changes.get('files_affected', []))}
# Estimated Lines: {changes.get('estimated_lines', 0)}

# TODO: Extract actual code template from git diff
"""
        return template
    
    def _identify_cross_project_opportunities(self):
        """
        Identify patterns that could be applied to other projects using CrossProjectLearningSystem
        
        For each pattern, find similar projects and create cross-project learning records
        """
        # Get all projects
        projects = self.db.query(Project).all()
        
        if len(projects) <= 1:
            return  # Need multiple projects
        
        # Get recent high-confidence patterns
        patterns = self.db.query(LearnedPattern)\
            .filter(LearnedPattern.confidence >= 0.7)\
            .filter(LearnedPattern.created_at >= datetime.now() - timedelta(days=7))\
            .all()
        
        opportunities = 0
        
        for pattern in patterns:
            # Find source project (where pattern originated)
            # Look for proposals that created this pattern
            source_proposal = self.db.query(Proposal)\
                .filter(Proposal.project_id.isnot(None))\
                .order_by(Proposal.created_at.desc())\
                .first()
            
            if not source_proposal:
                continue
            
            source_project_id = source_proposal.project_id
            
            # Find similar projects and suggest the pattern
            for target_project in projects:
                if target_project.project_id == source_project_id:
                    continue
                
                # Calculate similarity using CrossProjectLearningSystem
                similarity = self.xp_system.calculate_project_similarity(
                    source_project_id,
                    target_project.project_id
                )
                
                # If similarity meets threshold, record the opportunity
                if similarity >= self.config.cross_project.min_language_similarity:
                    learning = self.xp_system.record_pattern_application(
                        source_project_id=source_project_id,
                        target_project_id=target_project.project_id,
                        pattern_id=pattern.pattern_id,
                        applied=False,  # Just a suggestion
                    )
                    
                    if learning:
                        opportunities += 1
                        logger.debug(f"Suggested pattern {pattern.pattern_name} "
                                   f"for project {target_project.project_id} "
                                   f"(similarity: {similarity:.2f})")
        
        if opportunities > 0:
            logger.info(f"Identified {opportunities} cross-project learning opportunities")
    
    
    def _get_current_performance(self) -> Dict:
        """Get recent performance metrics for experiment baseline"""
        # Get recent patterns
        recent_patterns = self.db.query(LearnedPattern)\
            .filter(LearnedPattern.created_at >= datetime.now() - timedelta(days=7))\
            .all()
        
        if not recent_patterns:
            return {
                'patterns_per_day': 2.0,
                'avg_confidence': 0.75,
                'avg_reuse_rate': 0.40,
                'cross_project_rate': 0.20,
                'current_strategy': self.current_strategy
            }
        
        # Calculate metrics
        total_success = sum(p.success_count for p in recent_patterns)
        total_attempts = sum(p.success_count + p.failure_count for p in recent_patterns)
        
        return {
            'patterns_per_day': len(recent_patterns) / 7,
            'avg_confidence': sum(p.confidence for p in recent_patterns) / len(recent_patterns),
            'avg_reuse_rate': total_success / max(total_attempts, 1),
            'cross_project_rate': 0.20,  # TODO: Calculate actual rate
            'current_strategy': self.current_strategy
        }
    
    def _try_experimental_approach(self, proposal: Proposal, approach: str) -> Dict:
        """
        Execute experimental learning approach
        
        Could try:
        - Different pattern abstraction levels
        - Meta-learning from failures
        - Ensemble pattern extraction
        - Temporal pattern evolution
        """
        # For now, just run standard extraction
        success = self._extract_and_store_pattern(proposal)
        
        return {
            'patterns_extracted': 1 if success else 0,
            'pattern_quality_score': 0.75,
            'generalization_score': 0.70,
            'reuse_potential': 0.65
        }
    
    def _calculate_improvement(self, result: Dict, baseline: Dict) -> float:
        """
        Calculate improvement percentage over baseline
        
        Factors:
        - More patterns extracted = better
        - Higher quality patterns = better
        - Better generalization = better
        """
        result_patterns = result.get('patterns_extracted', 0)
        baseline_patterns = baseline.get('patterns_per_day', 2) / 240  # Per cycle (6 min)
        
        if baseline_patterns == 0:
            pattern_improvement = 0.0
        else:
            pattern_improvement = (result_patterns - baseline_patterns) / baseline_patterns
        
        # Consider quality
        quality_score = result.get('pattern_quality_score', 0.75)
        baseline_quality = baseline.get('avg_confidence', 0.75)
        quality_improvement = (quality_score - baseline_quality) / max(baseline_quality, 0.1)
        
        total_improvement = pattern_improvement * 0.6 + quality_improvement * 0.4
        
        return total_improvement
    
    def _check_for_promoted_strategies(self):
        """Check if any experiments have been promoted to production"""
        promoted = self.dreamer.get_promoted_experiments("learning")
        
        if promoted and promoted[0].experiment_name != self.current_strategy:
            logger.info(f"🎉 Adopting promoted strategy: {promoted[0].experiment_name}")
            self.current_strategy = promoted[0].experiment_name
            # TODO: Actually implement strategy switching
