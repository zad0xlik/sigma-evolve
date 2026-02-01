"""
Git/GitHub Operations Layer for SIGMA Phase 3

Handles active Git operations for autonomous code changes:
- Branch creation and management
- Committing changes from Docker containers
- Push operations to remote repositories
- Pull request creation and management
- Auto-merge capabilities
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

try:
    from git import Repo, GitCommandError, InvalidGitRepositoryError
    from git.exc import GitError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

try:
    from github import Github, GithubException
    from github.PullRequest import PullRequest
    from github.Repository import Repository
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class BranchResult:
    """Result of branch operations"""
    success: bool
    branch_name: str
    error: Optional[str] = None
    base_branch: Optional[str] = None
    commit_sha: Optional[str] = None


@dataclass
class CommitResult:
    """Result of commit operations"""
    success: bool
    commit_sha: str
    commit_message: str
    files_changed: int
    error: Optional[str] = None
    branch_name: Optional[str] = None


@dataclass
class PushResult:
    """Result of push operations"""
    success: bool
    branch_name: str
    remote_name: str
    error: Optional[str] = None
    commits_pushed: int = 0


@dataclass
class PullRequestResult:
    """Result of pull request operations"""
    success: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    error: Optional[str] = None
    branch_name: Optional[str] = None
    merged: bool = False


class GitOperations:
    """Manages Git and GitHub operations for SIGMA agent system."""
    
    def __init__(
        self,
        repo_path: str,
        github_token: Optional[str] = None,
        default_branch: str = "main",
    ):
        """Initialize Git operations manager.
        
        Args:
            repo_path: Path to local git repository
            github_token: GitHub personal access token for API operations
            default_branch: Default branch name (usually 'main' or 'master')
            
        Raises:
            ValueError: If dependencies not available or repo invalid
        """
        if not GIT_AVAILABLE:
            raise ValueError("GitPython not installed. Install with: pip install gitpython")
        
        self.repo_path = Path(repo_path).resolve()
        self.default_branch = default_branch
        self.github_token = github_token
        
        # Initialize Git repo
        try:
            self.repo = Repo(self.repo_path)
        except InvalidGitRepositoryError:
            raise ValueError(f"Not a valid git repository: {repo_path}")
        
        # Initialize GitHub API if token provided
        self.github_client = None
        self.github_repo = None
        if github_token and GITHUB_AVAILABLE:
            try:
                self.github_client = Github(github_token)
                self._init_github_repo()
            except Exception as e:
                logger.warning(f"Failed to initialize GitHub client: {e}")
        elif not GITHUB_AVAILABLE:
            logger.warning("PyGithub not installed. GitHub operations will be unavailable.")
    
    def _init_github_repo(self):
        """Initialize GitHub repository object from remote URL."""
        try:
            # Get origin remote URL
            if 'origin' not in self.repo.remotes:
                logger.warning("No 'origin' remote found")
                return
            
            origin_url = next(self.repo.remotes.origin.urls)
            
            # Parse GitHub repo from URL
            # Handles: https://github.com/user/repo.git or git@github.com:user/repo.git
            if 'github.com' in origin_url:
                if origin_url.startswith('https://'):
                    # https://github.com/user/repo.git
                    parts = origin_url.replace('https://github.com/', '').replace('.git', '').split('/')
                elif origin_url.startswith('git@'):
                    # git@github.com:user/repo.git
                    parts = origin_url.replace('git@github.com:', '').replace('.git', '').split('/')
                else:
                    logger.warning(f"Unrecognized GitHub URL format: {origin_url}")
                    return
                
                if len(parts) >= 2:
                    repo_full_name = f"{parts[0]}/{parts[1]}"
                    self.github_repo = self.github_client.get_repo(repo_full_name)
                    logger.info(f"Initialized GitHub repo: {repo_full_name}")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub repository: {e}")
    
    @staticmethod
    def clone_repository(
        workspace_root: str,
        repo_url: str,
        branch: str = "main",
        force: bool = False,
    ) -> Dict[str, Any]:
        """Clone a GitHub repository to the workspace.
        
        This is a static method for cloning repos before GitOperations is initialized.
        
        Args:
            workspace_root: Root directory where all projects will be cloned
            repo_url: GitHub repository URL
            branch: Branch to clone (default: main)
            force: If True, delete existing clone and re-clone
            
        Returns:
            {
                'success': bool,
                'workspace_path': str,
                'repo_name': str,
                'message': str,
                'commit_sha': str (optional),
                'already_existed': bool
            }
        """
        if not GIT_AVAILABLE:
            return {
                'success': False,
                'error': 'GitPython not installed',
                'message': 'GitPython not installed. Install with: pip install gitpython'
            }
        
        try:
            # Extract repo name from URL
            # https://github.com/zad0xlik/sigma-evolve.git → sigma-evolve
            repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
            
            # Ensure workspace root exists
            workspace_path_obj = Path(workspace_root)
            workspace_path_obj.mkdir(parents=True, exist_ok=True)
            
            # Target directory
            target_path = workspace_path_obj / repo_name
            
            # Check if already exists
            if target_path.exists():
                if force:
                    logger.info(f"Force flag set, removing existing: {target_path}")
                    import shutil
                    shutil.rmtree(target_path)
                else:
                    logger.info(f"Repository already cloned at: {target_path}")
                    
                    # Try to get commit SHA from existing repo
                    try:
                        existing_repo = Repo(str(target_path))
                        commit_sha = existing_repo.head.commit.hexsha[:8]
                    except:
                        commit_sha = None
                    
                    return {
                        'success': True,
                        'workspace_path': str(target_path),
                        'repo_name': repo_name,
                        'message': f'Repository already exists at {target_path}',
                        'already_existed': True,
                        'commit_sha': commit_sha,
                    }
            
            # Clone the repository
            logger.info(f"Cloning {repo_url} (branch: {branch}) to {target_path}")
            
            try:
                repo = Repo.clone_from(
                    url=repo_url,
                    to_path=str(target_path),
                    branch=branch,
                    depth=1  # Shallow clone for speed
                )
                commit_sha = repo.head.commit.hexsha[:8]
                
                logger.info(f"Successfully cloned {repo_name} (commit: {commit_sha})")
                
                return {
                    'success': True,
                    'workspace_path': str(target_path),
                    'repo_name': repo_name,
                    'message': f'Successfully cloned {repo_name}',
                    'commit_sha': commit_sha,
                    'already_existed': False,
                }
                
            except GitCommandError as e:
                # If branch doesn't exist, try 'master' as fallback
                if branch == 'main' and 'does not' in str(e).lower():
                    logger.warning(f"Branch 'main' not found, trying 'master'")
                    repo = Repo.clone_from(
                        url=repo_url,
                        to_path=str(target_path),
                        branch='master',
                        depth=1
                    )
                    commit_sha = repo.head.commit.hexsha[:8]
                    
                    return {
                        'success': True,
                        'workspace_path': str(target_path),
                        'repo_name': repo_name,
                        'message': f'Successfully cloned {repo_name} (used master branch)',
                        'commit_sha': commit_sha,
                        'already_existed': False,
                        'branch_used': 'master',
                    }
                else:
                    raise
            
        except GitCommandError as e:
            logger.error(f"Git clone failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to clone repository: {e}',
                'repo_name': repo_name if 'repo_name' in locals() else None,
            }
        except Exception as e:
            logger.error(f"Unexpected error during clone: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': f'Unexpected error: {e}',
                'repo_name': repo_name if 'repo_name' in locals() else None,
            }
    
    def create_feature_branch(
        self,
        branch_name: str,
        base_branch: Optional[str] = None,
    ) -> BranchResult:
        """Create a new feature branch.
        
        Args:
            branch_name: Name for the new branch
            base_branch: Branch to create from (defaults to default_branch)
            
        Returns:
            BranchResult with operation details
        """
        try:
            if base_branch is None:
                base_branch = self.default_branch
            
            # Ensure we're on the base branch and up to date
            logger.info(f"Creating branch '{branch_name}' from '{base_branch}'")
            
            # Check if branch already exists
            if branch_name in [b.name for b in self.repo.branches]:
                logger.warning(f"Branch '{branch_name}' already exists")
                return BranchResult(
                    success=False,
                    branch_name=branch_name,
                    error=f"Branch '{branch_name}' already exists",
                    base_branch=base_branch,
                )
            
            # Checkout base branch
            if self.repo.active_branch.name != base_branch:
                try:
                    self.repo.git.checkout(base_branch)
                except GitCommandError as e:
                    # Try to fetch if branch doesn't exist locally
                    logger.info(f"Fetching base branch '{base_branch}'")
                    self.repo.git.fetch('origin', base_branch)
                    self.repo.git.checkout(base_branch)
            
            # Pull latest changes
            try:
                self.repo.git.pull('origin', base_branch)
            except GitCommandError as e:
                logger.warning(f"Failed to pull latest changes: {e}")
            
            # Create and checkout new branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            
            commit_sha = self.repo.head.commit.hexsha
            
            logger.info(f"Created branch '{branch_name}' at commit {commit_sha[:7]}")
            
            return BranchResult(
                success=True,
                branch_name=branch_name,
                base_branch=base_branch,
                commit_sha=commit_sha,
            )
            
        except Exception as e:
            logger.error(f"Failed to create branch '{branch_name}': {e}")
            return BranchResult(
                success=False,
                branch_name=branch_name,
                error=str(e),
                base_branch=base_branch,
            )
    
    def apply_changes_from_docker(
        self,
        changes: Dict[str, Any],
        container_workspace: Path,
    ) -> Tuple[bool, List[str]]:
        """Apply changes from Docker container to local repository.
        
        Args:
            changes: Dict with file changes (from proposal)
            container_workspace: Path to container workspace with changes
            
        Returns:
            Tuple of (success, list of changed file paths)
        """
        changed_files = []
        
        try:
            # Changes format: {"file_path": "content"} or {"file_path": {"action": "create/modify/delete", "content": "..."}}
            for file_path, change_data in changes.items():
                target_path = self.repo_path / file_path
                
                # Handle different change formats
                if isinstance(change_data, str):
                    # Simple format: file_path -> content
                    action = "modify"
                    content = change_data
                elif isinstance(change_data, dict):
                    # Complex format: file_path -> {action, content}
                    action = change_data.get("action", "modify")
                    content = change_data.get("content", "")
                else:
                    logger.warning(f"Unsupported change format for {file_path}")
                    continue
                
                # Apply change based on action
                if action == "delete":
                    if target_path.exists():
                        target_path.unlink()
                        logger.info(f"Deleted: {file_path}")
                        changed_files.append(file_path)
                
                elif action in ["create", "modify"]:
                    # Create parent directories if needed
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write content
                    target_path.write_text(content)
                    logger.info(f"{action.capitalize()}d: {file_path}")
                    changed_files.append(file_path)
            
            return True, changed_files
            
        except Exception as e:
            logger.error(f"Failed to apply changes from Docker: {e}")
            return False, changed_files
    
    def commit_changes(
        self,
        message: str,
        files: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CommitResult:
        """Commit changes to current branch.
        
        Args:
            message: Commit message
            files: List of file paths to commit (None = all changes)
            metadata: Additional metadata to include in commit message
            
        Returns:
            CommitResult with operation details
        """
        try:
            branch_name = self.repo.active_branch.name
            
            # Add files
            if files:
                # Add specific files
                for file_path in files:
                    self.repo.index.add([file_path])
                    logger.debug(f"Staged: {file_path}")
            else:
                # Add all changes
                self.repo.git.add(A=True)
                logger.debug("Staged all changes")
            
            # Check if there are changes to commit
            if not self.repo.index.diff("HEAD"):
                logger.warning("No changes to commit")
                return CommitResult(
                    success=False,
                    commit_sha="",
                    commit_message=message,
                    files_changed=0,
                    error="No changes to commit",
                    branch_name=branch_name,
                )
            
            # Build commit message with metadata
            full_message = message
            if metadata:
                full_message += f"\n\n[SIGMA Metadata]\n"
                for key, value in metadata.items():
                    full_message += f"{key}: {value}\n"
            
            # Commit
            commit = self.repo.index.commit(full_message)
            files_changed = len(commit.stats.files)
            
            logger.info(f"Committed {files_changed} files: {commit.hexsha[:7]}")
            
            return CommitResult(
                success=True,
                commit_sha=commit.hexsha,
                commit_message=full_message,
                files_changed=files_changed,
                branch_name=branch_name,
            )
            
        except Exception as e:
            logger.error(f"Failed to commit changes: {e}")
            return CommitResult(
                success=False,
                commit_sha="",
                commit_message=message,
                files_changed=0,
                error=str(e),
                branch_name=self.repo.active_branch.name if not self.repo.head.is_detached else None,
            )
    
    def push_branch(
        self,
        branch_name: Optional[str] = None,
        remote_name: str = "origin",
        force: bool = False,
    ) -> PushResult:
        """Push branch to remote repository.
        
        Args:
            branch_name: Branch to push (None = current branch)
            remote_name: Remote name (default: 'origin')
            force: Force push (use with caution)
            
        Returns:
            PushResult with operation details
        """
        try:
            if branch_name is None:
                branch_name = self.repo.active_branch.name
            
            # Ensure remote exists
            if remote_name not in [r.name for r in self.repo.remotes]:
                return PushResult(
                    success=False,
                    branch_name=branch_name,
                    remote_name=remote_name,
                    error=f"Remote '{remote_name}' not found",
                )
            
            remote = self.repo.remote(remote_name)
            
            # Count commits ahead of remote
            try:
                commits_ahead = len(list(self.repo.iter_commits(f'{remote_name}/{branch_name}..{branch_name}')))
            except GitCommandError:
                # Branch doesn't exist on remote yet
                commits_ahead = len(list(self.repo.iter_commits(branch_name)))
            
            logger.info(f"Pushing branch '{branch_name}' to '{remote_name}' ({commits_ahead} commits)")
            
            # Push
            push_args = [branch_name]
            if force:
                push_args.append('--force')
            
            push_info = remote.push(push_args)
            
            # Check push result
            if push_info and push_info[0].flags & 1024:  # ERROR flag
                return PushResult(
                    success=False,
                    branch_name=branch_name,
                    remote_name=remote_name,
                    error=f"Push rejected: {push_info[0].summary}",
                )
            
            logger.info(f"Successfully pushed '{branch_name}' to '{remote_name}'")
            
            return PushResult(
                success=True,
                branch_name=branch_name,
                remote_name=remote_name,
                commits_pushed=commits_ahead,
            )
            
        except Exception as e:
            logger.error(f"Failed to push branch '{branch_name}': {e}")
            return PushResult(
                success=False,
                branch_name=branch_name or "unknown",
                remote_name=remote_name,
                error=str(e),
            )
    
    def create_pull_request(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: Optional[str] = None,
        labels: Optional[List[str]] = None,
        draft: bool = False,
    ) -> PullRequestResult:
        """Create a pull request on GitHub.
        
        Args:
            title: PR title
            body: PR description/body
            head_branch: Source branch (the feature branch)
            base_branch: Target branch (defaults to default_branch)
            labels: List of label names to apply
            draft: Create as draft PR
            
        Returns:
            PullRequestResult with operation details
        """
        if not self.github_repo:
            return PullRequestResult(
                success=False,
                error="GitHub repository not initialized. Check token and remote URL.",
                branch_name=head_branch,
            )
        
        try:
            if base_branch is None:
                base_branch = self.default_branch
            
            logger.info(f"Creating PR: '{title}' ({head_branch} -> {base_branch})")
            
            # Create PR
            pr = self.github_repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch,
                draft=draft,
            )
            
            # Add labels if provided
            if labels:
                try:
                    pr.add_to_labels(*labels)
                    logger.info(f"Added labels: {', '.join(labels)}")
                except Exception as e:
                    logger.warning(f"Failed to add labels: {e}")
            
            logger.info(f"Created PR #{pr.number}: {pr.html_url}")
            
            return PullRequestResult(
                success=True,
                pr_number=pr.number,
                pr_url=pr.html_url,
                branch_name=head_branch,
            )
            
        except GithubException as e:
            logger.error(f"GitHub API error creating PR: {e}")
            return PullRequestResult(
                success=False,
                error=f"GitHub API error: {e.data.get('message', str(e))}",
                branch_name=head_branch,
            )
        except Exception as e:
            logger.error(f"Failed to create PR: {e}")
            return PullRequestResult(
                success=False,
                error=str(e),
                branch_name=head_branch,
            )
    
    def merge_pull_request(
        self,
        pr_number: int,
        merge_method: str = "squash",
        commit_message: Optional[str] = None,
    ) -> PullRequestResult:
        """Merge a pull request on GitHub.
        
        Args:
            pr_number: PR number to merge
            merge_method: Merge method ('merge', 'squash', 'rebase')
            commit_message: Custom commit message for merge
            
        Returns:
            PullRequestResult with operation details
        """
        if not self.github_repo:
            return PullRequestResult(
                success=False,
                error="GitHub repository not initialized",
                pr_number=pr_number,
            )
        
        try:
            pr = self.github_repo.get_pull(pr_number)
            
            logger.info(f"Merging PR #{pr_number} using '{merge_method}' method")
            
            # Check if PR is mergeable
            if pr.mergeable is False:
                return PullRequestResult(
                    success=False,
                    pr_number=pr_number,
                    pr_url=pr.html_url,
                    error="PR has merge conflicts or is not mergeable",
                    branch_name=pr.head.ref,
                )
            
            # Merge PR
            merge_result = pr.merge(
                commit_message=commit_message,
                merge_method=merge_method,
            )
            
            if merge_result.merged:
                logger.info(f"Successfully merged PR #{pr_number}")
                return PullRequestResult(
                    success=True,
                    pr_number=pr_number,
                    pr_url=pr.html_url,
                    branch_name=pr.head.ref,
                    merged=True,
                )
            else:
                return PullRequestResult(
                    success=False,
                    pr_number=pr_number,
                    pr_url=pr.html_url,
                    error=f"Merge failed: {merge_result.message}",
                    branch_name=pr.head.ref,
                )
            
        except GithubException as e:
            logger.error(f"GitHub API error merging PR: {e}")
            return PullRequestResult(
                success=False,
                pr_number=pr_number,
                error=f"GitHub API error: {e.data.get('message', str(e))}",
            )
        except Exception as e:
            logger.error(f"Failed to merge PR: {e}")
            return PullRequestResult(
                success=False,
                pr_number=pr_number,
                error=str(e),
            )
    
    def get_pull_request_status(self, pr_number: int) -> Optional[Dict[str, Any]]:
        """Get status of a pull request.
        
        Args:
            pr_number: PR number
            
        Returns:
            Dict with PR status information or None if unavailable
        """
        if not self.github_repo:
            logger.warning("GitHub repository not initialized")
            return None
        
        try:
            pr = self.github_repo.get_pull(pr_number)
            
            return {
                "number": pr.number,
                "title": pr.title,
                "state": pr.state,
                "merged": pr.merged,
                "mergeable": pr.mergeable,
                "mergeable_state": pr.mergeable_state,
                "draft": pr.draft,
                "head_branch": pr.head.ref,
                "base_branch": pr.base.ref,
                "url": pr.html_url,
                "created_at": pr.created_at.isoformat(),
                "updated_at": pr.updated_at.isoformat(),
                "commits": pr.commits,
                "changed_files": pr.changed_files,
                "additions": pr.additions,
                "deletions": pr.deletions,
            }
            
        except Exception as e:
            logger.error(f"Failed to get PR status: {e}")
            return None
    
    def cleanup_branch(self, branch_name: str, remote: bool = True) -> bool:
        """Delete a branch locally and optionally on remote.
        
        Args:
            branch_name: Branch name to delete
            remote: Also delete from remote
            
        Returns:
            True if successful
        """
        try:
            # Ensure we're not on the branch we're deleting
            if self.repo.active_branch.name == branch_name:
                self.repo.git.checkout(self.default_branch)
            
            # Delete local branch
            if branch_name in [b.name for b in self.repo.branches]:
                self.repo.delete_head(branch_name, force=True)
                logger.info(f"Deleted local branch: {branch_name}")
            
            # Delete remote branch
            if remote:
                try:
                    self.repo.git.push('origin', '--delete', branch_name)
                    logger.info(f"Deleted remote branch: {branch_name}")
                except GitCommandError as e:
                    logger.warning(f"Failed to delete remote branch: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup branch '{branch_name}': {e}")
            return False
    
    def execute_full_workflow(
        self,
        proposal_id: str,
        changes: Dict[str, Any],
        container_workspace: Path,
        test_results: Dict[str, Any],
        build_results: Dict[str, Any],
        confidence: float,
        autonomy_level: int,
    ) -> Dict[str, Any]:
        """Execute complete Git workflow for a proposal.
        
        This is the main integration point for Think Worker.
        
        Args:
            proposal_id: Unique proposal identifier
            changes: File changes to apply
            container_workspace: Path to Docker container workspace
            test_results: Results from test execution
            build_results: Results from build validation
            confidence: Committee confidence score
            autonomy_level: Current autonomy level (1-3)
            
        Returns:
            Dict with workflow results
        """
        workflow_result = {
            "success": False,
            "branch_created": False,
            "committed": False,
            "pushed": False,
            "pr_created": False,
            "pr_merged": False,
            "error": None,
            "branch_name": None,
            "commit_sha": None,
            "pr_number": None,
            "pr_url": None,
        }
        
        try:
            # 1. Create feature branch
            branch_name = f"sigma/proposal-{proposal_id}"
            branch_result = self.create_feature_branch(branch_name)
            
            if not branch_result.success:
                workflow_result["error"] = f"Branch creation failed: {branch_result.error}"
                return workflow_result
            
            workflow_result["branch_created"] = True
            workflow_result["branch_name"] = branch_name
            logger.info(f"✓ Created branch: {branch_name}")
            
            # 2. Apply changes from Docker
            success, changed_files = self.apply_changes_from_docker(changes, container_workspace)
            
            if not success or not changed_files:
                workflow_result["error"] = "Failed to apply changes from Docker"
                return workflow_result
            
            logger.info(f"✓ Applied {len(changed_files)} file changes")
            
            # 3. Commit changes with metadata
            commit_metadata = {
                "proposal_id": proposal_id,
                "confidence": f"{confidence:.2f}",
                "test_coverage": f"{test_results.get('coverage_percent', 0):.1f}%",
                "tests_passed": test_results.get('tests_passed', 0),
                "autonomy_level": autonomy_level,
                "timestamp": datetime.now().isoformat(),
            }
            
            commit_message = f"SIGMA Proposal {proposal_id}: Automated code improvement\n\n"
            commit_message += f"This change was proposed by the SIGMA agent system.\n"
            commit_message += f"Committee confidence: {confidence:.1%}\n"
            commit_message += f"Tests: {test_results.get('tests_passed', 0)} passed"
            
            commit_result = self.commit_changes(
                message=commit_message,
                files=changed_files,
                metadata=commit_metadata,
            )
            
            if not commit_result.success:
                workflow_result["error"] = f"Commit failed: {commit_result.error}"
                return workflow_result
            
            workflow_result["committed"] = True
            workflow_result["commit_sha"] = commit_result.commit_sha
            logger.info(f"✓ Committed changes: {commit_result.commit_sha[:7]}")
            
            # 4. Push to remote (Level 2+)
            if autonomy_level >= 2:
                push_result = self.push_branch(branch_name)
                
                if not push_result.success:
                    workflow_result["error"] = f"Push failed: {push_result.error}"
                    return workflow_result
                
                workflow_result["pushed"] = True
                logger.info(f"✓ Pushed to remote: {push_result.commits_pushed} commits")
            
            # 5. Create pull request (Level 2+)
            if autonomy_level >= 2:
                pr_title = f"SIGMA: Automated improvement ({confidence:.0%} confidence)"
                pr_body = f"""## 🤖 SIGMA Automated Proposal
                
