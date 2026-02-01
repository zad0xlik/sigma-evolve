"""
Test suite for Knowledge Reception (Phase 3)

Tests the complete knowledge reception infrastructure including:
- Knowledge processing in BaseWorker
- Knowledge query methods
- Knowledge filtering and prioritization
- Integration with all 5 workers
"""

import sys
import os
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from typing import List, Dict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openmemory.app.agents.base_worker import BaseWorker
from openmemory.app.agents.think_worker import ThinkWorker
from openmemory.app.agents.learning_worker import LearningWorker
from openmemory.app.agents.analysis_worker import AnalysisWorker
from openmemory.app.agents.dream_worker import DreamWorker
from openmemory.app.agents.recall_worker import RecallWorker
from openmemory.app.agents.dreamer import DreamerMetaAgent


# Test Data Fixtures
@pytest.fixture
def mock_db():
    """Create mock database session"""
    db = Mock()
    db.rollback = Mock()
    db.commit = Mock()
    return db


@pytest.fixture
def mock_dreamer():
    """Create mock DreamerMetaAgent"""
    dreamer = Mock(spec=DreamerMetaAgent)
    dreamer.should_experiment = Mock(return_value=False)
    return dreamer


@pytest.fixture
def mock_knowledge_protocol():
    """Create mock KnowledgeExchangeProtocol"""
    protocol = Mock()
    protocol.query_knowledge = AsyncMock(return_value=[])
    protocol.update_worker_knowledge_state = AsyncMock()
    return protocol


# ============================================================================
# Test Knowledge Reception Infrastructure
# ============================================================================

