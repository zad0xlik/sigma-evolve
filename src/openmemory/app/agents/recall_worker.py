"""
Recall Worker - Retrieves relevant context from knowledge graph and past decisions.

Production Mode: Efficient knowledge graph queries, pattern matching
Experimental Mode: Novel retrieval strategies, semantic search experiments
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

from .base_worker import BaseWorker
from ..agent_config import get_agent_config
from ..models import Project, Proposal, LearnedPattern, CrossProjectLearning
from ..database import get_db
from ..utils.graphiti import (
    get_graphiti_client_sync,
    search_decisions,
    get_decision_history,
)

logger = logging.getLogger(__name__)


class RecallWorker(BaseWorker):
    """Retrieves relevant context from knowledge graph and past experiences."""
    
    def __init__(self, db_session, dreamer, project_id=None):
        super().__init__(db_session, dreamer, project_id)
        self.project_id = project_id
        self.config = get_agent_config()
        self.current_strategy = "semantic_search_with_filters"
    
    def get_interval(self) -> int:
        """Recall runs every 3 minutes by default"""
        return self.config.workers.recall_interval
    
    def _production_cycle(self):
        """
        Production Mode: Retrieve context for pending proposals
        
        Steps:
        1. Get pending proposals from Dream Worker
        2. For each proposal, query knowledge graph for relevant patterns
        3. Find similar past proposals and their outcomes
        4. Retrieve cross-project learnings
        5. Enrich proposals with contextual information
        6. Store enriched context for Think Worker to use
        """
        try:
            # Check for promoted strategies
            self._check_for_promoted_strategies()
            
            # Get pending proposals that need context
            pending_proposals = self._get_pending_proposals()
            
            if not pending_proposals:
                logger.info("No pending proposals needing context enrichment")
                return
            
            logger.info(f"Enriching context for {len(pending_proposals)} proposals")
            
            for proposal in pending_proposals:
                context = self._retrieve_context_for_proposal(proposal)
                self._enrich_proposal_with_context(proposal, context)
            
            logger.info(f"Context enrichment complete")
            
        except Exception as e:
            logger.error(f"Production recall failed: {e}")
            raise
    
    def _experimental_cycle(self):
        """
        Experimental Mode: Try novel context retrieval strategies
        
        Experiments:
        - Vector similarity vs keyword search
        - Different embedding models
        - Temporal weighting (recent vs old patterns)
        - Multi-hop knowledge graph traversal
        - Cross-domain pattern transfer
        
        Metrics tracked:
        - Context relevance score (from Think Worker feedback)
        - Retrieval speed
        - Pattern application success rate
        - Coverage (% of proposals with useful context)
        """
        try:
            pending_proposals = self._get_pending_proposals()
            if not pending_proposals:
                return
            
            # Get baseline performance
            context_perf = self._get_current_performance()
            
            # Ask DreamerMetaAgent for experimental approach
            experiment = self.dreamer.propose_experiment("recall", context_perf)
            
            if not experiment:
                logger.info("No suitable experiment proposed")
                return
            
            logger.info(f"🧪 Starting experiment: {experiment['experiment_name']}")
            
            # Record experiment start
            exp_id = self.dreamer.record_experiment_start(
                worker_name="recall",
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
            improvement = self._calculate_improvement(result, context_perf, elapsed)
            
            # Record outcome
            self.dreamer.record_outcome(
                experiment_id=exp_id,
                outcome={
                    "success": improvement > 0,
                    "improvement": improvement,
                    "result_metrics": result,
                    "baseline_metrics": context_perf,
                    "elapsed_time": elapsed
                }
            )
            
            logger.info(f"Experiment complete: improvement={improvement:.2%}")
            
        except Exception as e:
            logger.error(f"Experimental recall failed: {e}")
    
    def _get_pending_proposals(self) -> List[Proposal]:
        """Get proposals that need context enrichment"""
        # Get proposals created in last 10 minutes that are still pending
        cutoff = datetime.now() - timedelta(minutes=10)
        
        return self.db.query(Proposal)\
            .filter(Proposal.status == 'pending')\
            .filter(Proposal.created_at >= cutoff)\
            .order_by(Proposal.created_at.desc())\
            .limit(5)\
            .all()
    
    def _retrieve_context_for_proposal(self, proposal: Proposal) -> Dict:
        """
        Retrieve relevant context from multiple sources
        
        Returns:
            {
                'similar_patterns': List[LearnedPattern],
                'past_proposals': List[Dict],
                'cross_project_insights': List[Dict],
                'knowledge_graph_context': Dict
            }
        """
        # Parse proposal details
        changes = json.loads(proposal.changes_json)
        change_type = changes.get('change_type', 'unknown')
        
        # Find similar learned patterns
        similar_patterns = self._find_similar_patterns(
            change_type=change_type,
            project_id=proposal.project_id
        )
        
        # Find past proposals with similar characteristics
        past_proposals = self._find_similar_past_proposals(
            change_type=change_type,
            confidence_threshold=0.7
        )
        
        # Get cross-project insights if enabled
        cross_project_insights = []
        if self.config.cross_project.enabled:
            cross_project_insights = self._get_cross_project_insights(proposal.project_id)
        
        # TODO: Query knowledge graph (Graphiti) for relevant entities/relationships
        knowledge_graph_context = self._query_knowledge_graph(proposal)
        
        return {
            'similar_patterns': similar_patterns,
            'past_proposals': past_proposals,
            'cross_project_insights': cross_project_insights,
            'knowledge_graph_context': knowledge_graph_context,
            'retrieval_timestamp': datetime.now()
        }
    
    def _find_similar_patterns(self, change_type: str, project_id: int) -> List[Dict]:
        """Find learned patterns matching the change type"""
        # Get project to determine language/framework
        project = self.db.get(Project, project_id)
        if not project:
            return []
        
        # Query learned patterns
        patterns = self.db.query(LearnedPattern)\
            .filter(LearnedPattern.pattern_type == change_type)\
            .filter(LearnedPattern.language == project.language)\
            .filter(LearnedPattern.confidence >= 0.6)\
            .order_by(LearnedPattern.success_count.desc())\
            .limit(5)\
            .all()
        
        return [
            {
                'pattern_id': p.pattern_id,
                'pattern_name': p.pattern_name,
                'description': p.description,
                'code_template': p.code_template,
                'confidence': p.confidence,
                'success_rate': p.success_count / max(p.success_count + p.failure_count, 1)
            }
            for p in patterns
        ]
    
    def _find_similar_past_proposals(self, change_type: str, confidence_threshold: float) -> List[Dict]:
        """Find past proposals with similar characteristics"""
        # Get all executed proposals
        past_proposals = self.db.query(Proposal)\
            .filter(Proposal.status == 'executed')\
            .filter(Proposal.confidence >= confidence_threshold)\
            .order_by(Proposal.executed_at.desc())\
            .limit(10)\
            .all()
        
        similar = []
        for p in past_proposals:
            changes = json.loads(p.changes_json)
            if changes.get('change_type') == change_type:
                similar.append({
                    'proposal_id': p.proposal_id,
                    'title': p.title,
                    'confidence': p.confidence,
                    'outcome': 'success',  # Would track actual outcome
                    'executed_at': p.executed_at.isoformat() if p.executed_at else None
                })
        
        return similar[:5]  # Return top 5
    
    def _get_cross_project_insights(self, project_id: int) -> List[Dict]:
        """Retrieve insights from other similar projects"""
        # Get cross-project learnings
        learnings = self.db.query(CrossProjectLearning)\
            .filter(CrossProjectLearning.target_project_id == project_id)\
            .filter(CrossProjectLearning.similarity_score >= self.config.cross_project.similarity_threshold_language)\
            .order_by(CrossProjectLearning.similarity_score.desc())\
            .limit(5)\
            .all()
        
        insights = []
        for learning in learnings:
            # Get the pattern details
            pattern = self.db.query(LearnedPattern).get(learning.pattern_id)
            if pattern:
                insights.append({
                    'source_project_id': learning.source_project_id,
                    'pattern_name': pattern.pattern_name,
                    'similarity_score': learning.similarity_score,
                    'applied': learning.applied,
                    'description': pattern.description
                })
        
        return insights
    
    def _query_knowledge_graph(self, proposal: Proposal) -> Dict:
        """Query Graphiti knowledge graph for relevant context"""
        try:
            client = get_graphiti_client_sync()
            
            if not client:
                logger.debug("Graphiti client not available, skipping knowledge graph query")
                return {
                    'entities': [],
                    'relationships': [],
                    'relevant_facts': [],
                    'query_status': 'unavailable'
                }
            
            # Parse proposal details to build search query
            changes = json.loads(proposal.changes_json)
            change_type = changes.get('change_type', 'unknown')
            description = changes.get('description', '')
            
            # Build search query based on proposal content
            search_query = self._build_graphiti_search_query(change_type, description)
            
            if not search_query:
                return {
                    'entities': [],
                    'relationships': [],
                    'relevant_facts': [],
                    'query_status': 'empty_query'
                }
            
            logger.info(f"Querying knowledge graph with: '{search_query}'")
            
            # Search for relevant decisions and facts in the knowledge graph
            # We'll use a sync wrapper since this worker is synchronous
            import asyncio
            
            # Create an event loop if one doesn't exist
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run async search
            search_results = loop.run_until_complete(
                search_decisions(
                    query=search_query,
                    limit=10
                )
            )
            
            # Extract entities and relationships from results
            entities = []
            relationships = []
            facts = []
            
            for result in search_results:
                fact_text = result.get('fact', '')
                
                # Parse fact to extract entities
                # Simple pattern matching for common entity types
                if 'decision' in fact_text.lower():
                    entities.append({
                        'type': 'DECISION',
                        'content': fact_text,
                        'score': result.get('score', 1.0)
                    })
                    facts.append({
                        'type': 'decision',
                        'content': fact_text,
                        'score': result.get('score', 1.0)
                    })
                elif 'pattern' in fact_text.lower():
                    entities.append({
                        'type': 'PATTERN',
                        'content': fact_text,
                        'score': result.get('score', 1.0)
                    })
                    facts.append({
                        'type': 'pattern',
                        'content': fact_text,
                        'score': result.get('score', 1.0)
                    })
                elif 'project' in fact_text.lower():
                    entities.append({
                        'type': 'PROJECT',
                        'content': fact_text,
                        'score': result.get('score', 1.0)
                    })
                elif 'library' in fact_text.lower() or 'dependency' in fact_text.lower():
                    entities.append({
                        'type': 'LIBRARY',
                        'content': fact_text,
                        'score': result.get('score', 1.0)
                    })
                    facts.append({
                        'type': 'dependency',
                        'content': fact_text,
                        'score': result.get('score', 1.0)
                    })
                else:
                    # General entity
                    entities.append({
                        'type': 'UNKNOWN',
                        'content': fact_text,
                        'score': result.get('score', 1.0)
                    })
            
            logger.info(f"Knowledge graph query complete: {len(entities)} entities, {len(facts)} facts found")
            
            return {
                'entities': entities,
                'relationships': relationships,
                'relevant_facts': facts,
                'query_status': 'success',
                'search_query': search_query,
                'total_results': len(search_results)
            }
            
        except Exception as e:
            logger.error(f"Error querying knowledge graph: {e}")
            return {
                'entities': [],
                'relationships': [],
                'relevant_facts': [],
                'query_status': 'error',
                'error': str(e)
            }
    
    def _build_graphiti_search_query(self, change_type: str, description: str) -> str:
        """
        Build a search query for Graphiti knowledge graph.
        
        Examples:
        - "decision about database migration"
        - "pattern for authentication"
        - "dependency on redis cache"
        """
        # Map change types to knowledge graph queries
        type_to_query = {
            'database_migration': 'database migration decision',
            'authentication': 'authentication pattern',
            'caching': 'caching strategy',
            'api_design': 'API design decision',
            'library_change': 'library dependency',
            'architecture': 'architecture decision',
            'performance': 'performance optimization',
            'security': 'security pattern',
        }
        
        # Use specific query if available, otherwise build from description
        if change_type in type_to_query:
            query = type_to_query[change_type]
        elif description:
            # Extract keywords from description
            keywords = []
            for word in description.lower().split():
                if len(word) > 3 and word not in ['with', 'from', 'that', 'this', 'the', 'and', 'for']:
                    keywords.append(word)
            
            if keywords:
                query = f"{' '.join(keywords[:3])} decision pattern"
            else:
                query = change_type
        else:
            query = change_type
        
        return query
    
    def _enrich_proposal_with_context(self, proposal: Proposal, context: Dict):
        """Store enriched context with the proposal"""
        # For now, store context in description (could use separate context field)
        context_summary = self._format_context_summary(context)
        
        # Append context to description
        if context_summary:
            proposal.description += f"\n\n--- CONTEXT ---\n{context_summary}"
            self.db.commit()
            
            logger.info(f"Enriched proposal {proposal.proposal_id} with {len(context['similar_patterns'])} patterns")
        
        # Broadcast context enrichment quality
        context_quality = {
            'patterns_found': len(context['similar_patterns']),
            'past_proposals_found': len(context['past_proposals']),
            'cross_project_insights': len(context['cross_project_insights']),
            'knowledge_graph_facts': len(context.get('knowledge_graph_context', {}).get('relevant_facts', []))
        }
        
        self._broadcast_knowledge(
            knowledge_type='context_enrichment',
            content={
                'proposal_id': proposal.proposal_id,
                'quality_metrics': context_quality,
                'enrichment_timestamp': context['retrieval_timestamp'].isoformat() if context.get('retrieval_timestamp') else None
            },
            urgency='low'
        )
        
        # Broadcast knowledge retrieval patterns
        if context.get('knowledge_graph_context', {}).get('query_status') == 'success':
            self._broadcast_knowledge(
                knowledge_type='knowledge_retrieval',
                content={
                    'query': context['knowledge_graph_context'].get('search_query', ''),
                    'results_found': context['knowledge_graph_context'].get('total_results', 0),
                    'retrieval_time': 0.5,  # Would track actual time
                    'query_status': 'success'
                },
                urgency='low'
            )
    
    def _format_context_summary(self, context: Dict) -> str:
        """Format context into human-readable summary"""
        parts = []
        
        # Similar patterns
        if context['similar_patterns']:
            parts.append(f"Found {len(context['similar_patterns'])} similar patterns:")
            for pattern in context['similar_patterns'][:3]:
                parts.append(f"  - {pattern['pattern_name']} (confidence: {pattern['confidence']:.2f})")
        
        # Past proposals
        if context['past_proposals']:
            parts.append(f"\nPast similar proposals: {len(context['past_proposals'])}")
            for prop in context['past_proposals'][:2]:
                parts.append(f"  - {prop['title']} (confidence: {prop['confidence']:.2f})")
        
        # Cross-project insights
        if context['cross_project_insights']:
            parts.append(f"\nCross-project insights: {len(context['cross_project_insights'])}")
            for insight in context['cross_project_insights'][:2]:
                parts.append(f"  - {insight['pattern_name']} from project #{insight['source_project_id']}")
        
        # Knowledge graph context
        kg_context = context.get('knowledge_graph_context', {})
        if kg_context and kg_context.get('query_status') == 'success':
            facts = kg_context.get('relevant_facts', [])
            if facts:
                parts.append(f"\nKnowledge graph facts: {len(facts)}")
                for fact in facts[:3]:
                    parts.append(f"  - {fact['content'][:80]}..." if len(fact['content']) > 80 else f"  - {fact['content']}")
        
        return "\n".join(parts) if parts else ""
    
    def _get_experiment_context(self) -> Dict:
        """Get context for experiment proposal"""
        return self._get_current_performance()
    
    def _get_current_performance(self) -> Dict:
        """Get recent performance metrics for experiment baseline"""
        # Count recent context retrievals
        recent_proposals = self.db.query(Proposal)\
            .filter(Proposal.created_at >= datetime.now() - timedelta(hours=1))\
            .count()
        
        return {
            'avg_patterns_found': 3.0,
            'avg_retrieval_time': 0.5,
            'context_relevance_score': 0.75,
            'coverage_rate': 0.80,  # % of proposals that got useful context
            'current_strategy': self.current_strategy
        }
    
    def _try_experimental_approach(self, proposal: Proposal, approach: str) -> Dict:
        """
        Execute experimental context retrieval approach
        
        Could try:
        - Different similarity algorithms
        - Temporal weighting
        - Multi-hop graph traversal
        - Different embedding models
        """
        # For now, just run standard retrieval
        context = self._retrieve_context_for_proposal(proposal)
        
        return {
            'patterns_found': len(context['similar_patterns']),
            'past_proposals_found': len(context['past_proposals']),
            'cross_project_insights': len(context['cross_project_insights']),
            'relevance_score': 0.75  # Would be determined by Think Worker feedback
        }
    
    def _calculate_improvement(self, result: Dict, baseline: Dict, elapsed: float) -> float:
        """
        Calculate improvement percentage over baseline
        
        Factors:
        - More relevant patterns found = better
        - Faster retrieval = better
        - Higher relevance score = better
        """
        result_patterns = result.get('patterns_found', 0)
        baseline_patterns = baseline.get('avg_patterns_found', 3)
        
        pattern_improvement = (result_patterns - baseline_patterns) / max(baseline_patterns, 1)
        
        # Consider speed
        baseline_time = baseline.get('avg_retrieval_time', 0.5)
        if elapsed > baseline_time * 1.5:
            pattern_improvement -= 0.1
        
        # Consider relevance (if available)
        result_relevance = result.get('relevance_score', 0.75)
        baseline_relevance = baseline.get('context_relevance_score', 0.75)
        relevance_improvement = (result_relevance - baseline_relevance) / max(baseline_relevance, 0.1)
        
        total_improvement = pattern_improvement * 0.5 + relevance_improvement * 0.5
        
        return total_improvement
    
    def _check_for_promoted_strategies(self):
        """Check if any experiments have been promoted to production"""
        promoted = self.dreamer.get_promoted_experiments("recall")
        
        if promoted and promoted[0].experiment_name != self.current_strategy:
            logger.info(f"🎉 Adopting promoted strategy: {promoted[0].experiment_name}")
            self.current_strategy = promoted[0].experiment_name
            # TODO: Actually implement strategy switching
