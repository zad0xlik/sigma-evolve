"""
Git Integration Utility for SIGMA Phase 2

Analyzes git repositories to extract:
- Project metadata
- Commit history and patterns
- Dependencies from package files
- File structure and languages
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

try:
    from git import Repo, InvalidGitRepositoryError
    from git.exc import GitCommandError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

logger = logging.getLogger(__name__)


class GitProjectAnalyzer:
    """Analyzes git repositories for SIGMA knowledge graph ingestion."""
    
    DEPENDENCY_FILES = {
        "package.json": "javascript",
        "pyproject.toml": "python",
        "requirements.txt": "python",
        "Gemfile": "ruby",
        "go.mod": "go",
        "Cargo.toml": "rust",
        "pom.xml": "java",
        "build.gradle": "java",
        "composer.json": "php",
    }
    
    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".rb": "ruby",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".php": "php",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
    }
    
    def __init__(self, repo_path: str):
        """Initialize analyzer for a git repository.
        
        Args:
            repo_path: Path to the git repository
            
        Raises:
            ValueError: If git is not available or repo is invalid
        """
        if not GIT_AVAILABLE:
            raise ValueError("GitPython is not installed. Install with: uv sync")
        
        self.repo_path = Path(repo_path).resolve()
        
        try:
            self.repo = Repo(self.repo_path)
        except InvalidGitRepositoryError:
            raise ValueError(f"Not a valid git repository: {repo_path}")
        
        if self.repo.bare:
            raise ValueError(f"Cannot analyze bare repository: {repo_path}")
    
    def get_repository_info(self) -> Dict[str, Any]:
        """Get basic repository metadata.
        
        Returns:
            Dict with repository information including name, branches, remotes, etc.
        """
        info = {
            "name": self.repo_path.name,
            "path": str(self.repo_path),
            "active_branch": self.repo.active_branch.name if not self.repo.head.is_detached else None,
            "branches": [branch.name for branch in self.repo.branches],
            "remotes": {},
            "is_dirty": self.repo.is_dirty(),
            "untracked_files": self.repo.untracked_files,
        }
        
        # Add remote URLs
        for remote in self.repo.remotes:
            info["remotes"][remote.name] = list(remote.urls)
        
        return info
    
    def get_recent_commits(self, branch: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent commits from repository.
        
        Args:
            branch: Branch name (defaults to active branch)
            limit: Maximum number of commits to retrieve
            
        Returns:
            List of commit information dicts
        """
        commits = []
        
        try:
            # Use specified branch or active branch
            if branch:
                commit_iter = self.repo.iter_commits(branch, max_count=limit)
            else:
                commit_iter = self.repo.iter_commits(max_count=limit)
            
            for commit in commit_iter:
                commit_info = {
                    "hash": commit.hexsha,
                    "short_hash": commit.hexsha[:7],
                    "message": commit.message.strip(),
                    "author": {
                        "name": commit.author.name,
                        "email": commit.author.email,
                    },
                    "timestamp": datetime.fromtimestamp(commit.committed_date).isoformat(),
                    "files_changed": len(commit.stats.files),
                    "insertions": commit.stats.total["insertions"],
                    "deletions": commit.stats.total["deletions"],
                }
                commits.append(commit_info)
                
        except GitCommandError as e:
            logger.error(f"Error retrieving commits: {e}")
        
        return commits
    
    def analyze_commit_patterns(self, commits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in commit messages.
        
        Args:
            commits: List of commit dicts from get_recent_commits()
            
        Returns:
            Dict with pattern analysis
        """
        patterns = {
            "total_commits": len(commits),
            "commit_types": {},
            "decision_keywords": [],
            "authors": set(),
        }
        
        # Common commit type prefixes
        type_keywords = {
            "feature": ["feat", "feature", "add"],
            "fix": ["fix", "bugfix", "patch"],
            "refactor": ["refactor", "refact", "cleanup"],
            "docs": ["docs", "doc", "documentation"],
            "test": ["test", "tests"],
            "chore": ["chore", "deps", "dependency"],
            "style": ["style", "format"],
        }
        
        # Decision keywords
        decision_keywords = [
            "decided", "chose", "migrated", "switched", "adopted",
            "replaced", "upgraded", "deprecated", "removed", "added"
        ]
        
        for commit in commits:
            message = commit["message"].lower()
            patterns["authors"].add(commit["author"]["name"])
            
            # Detect commit type
            detected_type = "other"
            for type_name, keywords in type_keywords.items():
                if any(keyword in message for keyword in keywords):
                    detected_type = type_name
                    break
            
            patterns["commit_types"][detected_type] = patterns["commit_types"].get(detected_type, 0) + 1
            
            # Detect decision keywords
            for keyword in decision_keywords:
                if keyword in message:
                    patterns["decision_keywords"].append({
                        "keyword": keyword,
                        "commit": commit["short_hash"],
                        "message": commit["message"][:100],  # First 100 chars
                    })
        
        patterns["authors"] = list(patterns["authors"])
        return patterns
    
    def extract_file_structure(self, max_depth: int = 3) -> Dict[str, Any]:
        """Extract project file structure with language detection.
        
        Args:
            max_depth: Maximum directory depth to analyze
            
        Returns:
            Dict with file structure and language statistics
        """
        structure = {
            "total_files": 0,
            "languages": {},
            "directories": set(),
            "files": [],
        }
        
        # Walk through repository
        for root, dirs, files in os.walk(self.repo_path):
            # Skip .git directory
            if ".git" in root:
                continue
            
            # Calculate depth
            rel_path = Path(root).relative_to(self.repo_path)
            depth = len(rel_path.parts) if rel_path.parts != (".",) else 0
            
            if depth > max_depth:
                continue
            
            structure["directories"].add(str(rel_path))
            
            for file in files:
                file_path = Path(root) / file
                rel_file_path = file_path.relative_to(self.repo_path)
                
                # Detect language by extension
                ext = file_path.suffix.lower()
                language = self.LANGUAGE_EXTENSIONS.get(ext, "other")
                
                structure["languages"][language] = structure["languages"].get(language, 0) + 1
                structure["total_files"] += 1
                
                # Store file info (limit to prevent large payloads)
                if structure["total_files"] <= 500:
                    structure["files"].append({
                        "path": str(rel_file_path),
                        "language": language,
                        "size": file_path.stat().st_size if file_path.exists() else 0,
                    })
        
        structure["directories"] = sorted(list(structure["directories"]))
        return structure
    
    def detect_dependencies(self) -> Dict[str, List[Dict[str, str]]]:
        """Detect project dependencies from various package files.
        
        Returns:
            Dict mapping ecosystem to list of dependency dicts
        """
        dependencies = {}
        
        for dep_file, ecosystem in self.DEPENDENCY_FILES.items():
            file_path = self.repo_path / dep_file
            
            if not file_path.exists():
                continue
            
            try:
                if dep_file == "package.json":
                    deps = self._parse_package_json(file_path)
                elif dep_file == "pyproject.toml":
                    deps = self._parse_pyproject_toml(file_path)
                elif dep_file == "requirements.txt":
                    deps = self._parse_requirements_txt(file_path)
                elif dep_file == "Gemfile":
                    deps = self._parse_gemfile(file_path)
                else:
                    deps = []
                
                if deps:
                    dependencies[ecosystem] = dependencies.get(ecosystem, []) + deps
                    
            except Exception as e:
                logger.error(f"Error parsing {dep_file}: {e}")
        
        return dependencies
    
    def _parse_package_json(self, file_path: Path) -> List[Dict[str, str]]:
        """Parse Node.js package.json file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        deps = []
        for dep_type in ["dependencies", "devDependencies"]:
            if dep_type in data:
                for name, version in data[dep_type].items():
                    deps.append({
                        "name": name,
                        "version": version,
                        "type": "dev" if dep_type == "devDependencies" else "runtime"
                    })
        return deps
    
    def _parse_pyproject_toml(self, file_path: Path) -> List[Dict[str, str]]:
        """Parse Python pyproject.toml file (basic parsing)."""
        deps = []
        
        try:
            import tomli
        except ImportError:
            # Fallback to simple text parsing
            with open(file_path, 'r') as f:
                content = f.read()
                
            in_deps = False
            for line in content.split('\n'):
                line = line.strip()
                
                if line.startswith('[project') and 'dependencies' in line:
                    in_deps = True
                    continue
                elif line.startswith('['):
                    in_deps = False
                
                if in_deps and '"' in line:
                    # Extract package name (rough approximation)
                    if '"' in line:
                        pkg = line.split('"')[1]
                        name = pkg.split('>=')[0].split('==')[0].split('<')[0].strip()
                        version = pkg.split(name)[1] if len(pkg) > len(name) else "unknown"
                        deps.append({
                            "name": name,
                            "version": version.strip(),
                            "type": "runtime"
                        })
        
        return deps
    
    def _parse_requirements_txt(self, file_path: Path) -> List[Dict[str, str]]:
        """Parse Python requirements.txt file."""
        deps = []
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Skip -e editable installs
                if line.startswith('-e'):
                    continue
                
                # Parse package==version or package>=version
                if '==' in line:
                    name, version = line.split('==', 1)
                elif '>=' in line:
                    name, version = line.split('>=', 1)
                else:
                    name = line
                    version = "unknown"
                
                deps.append({
                    "name": name.strip(),
                    "version": version.strip(),
                    "type": "runtime"
                })
        
        return deps
    
    def _parse_gemfile(self, file_path: Path) -> List[Dict[str, str]]:
        """Parse Ruby Gemfile (basic parsing)."""
        deps = []
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Look for gem declarations
                if line.startswith('gem '):
                    parts = line.split()
                    if len(parts) >= 2:
                        name = parts[1].strip('\'"')
                        version = parts[2].strip('\'"') if len(parts) > 2 else "unknown"
                        deps.append({
                            "name": name,
                            "version": version,
                            "type": "runtime"
                        })
        
        return deps
    
    def analyze_full_project(self, branch: str = None, commit_limit: int = 50) -> Dict[str, Any]:
        """Perform complete project analysis.
        
        Args:
            branch: Branch to analyze (defaults to active branch)
            commit_limit: Maximum number of commits to analyze
            
        Returns:
            Complete analysis dict ready for knowledge graph ingestion
        """
        try:
            repo_info = self.get_repository_info()
            commits = self.get_recent_commits(branch=branch, limit=commit_limit)
            patterns = self.analyze_commit_patterns(commits)
            file_structure = self.extract_file_structure()
            dependencies = self.detect_dependencies()
            
            return {
                "repository": repo_info,
                "commits": {
                    "recent": commits[:10],  # Only include 10 most recent in output
                    "total_analyzed": len(commits),
                },
                "patterns": patterns,
                "file_structure": file_structure,
                "dependencies": dependencies,
                "analyzed_at": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error analyzing project: {e}", exc_info=True)
            raise


def is_git_integration_enabled() -> bool:
    """Check if git integration is enabled via environment variable."""
    enabled = os.getenv("GIT_INTEGRATION_ENABLED", "false").lower() == "true"
    
    if enabled and not GIT_AVAILABLE:
        logger.warning("GIT_INTEGRATION_ENABLED=true but GitPython is not installed")
        return False
    
    return enabled
