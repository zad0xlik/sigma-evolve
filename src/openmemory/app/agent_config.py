"""
Agent System Configuration

Centralized configuration for the SIGMA agent system.
"""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class AutonomyConfig:
    """Autonomy level configuration"""
    level: int = 1  # 1, 2, or 3
    min_confidence_thresholds: Dict[int, float] = field(default_factory=lambda: {
        1: 0.70,  # High bar for proposals
        2: 0.80,  # Higher for auto-commits
        3: 0.90,  # Highest for auto-merge
    })
    auto_execute: bool = False
    auto_create_branches: bool = False
    auto_commit_to_branch: bool = False
    auto_create_pr: bool = False
    auto_merge_pr: bool = False
    
    @classmethod
    def from_env(cls) -> "AutonomyConfig":
        """Load from environment variables"""
        level = int(os.getenv("AUTONOMY_LEVEL", "1"))
        return cls(
            level=level,
            min_confidence_thresholds={
                1: float(os.getenv("LEVEL_1_MIN_CONFIDENCE", "0.70")),
                2: float(os.getenv("LEVEL_2_MIN_CONFIDENCE", "0.80")),
                3: float(os.getenv("LEVEL_3_MIN_CONFIDENCE", "0.90")),
            },
            auto_execute=os.getenv("AUTO_EXECUTE", "false").lower() == "true",
            auto_create_branches=os.getenv("AUTO_CREATE_BRANCHES", "false").lower() == "true",
            auto_commit_to_branch=os.getenv("AUTO_COMMIT_TO_BRANCH", "false").lower() == "true",
            auto_create_pr=os.getenv("AUTO_CREATE_PR", "false").lower() == "true",
            auto_merge_pr=os.getenv("AUTO_MERGE_PR", "false").lower() == "true",
        )
    
    def can_execute(self, confidence: float) -> tuple[bool, str]:
        """Check if proposal can be executed at current autonomy level"""
        min_confidence = self.min_confidence_thresholds.get(self.level, 0.70)
        
        if confidence < min_confidence:
            return False, f"Confidence {confidence:.2f} below threshold {min_confidence:.2f}"
        
        if self.level == 1:
            return False, "Level 1: Manual approval required"
        elif self.level == 2:
            return True, "Level 2: Will create branch and PR for review"
        elif self.level == 3:
            return True, "Level 3: Will create, commit, and merge PR"
        
        return False, "Invalid autonomy level"


@dataclass
class ProjectConfig:
    """Project configuration"""
    repo_url: str
    branch: str = "main"
    token: Optional[str] = None
    workspace_dir: str = "/tmp/sigma-workspace"
    
    @classmethod
    def from_env(cls) -> "ProjectConfig":
        """Load from environment variables"""
        return cls(
            repo_url=os.getenv("GITHUB_REPO_URL", ""),
            branch=os.getenv("GITHUB_BRANCH", "main"),
            token=os.getenv("GITHUB_TOKEN"),
            workspace_dir=os.getenv("WORKSPACE_DIR", "/tmp/sigma-workspace"),
        )


@dataclass
class WorkerConfig:
    """Worker interval configuration"""
    analysis_interval: int = 300    # 5 minutes
    dream_interval: int = 240       # 4 minutes
    recall_interval: int = 180      # 3 minutes
    learning_interval: int = 360    # 6 minutes
    think_interval: int = 480       # 8 minutes
    
    # Dreaming configuration
    dream_evolution_rate: float = 0.15  # 15% of cycles are experimental
    experiment_confidence_threshold: float = 0.60
    
    @classmethod
    def from_env(cls) -> "WorkerConfig":
        """Load from environment variables"""
        return cls(
            analysis_interval=int(os.getenv("ANALYSIS_INTERVAL", "300")),
            dream_interval=int(os.getenv("DREAM_INTERVAL", "240")),
            recall_interval=int(os.getenv("RECALL_INTERVAL", "180")),
            learning_interval=int(os.getenv("LEARNING_INTERVAL", "360")),
            think_interval=int(os.getenv("THINK_INTERVAL", "480")),
            dream_evolution_rate=float(os.getenv("DREAM_EVOLUTION_RATE", "0.15")),
            experiment_confidence_threshold=float(os.getenv("EXPERIMENT_CONFIDENCE_THRESHOLD", "0.60")),
        )


@dataclass
class ExecutionConfig:
    """Execution environment configuration"""
    docker_enabled: bool = True
    docker_registry: str = "docker.io"
    docker_image_prefix: str = "sigma-project"
    
    # Test execution
    auto_test: bool = True
    test_timeout: int = 300
    min_test_coverage: float = 0.70
    
    # Build validation
    auto_build: bool = True
    build_timeout: int = 600
    
    @classmethod
    def from_env(cls) -> "ExecutionConfig":
        """Load from environment variables"""
        return cls(
            docker_enabled=os.getenv("DOCKER_ENABLED", "true").lower() == "true",
            docker_registry=os.getenv("DOCKER_REGISTRY", "docker.io"),
            docker_image_prefix=os.getenv("DOCKER_IMAGE_PREFIX", "sigma-project"),
            auto_test=os.getenv("AUTO_TEST", "true").lower() == "true",
            test_timeout=int(os.getenv("TEST_TIMEOUT", "300")),
            min_test_coverage=float(os.getenv("MIN_TEST_COVERAGE", "0.70")),
            auto_build=os.getenv("AUTO_BUILD", "true").lower() == "true",
            build_timeout=int(os.getenv("BUILD_TIMEOUT", "600")),
        )


