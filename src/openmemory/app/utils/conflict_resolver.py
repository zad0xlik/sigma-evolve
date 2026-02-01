"""
Conflict Resolution System for SIGMA Knowledge Exchange

Detects and resolves conflicts between knowledge items from different workers.
Supports three conflict types: duplicate, contradictory, and overlapping knowledge.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
import json
import difflib
from dataclasses import asdict

from app.database import get_db, get_worker_db, remove_worker_db
from app.models import KnowledgeExchange, WorkerKnowledgeState


class ConflictType(Enum):
    """Types of knowledge conflicts"""
    DUPLICATE = "duplicate"  # Same or highly similar knowledge
    CONTRADICTORY = "contradictory"  # Conflicting advice
    OVERLAPPING = "overlapping"  # Partially overlapping, needs merge


class ResolutionStrategy(Enum):
    """Strategies for resolving conflicts"""
    MERGE = "merge"  # Combine knowledge items
    SELECT_NEWER = "select_newer"  # Choose the most recent
    SELECT_HIGHER_QUALITY = "select_higher_quality"  # Choose based on confidence/quality
    KEEP_BOTH = "keep_both"  # Keep both, mark as related
    MARK_AS_RESOLVED = "mark_as_resolved"  # Mark as resolved without changes


@dataclass
class ConflictAnalysis:
    """Analysis result for a conflict"""
    conflict_id: str
    knowledge_a_id: str
    knowledge_b_id: str
    conflict_type: ConflictType
    similarity_score: Optional[float] = None
    contradiction_score: Optional[float] = None
    overlap_score: Optional[float] = None
    severity: str = "low"  # low, medium, high, critical
    summary: str = ""
    recommended_strategy: ResolutionStrategy = ResolutionStrategy.MERGE
    confidence: float = 0.0  # 0-1 confidence in analysis


@dataclass
class ResolutionResult:
    """Result of conflict resolution"""
    resolution_id: str
    conflict_id: str
    strategy: ResolutionStrategy
    selected_knowledge_id: Optional[str] = None
    merged_knowledge: Optional[Dict[str, Any]] = None
    resolved_at: datetime = field(default_factory=datetime.utcnow)
    resolution_notes: str = ""
    resolution_confidence: float = 0.0


class ConflictResolver:
    """
    Main conflict detection and resolution system
    
    Features:
    - Jaccard similarity for duplicate detection
    - Contradiction detection using LLM analysis
    - Overlapping knowledge identification
    - Multiple resolution strategies
    - Audit trail for all resolutions
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize conflict resolver
        
        Args:
            similarity_threshold: Threshold for duplicate detection (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.resolutions: Dict[str, ResolutionResult] = {}

    def analyze_conflicts(self, knowledge_a: KnowledgeExchange, knowledge_b: KnowledgeExchange) -> ConflictAnalysis:
        """
        Analyze potential conflicts between two knowledge items
        
        Args:
            knowledge_a: First knowledge item
            knowledge_b: Second knowledge item
            
        Returns:
            Conflict analysis result
        """
        conflict_id = f"conflict_{knowledge_a.id}_{knowledge_b.id}"
        
        # Detect duplicate (high similarity)
        duplicate_score = self._calculate_duplicate_score(knowledge_a, knowledge_b)
        
        # Detect contradiction (LLM analysis)
        contradiction_score = self._calculate_contradiction_score(knowledge_a, knowledge_b)
        
        # Detect overlap
        overlap_score = self._calculate_overlap_score(knowledge_a, knowledge_b)
        
        # Determine conflict type and severity
        conflict_type, severity, summary = self._determine_conflict_type(
            knowledge_a, knowledge_b, duplicate_score, contradiction_score, overlap_score
        )
        
        # Recommend resolution strategy
        recommended_strategy = self._recommend_strategy(
            conflict_type, knowledge_a, knowledge_b, duplicate_score, contradiction_score
        )
        
        return ConflictAnalysis(
            conflict_id=conflict_id,
            knowledge_a_id=knowledge_a.id,
            knowledge_b_id=knowledge_b.id,
            conflict_type=conflict_type,
            similarity_score=duplicate_score,
            contradiction_score=contradiction_score,
            overlap_score=overlap_score,
            severity=severity,
            summary=summary,
            recommended_strategy=recommended_strategy,
            confidence=self._calculate_confidence(duplicate_score, contradiction_score, overlap_score)
        )

    def resolve_conflict(self, analysis: ConflictAnalysis, strategy: Optional[ResolutionStrategy] = None) -> ResolutionResult:
        """
        Resolve a conflict using the specified strategy
        
        Args:
            analysis: Conflict analysis result
            strategy: Resolution strategy (default: use recommended)
            
        Returns:
            Resolution result
        """
        if strategy is None:
            strategy = analysis.recommended_strategy
        
        resolution_id = f"resolution_{analysis.conflict_id}_{datetime.utcnow().timestamp()}"
        
        # Get knowledge items
        session = get_worker_db()
        try:
            knowledge_a = session.query(KnowledgeExchange).filter_by(id=analysis.knowledge_a_id).first()
            knowledge_b = session.query(KnowledgeExchange).filter_by(id=analysis.knowledge_b_id).first()
            
            if not knowledge_a or not knowledge_b:
                raise ValueError("Knowledge items not found")
            
            # Apply resolution strategy
            if strategy == ResolutionStrategy.MERGE:
                result = self._resolve_merge(knowledge_a, knowledge_b, analysis)
            elif strategy == ResolutionStrategy.SELECT_NEWER:
                result = self._resolve_select_newer(knowledge_a, knowledge_b)
            elif strategy == ResolutionStrategy.SELECT_HIGHER_QUALITY:
                result = self._resolve_select_higher_quality(knowledge_a, knowledge_b)
            elif strategy == ResolutionStrategy.KEEP_BOTH:
                result = self._resolve_keep_both(knowledge_a, knowledge_b, analysis)
            elif strategy == ResolutionStrategy.MARK_AS_RESOLVED:
                result = self._resolve_mark_as_resolved(knowledge_a, knowledge_b, analysis)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")
            
            # Store resolution
            resolution = ResolutionResult(
                resolution_id=resolution_id,
                conflict_id=analysis.conflict_id,
                strategy=strategy,
                **result
            )
            
            self.resolutions[resolution_id] = resolution
            self._persist_resolution(knowledge_a, knowledge_b, resolution, session)
            
            return resolution
            
        finally:
            session.close()

    def _calculate_duplicate_score(self, a: KnowledgeExchange, b: KnowledgeExchange) -> float:
        """
        Calculate similarity score between two knowledge items
        
        Uses Jaccard similarity on tokenized content
        """
        if a.knowledge_type != b.knowledge_type:
            return 0.0
        
        # Extract relevant fields for comparison
        content_a = self._extract_comparison_text(a)
        content_b = self._extract_comparison_text(b)
        
        if not content_a or not content_b:
            return 0.0
        
        # Tokenize (split by words, remove punctuation)
        tokens_a = set(content_a.lower().split())
        tokens_b = set(content_b.lower().split())
        
        if not tokens_a or not tokens_b:
            return 0.0
        
        # Jaccard similarity
        intersection = len(tokens_a.intersection(tokens_b))
        union = len(tokens_a.union(tokens_b))
        
        return intersection / union if union > 0 else 0.0

    def _calculate_contradiction_score(self, a: KnowledgeExchange, b: KnowledgeExchange) -> float:
        """
        Calculate contradiction score using LLM analysis
        
        Returns 0-1 score (1 = definite contradiction)
        """
        # Check for obvious contradictions
        contradictions = self._check_obvious_contradictions(a, b)
        
        if contradictions:
            return 0.9  # High contradiction score
        
        # For complex contradictions, use LLM
        # For now, return moderate score for opposing advice
        if self._has_opposing_advice(a, b):
            return 0.6
        
        return 0.0

    def _check_obvious_contradictions(self, a: KnowledgeExchange, b: KnowledgeExchange) -> bool:
        """Check for obvious contradictions (e.g., opposite recommendations)"""
        # Example: "always use X" vs "never use X"
        a_content = a.knowledge_content.lower()
        b_content = b.knowledge_content.lower()
        
        # Check for negation patterns
        negation_pairs = [
            ("always", "never"),
            ("should", "should not"),
            ("must", "must not"),
            ("good", "bad"),
            ("recommended", "not recommended"),
            ("use", "avoid"),
            ("prefer", "avoid"),
        ]
        
        for pos, neg in negation_pairs:
            if pos in a_content and neg in b_content:
                return True
            if neg in a_content and pos in b_content:
                return True
        
        # Check for opposing decisions in knowledge content
        if a.knowledge_type == "decision_outcome" and b.knowledge_type == "decision_outcome":
            a_data = json.loads(a.knowledge_content) if isinstance(a.knowledge_content, str) else a.knowledge_content
            b_data = json.loads(b.knowledge_content) if isinstance(b.knowledge_content, str) else b.knowledge_content
            
            if isinstance(a_data, dict) and isinstance(b_data, dict):
                a_decision = a_data.get("decision")
                b_decision = b_data.get("decision")
                
                # Check for direct opposites
                if a_decision and b_decision:
                    # Check for opposite terms
                    opposites = [
                        ("microservices", "monolith"),
                        ("async", "sync"),
                        ("sqlite", "postgresql"),
                        ("orm", "raw_sql"),
                        ("caching", "no_caching"),
                        ("encryption", "no_encryption"),
                    ]
                    
                    for pair in opposites:
                        if (pair[0] in str(a_decision).lower() and pair[1] in str(b_decision).lower()) or \
                           (pair[1] in str(a_decision).lower() and pair[0] in str(b_decision).lower()):
                            return True
                    
                    # Check for different decisions on same topic
                    if a_decision != b_decision:
                        # If they're discussing the same concept but choosing different options
                        a_concept = a_data.get("pattern") or a_data.get("topic") or ""
                        b_concept = b_data.get("pattern") or b_data.get("topic") or ""
                        
                        if a_concept and b_concept and a_concept == b_concept:
                            return True
        
        return False

    def _has_opposing_advice(self, a: KnowledgeExchange, b: KnowledgeExchange) -> bool:
        """Check if knowledge items provide opposing advice"""
        # Check if both provide recommendations but with different parameters
        if a.knowledge_type == "decision_outcome" and b.knowledge_type == "decision_outcome":
            a_data = json.loads(a.knowledge_content) if isinstance(a.knowledge_content, str) else a.knowledge_content
            b_data = json.loads(b.knowledge_content) if isinstance(b.knowledge_content, str) else b.knowledge_content
            
            if isinstance(a_data, dict) and isinstance(b_data, dict):
                # Check if decisions differ
                a_decision = a_data.get("decision")
                b_decision = b_data.get("decision")
                
                if a_decision and b_decision and a_decision != b_decision:
                    # Check if they're discussing similar concepts
                    a_concept = a_data.get("topic") or a_data.get("pattern") or ""
                    b_concept = b_data.get("topic") or b_data.get("pattern") or ""
                    
                    # If they're discussing similar topics but choosing different options
                    if a_concept and b_concept and a_concept == b_concept:
                        return True
                    
                    # Check for opposite terms in decisions
                    opposites = [
                        ("microservices", "monolith"),
                        ("async", "sync"),
                        ("sqlite", "postgresql"),
                        ("orm", "raw_sql"),
                    ]
                    
                    for pair in opposites:
                        if (pair[0] in str(a_decision).lower() and pair[1] in str(b_decision).lower()) or \
                           (pair[1] in str(a_decision).lower() and pair[0] in str(b_decision).lower()):
                            return True
        
        # Also check risk patterns for opposing advice
        if a.knowledge_type == "risk_pattern" and b.knowledge_type == "risk_pattern":
            a_data = json.loads(a.knowledge_content) if isinstance(a.knowledge_content, str) else a.knowledge_content
            b_data = json.loads(b.knowledge_content) if isinstance(b.knowledge_content, str) else b.knowledge_content
            
            if isinstance(a_data, dict) and isinstance(b_data, dict):
                a_advice = a_data.get("advice") or a_data.get("mitigation") or ""
                b_advice = b_data.get("advice") or b_data.get("mitigation") or ""
                
                if a_advice and b_advice:
                    # Check for opposing advice
                    opposites = [
                        ("use", "avoid"),
                        ("should", "should not"),
                        ("always", "never"),
                    ]
                    
                    for pair in opposites:
                        if (pair[0] in a_advice.lower() and pair[1] in b_advice.lower()) or \
                           (pair[1] in a_advice.lower() and pair[0] in b_advice.lower()):
                            return True
        
        return False

    def _calculate_overlap_score(self, a: KnowledgeExchange, b: KnowledgeExchange) -> float:
        """
        Calculate overlap score between knowledge items
        
        Returns 0-1 score (1 = completely overlapping)
        """
        # Check if they share topics
        a_topics = set(json.loads(a.topics)) if isinstance(a.topics, str) else set(a.topics)
        b_topics = set(json.loads(b.topics)) if isinstance(b.topics, str) else set(b.topics)
        
        if not a_topics or not b_topics:
            return 0.0
        
        intersection = a_topics.intersection(b_topics)
        union = a_topics.union(b_topics)
        
        overlap = len(intersection) / len(union) if union else 0.0
        
        # Also check content overlap
        content_a = self._extract_comparison_text(a)
        content_b = self._extract_comparison_text(b)
        
        if content_a and content_b:
            # Calculate content overlap
            words_a = set(content_a.lower().split())
            words_b = set(content_b.lower().split())
            
            if words_a and words_b:
                word_overlap = len(words_a.intersection(words_b)) / len(words_a.union(words_b))
                overlap = (overlap + word_overlap) / 2
        
        return overlap

    def _determine_conflict_type(self, a: KnowledgeExchange, b: KnowledgeExchange, 
                                 duplicate_score: float, contradiction_score: float, 
                                 overlap_score: float) -> Tuple[ConflictType, str, str]:
        """
        Determine the primary conflict type and severity
        
        Returns:
            Tuple of (conflict_type, severity, summary)
        """
        # Priority: Contradictory > Duplicate > Overlapping
        
        if contradiction_score > 0.5:
            severity = "high" if contradiction_score > 0.7 else "medium"
            summary = f"Contradictory knowledge detected (score: {contradiction_score:.2f})"
            return ConflictType.CONTRADICTORY, severity, summary
        
        if duplicate_score > self.similarity_threshold:
            severity = "high" if duplicate_score > 0.95 else "medium"
            summary = f"Duplicate knowledge detected (similarity: {duplicate_score:.2f})"
            return ConflictType.DUPLICATE, severity, summary
        
        if overlap_score > 0.3:
            severity = "medium" if overlap_score > 0.5 else "low"
            summary = f"Overlapping knowledge detected (overlap: {overlap_score:.2f})"
            return ConflictType.OVERLAPPING, severity, summary
        
        return ConflictType.DUPLICATE, "low", "No significant conflict detected"

    def _recommend_strategy(self, conflict_type: ConflictType, a: KnowledgeExchange, 
                           b: KnowledgeExchange, duplicate_score: float, 
                           contradiction_score: float) -> ResolutionStrategy:
        """
        Recommend resolution strategy based on conflict type and context
        """
        if conflict_type == ConflictType.CONTRADICTORY:
            if contradiction_score > 0.8:
                # High contradiction: select newer with higher confidence
                return ResolutionStrategy.SELECT_HIGHER_QUALITY
            else:
                # Medium contradiction: merge with caution
                return ResolutionStrategy.MERGE
        
        if conflict_type == ConflictType.DUPLICATE:
            # Check if there's a quality difference
            confidence_a = a.metadata.get("confidence", 0.5) if isinstance(a.metadata, dict) else 0.5
            confidence_b = b.metadata.get("confidence", 0.5) if isinstance(b.metadata, dict) else 0.5
            confidence_diff = abs(confidence_a - confidence_b)
            
            # If confidence differs significantly (more than 0.1), select higher quality
            if confidence_diff > 0.1:
                return ResolutionStrategy.SELECT_HIGHER_QUALITY
            elif duplicate_score > 0.95:
                # Very similar with same quality: keep both for diversity
                return ResolutionStrategy.KEEP_BOTH
            else:
                # Similar but not identical: merge
                return ResolutionStrategy.MERGE
        
        if conflict_type == ConflictType.OVERLAPPING:
            # Overlapping: merge to combine knowledge
            return ResolutionStrategy.MERGE
        
        return ResolutionStrategy.MERGE

    def _calculate_confidence(self, duplicate_score: float, contradiction_score: float, 
                             overlap_score: float) -> float:
        """Calculate confidence in conflict analysis"""
        scores = [s for s in [duplicate_score, contradiction_score, overlap_score] if s > 0]
        
        if not scores:
            return 0.0
        
        # Confidence increases with clearer signals
        max_score = max(scores)
        return min(0.95, max_score * 0.9)

    def _extract_comparison_text(self, knowledge: KnowledgeExchange) -> str:
        """Extract text for comparison from knowledge item"""
        text_parts = []
        
        # Add content
        if knowledge.knowledge_content:
            text_parts.append(str(knowledge.knowledge_content))
        
        # Add summary if available
        if hasattr(knowledge, 'summary') and knowledge.summary:
            text_parts.append(knowledge.summary)
        
        # Add topics
        if knowledge.topics:
            text_parts.append(str(knowledge.topics))
        
        return " ".join(text_parts)

    def _resolve_merge(self, a: KnowledgeExchange, b: KnowledgeExchange, 
                      analysis: ConflictAnalysis) -> Dict[str, Any]:
        """Merge two knowledge items"""
        merged_content = self._merge_content(a, b, analysis)
        merged_topics = list(set(json.loads(a.topics) + json.loads(b.topics)))
        
        # Calculate average confidence
        confidence_a = a.metadata.get("confidence", 0.5) if isinstance(a.metadata, dict) else 0.5
        confidence_b = b.metadata.get("confidence", 0.5) if isinstance(b.metadata, dict) else 0.5
        merged_confidence = (confidence_a + confidence_b) / 2
        
        # Add merge metadata
        merged_metadata = {
            "confidence": merged_confidence,
            "merged_from": [a.id, b.id],
            "conflict_type": analysis.conflict_type.value,
            "merge_strategy": "smart_merge",
            "analysis_confidence": analysis.confidence
        }
        
        return {
            "selected_knowledge_id": None,
            "merged_knowledge": {
                "knowledge_content": merged_content,
                "topics": merged_topics,
                "metadata": merged_metadata
            },
            "resolution_notes": f"Merged knowledge items {a.id} and {b.id} using {analysis.conflict_type.value} resolution",
            "resolution_confidence": analysis.confidence
        }

    def _resolve_select_newer(self, a: KnowledgeExchange, b: KnowledgeExchange) -> Dict[str, Any]:
        """Select the newer knowledge item"""
        selected = a if a.created_at > b.created_at else b
        notes = f"Selected newer knowledge item {selected.id} (created: {selected.created_at})"
        
        return {
            "selected_knowledge_id": selected.id,
            "merged_knowledge": None,
            "resolution_notes": notes,
            "resolution_confidence": 0.9
        }

    def _resolve_select_higher_quality(self, a: KnowledgeExchange, b: KnowledgeExchange) -> Dict[str, Any]:
        """Select knowledge with higher quality/confidence"""
        confidence_a = a.metadata.get("confidence", 0.5) if isinstance(a.metadata, dict) else 0.5
        confidence_b = b.metadata.get("confidence", 0.5) if isinstance(b.metadata, dict) else 0.5
        
        selected = a if confidence_a >= confidence_b else b
        notes = f"Selected higher quality knowledge item {selected.id} (confidence: {max(confidence_a, confidence_b):.2f})"
        
        return {
            "selected_knowledge_id": selected.id,
            "merged_knowledge": None,
            "resolution_notes": notes,
            "resolution_confidence": max(confidence_a, confidence_b)
        }

    def _resolve_keep_both(self, a: KnowledgeExchange, b: KnowledgeExchange, 
                          analysis: ConflictAnalysis) -> Dict[str, Any]:
        """Keep both knowledge items, mark as related"""
        notes = f"Kept both knowledge items {a.id} and {b.id} as complementary (conflict: {analysis.conflict_type.value})"
        
        return {
            "selected_knowledge_id": None,
            "merged_knowledge": None,
            "resolution_notes": notes,
            "resolution_confidence": 1.0
        }

    def _resolve_mark_as_resolved(self, a: KnowledgeExchange, b: KnowledgeExchange, 
                                 analysis: ConflictAnalysis) -> Dict[str, Any]:
        """Mark as resolved without changes"""
        notes = f"Conflict between {a.id} and {b.id} marked as resolved"
        
        return {
            "selected_knowledge_id": None,
            "merged_knowledge": None,
            "resolution_notes": notes,
            "resolution_confidence": 0.5
        }

    def _merge_content(self, a: KnowledgeExchange, b: KnowledgeExchange, 
                      analysis: ConflictAnalysis) -> str:
        """Merge content from two knowledge items"""
        # For simple merges, combine with separator
        if analysis.conflict_type == ConflictType.DUPLICATE:
            # For duplicates, take the more detailed one
            a_len = len(a.knowledge_content) if a.knowledge_content else 0
            b_len = len(b.knowledge_content) if b.knowledge_content else 0
            
            if a_len >= b_len:
                return str(a.knowledge_content)
            else:
                return str(b.knowledge_content)
        
        # For overlapping, combine with context
        return f"{a.knowledge_content}\n\n{b.knowledge_content}"

    def _persist_resolution(self, a: KnowledgeExchange, b: KnowledgeExchange, 
                           resolution: ResolutionResult, session):
        """Persist resolution to database"""
        # Mark knowledge items as resolved
        a.is_resolved = True
        b.is_resolved = True
        
        # Store resolution metadata in knowledge
        a_resolution_metadata = {
            "conflict_resolution": {
                "resolution_id": resolution.resolution_id,
                "strategy": resolution.strategy.value,
                "resolved_at": resolution.resolved_at.isoformat(),
                "related_to": b.id
            }
        }
        
        b_resolution_metadata = {
            "conflict_resolution": {
                "resolution_id": resolution.resolution_id,
                "strategy": resolution.strategy.value,
                "resolved_at": resolution.resolved_at.isoformat(),
                "related_to": a.id
            }
        }
        
        # Update metadata
        if isinstance(a.metadata, dict):
            a.metadata.update(a_resolution_metadata)
        if isinstance(b.metadata, dict):
            b.metadata.update(b_resolution_metadata)
        
        session.commit()

    def get_conflict_summary(self) -> Dict[str, Any]:
        """Get summary of all conflicts and resolutions"""
        total_conflicts = len(self.resolutions)
        
        # Count by strategy
        strategy_counts = {}
        for resolution in self.resolutions.values():
            strategy = resolution.strategy.value
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        # Average confidence
        avg_confidence = sum(r.resolution_confidence for r in self.resolutions.values()) / total_conflicts if total_conflicts > 0 else 0.0
        
        return {
            "total_conflicts_resolved": total_conflicts,
            "by_strategy": strategy_counts,
            "average_confidence": round(avg_confidence, 3),
            "resolutions": list(self.resolutions.values())
        }

    def detect_conflicts_for_worker(self, worker_id: str, limit: int = 10) -> List[ConflictAnalysis]:
        """
        Detect conflicts for a specific worker
        
        Args:
            worker_id: Worker identifier
            limit: Maximum number of conflicts to return
            
        Returns:
            List of conflict analyses
        """
        session = get_worker_db()
        try:
            # Get knowledge from this worker
            worker_knowledge = session.query(KnowledgeExchange).filter_by(
                source_worker=worker_id
            ).order_by(KnowledgeExchange.created_at.desc()).limit(limit).all()
            
            conflicts = []
            
            # Compare with knowledge from other workers
            for kw_a in worker_knowledge:
                other_knowledge = session.query(KnowledgeExchange).filter(
                    KnowledgeExchange.source_worker != worker_id,
                    KnowledgeExchange.knowledge_type == kw_a.knowledge_type
                ).limit(5).all()
                
                for kw_b in other_knowledge:
                    conflict = self.analyze_conflicts(kw_a, kw_b)
                    if conflict.severity in ["medium", "high", "critical"]:
                        conflicts.append(conflict)
            
            # Sort by severity
            severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            conflicts.sort(key=lambda x: severity_order.get(x.severity, 0), reverse=True)
            
            return conflicts[:limit]
            
        finally:
            remove_worker_db()


class AutoConflictManager:
    """
    Automatic conflict detection and resolution manager
    
    Runs periodically to detect and auto-resolve conflicts
    """

    def __init__(self, auto_resolve: bool = False, min_confidence: float = 0.8):
        self.auto_resolve = auto_resolve
        self.min_confidence = min_confidence
        self.resolver = ConflictResolver()

    def run_cycle(self) -> Dict[str, Any]:
        """
        Run one cycle of conflict detection and resolution
        
        Returns:
            Summary of the cycle
        """
        session = get_worker_db()
        
        try:
            # Get recent unresolved knowledge
            recent_knowledge = session.query(KnowledgeExchange).filter_by(
                is_resolved=False
            ).order_by(KnowledgeExchange.created_at.desc()).limit(50).all()
            
            conflicts_detected = []
            resolutions_made = []
            
            # Check for conflicts
            for i, kw_a in enumerate(recent_knowledge):
                for kw_b in recent_knowledge[i+1:]:
                    # Skip same worker
                    if kw_a.source_worker == kw_b.source_worker:
                        continue
                    
                    # Analyze conflict
                    conflict = self.resolver.analyze_conflicts(kw_a, kw_b)
                    
                    if conflict.confidence >= self.min_confidence and conflict.severity != "low":
                        conflicts_detected.append(conflict)
                        
                        # Auto-resolve if enabled
                        if self.auto_resolve:
                            resolution = self.resolver.resolve_conflict(conflict)
                            resolutions_made.append(resolution)
            
            return {
                "cycle_timestamp": datetime.utcnow().isoformat(),
                "knowledge_checked": len(recent_knowledge),
                "conflicts_detected": len(conflicts_detected),
                "resolutions_made": len(resolutions_made),
                "auto_resolve_enabled": self.auto_resolve,
                "conflicts": [asdict(c) for c in conflicts_detected],
                "resolutions": [asdict(r) for r in resolutions_made]
            }
            
        finally:
            remove_worker_db()

    def get_conflict_dashboard(self) -> Dict[str, Any]:
        """Get dashboard data for conflict monitoring"""
        summary = self.resolver.get_conflict_summary()
        
        return {
            **summary,
            "auto_resolve": self.auto_resolve,
            "min_confidence": self.min_confidence,
            "health_status": self._calculate_health_status(summary)
        }

    def _calculate_health_status(self, summary: Dict[str, Any]) -> str:
        """Calculate system health status"""
        if summary["total_conflicts_resolved"] == 0:
            return "healthy"
        
        avg_confidence = summary.get("average_confidence", 0)
        
        if avg_confidence < 0.5:
            return "degraded"
        elif avg_confidence < 0.8:
            return "warning"
        else:
            return "healthy"
