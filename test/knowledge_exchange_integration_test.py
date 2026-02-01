"""
Integration tests for worker knowledge exchange (Phase 2)

Tests the complete knowledge exchange cycle between all 5 workers:
- ThinkWorker broadcasts decision outcomes
- LearningWorker broadcasts learned patterns
- AnalysisWorker broadcasts issue patterns
- DreamWorker broadcasts proposal quality
- RecallWorker broadcasts context enrichment
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.openmemory.app.agents.think_worker import ThinkWorker
from src.openmemory.app.agents.learning_worker import LearningWorker
from src.openmemory.app.agents.analysis_worker import AnalysisWorker
from src.openmemory.app.agents.dream_worker import DreamWorker
from src.openmemory.app.agents.recall_worker import RecallWorker
from src.openmemory.app.models import (
    Project, Proposal, CodeSnapshot, 
    KnowledgeExchange, WorkerKnowledgeState
)
from src.openmemory.app.utils.knowledge_exchange import KnowledgeExchangeProtocol


class MockDreamer:
    """Mock DreamerMetaAgent for testing"""
    
    def propose_experiment(self, worker_name, context):
        return None
    
    def record_experiment_start(self, worker_name, experiment_name, hypothesis, approach):
        return 1
    
    def record_outcome(self, experiment_id, success, improvement, details):
        pass
    
    def get_promoted_experiments(self, worker_name):
        return []


class MockConfig:
    """Mock configuration for testing"""
    
    def __init__(self):
        self.workers = Mock()
        self.workers.think_interval = 8
        self.workers.learning_interval = 6
        self.workers.analysis_interval = 5
        self.workers.dream_interval = 4
        self.workers.recall_interval = 3
        
        self.committee = Mock()
        self.committee.weights = {
            'architect': 0.25,
            'reviewer': 0.20,
            'tester': 0.20,
            'security': 0.20,
            'optimizer': 0.15
        }
        
        self.autonomy = Mock()
        self.autonomy.level = 3
        self.autonomy.can_execute = lambda score: (score >= 0.7, "Met threshold")
        
        self.execution = Mock()
        self.execution.docker_enabled = False
        self.execution.auto_test = False
        self.execution.auto_build = False
        self.execution.min_test_coverage = 0.8
        
        self.cross_project = Mock()
        self.cross_project.enabled = True
        self.cross_project.similarity_threshold_language = 0.7
        self.cross_project.min_language_similarity = 0.6
        
        self.project = Mock()
        self.project.repo_url = "https://github.com/test/repo"
        self.project.branch = "main"
        self.project.workspace = "/tmp/test"
        self.project.token = "test_token"


class TestWorkerKnowledgeExchangeIntegration:
    """Integration tests for worker knowledge exchange"""
    
    @pytest.fixture
    def db_session(self):
        """Create a test database session"""
        from src.openmemory.app.database import get_test_db
        return get_test_db()
    
    @pytest.fixture
    def setup_test_data(self, db_session):
        """Set up test data for integration tests"""
        # Create test project
        project = Project(
            project_id=1,
            repo_url="https://github.com/test/repo",
            branch="main",
            workspace_path="/tmp/test",
            language="python",
            framework=None,
            domain=None,
            created_at=datetime.now(),
            last_analyzed=None
        )
        db_session.add(project)
        
        # Create test code snapshot
        snapshot = CodeSnapshot(
            project_id=1,
            complexity=8.5,
            test_coverage=0.75,
            issues_found=3,
            metrics_json=json.dumps({
                'maintainability': 65.0,
                'files_analyzed': 5,
                'lines_of_code': 500,
                'issues': [
                    {
                        'file': 'test.py',
                        'line': 10,
                        'severity': 'error',
                        'message': 'Function missing return type hint'
                    },
                    {
                        'file': 'test.py',
                        'line': 20,
                        'severity': 'warning',
                        'message': 'Mutable default argument detected'
                    }
                ]
            }),
            created_at=datetime.now() - timedelta(minutes=5)
        )
        db_session.add(snapshot)
        db_session.commit()
        
        return project, snapshot
    
    @pytest.fixture
    def knowledge_protocol(self):
        """Create a knowledge exchange protocol instance"""
        return KnowledgeExchangeProtocol()
    
    @pytest.fixture
    def mock_graphiti(self):
        """Mock Graphiti client for testing"""
        with patch('src.openmemory.app.utils.graphiti.get_graphiti_client_sync') as mock:
            mock_client = Mock()
            mock.return_value = mock_client
            
            # Mock search_decisions to return empty results
            async def mock_search(*args, **kwargs):
                return []
            
            mock_client.search_decisions = mock_search
            
            yield mock_client
    
    def test_think_worker_broadcasts_decision_outcome(self, db_session, setup_test_data, mock_graphiti):
        """Test that ThinkWorker broadcasts decision outcomes"""
        project, _ = setup_test_data
        
        # Create test proposal
        proposal = Proposal(
            proposal_id=1,
            project_id=1,
            title="Test Proposal",
            description="Test description",
            agents_json=json.dumps({
                'architect': 0.85,
                'reviewer': 0.80,
                'tester': 0.90,
                'security': 0.75,
                'optimizer': 0.70
            }),
            changes_json=json.dumps({
                'files_affected': ['test.py'],
                'change_type': 'bug_fix',
                'description': 'Fix type hints'
            }),
            confidence=0.82,
            critic_score=0.75,
            status='pending',
            created_at=datetime.now()
        )
        db_session.add(proposal)
        db_session.commit()
        
        # Create ThinkWorker
        dreamer = MockDreamer()
        think_worker = ThinkWorker(db_session, dreamer)
        think_worker.config = MockConfig()
        
        # Mock the broadcast method to capture calls
        with patch.object(think_worker, '_broadcast_knowledge') as mock_broadcast:
            # Evaluate proposal (this should trigger broadcast)
            decision = think_worker._evaluate_proposal(proposal)
            
            # Verify broadcast was called
            assert mock_broadcast.call_count >= 1
            
            # Check that decision_outcome was broadcast
            broadcast_calls = [call for call in mock_broadcast.call_args_list 
                             if call[1].get('knowledge_type') == 'decision_outcome']
            assert len(broadcast_calls) > 0
            
            # Verify content structure
            call_args = broadcast_calls[0]
            content = call_args[1]['content']
            assert 'proposal_id' in content
            assert 'action' in content
            assert 'confidence' in content
            assert 'committee_scores' in content
    
    def test_learning_worker_broadcasts_learned_pattern(self, db_session, setup_test_data, mock_graphiti):
        """Test that LearningWorker broadcasts learned patterns"""
        project, snapshot = setup_test_data
        
        # Create executed proposal
        proposal = Proposal(
            proposal_id=2,
            project_id=1,
            title="Executed Proposal",
            description="Test description",
            agents_json=json.dumps({
                'architect': 0.85,
                'reviewer': 0.80,
                'tester': 0.90,
                'security': 0.75,
                'optimizer': 0.70
            }),
            changes_json=json.dumps({
                'files_affected': ['test.py'],
                'change_type': 'bug_fix',
                'description': 'Fix type hints'
            }),
            confidence=0.85,
            critic_score=0.75,
            status='executed',
            executed_at=datetime.now() - timedelta(minutes=10),
            commit_sha=json.dumps({'simulated': True})
        )
        db_session.add(proposal)
        db_session.commit()
        
        # Create LearnWorker
        dreamer = MockDreamer()
        learning_worker = LearningWorker(db_session, dreamer)
        learning_worker.config = MockConfig()
        
        # Mock the broadcast method
        with patch.object(learning_worker, '_broadcast_knowledge') as mock_broadcast:
            # Mock cross-project system to return a pattern
            with patch.object(learning_worker.xp_system, 'extract_pattern_from_proposal') as mock_extract:
                mock_pattern = Mock()
                mock_pattern.pattern_id = 1
                mock_pattern.pattern_name = "Test Pattern"
                mock_pattern.pattern_type = "bug_fix"
                mock_pattern.confidence = 0.80
                mock_pattern.success_count = 1
                mock_pattern.failure_count = 0
                mock_extract.return_value = mock_pattern
                
                # Extract pattern (this should trigger broadcast)
                success = learning_worker._extract_and_store_pattern(proposal)
                
                # Verify broadcast was called
                assert mock_broadcast.call_count >= 1
                
                # Check that learned_pattern was broadcast
                broadcast_calls = [call for call in mock_broadcast.call_args_list 
                                 if call[1].get('knowledge_type') == 'learned_pattern']
                assert len(broadcast_calls) > 0
                
                # Verify content structure
                call_args = broadcast_calls[0]
                content = call_args[1]['content']
                assert 'pattern_id' in content
                assert 'pattern_name' in content
                assert 'pattern_type' in content
                assert 'confidence' in content
                assert 'success_rate' in content
    
    def test_analysis_worker_broadcasts_issue_pattern(self, db_session, setup_test_data, mock_graphiti):
        """Test that AnalysisWorker broadcasts issue patterns"""
        project, _ = setup_test_data
        
        # Create AnalysisWorker
        dreamer = MockDreamer()
        analysis_worker = AnalysisWorker(db_session, dreamer, project_id=1)
        analysis_worker.config = MockConfig()
        
        # Mock _analyze_codebase to return snapshot with multiple issues
        with patch.object(analysis_worker, '_analyze_codebase') as mock_analyze:
            mock_analyze.return_value = {
                'complexity': 10.5,
                'maintainability': 60.0,
                'test_coverage': 0.70,
                'issues_found': 10,
                'files_analyzed': 3,
                'lines_of_code': 400,
                'issues': [
                    {
                        'file': 'test.py',
                        'line': 10,
                        'severity': 'warning',
                        'message': 'Function missing return type hint'
                    },
                    {
                        'file': 'test.py',
                        'line': 15,
                        'severity': 'warning',
                        'message': 'Function missing return type hint'
                    },
                    {
                        'file': 'test.py',
                        'line': 20,
                        'severity': 'warning',
                        'message': 'Function missing return type hint'
                    }
                ]
            }
            
            # Mock the broadcast method
            with patch.object(analysis_worker, '_broadcast_knowledge') as mock_broadcast:
                # Analyze codebase (this should trigger broadcast)
                snapshot = analysis_worker._analyze_codebase("/tmp/test", "python")
                
                # Verify broadcast was called
                assert mock_broadcast.call_count >= 1
                
                # Check that issue_pattern was broadcast
                broadcast_calls = [call for call in mock_broadcast.call_args_list 
                                 if call[1].get('knowledge_type') == 'issue_pattern']
                assert len(broadcast_calls) > 0
                
                # Verify content structure
                call_args = broadcast_calls[0]
                content = call_args[1]['content']
                assert 'issue_type' in content
                assert 'count' in content
                assert 'severity' in content
                assert 'files_affected' in content
    
    def test_dream_worker_broadcasts_proposal_quality(self, db_session, setup_test_data, mock_graphiti):
        """Test that DreamWorker broadcasts proposal quality"""
        project, snapshot = setup_test_data
        
        # Create DreamWorker
        dreamer = MockDreamer()
        dream_worker = DreamWorker(db_session, dreamer)
        dream_worker.config = MockConfig()
        
        # Mock LLM calls
        with patch('src.openmemory.app.agents.dream_worker.get_openai_client') as mock_llm:
            mock_client = Mock()
            mock_llm.return_value = mock_client
            
            # Mock response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "title": "Fix Type Hints",
                "description": "Add missing type hints",
                "confidence": 0.85,
                "changes": [
                    {
                        "file": "test.py",
                        "original": "def foo():",
                        "fixed": "def foo() -> None:",
                        "explanation": "Added return type"
                    }
                ],
                "testing_strategy": "Run mypy",
                "historical_lessons": "Type hints improve maintainability"
            })
            mock_client.chat.completions.create.return_value = mock_response
            
            # Mock the broadcast method
            with patch.object(dream_worker, '_broadcast_knowledge') as mock_broadcast:
                # Generate proposals (this should trigger broadcast)
                proposals = dream_worker._generate_proposals(snapshot)
                
                # Verify broadcast was called
                assert mock_broadcast.call_count >= 1
                
                # Check that proposal_quality was broadcast
                broadcast_calls = [call for call in mock_broadcast.call_args_list 
                                 if call[1].get('knowledge_type') == 'proposal_quality']
                assert len(broadcast_calls) > 0
                
                # Verify content structure
                call_args = broadcast_calls[0]
                content = call_args[1]['content']
                assert 'proposal_count' in content
                assert 'avg_confidence' in content
                assert 'issue_count' in content
                assert 'change_types' in content
    
    def test_recall_worker_broadcasts_context_enrichment(self, db_session, setup_test_data, mock_graphiti):
        """Test that RecallWorker broadcasts context enrichment"""
        project, _ = setup_test_data
        
        # Create test proposal
        proposal = Proposal(
            proposal_id=3,
            project_id=1,
            title="Test Proposal",
            description="Test description",
            agents_json=json.dumps({
                'architect': 0.85,
                'reviewer': 0.80,
                'tester': 0.90,
                'security': 0.75,
                'optimizer': 0.70
            }),
            changes_json=json.dumps({
                'files_affected': ['test.py'],
                'change_type': 'bug_fix',
                'description': 'Fix type hints'
            }),
            confidence=0.82,
            critic_score=0.75,
            status='pending',
            created_at=datetime.now()
        )
        db_session.add(proposal)
        db_session.commit()
        
        # Create RecallWorker
        dreamer = MockDreamer()
        recall_worker = RecallWorker(db_session, dreamer)
        recall_worker.config = MockConfig()
        
        # Mock the broadcast method
        with patch.object(recall_worker, '_broadcast_knowledge') as mock_broadcast:
            # Enrich proposal with context (this should trigger broadcast)
            context = {
                'similar_patterns': [{'pattern_name': 'Test Pattern', 'confidence': 0.85}],
                'past_proposals': [{'title': 'Past Proposal', 'confidence': 0.90}],
                'cross_project_insights': [],
                'knowledge_graph_context': {
                    'relevant_facts': [],
                    'query_status': 'success',
                    'search_query': 'bug fix',
                    'total_results': 2
                },
                'retrieval_timestamp': datetime.now()
            }
            
            recall_worker._enrich_proposal_with_context(proposal, context)
            
            # Verify broadcast was called
            assert mock_broadcast.call_count >= 2  # context_enrichment + knowledge_retrieval
            
            # Check that context_enrichment was broadcast
            enrichment_calls = [call for call in mock_broadcast.call_args_list 
                              if call[1].get('knowledge_type') == 'context_enrichment']
            assert len(enrichment_calls) > 0
            
            # Verify content structure
            call_args = enrichment_calls[0]
            content = call_args[1]['content']
            assert 'proposal_id' in content
            assert 'quality_metrics' in content
            assert 'enrichment_timestamp' in content
            
            # Check knowledge_retrieval broadcast
            retrieval_calls = [call for call in mock_broadcast.call_args_list 
                             if call[1].get('knowledge_type') == 'knowledge_retrieval']
            assert len(retrieval_calls) > 0
            
            retrieval_args = retrieval_calls[0]
            retrieval_content = retrieval_args[1]['content']
            assert 'query' in retrieval_content
            assert 'results_found' in retrieval_content
            assert 'query_status' in retrieval_content
    
    def test_cross_worker_knowledge_propagation(self, db_session, setup_test_data, mock_graphiti):
        """Test that knowledge propagates from one worker to another"""
        project, _ = setup_test_data
        
        # Create a proposal and decision
        proposal = Proposal(
            proposal_id=4,
            project_id=1,
            title="Test Proposal",
            description="Test description",
            agents_json=json.dumps({
                'architect': 0.85,
                'reviewer': 0.80,
                'tester': 0.90,
                'security': 0.75,
                'optimizer': 0.70
            }),
            changes_json=json.dumps({
                'files_affected': ['test.py'],
                'change_type': 'bug_fix',
                'description': 'Fix type hints'
            }),
            confidence=0.82,
            critic_score=0.75,
            status='pending',
            created_at=datetime.now()
        )
        db_session.add(proposal)
        db_session.commit()
        
        # Create ThinkWorker and broadcast
        dreamer = MockDreamer()
        think_worker = ThinkWorker(db_session, dreamer)
        think_worker.config = MockConfig()
        
        # Capture knowledge broadcast
        captured_knowledge = []
        original_broadcast = think_worker._broadcast_knowledge
        
        def capture_broadcast(knowledge_type, content, urgency):
            captured_knowledge.append({
                'knowledge_type': knowledge_type,
                'content': content,
                'urgency': urgency,
                'timestamp': datetime.now()
            })
            return original_broadcast(knowledge_type, content, urgency)
        
        with patch.object(think_worker, '_broadcast_knowledge', side_effect=capture_broadcast):
            think_worker._evaluate_proposal(proposal)
            
            # Verify knowledge was captured
            assert len(captured_knowledge) > 0
            
            # Find decision outcome knowledge
            decision_knowledge = [k for k in captured_knowledge 
                                if k['knowledge_type'] == 'decision_outcome']
            assert len(decision_knowledge) > 0
            
            # Verify knowledge structure
            knowledge = decision_knowledge[0]
            assert knowledge['content']['proposal_id'] == 4
            assert 'action' in knowledge['content']
            assert knowledge['urgency'] == 'low'
    
    def test_knowledge_freshness_decay(self, db_session, mock_graphiti):
        """Test that knowledge freshness decays over time"""
        # Create old knowledge exchange record
        old_exchange = KnowledgeExchange(
            worker_id='test_worker',
            knowledge_type='decision_outcome',
            content=json.dumps({'proposal_id': 1, 'action': 'execute'}),
            urgency='low',
            freshness_score=1.0,
            created_at=datetime.now() - timedelta(days=30)  # 30 days old
        )
        db_session.add(old_exchange)
        db_session.commit()
        
        # Create protocol and calculate freshness
        protocol = KnowledgeExchangeProtocol()
        
        # Freshness should decay with exponential decay
        # Half-life for decision outcomes is 7 days
        # After 30 days: exp(-30/7) ≈ 0.015
        expected_freshness = protocol.calculate_freshness(
            old_exchange.created_at,
            'decision_outcome'
        )
        
        assert expected_freshness < 0.1  # Should be very low after 30 days
        assert expected_freshness > 0.0  # Should still be positive
    
    def test_knowledge_validation(self, db_session):
        """Test that knowledge validation works correctly"""
        protocol = KnowledgeExchangeProtocol()
        
        # Test valid knowledge
        valid_knowledge = {
            'proposal_id': 1,
            'action': 'execute',
            'confidence': 0.85,
            'committee_scores': {
                'architect': 0.85,
                'reviewer': 0.80,
                'tester': 0.90,
                'security': 0.75,
                'optimizer': 0.70
            },
            'risk_assessment': {
                'risk_level': 'low',
                'factors': []
            }
        }
        
        is_valid, errors = protocol.validate_knowledge('decision_outcome', valid_knowledge)
        assert is_valid is True
        assert len(errors) == 0
        
        # Test invalid knowledge
        invalid_knowledge = {
            'proposal_id': 1,
            'action': 'invalid_action',  # Should be one of execute/approve/reject/defer
            'confidence': 0.85,
            'committee_scores': {
                'architect': 0.85,
                'reviewer': 0.80,
                'tester': 0.90,
                'security': 0.75,
                'optimizer': 0.70
            },
            'risk_assessment': {
                'risk_level': 'low',
                'factors': []
            }
        }
        
        is_valid, errors = protocol.validate_knowledge('decision_outcome', invalid_knowledge)
        assert is_valid is False
        assert len(errors) > 0
        assert 'action' in errors[0]
    
    def test_worker_statistics_tracking(self, db_session):
        """Test that worker statistics are tracked correctly"""
        # Create worker knowledge states
        states = [
            WorkerKnowledgeState(
                worker_id='think_worker',
                knowledge_type='decision_outcome',
                broadcast_count=5,
                received_count=3,
                last_broadcast=datetime.now(),
                last_received=datetime.now()
            ),
            WorkerKnowledgeState(
                worker_id='learning_worker',
                knowledge_type='learned_pattern',
                broadcast_count=8,
                received_count=12,
                last_broadcast=datetime.now(),
                last_received=datetime.now()
            ),
            WorkerKnowledgeState(
                worker_id='analysis_worker',
                knowledge_type='issue_pattern',
                broadcast_count=15,
                received_count=7,
                last_broadcast=datetime.now(),
                last_received=datetime.now()
            ),
            WorkerKnowledgeState(
                worker_id='dream_worker',
                knowledge_type='proposal_quality',
                broadcast_count=6,
                received_count=10,
                last_broadcast=datetime.now(),
                last_received=datetime.now()
            ),
            WorkerKnowledgeState(
                worker_id='recall_worker',
                knowledge_type='context_enrichment',
                broadcast_count=4,
                received_count=15,
                last_broadcast=datetime.now(),
                last_received=datetime.now()
            )
        ]
        
        for state in states:
            db_session.add(state)
        db_session.commit()
        
        # Query and verify statistics
        from src.openmemory.app.models import WorkerKnowledgeState
        
        think_state = db_session.query(WorkerKnowledgeState)\
            .filter(WorkerKnowledgeState.worker_id == 'think_worker')\
            .first()
        
        assert think_state is not None
        assert think_state.broadcast_count == 5
        assert think_state.received_count == 3
    
    def test_integration_with_all_workers(self, db_session, setup_test_data, mock_graphiti):
        """Test complete integration cycle through all workers"""
        project, snapshot = setup_test_data
        
        # Create DreamWorker and generate proposals
        dreamer = MockDreamer()
        dream_worker = DreamWorker(db_session, dreamer)
        dream_worker.config = MockConfig()
        
        # Mock LLM
        with patch('src.openmemory.app.agents.dream_worker.get_openai_client') as mock_llm:
            mock_client = Mock()
            mock_llm.return_value = mock_client
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "title": "Fix Issue",
                "description": "Fix code quality issue",
                "confidence": 0.80,
                "changes": [{"file": "test.py"}],
                "testing_strategy": "Run tests",
                "historical_lessons": "Test"
            })
            mock_client.chat.completions.create.return_value = mock_response
            
            # Generate proposals
            proposals = dream_worker._generate_proposals(snapshot)
            
            # Store proposal
            if proposals:
                dream_worker._store_proposal(1, proposals[0])
        
        # Get the stored proposal
        proposal = db_session.query(Proposal)\
            .filter(Proposal.title == "Fix Issue")\
            .first()
        
        assert proposal is not None
        
        # Create RecallWorker and enrich context
        recall_worker = RecallWorker(db_session, dreamer)
        recall_worker.config = MockConfig()
        
        with patch.object(recall_worker, '_broadcast_knowledge') as mock_broadcast:
            context = {
                'similar_patterns': [],
                'past_proposals': [],
                'cross_project_insights': [],
                'knowledge_graph_context': {
                    'relevant_facts': [],
                    'query_status': 'success',
                    'search_query': 'test',
                    'total_results': 0
                },
                'retrieval_timestamp': datetime.now()
            }
            
            recall_worker._enrich_proposal_with_context(proposal, context)
            
            # Verify knowledge was broadcast
            assert mock_broadcast.call_count >= 2
        
        # Create ThinkWorker and evaluate
        think_worker = ThinkWorker(db_session, dreamer)
        think_worker.config = MockConfig()
        
        with patch.object(think_worker, '_broadcast_knowledge') as mock_broadcast:
            decision = think_worker._evaluate_proposal(proposal)
            
            # Verify decision was made and knowledge was broadcast
            assert 'action' in decision
            assert mock_broadcast.call_count >= 1
    
    @pytest.mark.parametrize("worker_type,knowledge_type,expected_broadcast_count", [
        ('think', 'decision_outcome', 2),  # decision_outcome + risk_pattern
        ('learning', 'learned_pattern', 1),
        ('analysis', 'issue_pattern', 1),
        ('dream', 'proposal_quality', 1),
        ('recall', 'context_enrichment', 2),  # context_enrichment + knowledge_retrieval
    ])
    def test_worker_broadcasts_correct_knowledge_types(
        self, worker_type, knowledge_type, expected_broadcast_count,
        db_session, setup_test_data, mock_graphiti
    ):
        """Test that each worker broadcasts the correct knowledge types"""
        project, _ = setup_test_data
        
        dreamer = MockDreamer()
        
        if worker_type == 'think':
            worker = ThinkWorker(db_session, dreamer)
            worker.config = MockConfig()
            
            proposal = Proposal(
                proposal_id=5,
                project_id=1,
                title="Test",
                description="Test",
                agents_json=json.dumps({
                    'architect': 0.85,
                    'reviewer': 0.80,
                    'tester': 0.90,
                    'security': 0.75,
                    'optimizer': 0.70
                }),
                changes_json=json.dumps({
                    'files_affected': ['test.py'],
                    'change_type': 'bug_fix',
                    'description': 'Test'
                }),
                confidence=0.82,
                critic_score=0.75,
                status='pending',
                created_at=datetime.now()
            )
            db_session.add(proposal)
            db_session.commit()
            
            with patch.object(worker, '_broadcast_knowledge') as mock_broadcast:
                worker._evaluate_proposal(proposal)
                broadcast_calls = [call for call in mock_broadcast.call_args_list 
                                 if call[1].get('knowledge_type') == knowledge_type]
                assert len(broadcast_calls) == expected_broadcast_count
        
        elif worker_type == 'learning':
            worker = LearningWorker(db_session, dreamer)
            worker.config = MockConfig()
            
            proposal = Proposal(
                proposal_id=6,
                project_id=1,
                title="Test",
                description="Test",
                agents_json=json.dumps({
                    'architect': 0.85,
                    'reviewer': 0.80,
                    'tester': 0.90,
                    'security': 0.75,
                    'optimizer': 0.70
                }),
                changes_json=json.dumps({
                    'files_affected': ['test.py'],
                    'change_type': 'bug_fix',
                    'description': 'Test'
                }),
                confidence=0.85,
                critic_score=0.75,
                status='executed',
                executed_at=datetime.now() - timedelta(minutes=10),
                commit_sha=json.dumps({'simulated': True})
            )
            db_session.add(proposal)
            db_session.commit()
            
            with patch.object(worker, '_broadcast_knowledge') as mock_broadcast:
                with patch.object(worker.xp_system, 'extract_pattern_from_proposal') as mock_extract:
                    mock_pattern = Mock()
                    mock_pattern.pattern_id = 1
                    mock_pattern.pattern_name = "Test"
                    mock_pattern.pattern_type = "bug_fix"
                    mock_pattern.confidence = 0.80
                    mock_pattern.success_count = 1
                    mock_pattern.failure_count = 0
                    mock_extract.return_value = mock_pattern
                    
                    worker._extract_and_store_pattern(proposal)
                    broadcast_calls = [call for call in mock_broadcast.call_args_list 
                                     if call[1].get('knowledge_type') == knowledge_type]
                    assert len(broadcast_calls) == expected_broadcast_count
        
        elif worker_type == 'analysis':
            worker = AnalysisWorker(db_session, dreamer, project_id=1)
            worker.config = MockConfig()
            
            with patch.object(worker, '_analyze_codebase') as mock_analyze:
                mock_analyze.return_value = {
                    'complexity': 10.5,
                    'maintainability': 60.0,
                    'test_coverage': 0.70,
                    'issues_found': 10,
                    'files_analyzed': 3,
                    'lines_of_code': 400,
                    'issues': [
                        {
                            'file': 'test.py',
                            'line': 10,
                            'severity': 'warning',
                            'message': 'Function missing return type hint'
                        },
                        {
                            'file': 'test.py',
                            'line': 15,
                            'severity': 'warning',
                            'message': 'Function missing return type hint'
                        },
                        {
                            'file': 'test.py',
                            'line': 20,
                            'severity': 'warning',
                            'message': 'Function missing return type hint'
                        }
                    ]
                }
                
                with patch.object(worker, '_broadcast_knowledge') as mock_broadcast:
                    worker._analyze_codebase("/tmp/test", "python")
                    broadcast_calls = [call for call in mock_broadcast.call_args_list 
                                     if call[1].get('knowledge_type') == knowledge_type]
                    assert len(broadcast_calls) == expected_broadcast_count
        
        elif worker_type == 'dream':
            worker = DreamWorker(db_session, dreamer)
            worker.config = MockConfig()
            
            snapshot = CodeSnapshot(
                project_id=1,
                complexity=8.5,
                test_coverage=0.75,
                issues_found=3,
                metrics_json=json.dumps({
                    'maintainability': 65.0,
                    'files_analyzed': 5,
                    'lines_of_code': 500,
                    'issues': [
                        {
                            'file': 'test.py',
                            'line': 10,
                            'severity': 'error',
                            'message': 'Function missing return type hint'
                        }
                    ]
                }),
                created_at=datetime.now() - timedelta(minutes=5)
            )
            
            with patch('src.openmemory.app.agents.dream_worker.get_openai_client') as mock_llm:
                mock_client = Mock()
                mock_llm.return_value = mock_client
                
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = json.dumps({
                    "title": "Fix",
                    "description": "Fix",
                    "confidence": 0.80,
                    "changes": [{"file": "test.py"}],
                    "testing_strategy": "Test",
                    "historical_lessons": "Test"
                })
                mock_client.chat.completions.create.return_value = mock_response
                
                with patch.object(worker, '_broadcast_knowledge') as mock_broadcast:
                    worker._generate_proposals(snapshot)
                    broadcast_calls = [call for call in mock_broadcast.call_args_list 
                                     if call[1].get('knowledge_type') == knowledge_type]
                    assert len(broadcast_calls) == expected_broadcast_count
        
        elif worker_type == 'recall':
            worker = RecallWorker(db_session, dreamer)
            worker.config = MockConfig()
            
            proposal = Proposal(
                proposal_id=7,
                project_id=1,
                title="Test",
                description="Test",
                agents_json=json.dumps({
                    'architect': 0.85,
                    'reviewer': 0.80,
                    'tester': 0.90,
                    'security': 0.75,
                    'optimizer': 0.70
                }),
                changes_json=json.dumps({
                    'files_affected': ['test.py'],
                    'change_type': 'bug_fix',
                    'description': 'Test'
                }),
                confidence=0.82,
                critic_score=0.75,
                status='pending',
                created_at=datetime.now()
            )
            db_session.add(proposal)
            db_session.commit()
            
            with patch.object(worker, '_broadcast_knowledge') as mock_broadcast:
                context = {
                    'similar_patterns': [],
                    'past_proposals': [],
                    'cross_project_insights': [],
                    'knowledge_graph_context': {
                        'relevant_facts': [],
                        'query_status': 'success',
                        'search_query': 'test',
                        'total_results': 0
                    },
                    'retrieval_timestamp': datetime.now()
                }
                
                worker._enrich_proposal_with_context(proposal, context)
                broadcast_calls = [call for call in mock_broadcast.call_args_list 
                                 if call[1].get('knowledge_type') == knowledge_type]
                assert len(broadcast_calls) == expected_broadcast_count