class TestKnowledgeReceptionInfrastructure:
    """Test knowledge reception infrastructure in BaseWorker"""

    def test_process_received_knowledge_empty_list(self, mock_db, mock_dreamer):
        """Test processing empty knowledge list"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Should handle empty list gracefully
        worker.process_received_knowledge([])
        
        # No errors should occur
        assert True

    def test_process_received_knowledge_risk_pattern(self, mock_db, mock_dreamer):
        """Test processing risk pattern knowledge"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock the _update_risk_model method
        worker._update_risk_model = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'risk_pattern',
            'source': 'think_worker',
            'payload': {'risk_level': 'high', 'description': 'Test risk'}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # Verify _update_risk_model was called
        worker._update_risk_model.assert_called_once()
        assert worker.stats['knowledge_received'] == 1

    def test_process_received_knowledge_learned_pattern(self, mock_db, mock_dreamer):
        """Test processing learned pattern knowledge"""
        worker = LearningWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock the _update_pattern_models method
        worker._update_pattern_models = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'learned_pattern',
            'source': 'learning_worker',
            'payload': {'pattern_id': 1, 'name': 'Test Pattern', 'confidence': 0.85}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # Verify _update_pattern_models was called
        worker._update_pattern_models.assert_called_once()
        assert worker.stats['knowledge_received'] == 1

    def test_process_received_knowledge_issue_pattern(self, mock_db, mock_dreamer):
        """Test processing issue pattern knowledge"""
        worker = AnalysisWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock the _update_issue_detection method
        worker._update_issue_detection = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'issue_pattern',
            'source': 'analysis_worker',
            'payload': {'issue_type': 'bug', 'count': 5, 'severity': 'high'}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # Verify _update_issue_detection was called
        worker._update_issue_detection.assert_called_once()
        assert worker.stats['knowledge_received'] == 1

    def test_process_received_knowledge_proposal_quality(self, mock_db, mock_dreamer):
        """Test processing proposal quality knowledge"""
        worker = DreamWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock the _update_proposal_generation method
        worker._update_proposal_generation = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'proposal_quality',
            'source': 'dream_worker',
            'payload': {'proposal_count': 3, 'avg_confidence': 0.75}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # Verify _update_proposal_generation was called
        worker._update_proposal_generation.assert_called_once()
        assert worker.stats['knowledge_received'] == 1

    def test_process_received_knowledge_context_enrichment(self, mock_db, mock_dreamer):
        """Test processing context enrichment knowledge"""
        worker = RecallWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock the _update_context_retrieval method
        worker._update_context_retrieval = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'context_enrichment',
            'source': 'recall_worker',
            'payload': {'quality_score': 0.92, 'patterns_found': 5}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # Verify _update_context_retrieval was called
        worker._update_context_retrieval.assert_called_once()
        assert worker.stats['knowledge_received'] == 1

    def test_process_received_knowledge_decision_outcome(self, mock_db, mock_dreamer):
        """Test processing decision outcome knowledge"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock the _update_decision_making method
        worker._update_decision_making = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'decision_outcome',
            'source': 'think_worker',
            'payload': {'decision': 'execute', 'confidence': 0.88}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # Verify _update_decision_making was called
        worker._update_decision_making.assert_called_once()
        assert worker.stats['knowledge_received'] == 1

    def test_process_received_knowledge_complexity_trend(self, mock_db, mock_dreamer):
        """Test processing complexity trend knowledge"""
        worker = AnalysisWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock the _update_complexity_analysis method
        worker._update_complexity_analysis = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'complexity_trend',
            'source': 'analysis_worker',
            'payload': {'current_complexity': 15, 'trend': 'increasing'}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # Verify _update_complexity_analysis was called
        worker._update_complexity_analysis.assert_called_once()
        assert worker.stats['knowledge_received'] == 1

    def test_process_received_knowledge_unknown_type(self, mock_db, mock_dreamer):
        """Test processing unknown knowledge type"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Should not crash on unknown knowledge type
        knowledge_list = [{
            'knowledge_type': 'unknown_type',
            'source': 'test_worker',
            'payload': {'test': 'data'}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # Should still update stats
        assert worker.stats['knowledge_received'] == 1

    def test_process_received_knowledge_multiple_items(self, mock_db, mock_dreamer):
        """Test processing multiple knowledge items"""
        worker = LearningWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock all relevant methods
        worker._update_pattern_models = Mock()
        worker._update_decision_making = Mock()
        worker._update_risk_model = Mock()
        
        knowledge_list = [
            {
                'knowledge_type': 'learned_pattern',
                'source': 'learning_worker',
                'payload': {'pattern_id': 1}
            },
            {
                'knowledge_type': 'decision_outcome',
                'source': 'think_worker',
                'payload': {'decision': 'execute'}
            },
            {
                'knowledge_type': 'risk_pattern',
                'source': 'think_worker',
                'payload': {'risk_level': 'low'}
            }
        ]
        
        worker.process_received_knowledge(knowledge_list)
        
        # Verify all handlers were called
        worker._update_pattern_models.assert_called_once()
        worker._update_decision_making.assert_called_once()
        worker._update_risk_model.assert_called_once()
        assert worker.stats['knowledge_received'] == 3

    def test_process_received_knowledge_with_exception(self, mock_db, mock_dreamer):
        """Test processing knowledge with exception in handler"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock _update_risk_model to raise exception
        worker._update_risk_model = Mock(side_effect=Exception("Test error"))
        
        knowledge_list = [{
            'knowledge_type': 'risk_pattern',
            'source': 'think_worker',
            'payload': {'risk_level': 'high'}
        }]
        
        # Should not crash despite exception
        worker.process_received_knowledge(knowledge_list)
        
        # Should still update stats
        assert worker.stats['knowledge_received'] == 1

    def test_persist_knowledge_state(self, mock_db, mock_dreamer):
        """Test persisting knowledge state"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Add some received knowledge
        worker.received_knowledge = [
            {'knowledge_type': 'risk_pattern', 'source': 'think_worker', 'payload': {}}
        ]
        
        worker._persist_knowledge_state()
        
        # Verify update_worker_knowledge_state was called
        mock_knowledge_protocol.update_worker_knowledge_state.assert_called_once()

    def test_persist_knowledge_state_no_protocol(self, mock_db, mock_dreamer):
        """Test persisting knowledge state when protocol unavailable"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = None
        
        # Should not crash
        worker._persist_knowledge_state()
        
        assert True

    def test_persist_knowledge_state_exception(self, mock_db, mock_dreamer):
        """Test persisting knowledge state with exception"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock to raise exception
        mock_knowledge_protocol.update_worker_knowledge_state = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        worker.received_knowledge = [
            {'knowledge_type': 'risk_pattern', 'source': 'think_worker', 'payload': {}}
        ]
        
        # Should not crash
        worker._persist_knowledge_state()
        
        assert True


# ============================================================================
# Test Knowledge Query Methods
# ============================================================================

class TestKnowledgeQueryMethods:
    """Test knowledge query functionality"""

    def test_query_knowledge_basic(self, mock_db, mock_dreamer):
        """Test basic knowledge query"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock query_knowledge to return test data
        test_knowledge = [
            {'knowledge_type': 'risk_pattern', 'source': 'think_worker', 'payload': {}}
        ]
        mock_knowledge_protocol.query_knowledge = AsyncMock(return_value=test_knowledge)
        
        result = worker.query_knowledge()
        
        assert len(result) == 1
        mock_knowledge_protocol.query_knowledge.assert_called_once()

    def test_query_knowledge_with_filters(self, mock_db, mock_dreamer):
        """Test knowledge query with filters"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        test_knowledge = [
            {'knowledge_type': 'learned_pattern', 'source': 'learning_worker', 'payload': {}}
        ]
        mock_knowledge_protocol.query_knowledge = AsyncMock(return_value=test_knowledge)
        
        result = worker.query_knowledge(
            knowledge_types=['learned_pattern'],
            min_freshness=0.8,
            urgency='high',
            limit=5,
            worker_name='learning_worker'
        )
        
        assert len(result) == 1
        # Verify query was called with correct parameters
        call_kwargs = mock_knowledge_protocol.query_knowledge.call_args[1]
        assert call_kwargs['knowledge_types'] == ['learned_pattern']
        assert call_kwargs['min_freshness'] == 0.8
        assert call_kwargs['urgency'] == 'high'
        assert call_kwargs['limit'] == 5
        assert call_kwargs['source_worker'] == 'learning_worker'

    def test_query_knowledge_no_protocol(self, mock_db, mock_dreamer):
        """Test query when protocol unavailable"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = None
        
        result = worker.query_knowledge()
        
        assert result == []

    def test_query_knowledge_exception(self, mock_db, mock_dreamer):
        """Test query with exception"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock to raise exception
        mock_knowledge_protocol.query_knowledge = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        result = worker.query_knowledge()
        
        assert result == []

    def test_get_relevant_knowledge(self, mock_db, mock_dreamer):
        """Test get_relevant_knowledge (base implementation)"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        
        # Base implementation returns empty list
        result = worker.get_relevant_knowledge()
        
        assert result == []


# ============================================================================
# Test Worker-Specific Reception Logic
# ============================================================================

class TestWorkerSpecificReception:
    """Test reception logic specific to each worker type"""

    def test_think_worker_receives_learned_patterns(self, mock_db, mock_dreamer):
        """Test ThinkWorker receives and processes learned patterns"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock _update_pattern_models
        worker._update_pattern_models = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'learned_pattern',
            'source': 'learning_worker',
            'payload': {'pattern_id': 1, 'name': 'Test Pattern', 'confidence': 0.85}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # ThinkWorker should process learned patterns to inform decisions
        worker._update_pattern_models.assert_called_once()

    def test_think_worker_receives_issue_patterns(self, mock_db, mock_dreamer):
        """Test ThinkWorker receives and processes issue patterns"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock _update_issue_detection
        worker._update_issue_detection = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'issue_pattern',
            'source': 'analysis_worker',
            'payload': {'issue_type': 'bug', 'count': 5}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # ThinkWorker should process issue patterns for risk assessment
        worker._update_issue_detection.assert_called_once()

    def test_learning_worker_receives_decision_outcomes(self, mock_db, mock_dreamer):
        """Test LearningWorker receives decision outcomes"""
        worker = LearningWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock _update_decision_making
        worker._update_decision_making = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'decision_outcome',
            'source': 'think_worker',
            'payload': {'decision': 'execute', 'confidence': 0.88}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # LearningWorker should learn from decision outcomes
        worker._update_decision_making.assert_called_once()

    def test_learning_worker_receives_risk_patterns(self, mock_db, mock_dreamer):
        """Test LearningWorker receives risk patterns"""
        worker = LearningWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock _update_risk_model
        worker._update_risk_model = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'risk_pattern',
            'source': 'think_worker',
            'payload': {'risk_level': 'high', 'description': 'Test'}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # LearningWorker should learn from risk patterns
        worker._update_risk_model.assert_called_once()

    def test_analysis_worker_receives_learned_patterns(self, mock_db, mock_dreamer):
        """Test AnalysisWorker receives learned patterns"""
        worker = AnalysisWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock _update_pattern_models
        worker._update_pattern_models = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'learned_pattern',
            'source': 'learning_worker',
            'payload': {'pattern_id': 1, 'name': 'Test Pattern'}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # AnalysisWorker should use learned patterns for better analysis
        worker._update_pattern_models.assert_called_once()

    def test_dream_worker_receives_issue_patterns(self, mock_db, mock_dreamer):
        """Test DreamWorker receives issue patterns"""
        worker = DreamWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock _update_issue_detection
        worker._update_issue_detection = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'issue_pattern',
            'source': 'analysis_worker',
            'payload': {'issue_type': 'bug', 'count': 5}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # DreamWorker should know what issues to address in proposals
        worker._update_issue_detection.assert_called_once()

    def test_dream_worker_receives_complexity_trends(self, mock_db, mock_dreamer):
        """Test DreamWorker receives complexity trends"""
        worker = DreamWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock _update_complexity_analysis
        worker._update_complexity_analysis = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'complexity_trend',
            'source': 'analysis_worker',
            'payload': {'current_complexity': 15, 'trend': 'increasing'}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # DreamWorker should consider complexity in proposals
        worker._update_complexity_analysis.assert_called_once()

    def test_recall_worker_receives_context_enrichment(self, mock_db, mock_dreamer):
        """Test RecallWorker receives context enrichment metrics"""
        worker = RecallWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock _update_context_retrieval
        worker._update_context_retrieval = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'context_enrichment',
            'source': 'recall_worker',
            'payload': {'quality_score': 0.92, 'patterns_found': 5}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # RecallWorker should learn from enrichment quality
        worker._update_context_retrieval.assert_called_once()

    def test_recall_worker_receives_knowledge_retrieval(self, mock_db, mock_dreamer):
        """Test RecallWorker receives knowledge retrieval metrics"""
        worker = RecallWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock _update_context_retrieval
        worker._update_context_retrieval = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'knowledge_retrieval',
            'source': 'recall_worker',
            'payload': {'retrieval_success': True, 'query_time_ms': 45}
        }]
        
        worker.process_received_knowledge(knowledge_list)
        
        # RecallWorker should learn from retrieval patterns
        worker._update_context_retrieval.assert_called_once()


# ============================================================================
# Test Knowledge Filtering and Prioritization
# ============================================================================

class TestKnowledgeFiltering:
    """Test knowledge filtering and prioritization"""

    def test_process_high_priority_knowledge(self, mock_db, mock_dreamer):
        """Test processing high-priority knowledge immediately"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock _update_risk_model for high-priority processing
        worker._update_risk_model = Mock()
        
        # Create high-urgency knowledge
        knowledge = {
            'knowledge_type': 'risk_pattern',
            'source': 'think_worker',
            'payload': {'urgency': 'high', 'risk_level': 'critical'}
        }
        
        worker._process_high_priority_knowledge(knowledge)
        
        # Verify immediate processing
        worker._update_risk_model.assert_called_once_with({
            'urgency': 'high',
            'risk_level': 'critical'
        })

    def test_critical_issue_processing(self, mock_db, mock_dreamer):
        """Test critical issue flagging"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock _flag_critical_issue
        worker._flag_critical_issue = Mock()
        
        knowledge = {
            'knowledge_type': 'critical_issue',
            'source': 'analysis_worker',
            'payload': {'severity': 'critical', 'description': 'Test'}
        }
        
        worker._process_high_priority_knowledge(knowledge)
        
        # Verify critical issue was flagged
        worker._flag_critical_issue.assert_called_once()

    def test_urgency_levels(self, mock_db, mock_dreamer):
        """Test different urgency levels are handled correctly"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        worker._update_risk_model = Mock()
        
        # Test normal urgency (should not trigger immediate processing)
        knowledge_normal = {
            'knowledge_type': 'risk_pattern',
            'source': 'think_worker',
            'payload': {'urgency': 'normal', 'risk_level': 'low'}
        }
        
        # Add to received knowledge (not immediate processing)
        worker.received_knowledge.append(knowledge_normal)
        
        # Test high urgency (should trigger immediate processing)
        knowledge_high = {
            'knowledge_type': 'risk_pattern',
            'source': 'think_worker',
            'payload': {'urgency': 'high', 'risk_level': 'high'}
        }
        
        worker._process_high_priority_knowledge(knowledge_high)
        
        # Verify _update_risk_model was called only for high urgency
        worker._update_risk_model.assert_called_once()


# ============================================================================
# Test Knowledge Exchange Integration
# ============================================================================

class TestKnowledgeExchangeIntegration:
    """Test integration with knowledge exchange system"""

    def test_exchange_knowledge_receives_and_processes(self, mock_db, mock_dreamer):
        """Test _exchange_knowledge receives and processes knowledge"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock receive_knowledge to return test data
        test_knowledge = {
            'knowledge_type': 'risk_pattern',
            'source': 'think_worker',
            'payload': {'urgency': 'high', 'risk_level': 'high'}
        }
        
        # Mock to return one item then None to end loop
        mock_knowledge_protocol.receive_knowledge = AsyncMock(
            side_effect=[test_knowledge, None]
        )
        
        worker._exchange_knowledge()
        
        # Verify knowledge was received and stored
        assert len(worker.received_knowledge) == 1
        assert worker.stats['knowledge_exchanges'] == 1

    def test_exchange_knowledge_broadcasts_learnings(self, mock_db, mock_dreamer):
        """Test _exchange_knowledge broadcasts recent learnings"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock receive_knowledge to return empty
        mock_knowledge_protocol.receive_knowledge = AsyncMock(return_value=None)
        
        # Mock _get_recent_successes to return test data
        worker._get_recent_successes = Mock(return_value=[
            {'decision': 'execute', 'confidence': 0.85}
        ])
        
        worker._exchange_knowledge()
        
        # Verify broadcast_knowledge was called
        mock_knowledge_protocol.broadcast_knowledge.assert_called_once()

    def test_exchange_knowledge_updates_state(self, mock_db, mock_dreamer):
        """Test _exchange_knowledge updates worker knowledge state"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock receive_knowledge to return item then None
        test_knowledge = {
            'knowledge_type': 'risk_pattern',
            'source': 'think_worker',
            'payload': {}
        }
        mock_knowledge_protocol.receive_knowledge = AsyncMock(
            side_effect=[test_knowledge, None]
        )
        
        worker._exchange_knowledge()
        
        # Verify worker knowledge state was updated
        mock_knowledge_protocol.update_worker_knowledge_state.assert_called_once()

    def test_exchange_knowledge_no_protocol(self, mock_db, mock_dreamer):
        """Test _exchange_knowledge when protocol unavailable"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = None
        
        # Should not crash
        worker._exchange_knowledge()
        
        assert True

    def test_exchange_knowledge_exception(self, mock_db, mock_dreamer):
        """Test _exchange_knowledge with exception"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock receive_knowledge to raise exception
        mock_knowledge_protocol.receive_knowledge = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        # Should not crash
        worker._exchange_knowledge()
        
        assert True


# ============================================================================
# Test Statistics Tracking
# ============================================================================

class TestStatisticsTracking:
    """Test knowledge-related statistics tracking"""

    def test_knowledge_received_stat(self, mock_db, mock_dreamer):
        """Test knowledge_received statistic is tracked"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        knowledge_list = [
            {'knowledge_type': 'risk_pattern', 'source': 'think_worker', 'payload': {}},
            {'knowledge_type': 'learned_pattern', 'source': 'learning_worker', 'payload': {}}
        ]
        
        worker.process_received_knowledge(knowledge_list)
        
        assert worker.stats['knowledge_received'] == 2

    def test_knowledge_exchanges_stat(self, mock_db, mock_dreamer):
        """Test knowledge_exchanges statistic is tracked"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock receive_knowledge to return items
        test_knowledge = {
            'knowledge_type': 'risk_pattern',
            'source': 'think_worker',
            'payload': {}
        }
        mock_knowledge_protocol.receive_knowledge = AsyncMock(
            side_effect=[test_knowledge, test_knowledge, None]
        )
        
        worker._exchange_knowledge()
        
        assert worker.stats['knowledge_exchanges'] == 2

    def test_get_stats_includes_knowledge_stats(self, mock_db, mock_dreamer):
        """Test get_stats includes knowledge-related statistics"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Set some knowledge stats
        worker.stats['knowledge_received'] = 5
        worker.stats['knowledge_exchanges'] = 3
        
        stats = worker.get_stats()
        
        assert 'knowledge_received' in stats
        assert 'knowledge_exchanges' in stats
        assert stats['knowledge_received'] == 5
        assert stats['knowledge_exchanges'] == 3


