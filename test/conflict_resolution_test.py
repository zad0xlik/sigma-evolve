"""
Conflict Resolution System Tests

Tests for conflict detection and resolution functionality.
"""

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from src.openmemory.app.database import get_session
from src.openmemory.app.models import KnowledgeExchange
from src.openmemory.app.utils.conflict_resolver import (
    ConflictResolver,
    ConflictAnalysis,
    ResolutionStrategy,
    ConflictType,
    AutoConflictManager,
)


class TestConflictResolver(unittest.TestCase):
    """Test conflict resolver functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.resolver = ConflictResolver(similarity_threshold=0.85)
        
        # Create mock knowledge items
        self.knowledge_a = KnowledgeExchange(
            id="kw_001",
            knowledge_type="risk_pattern",
            knowledge_content=json.dumps({
                "risk_level": "high",
                "description": "Always use try-except blocks for error handling"
            }),
            topics=json.dumps(["error_handling", "best_practices"]),
            source_worker="think_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.9, "source": "production"},
            created_at=datetime.now(timezone.utc)
        )
        
        self.knowledge_b = KnowledgeExchange(
            id="kw_002",
            knowledge_type="risk_pattern",
            knowledge_content=json.dumps({
                "risk_level": "high",
                "description": "Never use try-except blocks, let errors propagate"
            }),
            topics=json.dumps(["error_handling", "anti_pattern"]),
            source_worker="learning_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.85, "source": "experiment"},
            created_at=datetime.now(timezone.utc)
        )
        
        self.knowledge_c = KnowledgeExchange(
            id="kw_003",
            knowledge_type="learned_pattern",
            knowledge_content=json.dumps({
                "pattern": "retry_mechanism",
                "success_rate": 0.85
            }),
            topics=json.dumps(["reliability", "pattern"]),
            source_worker="recall_worker",
            target_worker="think_worker",
            urgency="normal",
            metadata={"confidence": 0.92},
            created_at=datetime.now(timezone.utc)
        )
        
        self.knowledge_d = KnowledgeExchange(
            id="kw_004",
            knowledge_type="learned_pattern",
            knowledge_content=json.dumps({
                "pattern": "retry_mechanism",
                "success_rate": 0.90
            }),
            topics=json.dumps(["reliability", "pattern"]),
            source_worker="analysis_worker",
            target_worker="think_worker",
            urgency="normal",
            metadata={"confidence": 0.88},
            created_at=datetime.now(timezone.utc)
        )

    def test_duplicate_detection(self):
        """Test detection of duplicate knowledge"""
        # Create similar knowledge items
        kw1 = KnowledgeExchange(
            id="dup_1",
            knowledge_type="decision_outcome",
            knowledge_content=json.dumps({
                "decision": "use_sqlite",
                "reason": "faster for local development"
            }),
            topics=json.dumps(["database", "local_dev"]),
            source_worker="think_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.8},
            created_at=datetime.now(timezone.utc)
        )
        
        kw2 = KnowledgeExchange(
            id="dup_2",
            knowledge_type="decision_outcome",
            knowledge_content=json.dumps({
                "decision": "use_sqlite",
                "reason": "faster for local development"
            }),
            topics=json.dumps(["database", "local_dev"]),
            source_worker="learning_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.85},
            created_at=datetime.now(timezone.utc)
        )
        
        conflict = self.resolver.analyze_conflicts(kw1, kw2)
        
        self.assertEqual(conflict.conflict_type, ConflictType.DUPLICATE)
        self.assertGreater(conflict.similarity_score, 0.95)
        self.assertIn("duplicate", conflict.summary.lower())

    def test_contradiction_detection(self):
        """Test detection of contradictory knowledge"""
        conflict = self.resolver.analyze_conflicts(self.knowledge_a, self.knowledge_b)
        
        self.assertEqual(conflict.conflict_type, ConflictType.CONTRADICTORY)
        self.assertGreater(conflict.contradiction_score, 0.5)
        self.assertIn("contradictory", conflict.summary.lower())

    def test_overlap_detection(self):
        """Test detection of overlapping knowledge"""
        conflict = self.resolver.analyze_conflicts(self.knowledge_c, self.knowledge_d)
        
        self.assertEqual(conflict.conflict_type, ConflictType.OVERLAPPING)
        self.assertGreater(conflict.overlap_score, 0.3)
        self.assertIn("overlapping", conflict.summary.lower())

    def test_resolve_contradiction_select_newer(self):
        """Test resolving contradiction by selecting newer knowledge"""
        analysis = ConflictAnalysis(
            conflict_id="test_conflict",
            knowledge_a_id="kw_001",
            knowledge_b_id="kw_002",
            conflict_type=ConflictType.CONTRADICTORY,
            severity="high",
            confidence=0.9,
            recommended_strategy=ResolutionStrategy.SELECT_NEWER
        )
        
        resolution = self.resolver.resolve_conflict(analysis, ResolutionStrategy.SELECT_NEWER)
        
        self.assertEqual(resolution.strategy, ResolutionStrategy.SELECT_NEWER)
        self.assertIsNotNone(resolution.selected_knowledge_id)
        self.assertIn("Selected newer", resolution.resolution_notes)
        self.assertGreater(resolution.resolution_confidence, 0.5)

    def test_resolve_contradiction_select_higher_quality(self):
        """Test resolving contradiction by selecting higher quality knowledge"""
        analysis = ConflictAnalysis(
            conflict_id="test_conflict",
            knowledge_a_id="kw_001",
            knowledge_b_id="kw_002",
            conflict_type=ConflictType.CONTRADICTORY,
            severity="high",
            confidence=0.9,
            recommended_strategy=ResolutionStrategy.SELECT_HIGHER_QUALITY
        )
        
        resolution = self.resolver.resolve_conflict(analysis, ResolutionStrategy.SELECT_HIGHER_QUALITY)
        
        self.assertEqual(resolution.strategy, ResolutionStrategy.SELECT_HIGHER_QUALITY)
        self.assertIsNotNone(resolution.selected_knowledge_id)
        self.assertIn("higher quality", resolution.resolution_notes.lower())

    def test_resolve_duplicate_merge(self):
        """Test resolving duplicate by merging"""
        analysis = ConflictAnalysis(
            conflict_id="test_conflict",
            knowledge_a_id="dup_1",
            knowledge_b_id="dup_2",
            conflict_type=ConflictType.DUPLICATE,
            severity="medium",
            confidence=0.95,
            recommended_strategy=ResolutionStrategy.MERGE
        )
        
        resolution = self.resolver.resolve_conflict(analysis, ResolutionStrategy.MERGE)
        
        self.assertEqual(resolution.strategy, ResolutionStrategy.MERGE)
        self.assertIsNotNone(resolution.merged_knowledge)
        self.assertIn("merged", resolution.resolution_notes.lower())

    def test_resolve_duplicate_keep_both(self):
        """Test resolving duplicate by keeping both"""
        analysis = ConflictAnalysis(
            conflict_id="test_conflict",
            knowledge_a_id="dup_1",
            knowledge_b_id="dup_2",
            conflict_type=ConflictType.DUPLICATE,
            severity="low",
            confidence=0.98,
            recommended_strategy=ResolutionStrategy.KEEP_BOTH
        )
        
        resolution = self.resolver.resolve_conflict(analysis, ResolutionStrategy.KEEP_BOTH)
        
        self.assertEqual(resolution.strategy, ResolutionStrategy.KEEP_BOTH)
        self.assertIsNone(resolution.selected_knowledge_id)
        self.assertIn("kept both", resolution.resolution_notes.lower())

    def test_resolve_overlapping_merge(self):
        """Test resolving overlapping knowledge by merging"""
        analysis = ConflictAnalysis(
            conflict_id="test_conflict",
            knowledge_a_id="kw_003",
            knowledge_b_id="kw_004",
            conflict_type=ConflictType.OVERLAPPING,
            severity="medium",
            confidence=0.9,
            recommended_strategy=ResolutionStrategy.MERGE
        )
        
        resolution = self.resolver.resolve_conflict(analysis, ResolutionStrategy.MERGE)
        
        self.assertEqual(resolution.strategy, ResolutionStrategy.MERGE)
        self.assertIsNotNone(resolution.merged_knowledge)
        self.assertIn("merged", resolution.resolution_notes.lower())

    def test_jaccard_similarity_calculation(self):
        """Test Jaccard similarity calculation for duplicate detection"""
        # Create nearly identical knowledge
        kw1 = KnowledgeExchange(
            id="sim_1",
            knowledge_type="decision_outcome",
            knowledge_content=json.dumps({"decision": "use_cache", "reason": "improve performance"}),
            topics=json.dumps(["performance", "optimization"]),
            source_worker="think_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.8},
            created_at=datetime.now(timezone.utc)
        )
        
        kw2 = KnowledgeExchange(
            id="sim_2",
            knowledge_type="decision_outcome",
            knowledge_content=json.dumps({"decision": "use_cache", "reason": "improve performance"}),
            topics=json.dumps(["performance", "optimization"]),
            source_worker="learning_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.85},
            created_at=datetime.now(timezone.utc)
        )
        
        score = self.resolver._calculate_duplicate_score(kw1, kw2)
        
        self.assertGreater(score, 0.9)
        self.assertLessEqual(score, 1.0)

    def test_different_types_no_conflict(self):
        """Test that different knowledge types don't conflict"""
        kw1 = KnowledgeExchange(
            id="type_1",
            knowledge_type="decision_outcome",
            knowledge_content=json.dumps({"decision": "use_sql"}),
            topics=json.dumps(["database"]),
            source_worker="think_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.8},
            created_at=datetime.now(timezone.utc)
        )
        
        kw2 = KnowledgeExchange(
            id="type_2",
            knowledge_type="risk_pattern",
            knowledge_content=json.dumps({"risk_level": "medium"}),
            topics=json.dumps(["security"]),
            source_worker="learning_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.8},
            created_at=datetime.now(timezone.utc)
        )
        
        conflict = self.resolver.analyze_conflicts(kw1, kw2)
        
        # Different types should have low similarity
        self.assertLess(conflict.similarity_score, 0.5)
        self.assertLess(conflict.overlap_score, 0.5)

    def test_obvious_contradiction_detection(self):
        """Test detection of obvious contradictions"""
        kw1 = KnowledgeExchange(
            id="contra_1",
            knowledge_type="risk_pattern",
            knowledge_content="Always use microservices for scalability",
            topics=json.dumps(["architecture", "scalability"]),
            source_worker="think_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.8},
            created_at=datetime.now(timezone.utc)
        )
        
        kw2 = KnowledgeExchange(
            id="contra_2",
            knowledge_type="risk_pattern",
            knowledge_content="Never use microservices, they add unnecessary complexity",
            topics=json.dumps(["architecture", "complexity"]),
            source_worker="learning_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.85},
            created_at=datetime.now(timezone.utc)
        )
        
        contradiction_score = self.resolver._calculate_contradiction_score(kw1, kw2)
        
        self.assertGreater(contradiction_score, 0.5)

    def test_confidence_calculation(self):
        """Test confidence calculation based on scores"""
        confidence = self.resolver._calculate_confidence(
            duplicate_score=0.9,
            contradiction_score=0.0,
            overlap_score=0.0
        )
        
        self.assertGreater(confidence, 0.8)
        self.assertLessEqual(confidence, 1.0)

    def test_recommend_strategy_contradictory_high(self):
        """Test strategy recommendation for high contradiction"""
        kw1 = KnowledgeExchange(
            id="high_contra_1",
            knowledge_type="risk_pattern",
            knowledge_content="Always use X",
            topics=json.dumps(["best_practices"]),
            source_worker="think_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.9},
            created_at=datetime.now(timezone.utc)
        )
        
        kw2 = KnowledgeExchange(
            id="high_contra_2",
            knowledge_type="risk_pattern",
            knowledge_content="Never use X",
            topics=json.dumps(["best_practices"]),
            source_worker="learning_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.95},
            created_at=datetime.now(timezone.utc)
        )
        
        conflict = self.resolver.analyze_conflicts(kw1, kw2)
        
        # High contradiction should recommend select_higher_quality
        self.assertEqual(conflict.recommended_strategy, ResolutionStrategy.SELECT_HIGHER_QUALITY)

    def test_recommend_strategy_duplicate_high_similarity(self):
        """Test strategy recommendation for very similar duplicates"""
        kw1 = KnowledgeExchange(
            id="dup_high_1",
            knowledge_type="learned_pattern",
            knowledge_content=json.dumps({"pattern": "retry", "rate": 0.85}),
            topics=json.dumps(["reliability"]),
            source_worker="think_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.8},
            created_at=datetime.now(timezone.utc)
        )
        
        kw2 = KnowledgeExchange(
            id="dup_high_2",
            knowledge_type="learned_pattern",
            knowledge_content=json.dumps({"pattern": "retry", "rate": 0.85}),
            topics=json.dumps(["reliability"]),
            source_worker="learning_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.85},
            created_at=datetime.now(timezone.utc)
        )
        
        conflict = self.resolver.analyze_conflicts(kw1, kw2)
        
        # Very similar duplicates should recommend keep_both
        self.assertEqual(conflict.recommended_strategy, ResolutionStrategy.KEEP_BOTH)