**Proposal ID:** `{proposal_id}`  
**Committee Confidence:** {confidence:.1%}  
**Autonomy Level:** {autonomy_level}

### Test Results
- ✅ Tests Passed: {test_results.get('tests_passed', 0)}
- ❌ Tests Failed: {test_results.get('tests_failed', 0)}
- 📊 Coverage: {test_results.get('coverage_percent', 0):.1f}%
- ⏱️ Execution Time: {test_results.get('execution_time', 0):.1f}s

### Build Results
- Status: {'✅ Success' if build_results.get('success') else '❌ Failed'}
- Build Time: {build_results.get('build_time', 0):.1f}s

### Files Changed
{chr(10).join(f'- `{f}`' for f in changed_files[:10])}
{f'... and {len(changed_files) - 10} more' if len(changed_files) > 10 else ''}

---
*This PR was automatically created by SIGMA agent system.*
"""
                
                pr_result = self.create_pull_request(
                    title=pr_title,
                    body=pr_body,
                    head_branch=branch_name,
                    labels=["sigma-automated", f"confidence-{int(confidence*100)}"],
                    draft=(autonomy_level == 2),  # Draft for Level 2, ready for Level 3
                )
                
                if not pr_result.success:
                    workflow_result["error"] = f"PR creation failed: {pr_result.error}"
                    return workflow_result
                
                workflow_result["pr_created"] = True
                workflow_result["pr_number"] = pr_result.pr_number
                workflow_result["pr_url"] = pr_result.pr_url
                logger.info(f"✓ Created PR #{pr_result.pr_number}: {pr_result.pr_url}")
            
            # 6. Auto-merge (Level 3 only)
            if autonomy_level >= 3 and workflow_result["pr_number"]:
                # Wait a moment for CI checks to start (if any)
                import time
                time.sleep(5)
                
                merge_result = self.merge_pull_request(
                    pr_number=workflow_result["pr_number"],
                    merge_method="squash",
                )
                
                if merge_result.success:
                    workflow_result["pr_merged"] = True
                    logger.info(f"✓ Merged PR #{workflow_result['pr_number']}")
                    
                    # Cleanup branch after successful merge
                    self.cleanup_branch(branch_name, remote=True)
                    logger.info(f"✓ Cleaned up branch: {branch_name}")
                else:
                    logger.warning(f"Failed to auto-merge PR: {merge_result.error}")
            
            workflow_result["success"] = True
            return workflow_result
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)
            workflow_result["error"] = str(e)
            return workflow_result


def is_git_operations_available() -> bool:
    """Check if Git operations are available."""
    return GIT_AVAILABLE


def is_github_operations_available() -> bool:
    """Check if GitHub operations are available."""
    return GITHUB_AVAILABLE