# ============================================================================
# Test Error Handling and Edge Cases
# ============================================================================

class TestErrorHandling:
    """Test error handling in knowledge reception"""

    def test_process_empty_list(self, mock_db, mock_dreamer):
        """Test processing empty knowledge list"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        worker.process_received_knowledge([])
        
        # Should not crash
        assert worker.stats.get('knowledge_received', 0) == 0

    def test_process_none_list(self, mock_db, mock_dreamer):
        """Test processing None knowledge list"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Should not crash on None
        worker.process_received_knowledge(None)
        
        assert True

    def test_process_knowledge_without_knowledge_type(self, mock_db, mock_dreamer):
        """Test processing knowledge without knowledge_type"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        knowledge_list = [{
            'source': 'test_worker',
            'payload': {}
        }]
        
        # Should not crash
        worker.process_received_knowledge(knowledge_list)
        
        assert worker.stats['knowledge_received'] == 1

    def test_process_knowledge_without_payload(self, mock_db, mock_dreamer):
        """Test processing knowledge without payload"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        worker._update_risk_model = Mock()
        
        knowledge_list = [{
            'knowledge_type': 'risk_pattern',
            'source': 'think_worker'
        }]
        
        # Should not crash
        worker.process_received_knowledge(knowledge_list)
        
        # Should still call handler (with empty dict)
        worker._update_risk_model.assert_called_once_with({})

    def test_query_with_empty_results(self, mock_db, mock_dreamer):
        """Test query returns empty list"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        mock_knowledge_protocol.query_knowledge = AsyncMock(return_value=[])
        
        result = worker.query_knowledge()
        
        assert result == []

    def test_multiple_workers_receiving_same_knowledge(self, mock_db, mock_dreamer):
        """Test multiple workers receiving the same knowledge"""
        # Create knowledge that's relevant to multiple workers
        knowledge = {
            'knowledge_type': 'learned_pattern',
            'source': 'learning_worker',
            'payload': {'pattern_id': 1, 'name': 'Common Pattern', 'confidence': 0.85}
        }
        
        # Test ThinkWorker
        think_worker = ThinkWorker(mock_db, mock_dreamer)
        think_worker.knowledge_protocol = mock_knowledge_protocol
        think_worker._update_pattern_models = Mock()
        
        think_worker.process_received_knowledge([knowledge])
        think_worker._update_pattern_models.assert_called_once()
        
        # Test AnalysisWorker
        analysis_worker = AnalysisWorker(mock_db, mock_dreamer)
        analysis_worker.knowledge_protocol = mock_knowledge_protocol
        analysis_worker._update_pattern_models = Mock()
        
        analysis_worker.process_received_knowledge([knowledge])
        analysis_worker._update_pattern_models.assert_called_once()


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test performance of knowledge reception"""

    def test_large_knowledge_batch(self, mock_db, mock_dreamer):
        """Test processing large batch of knowledge"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock handlers
        worker._update_risk_model = Mock()
        worker._update_pattern_models = Mock()
        
        # Create large batch
        knowledge_list = []
        for i in range(100):
            if i % 2 == 0:
                knowledge_list.append({
                    'knowledge_type': 'risk_pattern',
                    'source': 'think_worker',
                    'payload': {'risk_level': 'low' if i % 3 == 0 else 'high'}
                })
            else:
                knowledge_list.append({
                    'knowledge_type': 'learned_pattern',
                    'source': 'learning_worker',
                    'payload': {'pattern_id': i, 'confidence': 0.5 + (i * 0.005)}
                })
        
        # Should process without error
        worker.process_received_knowledge(knowledge_list)
        
        assert worker.stats['knowledge_received'] == 100

    def test_query_performance(self, mock_db, mock_dreamer):
        """Test query performance with filters"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Mock query to return results
        test_knowledge = [{'knowledge_type': 'risk_pattern', 'source': 'think_worker', 'payload': {}}]
        mock_knowledge_protocol.query_knowledge = AsyncMock(return_value=test_knowledge)
        
        # Query with multiple filters
        result = worker.query_knowledge(
            knowledge_types=['risk_pattern', 'learned_pattern'],
            min_freshness=0.7,
            urgency='high',
            limit=20,
            worker_name='think_worker'
        )
        
        assert len(result) == 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestEndToEndIntegration:
    """End-to-end integration tests"""

    def test_complete_knowledge_lifecycle(self, mock_db, mock_dreamer):
        """Test complete knowledge lifecycle: broadcast -> query -> receive -> process"""
        worker = ThinkWorker(mock_db, mock_dreamer)
        worker.knowledge_protocol = mock_knowledge_protocol
        
        # Step 1: Query for knowledge
        test_knowledge = {
            'knowledge_type': 'learned_pattern',
            'source': 'learning_worker',
            'payload': {'pattern_id': 1, 'name': 'Test', 'confidence': 0.85}
        }
        mock_knowledge_protocol.query_knowledge = AsyncMock(return_value=[test_knowledge])
        
        knowledge = worker.query_knowledge(knowledge_types=['learned_pattern'])
        assert len(knowledge) == 1
        
        # Step 2: Process received knowledge
        worker._update_pattern_models = Mock()
        worker.process_received_knowledge(knowledge)
        
        # Step 3: Verify processing occurred
        worker._update_pattern_models.assert_called_once()
        
        # Step 4: Verify statistics updated
        assert worker.stats['knowledge_received'] == 1

    def test_worker_specific_knowledge_flow(self, mock_db, mock_dreamer):
        """Test knowledge flow through specific worker"""
        # LearningWorker broadcasts knowledge
        learning_worker = LearningWorker(mock_db, mock_dreamer)
        learning_worker.knowledge_protocol = mock_knowledge_protocol
        
        # ThinkWorker receives and uses knowledge
        think_worker = ThinkWorker(mock_db, mock_dreamer)
        think_worker.knowledge_protocol = mock_knowledge_protocol
        think_worker._update_pattern_models = Mock()
        
        # Simulate knowledge being available
        knowledge = {
            'knowledge_type': 'learned_pattern',
            'source': 'learning_worker',
            'payload': {'pattern_id': 1, 'name': 'Test Pattern', 'confidence': 0.85}
        }
        
        # ThinkWorker queries and processes
        mock_knowledge_protocol.query_knowledge = AsyncMock(return_value=[knowledge])
        queried = think_worker.query_knowledge(knowledge_types=['learned_pattern'])
        think_worker.process_received_knowledge(queried)
        
        # Verify knowledge was used
        think_worker._update_pattern_models.assert_called_once()

    def test_cross_worker_knowledge_propagation(self, mock_db, mock_dreamer):
        """Test knowledge propagation across multiple workers"""
        # Create knowledge that propagates through system
        knowledge_chain = [
            {
                'knowledge_type': 'learned_pattern',
                'source': 'learning_worker',
                'payload': {'pattern_id': 1, 'confidence': 0.85}
            },
            {
                'knowledge_type': 'decision_outcome',
                'source': 'think_worker',
                'payload': {'decision': 'execute', 'confidence': 0.88}
            },
            {
                'knowledge_type': 'issue_pattern',
                'source': 'analysis_worker',
                'payload': {'issue_type': 'bug', 'count': 5}
            }
        ]
        
        # ThinkWorker processes learned pattern
        think_worker = ThinkWorker(mock_db, mock_dreamer)
        think_worker.knowledge_protocol = mock_knowledge_protocol
        think_worker._update_pattern_models = Mock()
        
        think_worker.process_received_knowledge([knowledge_chain[0]])
        think_worker._update_pattern_models.assert_called_once()
        
        # LearningWorker processes decision outcome
        learning_worker = LearningWorker(mock_db, mock_dreamer)
        learning_worker.knowledge_protocol = mock_knowledge_protocol
        learning_worker._update_decision_making = Mock()
        
        learning_worker.process_received_knowledge([knowledge_chain[1]])
        learning_worker._update_decision_making.assert_called_once()
        
        # AnalysisWorker processes issue pattern
        analysis_worker = AnalysisWorker(mock_db, mock_dreamer)
        analysis_worker.knowledge_protocol = mock_knowledge_protocol
        analysis_worker._update_issue_detection = Mock()
        
        analysis_worker.process_received_knowledge([knowledge_chain[2]])
        analysis_worker._update_issue_detection.assert_called_once()


