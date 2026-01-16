"""
Utils package exports

Note: To avoid circular imports, individual modules should be imported directly:
- from app.utils.docker_executor import DockerExecutor
- from app.utils.git_operations import GitOperations
- from app.utils.cross_project import CrossProjectLearningSystem
"""

# Do not import modules here to avoid circular dependencies
__all__ = [
    'DockerExecutor',
    'ExecutionResult',
    'TestResult',
    'BuildResult',
    'GitOperations',
    'BranchResult',
    'CommitResult',
    'PushResult',
    'PullRequestResult',
    'is_git_operations_available',
    'is_github_operations_available',
    'CrossProjectLearningSystem',
    'PatternMatch',
    'ProjectSimilarity',
    'get_cross_project_system',
]
