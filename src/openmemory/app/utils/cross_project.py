"""
Cross-Project Learning System for SIGMA

This module enables pattern sharing and learning across multiple projects.
It extracts successful patterns from proposals, calculates project similarity,
and suggests relevant patterns from similar projects.

Key Features:
- Pattern extraction from successful proposals
- Multi-dimensional project similarity calculation
- Pattern recommendation engine
- Cross-project learning effectiveness tracking
- Automatic pattern evolution and refinement
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from ..models import (
    CodeSnapshot,
    CrossProjectLearning,
    LearnedPattern,
    Project,
    Proposal,
)

logger = logging.getLogger(__name__)


@dataclass
class PatternMatch:
    """A pattern matched for a target project"""
    pattern_id: int
    pattern_name: str
    pattern_type: str
    description: str
    code_template: str
    confidence: float
    similarity_score: float
    source_project_id: int
    success_rate: float
    usage_count: int


@dataclass
class ProjectSimilarity:
    """Similarity between two projects"""
    project_id: int
    repo_url: str
    language: str
    framework: Optional[str]
    domain: Optional[str]
    similarity_score: float
    language_match: bool
    framework_match: bool
    domain_match: bool


class CrossProjectLearningSystem:
    """
    Manages cross-project learning and pattern sharing
    
    This system enables SIGMA to learn from successful improvements
    in one project and apply those learnings to similar projects.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the cross-project learning system
        
        Args:
            db: Database session for queries and updates
        """
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def extract_pattern_from_proposal(
        self,
        proposal: Proposal,
        pattern_name: str,
        pattern_type: str,
        description: Optional[str] = None,
    ) -> Optional[LearnedPattern]:
        """
        Extract a learned pattern from a successful proposal
        
        Args:
            proposal: The successful proposal to extract pattern from
            pattern_name: Name for the pattern
            pattern_type: Type of pattern (e.g., 'refactoring', 'optimization', 'bug_fix')
            description: Optional description of the pattern
            
        Returns:
            LearnedPattern instance if extraction successful, None otherwise
        """
        try:
            # Get the project details
            project = self.db.query(Project).filter(
                Project.project_id == proposal.project_id
            ).first()
            
            if not project:
                self.logger.error(f"Project {proposal.project_id} not found")
                return None
            
            # Parse the changes JSON to create a code template
            changes = json.loads(proposal.changes_json) if proposal.changes_json else {}
            
            # Create a generalized code template from the changes
            code_template = self._generalize_changes(changes)
            
            # Check if pattern already exists
            existing = self.db.query(LearnedPattern).filter(
                and_(
                    LearnedPattern.pattern_name == pattern_name,
                    LearnedPattern.language == project.language,
                    LearnedPattern.pattern_type == pattern_type,
                )
            ).first()
            
            if existing:
                # Update existing pattern
                existing.confidence = min(1.0, existing.confidence + 0.1)
                existing.success_count += 1
                existing.last_used = datetime.now(timezone.utc)
                if description:
                    existing.description = description
                self.db.commit()
                self.logger.info(f"Updated existing pattern: {pattern_name}")
                return existing
            
            # Create new pattern
            pattern = LearnedPattern(
                pattern_name=pattern_name,
                pattern_type=pattern_type,
                description=description or f"Pattern extracted from proposal {proposal.proposal_id}",
                code_template=code_template,
                language=project.language,
                framework=project.framework,
                domain=project.domain,
                confidence=proposal.confidence or 0.5,
                success_count=1,
                failure_count=0,
                last_used=datetime.now(timezone.utc),
            )
            
            self.db.add(pattern)
            self.db.commit()
            
            self.logger.info(f"✅ Extracted new pattern: {pattern_name} from proposal {proposal.proposal_id}")
            return pattern
            
        except Exception as e:
            self.logger.error(f"Error extracting pattern: {e}")
            self.db.rollback()
            return None
    
    def calculate_project_similarity(
        self,
        project1_id: int,
        project2_id: int,
    ) -> float:
        """
        Calculate similarity score between two projects
        
        Similarity is calculated based on:
        - Language match (40% weight)
        - Framework match (30% weight)
        - Domain match (30% weight)
        
        Args:
            project1_id: First project ID
            project2_id: Second project ID
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            project1 = self.db.query(Project).filter(
                Project.project_id == project1_id
            ).first()
            project2 = self.db.query(Project).filter(
                Project.project_id == project2_id
            ).first()
            
            if not project1 or not project2:
                return 0.0
            
            similarity = 0.0
            
            # Language match (40% weight)
            if project1.language and project2.language:
                if project1.language.lower() == project2.language.lower():
                    similarity += 0.4
            
            # Framework match (30% weight)
            if project1.framework and project2.framework:
                if project1.framework.lower() == project2.framework.lower():
                    similarity += 0.3
                elif self._are_frameworks_similar(project1.framework, project2.framework):
                    similarity += 0.15  # Partial match for similar frameworks
            
            # Domain match (30% weight)
            if project1.domain and project2.domain:
                if project1.domain.lower() == project2.domain.lower():
                    similarity += 0.3
                elif self._are_domains_similar(project1.domain, project2.domain):
                    similarity += 0.15  # Partial match for similar domains
            
            return round(similarity, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def find_similar_projects(
        self,
        project_id: int,
        min_similarity: float = 0.5,
        limit: int = 10,
    ) -> List[ProjectSimilarity]:
        """
        Find projects similar to the given project
        
        Args:
            project_id: Target project ID
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
            limit: Maximum number of results
            
        Returns:
            List of ProjectSimilarity objects
        """
        try:
            target_project = self.db.query(Project).filter(
                Project.project_id == project_id
            ).first()
            
            if not target_project:
                return []
            
            # Get all other projects
            all_projects = self.db.query(Project).filter(
                Project.project_id != project_id
            ).all()
            
            similar_projects = []
            
            for project in all_projects:
                similarity = self.calculate_project_similarity(project_id, project.project_id)
                
                if similarity >= min_similarity:
                    similar_projects.append(ProjectSimilarity(
                        project_id=project.project_id,
                        repo_url=project.repo_url,
                        language=project.language,
                        framework=project.framework,
                        domain=project.domain,
                        similarity_score=similarity,
                        language_match=target_project.language == project.language,
                        framework_match=target_project.framework == project.framework,
                        domain_match=target_project.domain == project.domain,
                    ))
            
            # Sort by similarity score (highest first)
            similar_projects.sort(key=lambda x: x.similarity_score, reverse=True)
            
            return similar_projects[:limit]
            
        except Exception as e:
            self.logger.error(f"Error finding similar projects: {e}")
            return []
    
    def suggest_patterns_for_project(
        self,
        project_id: int,
        pattern_types: Optional[List[str]] = None,
        min_confidence: float = 0.5,
        limit: int = 20,
    ) -> List[PatternMatch]:
        """
        Suggest relevant patterns for a project based on similar projects
        
        Args:
            project_id: Target project ID
            pattern_types: Optional list of pattern types to filter by
            min_confidence: Minimum pattern confidence threshold
            limit: Maximum number of patterns to return
            
        Returns:
            List of PatternMatch objects with suggested patterns
        """
        try:
            target_project = self.db.query(Project).filter(
                Project.project_id == project_id
            ).first()
            
            if not target_project:
                return []
            
            # Build query for patterns matching project characteristics
            query = self.db.query(LearnedPattern).filter(
                LearnedPattern.confidence >= min_confidence
            )
            
            # Filter by language (required)
            if target_project.language:
                query = query.filter(LearnedPattern.language == target_project.language)
            
            # Filter by pattern type if specified
            if pattern_types:
                query = query.filter(LearnedPattern.pattern_type.in_(pattern_types))
            
            # Order by confidence and success rate
            patterns = query.order_by(
                desc(LearnedPattern.confidence),
                desc(LearnedPattern.success_count)
            ).limit(limit * 2).all()  # Get more to filter by similarity
            
            pattern_matches = []
            
            for pattern in patterns:
                # Calculate similarity score based on framework and domain match
                similarity = 0.0
                
                # Language is already filtered, so base similarity is 0.4
                similarity = 0.4
                
                # Framework match (30%)
                if pattern.framework and target_project.framework:
                    if pattern.framework.lower() == target_project.framework.lower():
                        similarity += 0.3
                    elif self._are_frameworks_similar(pattern.framework, target_project.framework):
                        similarity += 0.15
                
                # Domain match (30%)
                if pattern.domain and target_project.domain:
                    if pattern.domain.lower() == target_project.domain.lower():
                        similarity += 0.3
                    elif self._are_domains_similar(pattern.domain, target_project.domain):
                        similarity += 0.15
                
                # Calculate success rate
                total_uses = pattern.success_count + pattern.failure_count
                success_rate = pattern.success_count / total_uses if total_uses > 0 else 0.0
                
                # Find source projects that used this pattern successfully
                source_projects = self.db.query(CrossProjectLearning).filter(
                    and_(
                        CrossProjectLearning.pattern_id == pattern.pattern_id,
                        CrossProjectLearning.applied == True,
                    )
                ).all()
                
                source_project_id = source_projects[0].source_project_id if source_projects else None
                
                pattern_matches.append(PatternMatch(
                    pattern_id=pattern.pattern_id,
                    pattern_name=pattern.pattern_name,
                    pattern_type=pattern.pattern_type,
                    description=pattern.description,
                    code_template=pattern.code_template,
                    confidence=pattern.confidence,
                    similarity_score=round(similarity, 2),
                    source_project_id=source_project_id,
                    success_rate=success_rate,
                    usage_count=total_uses,
                ))
            
            # Sort by combined score (similarity * confidence * success_rate)
            pattern_matches.sort(
                key=lambda x: x.similarity_score * x.confidence * (x.success_rate or 0.5),
                reverse=True
            )
            
            return pattern_matches[:limit]
            
        except Exception as e:
            self.logger.error(f"Error suggesting patterns: {e}")
            return []
    
    def record_pattern_application(
        self,
        source_project_id: int,
        target_project_id: int,
        pattern_id: int,
        applied: bool = False,
    ) -> Optional[CrossProjectLearning]:
        """
        Record that a pattern was suggested or applied to a project
        
        Args:
            source_project_id: Project where pattern was learned
            target_project_id: Project where pattern is being applied
            pattern_id: The pattern being applied
            applied: Whether the pattern was actually applied (vs just suggested)
            
        Returns:
            CrossProjectLearning record
        """
        try:
            # Calculate similarity
            similarity = self.calculate_project_similarity(source_project_id, target_project_id)
            
            # Check if record already exists
            existing = self.db.query(CrossProjectLearning).filter(
                and_(
                    CrossProjectLearning.source_project_id == source_project_id,
                    CrossProjectLearning.target_project_id == target_project_id,
                    CrossProjectLearning.pattern_id == pattern_id,
                )
            ).first()
            
            if existing:
                if applied and not existing.applied:
                    existing.applied = True
                    existing.applied_at = datetime.now(timezone.utc)
                self.db.commit()
                return existing
            
            # Create new record
            learning = CrossProjectLearning(
                source_project_id=source_project_id,
                target_project_id=target_project_id,
                pattern_id=pattern_id,
                similarity_score=similarity,
                applied=applied,
                applied_at=datetime.now(timezone.utc) if applied else None,
            )
            
            self.db.add(learning)
            self.db.commit()
            
            self.logger.info(
                f"Recorded pattern {pattern_id} "
                f"{'application' if applied else 'suggestion'} "
                f"from project {source_project_id} to {target_project_id}"
            )
            
            return learning
            
        except Exception as e:
            self.logger.error(f"Error recording pattern application: {e}")
            self.db.rollback()
            return None
    
    def track_pattern_outcome(
        self,
        pattern_id: int,
        success: bool,
    ) -> bool:
        """
        Update pattern statistics based on application outcome
        
        Args:
            pattern_id: Pattern ID
            success: Whether the pattern application was successful
            
        Returns:
            True if update successful
        """
        try:
            pattern = self.db.query(LearnedPattern).filter(
                LearnedPattern.pattern_id == pattern_id
            ).first()
            
            if not pattern:
                return False
            
            if success:
                pattern.success_count += 1
                # Increase confidence for successful applications
                pattern.confidence = min(1.0, pattern.confidence + 0.05)
            else:
                pattern.failure_count += 1
                # Decrease confidence for failures
                pattern.confidence = max(0.0, pattern.confidence - 0.1)
            
            pattern.last_used = datetime.now(timezone.utc)
            
            self.db.commit()
            
            self.logger.info(
                f"Updated pattern {pattern_id}: "
                f"Success={success}, "
                f"Confidence={pattern.confidence:.2f}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error tracking pattern outcome: {e}")
            self.db.rollback()
            return False
    
    def get_cross_project_insights(
        self,
        project_id: int,
    ) -> Dict[str, Any]:
        """
        Get comprehensive cross-project learning insights for a project
        
        Args:
            project_id: Target project ID
            
        Returns:
            Dictionary with insights including:
            - Similar projects
            - Suggested patterns
            - Applied patterns and their outcomes
            - Learning statistics
        """
        try:
            project = self.db.query(Project).filter(
                Project.project_id == project_id
            ).first()
            
            if not project:
                return {}
            
            # Find similar projects
            similar_projects = self.find_similar_projects(project_id, min_similarity=0.5)
            
            # Get suggested patterns
            suggested_patterns = self.suggest_patterns_for_project(project_id)
            
            # Get applied patterns
            applied_learnings = self.db.query(CrossProjectLearning).filter(
                and_(
                    CrossProjectLearning.target_project_id == project_id,
                    CrossProjectLearning.applied == True,
                )
            ).all()
            
            # Get statistics
            total_suggestions = self.db.query(CrossProjectLearning).filter(
                CrossProjectLearning.target_project_id == project_id
            ).count()
            
            total_applied = len(applied_learnings)
            
            return {
                "project": {
                    "project_id": project.project_id,
                    "repo_url": project.repo_url,
                    "language": project.language,
                    "framework": project.framework,
                    "domain": project.domain,
                },
                "similar_projects": [
                    {
                        "project_id": sp.project_id,
                        "repo_url": sp.repo_url,
                        "similarity_score": sp.similarity_score,
                        "language_match": sp.language_match,
                        "framework_match": sp.framework_match,
                        "domain_match": sp.domain_match,
                    }
                    for sp in similar_projects
                ],
                "suggested_patterns": [
                    {
                        "pattern_id": pm.pattern_id,
                        "pattern_name": pm.pattern_name,
                        "pattern_type": pm.pattern_type,
                        "confidence": pm.confidence,
                        "similarity_score": pm.similarity_score,
                        "success_rate": pm.success_rate,
                    }
                    for pm in suggested_patterns
                ],
                "applied_patterns": [
                    {
                        "pattern_id": al.pattern_id,
                        "source_project_id": al.source_project_id,
                        "applied_at": al.applied_at.isoformat() if al.applied_at else None,
                    }
                    for al in applied_learnings
                ],
                "statistics": {
                    "total_suggestions": total_suggestions,
                    "total_applied": total_applied,
                    "application_rate": total_applied / total_suggestions if total_suggestions > 0 else 0.0,
                    "similar_projects_count": len(similar_projects),
                },
            }
            
        except Exception as e:
            self.logger.error(f"Error getting insights: {e}")
            return {}
    
    # Private helper methods
    
    def _generalize_changes(self, changes: Dict[str, Any]) -> str:
        """
        Create a generalized code template from specific changes
        
        Args:
            changes: Dictionary of file changes
            
        Returns:
            JSON string representing the generalized template
        """
        try:
            template = {
                "files_modified": len(changes.get("files", [])),
                "change_types": [],
                "patterns": [],
            }
            
            for file_path, file_changes in changes.get("files", {}).items():
                # Extract change type (add, modify, delete)
                if file_changes.get("action") == "add":
                    template["change_types"].append("file_addition")
                elif file_changes.get("action") == "delete":
                    template["change_types"].append("file_deletion")
                else:
                    template["change_types"].append("file_modification")
                
                # Extract patterns from the changes
                content = file_changes.get("content", "")
                if "class " in content:
                    template["patterns"].append("class_definition")
                if "def " in content or "function " in content:
                    template["patterns"].append("function_definition")
                if "import " in content or "require(" in content:
                    template["patterns"].append("dependency_addition")
            
            # Remove duplicates
            template["change_types"] = list(set(template["change_types"]))
            template["patterns"] = list(set(template["patterns"]))
            
            return json.dumps(template, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error generalizing changes: {e}")
            return json.dumps({"error": str(e)})
    
    def _are_frameworks_similar(self, framework1: str, framework2: str) -> bool:
        """Check if two frameworks are similar (e.g., React vs Vue, Django vs Flask)"""
        framework1 = framework1.lower()
        framework2 = framework2.lower()
        
        # Define framework families
        web_frameworks = [
            ["react", "vue", "angular", "svelte"],
            ["django", "flask", "fastapi"],
            ["express", "koa", "hapi"],
            ["spring", "springboot"],
        ]
        
        for family in web_frameworks:
            if framework1 in family and framework2 in family:
                return True
        
        return False
    
    def _are_domains_similar(self, domain1: str, domain2: str) -> bool:
        """Check if two domains are similar"""
        domain1 = domain1.lower()
        domain2 = domain2.lower()
        
        # Define domain families
        domain_families = [
            ["web", "webapp", "website", "frontend", "backend"],
            ["ml", "ai", "machine learning", "deep learning"],
            ["api", "rest", "graphql", "microservice"],
            ["data", "analytics", "etl"],
        ]
        
        for family in domain_families:
            if domain1 in family and domain2 in family:
                return True
        
        return False


def get_cross_project_system(db: Session) -> CrossProjectLearningSystem:
    """
    Factory function to create CrossProjectLearningSystem instance
    
    Args:
        db: Database session
        
    Returns:
        CrossProjectLearningSystem instance
    """
    return CrossProjectLearningSystem(db)