# ============================================================================
# Test Fixtures for All Workers
# ============================================================================

@pytest.fixture
def all_workers(mock_db, mock_dreamer):
    """Create all 5 workers for comprehensive testing"""
    return {
        'think': ThinkWorker(mock_db, mock_dreamer),
        'learning': LearningWorker(mock_db, mock_dreamer),
        'analysis': AnalysisWorker(mock_db, mock_dreamer),
        'dream': DreamWorker(mock_db, mock_dreamer),
        'recall': RecallWorker(mock_db, mock_dreamer),
    }


# ============================================================================
# Comprehensive Worker Integration Tests
# ============================================================================

class TestAllWorkersIntegration:
    """Test knowledge reception across all workers"""

    def test_all_workers_can_receive_knowledge(self, all_workers, mock_knowledge_protocol):
        """Test all workers can receive and process knowledge"""
        for name, worker in all_workers.items():
            worker.knowledge_protocol = mock_knowledge_protocol
            
            # Mock appropriate handler
            if name == 'think':
                worker._update_risk_model = Mock()
            elif name == 'learning':
                worker._update_pattern_models = Mock()
            elif name == 'analysis':
                worker._update_issue_detection = Mock()
            elif name == 'dream':
                worker._update_proposal_generation = Mock()
            elif name == 'recall':
                worker._update_context_retrieval = Mock()
            
            # Process knowledge
            knowledge = {
                'knowledge_type': 'risk_pattern',
                'source': 'think_worker',
                'payload': {'risk_level': 'high'}
            }
            worker.process_received_knowledge([knowledge])
            
            # Verify knowledge was received
            assert worker.stats['knowledge_received'] == 1

    def test_all_workers_can_query_knowledge(self, all_workers, mock_knowledge_protocol):
        """Test all workers can query for knowledge"""
        mock_knowledge_protocol.query_knowledge = AsyncMock(return_value=[])
        
        for name, worker in all_workers.items():
            worker.knowledge_protocol = mock_knowledge_protocol
            
            # Should not crash
            result = worker.query_knowledge()
            assert result == []

    def test_worker_specific_knowledge_types(self, all_workers, mock_knowledge_protocol):
        """Test workers process their specific knowledge types"""
        # ThinkWorker receives risk patterns
        think_worker = all_workers['think']
        think_worker.knowledge_protocol = mock_knowledge_protocol
        think_worker._update_risk_model = Mock()
        
        think_worker.process_received_knowledge([{
            'knowledge_type': 'risk_pattern',
            'source': 'think_worker',
            'payload': {'risk_level': 'high'}
        }])
        think_worker._update_risk_model.assert_called_once()
        
        # LearningWorker receives learned patterns
        learning_worker = all_workers['learning']
        learning_worker.knowledge_protocol = mock_knowledge_protocol
        learning_worker._update_pattern_models = Mock()
        
        learning_worker.process_received_knowledge([{
            'knowledge_type': 'learned_pattern',
            'source': 'learning_worker',
            'payload': {'pattern_id': 1}
        }])
        learning_worker._update_pattern_models.assert_called_once()
        
        # AnalysisWorker receives issue patterns
        analysis_worker = all_workers['analysis']
        analysis_worker.knowledge_protocol = mock_knowledge_protocol
        analysis_worker._update_issue_detection = Mock()
        
        analysis_worker.process_received_knowledge([{
            'knowledge_type': 'issue_pattern',
            'source': 'analysis_worker',
            'payload': {'issue_type': 'bug'}
        }])
        analysis_worker._update_issue_detection.assert_called_once()
        
        # DreamWorker receives proposal quality
        dream_worker = all_workers['dream']
        dream_worker.knowledge_protocol = mock_knowledge_protocol
        dream_worker._update_proposal_generation = Mock()
        
        dream_worker.process_received_knowledge([{
            'knowledge_type': 'proposal_quality',
            'source': 'dream_worker',
            'payload': {'proposal_count': 3}
        }])
        dream_worker._update_proposal_generation.assert_called_once()
        
        # RecallWorker receives context enrichment
        recall_worker = all_workers['recall']
        recall_worker.knowledge_protocol = mock_knowledge_protocol
        recall_worker._update_context_retrieval = Mock()
        
        recall_worker.process_received_knowledge([{
            'knowledge_type': 'context_enrichment',
            'source': 'recall_worker',
            'payload': {'quality_score': 0.9}
        }])
        recall_worker._update_context_retrieval.assert_called_once()