@dataclass
class CrossProjectConfig:
    """Cross-project learning configuration"""
    enabled: bool = True
    
    # Similarity thresholds
    similarity_threshold_language: float = 0.80
    similarity_threshold_framework: float = 0.90
    similarity_threshold_domain: float = 0.70
    
    # Pattern transfer
    min_pattern_confidence: float = 0.75
    min_pattern_success_count: int = 3
    
    @classmethod
    def from_env(cls) -> "CrossProjectConfig":
        """Load from environment variables"""
        return cls(
            enabled=os.getenv("CROSS_PROJECT_LEARNING", "true").lower() == "true",
            similarity_threshold_language=float(os.getenv("SIMILARITY_THRESHOLD_LANGUAGE", "0.80")),
            similarity_threshold_framework=float(os.getenv("SIMILARITY_THRESHOLD_FRAMEWORK", "0.90")),
            similarity_threshold_domain=float(os.getenv("SIMILARITY_THRESHOLD_DOMAIN", "0.70")),
            min_pattern_confidence=float(os.getenv("MIN_PATTERN_CONFIDENCE", "0.75")),
            min_pattern_success_count=int(os.getenv("MIN_PATTERN_SUCCESS_COUNT", "3")),
        )


@dataclass
class AgentCommitteeConfig:
    """Agent committee configuration"""
    agents: List[str] = field(default_factory=lambda: [
        "architect", "reviewer", "tester", "security", "optimizer"
    ])
    
    # Agent weights
    weights: Dict[str, float] = field(default_factory=lambda: {
        "architect": 1.0,
        "reviewer": 1.0,
        "tester": 0.9,
        "security": 1.1,
        "optimizer": 0.8,
    })
    
    # Proposal scoring
    star_threshold: float = 0.75
    min_explanation_length: int = 180
    
    @classmethod
    def from_env(cls) -> "AgentCommitteeConfig":
        """Load from environment variables"""
        agents_str = os.getenv("AGENT_COMMITTEE", "architect,reviewer,tester,security,optimizer")
        agents = [a.strip() for a in agents_str.split(",")]
        
        return cls(
            agents=agents,
            weights={
                "architect": float(os.getenv("ARCHITECT_WEIGHT", "1.0")),
                "reviewer": float(os.getenv("REVIEWER_WEIGHT", "1.0")),
                "tester": float(os.getenv("TESTER_WEIGHT", "0.9")),
                "security": float(os.getenv("SECURITY_WEIGHT", "1.1")),
                "optimizer": float(os.getenv("OPTIMIZER_WEIGHT", "0.8")),
            },
            star_threshold=float(os.getenv("PROPOSAL_STAR_THRESHOLD", "0.75")),
            min_explanation_length=int(os.getenv("PROPOSAL_MIN_EXPLANATION_LENGTH", "180")),
        )


@dataclass
class ExternalIntelligenceConfig:
    """External intelligence configuration"""
    context7_enabled: bool = True
    playwright_enabled: bool = True
    
    @classmethod
    def from_env(cls) -> "ExternalIntelligenceConfig":
        """Load from environment variables"""
        return cls(
            context7_enabled=os.getenv("CONTEXT7_ENABLED", "true").lower() == "true",
            playwright_enabled=os.getenv("PLAYWRIGHT_ENABLED", "true").lower() == "true",
        )


@dataclass
class AgentSystemConfig:
    """Complete agent system configuration"""
    autonomy: AutonomyConfig
    project: ProjectConfig
    workers: WorkerConfig
    execution: ExecutionConfig
    cross_project: CrossProjectConfig
    committee: AgentCommitteeConfig
    external_intel: ExternalIntelligenceConfig
    
    @classmethod
    def from_env(cls) -> "AgentSystemConfig":
        """Load all configuration from environment"""
        return cls(
            autonomy=AutonomyConfig.from_env(),
            project=ProjectConfig.from_env(),
            workers=WorkerConfig.from_env(),
            execution=ExecutionConfig.from_env(),
            cross_project=CrossProjectConfig.from_env(),
            committee=AgentCommitteeConfig.from_env(),
            external_intel=ExternalIntelligenceConfig.from_env(),
        )


# Global configuration instance
_config: Optional[AgentSystemConfig] = None


def get_agent_config() -> AgentSystemConfig:
    """Get the global agent system configuration"""
    global _config
    if _config is None:
        _config = AgentSystemConfig.from_env()
    return _config


def reload_agent_config():
    """Reload configuration from environment"""
    global _config
    _config = AgentSystemConfig.from_env()
    return _config