class TestAutoConflictManager(unittest.TestCase):
    """Test auto conflict manager functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.manager = AutoConflictManager(auto_resolve=False, min_confidence=0.8)

    def test_manager_initialization(self):
        """Test manager initialization"""
        self.assertFalse(self.manager.auto_resolve)
        self.assertEqual(self.manager.min_confidence, 0.8)
        self.assertIsNotNone(self.manager.resolver)

    def test_health_status_calculation(self):
        """Test health status calculation"""
        summary_healthy = {
            "total_conflicts_resolved": 10,
            "average_confidence": 0.95
        }
        
        status = self.manager._calculate_health_status(summary_healthy)
        self.assertEqual(status, "healthy")
        
        summary_warning = {
            "total_conflicts_resolved": 10,
            "average_confidence": 0.75
        }
        
        status = self.manager._calculate_health_status(summary_warning)
        self.assertEqual(status, "warning")
        
        summary_degraded = {
            "total_conflicts_resolved": 10,
            "average_confidence": 0.4
        }
        
        status = self.manager._calculate_health_status(summary_degraded)
        self.assertEqual(status, "degraded")

    def test_conflict_dashboard(self):
        """Test getting conflict dashboard data"""
        dashboard = self.manager.get_conflict_dashboard()
        
        self.assertIn("auto_resolve", dashboard)
        self.assertIn("min_confidence", dashboard)
        self.assertIn("health_status", dashboard)
        self.assertEqual(dashboard["auto_resolve"], False)
        self.assertEqual(dashboard["min_confidence"], 0.8)


class TestConflictResolverIntegration(unittest.TestCase):
    """Integration tests for conflict resolution"""

    def setUp(self):
        """Set up test fixtures"""
        self.resolver = ConflictResolver()
        
        # Create knowledge items with realistic content
        self.knowledge_items = []
        
        for i in range(5):
            kw = KnowledgeExchange(
                id=f"int_kw_{i}",
                knowledge_type="learned_pattern",
                knowledge_content=json.dumps({
                    "pattern": f"pattern_{i}",
                    "success_rate": 0.8 + (i * 0.02),
                    "description": "This is a test pattern with some detailed information"
                }),
                topics=json.dumps(["test", f"pattern_{i}"]),
                source_worker=f"worker_{i % 3}",
                target_worker="analysis_worker",
                urgency="normal",
                metadata={"confidence": 0.8 + (i * 0.03)},
                created_at=datetime.now(timezone.utc)
            )
            self.knowledge_items.append(kw)

    def test_multiple_conflict_detection(self):
        """Test detecting conflicts between multiple knowledge items"""
        conflicts = []
        
        # Check pairs of knowledge items
        for i in range(len(self.knowledge_items)):
            for j in range(i + 1, len(self.knowledge_items)):
                conflict = self.resolver.analyze_conflicts(
                    self.knowledge_items[i],
                    self.knowledge_items[j]
                )
                conflicts.append(conflict)
        
        # Should detect some conflicts
        self.assertGreater(len(conflicts), 0)
        
        # Check that conflicts have reasonable confidence
        for conflict in conflicts:
            self.assertLessEqual(conflict.confidence, 1.0)
            self.assertIsNotNone(conflict.summary)

    def test_conflict_severity_levels(self):
        """Test that conflicts have appropriate severity levels"""
        # Create high severity conflict (contradictory)
        kw1 = KnowledgeExchange(
            id="sev_high_1",
            knowledge_type="decision_outcome",
            knowledge_content=json.dumps({"decision": "use_sql", "reason": "better for complex queries"}),
            topics=json.dumps(["database"]),
            source_worker="think_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.9},
            created_at=datetime.now(timezone.utc)
        )
        
        kw2 = KnowledgeExchange(
            id="sev_high_2",
            knowledge_type="decision_outcome",
            knowledge_content=json.dumps({"decision": "use_nosql", "reason": "better for scalability"}),
            topics=json.dumps(["database"]),
            source_worker="learning_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.9},
            created_at=datetime.now(timezone.utc)
        )
        
        conflict = self.resolver.analyze_conflicts(kw1, kw2)
        self.assertEqual(conflict.severity, "high")
        
        # Create medium severity conflict (duplicate)
        kw3 = KnowledgeExchange(
            id="sev_med_1",
            knowledge_type="learned_pattern",
            knowledge_content=json.dumps({"pattern": "caching", "rate": 0.8}),
            topics=json.dumps(["performance"]),
            source_worker="think_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.8},
            created_at=datetime.now(timezone.utc)
        )
        
        kw4 = KnowledgeExchange(
            id="sev_med_2",
            knowledge_type="learned_pattern",
            knowledge_content=json.dumps({"pattern": "caching", "rate": 0.82}),
            topics=json.dumps(["performance"]),
            source_worker="learning_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.85},
            created_at=datetime.now(timezone.utc)
        )
        
        conflict = self.resolver.analyze_conflicts(kw3, kw4)
        self.assertEqual(conflict.severity, "medium")


class TestConflictResolutionStrategies(unittest.TestCase):
    """Test different resolution strategies"""

    def setUp(self):
        """Set up test fixtures"""
        self.resolver = ConflictResolver()

    def test_merge_strategy_output(self):
        """Test that merge strategy produces valid output"""
        kw1 = KnowledgeExchange(
            id="merge_1",
            knowledge_type="learned_pattern",
            knowledge_content=json.dumps({"pattern": "retry", "description": "retry mechanism"}),
            topics=json.dumps(["reliability"]),
            source_worker="think_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.8},
            created_at=datetime.now(timezone.utc)
        )
        
        kw2 = KnowledgeExchange(
            id="merge_2",
            knowledge_type="learned_pattern",
            knowledge_content=json.dumps({"pattern": "retry", "description": "exponential backoff"}),
            topics=json.dumps(["reliability", "backoff"]),
            source_worker="learning_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.85},
            created_at=datetime.now(timezone.utc)
        )
        
        analysis = ConflictAnalysis(
            conflict_id="merge_test",
            knowledge_a_id="merge_1",
            knowledge_b_id="merge_2",
            conflict_type=ConflictType.OVERLAPPING,
            severity="medium",
            confidence=0.9,
            recommended_strategy=ResolutionStrategy.MERGE
        )
        
        resolution = self.resolver.resolve_conflict(analysis, ResolutionStrategy.MERGE)
        
        self.assertIsNotNone(resolution.merged_knowledge)
        self.assertIn("knowledge_content", resolution.merged_knowledge)
        self.assertIn("topics", resolution.merged_knowledge)
        self.assertIn("metadata", resolution.merged_knowledge)

    def test_select_newer_strategy(self):
        """Test selecting newer knowledge"""
        kw_older = KnowledgeExchange(
            id="old",
            knowledge_type="decision_outcome",
            knowledge_content=json.dumps({"decision": "old_decision"}),
            topics=json.dumps(["test"]),
            source_worker="think_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.8},
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc)
        )
        
        kw_newer = KnowledgeExchange(
            id="new",
            knowledge_type="decision_outcome",
            knowledge_content=json.dumps({"decision": "new_decision"}),
            topics=json.dumps(["test"]),
            source_worker="learning_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.8},
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        
        analysis = ConflictAnalysis(
            conflict_id="newer_test",
            knowledge_a_id="old",
            knowledge_b_id="new",
            conflict_type=ConflictType.DUPLICATE,
            severity="medium",
            confidence=0.9,
            recommended_strategy=ResolutionStrategy.SELECT_NEWER
        )
        
        resolution = self.resolver.resolve_conflict(analysis, ResolutionStrategy.SELECT_NEWER)
        
        self.assertEqual(resolution.selected_knowledge_id, "new")
        self.assertIn("newer", resolution.resolution_notes.lower())

    def test_select_higher_quality_strategy(self):
        """Test selecting higher quality knowledge"""
        kw_lower = KnowledgeExchange(
            id="lower",
            knowledge_type="decision_outcome",
            knowledge_content=json.dumps({"decision": "decision_a"}),
            topics=json.dumps(["test"]),
            source_worker="think_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.7},
            created_at=datetime.now(timezone.utc)
        )
        
        kw_higher = KnowledgeExchange(
            id="higher",
            knowledge_type="decision_outcome",
            knowledge_content=json.dumps({"decision": "decision_b"}),
            topics=json.dumps(["test"]),
            source_worker="learning_worker",
            target_worker="analysis_worker",
            urgency="normal",
            metadata={"confidence": 0.9},
            created_at=datetime.now(timezone.utc)
        )
        
        analysis = ConflictAnalysis(
            conflict_id="quality_test",
            knowledge_a_id="lower",
            knowledge_b_id="higher",
            conflict_type=ConflictType.CONTRADICTORY,
            severity="high",
            confidence=0.95,
            recommended_strategy=ResolutionStrategy.SELECT_HIGHER_QUALITY
        )
        
        resolution = self.resolver.resolve_conflict(analysis, ResolutionStrategy.SELECT_HIGHER_QUALITY)
        
        self.assertEqual(resolution.selected_knowledge_id, "higher")
        self.assertIn("higher quality", resolution.resolution_notes.lower())


if __name__ == "__main__":
    unittest.main()