# ============================================================================
# Summary Tests
# ============================================================================

class TestSummary:
    """Summary tests to verify Phase 3 implementation"""

    def test_all_workers_have_knowledge_reception(self, all_workers):
        """Verify all workers have knowledge reception capabilities"""
        for name, worker in all_workers.items():
            # Check process_received_knowledge method exists
            assert hasattr(worker, 'process_received_knowledge')
            assert callable(worker.process_received_knowledge)
            
            # Check query_knowledge method exists
            assert hasattr(worker, 'query_knowledge')
            assert callable(worker.query_knowledge)
            
            # Check get_relevant_knowledge method exists
            assert hasattr(worker, 'get_relevant_knowledge')
            assert callable(worker.get_relevant_knowledge)

    def test_all_workers_have_reception_methods(self, all_workers):
        """Verify all workers have reception-related methods"""
        for name, worker in all_workers.items():
            # Check update methods exist
            assert hasattr(worker, '_update_pattern_models')
            assert hasattr(worker, '_update_issue_detection')
            assert hasattr(worker, '_update_proposal_generation')
            assert hasattr(worker, '_update_context_retrieval')
            assert hasattr(worker, '_update_decision_making')
            assert hasattr(worker, '_update_complexity_analysis')

    def test_knowledge_protocol_available(self, all_workers):
        """Verify knowledge protocol is available to all workers"""
        for name, worker in all_workers.items():
            # Protocol should be initialized (even if None initially)
            assert hasattr(worker, 'knowledge_protocol')
            assert hasattr(worker, 'received_knowledge')

    def test_statistics_tracking(self, all_workers):
        """Verify statistics are properly tracked"""
        for name, worker in all_workers.items():
            # Check stats include knowledge tracking
            assert 'knowledge_exchanges' in worker.stats
            
            # Check get_stats includes knowledge stats
            stats = worker.get_stats()
            assert 'knowledge_exchanges' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
