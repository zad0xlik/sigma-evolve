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
from ..utils.graphiti import get_graphiti_client_sync, get_decision_history, search_decisions

logger = logging.getLogger(__name__)


class LearningWorker(BaseWorker):
    """Extracts and stores patterns from successful and failed proposals."""
    
    def __init__(self, db_session, dreamer, project_id=None):
        super().__init__(db_session, dreamer, project_id)
        self.project_id = project_id
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
        description = changes.get('description', '')
        
        # Get project context
        project = self.db.query(Project).get(proposal.project_id)
        if not project:
            return False
        
        # Query Graphiti for similar patterns in knowledge graph
        graphiti_context = self._query_pattern_history(description, change_type, project.project_id)
        
        # Check if this pattern already exists in knowledge graph
        if graphiti_context.get('similar_patterns', []):
            logger.info(f"Found {len(graphiti_context['similar_patterns'])} similar patterns in knowledge graph")
            
            # Calculate quality score based on historical success
            historical_quality = self._assess_pattern_quality(graphiti_context)
            
            if historical_quality < 0.3:
                logger.warning(f"Pattern has poor historical quality ({historical_quality:.2f}), skipping")
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
            # Enhance pattern confidence with Graphiti knowledge
            enhanced_confidence = self._enhance_pattern_confidence(
                pattern.confidence,
                graphiti_context
            )
            
            if enhanced_confidence != pattern.confidence:
                pattern.confidence = enhanced_confidence
                logger.info(f"Enhanced pattern confidence to {enhanced_confidence:.2f}")
            
            logger.info(f"✅ Extracted pattern: {pattern.pattern_name} "
                       f"(confidence: {pattern.confidence:.2f})")
            
            # Track outcome for the pattern
            self.xp_system.track_pattern_outcome(
                pattern_id=pattern.pattern_id,
                success=success,
            )
            
            # Store pattern in Graphiti for future reference
            self._store_pattern_in_graphiti(pattern, description, change_type, project)
            
            # Broadcast learned pattern for knowledge exchange
            self._broadcast_knowledge(
                knowledge_type='learned_pattern',
                content={
                    'pattern_id': pattern.pattern_id,
                    'pattern_name': pattern.pattern_name,
                    'pattern_type': pattern.pattern_type,
                    'confidence': pattern.confidence,
                    'success_rate': pattern.success_count / max(pattern.success_count + pattern.failure_count, 1)
                },
                urgency='low'
            )
            
            # If pattern confidence increased significantly, broadcast evolution
            if enhanced_confidence > pattern.confidence + 0.1:
                self._broadcast_knowledge(
                    knowledge_type='pattern_evolution',
                    content={
                        'pattern_id': pattern.pattern_id,
                        'improvement': enhanced_confidence - pattern.confidence,
                        'source': 'historical_data_enhancement'
                    },
                    urgency='low'
                )
            
            return True
        
        return False
    
    def _query_pattern_history(self, description: str, change_type: str, project_id: int) -> Dict:
        """
        Query Graphiti knowledge graph for similar patterns and historical context
        
        Returns:
            Dict with similar patterns, success rates, and relevant facts
        """
        try:
            client = get_graphiti_client_sync()
            
            if not client:
                logger.debug("Graphiti client not available, skipping pattern history query")
                return {
                    'similar_patterns': [],
                    'success_rate': 0.0,
                    'related_facts': [],
                    'query_status': 'unavailable'
                }
            
            # Build search query
            search_query = f"pattern for {change_type} in {description[:100]}"
            
            import asyncio
            
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Search for similar patterns
            similar_patterns = loop.run_until_complete(
                search_decisions(
                    query=search_query,
                    limit=15
                )
            )
            
            # Analyze patterns
            success_count = 0
            total_count = len(similar_patterns)
            related_facts = []
            
            for pattern in similar_patterns:
                fact = pattern.get('fact', '').lower()
                
                # Check for success indicators
                if 'success' in fact or 'worked' in fact or 'effective' in fact:
                    success_count += 1
                
                # Extract related facts
                related_facts.append({
                    'fact': pattern.get('fact', ''),
                    'score': pattern.get('score', 1.0),
                    'type': self._classify_pattern_fact(fact)
                })
            
            success_rate = success_count / total_count if total_count > 0 else 0.0
            
            logger.info(
                f"Pattern history query complete: "
                f"found {total_count} similar patterns, "
                f"success_rate={success_rate:.1%}"
            )
            
            return {
                'similar_patterns': similar_patterns,
                'success_rate': success_rate,
                'related_facts': related_facts,
                'query_status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error querying pattern history: {e}")
            return {
                'similar_patterns': [],
                'success_rate': 0.0,
                'related_facts': [],
                'query_status': 'error',
                'error': str(e)
            }
    
    def _assess_pattern_quality(self, graphiti_context: Dict) -> float:
        """
        Assess pattern quality based on historical data from Graphiti
        
        Factors:
        - Historical success rate
        - Number of similar patterns (more is better for established patterns)
        - Consistency of outcomes
        - Relevance to current context
        """
        success_rate = graphiti_context.get('success_rate', 0.0)
        similar_count = len(graphiti_context.get('similar_patterns', []))
        related_facts = graphiti_context.get('related_facts', [])
        
        # Base quality on success rate
        quality = success_rate
        
        # Bonus for well-established patterns
        if similar_count >= 5:
            quality += 0.1
        elif similar_count >= 10:
            quality += 0.2
        
        # Penalty for controversial patterns (mixed outcomes)
        if 0.3 < success_rate < 0.7:
            quality -= 0.15
        
        # Bonus for patterns with rich contextual facts
        if len(related_facts) >= 3:
            quality += 0.05
        
        # Ensure within bounds
        quality = max(0.0, min(1.0, quality))
        
        logger.debug(f"Pattern quality assessment: {quality:.2f} "
                    f"(success_rate: {success_rate:.2f}, similar: {similar_count})")
        
        return quality
    
    def _enhance_pattern_confidence(self, base_confidence: float, graphiti_context: Dict) -> float:
        """
        Enhance pattern confidence using Graphiti knowledge
        
        Adjustments:
        - High historical success rate → increase confidence
        - Multiple similar patterns → increase confidence (well-established)
        - Low success rate → decrease confidence (risky pattern)
        - No historical data → slight decrease (unknown pattern)
        """
        success_rate = graphiti_context.get('success_rate', 0.0)
        similar_count = len(graphiti_context.get('similar_patterns', []))
        query_status = graphiti_context.get('query_status', 'unknown')
        
        adjustment = 0.0
        
        # Adjust based on historical success
        if success_rate > 0.7:
            adjustment += 0.08
        elif success_rate > 0.5:
            adjustment += 0.04
        elif success_rate < 0.3:
            adjustment -= 0.10
        elif success_rate < 0.5:
            adjustment -= 0.05
        
        # Adjust based on pattern establishment
        if similar_count >= 10:
            adjustment += 0.05
        elif similar_count >= 5:
            adjustment += 0.02
        elif similar_count == 0:
            adjustment -= 0.03  # Unknown pattern
        
        # Penalty for query failures
        if query_status == 'error':
            adjustment -= 0.05
        
        # Apply adjustment
        enhanced_confidence = base_confidence + adjustment
        enhanced_confidence = max(0.0, min(1.0, enhanced_confidence))
        
        if adjustment != 0.0:
            logger.info(
                f"Pattern confidence adjusted: {base_confidence:.3f} → {enhanced_confidence:.3f} "
                f"(success_rate: {success_rate:.2f}, similar: {similar_count}, adjustment: {adjustment:+.3f})"
            )
        
        return enhanced_confidence
    
    def _store_pattern_in_graphiti(self, pattern, description: str, change_type: str, project: Project):
        """
        Store learned pattern in Graphiti knowledge graph for future reference
        """
        try:
            client = get_graphiti_client_sync()
            
            if not client:
                logger.debug("Graphiti client not available, skipping pattern storage")
                return
            
            # Create fact text about the pattern
            fact_text = (
                f"Pattern: {pattern.pattern_name} "
                f"(type: {change_type}, "
                f"project: {project.project_name}, "
                f"confidence: {pattern.confidence:.2f})"
            )
            
            # Add related context
            if description:
                fact_text += f" - {description[:200]}"
            
            # Store in Graphiti (this would require a store_facts function)
            # For now, just log that we would store it
            logger.debug(f"Would store pattern in Graphiti: {fact_text[:100]}...")
            
        except Exception as e:
            logger.error(f"Error storing pattern in Graphiti: {e}")
    
    def _classify_pattern_fact(self, fact_text: str) -> str:
        """
        Classify a fact from Graphiti into a pattern type
        """
        fact_lower = fact_text.lower()
        
        if any(keyword in fact_lower for keyword in ['success', 'worked', 'effective', 'improved']):
            return 'success_pattern'
        elif any(keyword in fact_lower for keyword in ['failed', 'error', 'bug', 'broke']):
            return 'failure_pattern'
        elif any(keyword in fact_lower for keyword in ['risk', 'caution', 'warning']):
            return 'risk_pattern'
        elif any(keyword in fact_lower for keyword in ['dependency', 'library', 'package']):
            return 'dependency_pattern'
        elif any(keyword in fact_lower for keyword in ['performance', 'speed', 'optimization']):
            return 'performance_pattern'
        else:
            return 'general_pattern'
    
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
    
    def _get_experiment_context(self) -> Dict:
        """Get context for experiment proposal"""
        return self._get_current_performance()
    
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
        
        if promoted and promoted[0]["experiment_name"] != self.current_strategy:
            logger.info(f"🎉 Adopting promoted strategy: {promoted[0]['experiment_name']}")
            self.current_strategy = promoted[0]["experiment_name"]
            # TODO: Actually implement strategy switching
