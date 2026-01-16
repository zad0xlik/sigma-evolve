# Git/GitHub Operations Layer

Comprehensive Git and GitHub operations for the SIGMA agent system, enabling autonomous code changes through the full software development lifecycle.

## Overview

The Git Operations layer (`git_operations.py`) provides a production-ready interface for:

- **Branch Management**: Create, checkout, and cleanup feature branches
- **Commit Operations**: Stage, commit, and push changes with rich metadata
- **Pull Request Management**: Create, merge, and monitor PRs via GitHub API
- **Full Workflow Execution**: Complete end-to-end Git workflow from branch creation to PR merge
- **Multi-level Autonomy**: Respects autonomy levels (1-3) for different permission levels

## Architecture

```
GitOperations
├── Branch Operations
│   ├── create_feature_branch()
│   └── cleanup_branch()
├── Commit Operations
│   ├── apply_changes_from_docker()
│   ├── commit_changes()
│   └── push_branch()
├── Pull Request Operations
│   ├── create_pull_request()
│   ├── merge_pull_request()
│   └── get_pull_request_status()
└── Workflow Orchestration
    └── execute_full_workflow()  ← Main integration point
```

## Result Classes

### BranchResult
```python
@dataclass
class BranchResult:
    success: bool
    branch_name: str
    error: Optional[str] = None
    base_branch: Optional[str] = None
    commit_sha: Optional[str] = None
```

### CommitResult
```python
@dataclass
class CommitResult:
    success: bool
    commit_sha: str
    commit_message: str
    files_changed: int
    error: Optional[str] = None
    branch_name: Optional[str] = None
```

### PushResult
```python
@dataclass
class PushResult:
    success: bool
    branch_name: str
    remote_name: str
    error: Optional[str] = None
    commits_pushed: int = 0
```

### PullRequestResult
```python
@dataclass
class PullRequestResult:
    success: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    error: Optional[str] = None
    branch_name: Optional[str] = None
    merged: bool = False
```

## Usage Examples

### 1. Basic Initialization

```python
from openmemory.app.utils import GitOperations

# Initialize with GitHub token for API operations
git_ops = GitOperations(
    repo_path="/path/to/repo",
    github_token="ghp_xxxxxxxxxxxx",
    default_branch="main",
)
```

### 2. Create Feature Branch

```python
# Create new feature branch from main
result = git_ops.create_feature_branch(
    branch_name="sigma/proposal-12345",
    base_branch="main",  # Optional, defaults to default_branch
)

if result.success:
    print(f"✓ Created branch: {result.branch_name}")
    print(f"  Base: {result.base_branch}")
    print(f"  Commit: {result.commit_sha[:7]}")
else:
    print(f"✗ Failed: {result.error}")
```

### 3. Apply Changes and Commit

```python
# Apply changes from proposal
changes = {
    "src/main.py": {
        "action": "modify",
        "content": "# Updated code\nprint('Hello SIGMA')\n"
    },
    "src/utils.py": {
        "action": "create",
        "content": "def helper():\n    pass\n"
    },
    "old_file.py": {
        "action": "delete"
    }
}

success, changed_files = git_ops.apply_changes_from_docker(
    changes=changes,
    container_workspace=Path("/tmp/container-workspace"),
)

if success:
    print(f"✓ Applied {len(changed_files)} changes")
    
    # Commit with metadata
    commit_result = git_ops.commit_changes(
        message="SIGMA Proposal 12345: Improve performance",
        files=changed_files,
        metadata={
            "proposal_id": "12345",
            "confidence": "0.85",
            "autonomy_level": 2,
        }
    )
    
    if commit_result.success:
        print(f"✓ Committed: {commit_result.commit_sha[:7]}")
        print(f"  Files changed: {commit_result.files_changed}")
```

### 4. Push to Remote

```python
# Push feature branch
push_result = git_ops.push_branch(
    branch_name="sigma/proposal-12345",
    remote_name="origin",
)

if push_result.success:
    print(f"✓ Pushed {push_result.commits_pushed} commits")
else:
    print(f"✗ Push failed: {push_result.error}")
```

### 5. Create Pull Request

```python
# Create PR with rich description
pr_result = git_ops.create_pull_request(
    title="SIGMA: Automated improvement (85% confidence)",
    body="""## 🤖 SIGMA Automated Proposal

**Proposal ID:** `12345`
**Confidence:** 85%

### Test Results
- ✅ Tests Passed: 42
- ❌ Tests Failed: 0
- 📊 Coverage: 87.5%

### Changes
- Optimized database queries
- Reduced response time by 30%
""",
    head_branch="sigma/proposal-12345",
    base_branch="main",
    labels=["sigma-automated", "confidence-85"],
    draft=True,  # True for Level 2 autonomy
)

if pr_result.success:
    print(f"✓ Created PR #{pr_result.pr_number}")
    print(f"  URL: {pr_result.pr_url}")
```

### 6. Merge Pull Request (Level 3 Autonomy)

```python
# Auto-merge for high confidence proposals
merge_result = git_ops.merge_pull_request(
    pr_number=123,
    merge_method="squash",  # or "merge", "rebase"
)

if merge_result.success and merge_result.merged:
    print(f"✓ Merged PR #{merge_result.pr_number}")
    
    # Cleanup branch after merge
    git_ops.cleanup_branch("sigma/proposal-12345", remote=True)
else:
    print(f"✗ Merge failed: {merge_result.error}")
```

### 7. Full Workflow Execution (Think Worker Integration)

```python
# Complete workflow from branch to PR/merge
workflow_result = git_ops.execute_full_workflow(
    proposal_id="12345",
    changes={
        "src/main.py": "# Updated code\n...",
    },
    container_workspace=Path("/tmp/workspace"),
    test_results={
        'success': True,
        'tests_passed': 42,
        'tests_failed': 0,
        'coverage_percent': 87.5,
        'execution_time': 15.2,
    },
    build_results={
        'success': True,
        'build_time': 8.5,
    },
    confidence=0.85,
    autonomy_level=2,  # 1, 2, or 3
)

if workflow_result['success']:
    print("✓ Full workflow completed:")
    print(f"  Branch: {workflow_result['branch_name']}")
    print(f"  Commit: {workflow_result['commit_sha'][:7]}")
    print(f"  PR: {workflow_result['pr_url']}")
    if workflow_result['pr_merged']:
        print("  Status: ✅ Merged")
    else:
        print("  Status: 📝 Awaiting review")
else:
    print(f"✗ Workflow failed: {workflow_result['error']}")
```

## Autonomy Level Behavior

The Git operations respect the configured autonomy level:

### Level 1: Propose Only
- ❌ No Git operations performed
- ✅ Proposals stored in database for manual review

### Level 2: Auto-Commit + PR
- ✅ Create feature branch
- ✅ Commit changes
- ✅ Push to remote
- ✅ Create **draft** pull request
- ❌ No auto-merge (requires manual approval)

### Level 3: Fully Autonomous
- ✅ Create feature branch
- ✅ Commit changes
- ✅ Push to remote
- ✅ Create **ready** pull request
- ✅ **Auto-merge** if confidence threshold met
- ✅ Cleanup branch after merge

## Configuration

All Git operations use configuration from `agent_config.py`:

```python
from openmemory.app.agent_config import get_agent_config

config = get_agent_config()

# Autonomy settings
config.autonomy.level                    # 1, 2, or 3
config.autonomy.auto_create_branches     # Enable branch creation
config.autonomy.auto_commit_to_branch    # Enable commits
config.autonomy.auto_create_pr           # Enable PR creation
config.autonomy.auto_merge_pr            # Enable auto-merge

# Project settings
config.project.repo_url                  # GitHub repository URL
config.project.branch                    # Default branch (main/master)
config.project.token                     # GitHub personal access token
config.project.workspace_dir             # Local workspace path
```

### Environment Variables

```bash
# Autonomy Level
AUTONOMY_LEVEL=2                         # 1, 2, or 3

# Git/GitHub Settings
GITHUB_REPO_URL=https://github.com/user/repo
GITHUB_BRANCH=main
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
WORKSPACE_DIR=/tmp/sigma-workspace

# Auto-action Flags
AUTO_CREATE_BRANCHES=true
AUTO_COMMIT_TO_BRANCH=true
AUTO_CREATE_PR=true
AUTO_MERGE_PR=false                      # Only for Level 3
```

## Integration with Think Worker

The Think Worker uses `execute_full_workflow()` to handle all Git operations:

```python
class ThinkWorker(BaseWorker):
    def _execute_proposal(self, proposal, decision):
        # ... Docker execution ...
        
        # Git operations for Level 2+
        if self.config.autonomy.level >= 2:
            git_ops = GitOperations(
                repo_path=project.workspace_path,
                github_token=self.config.project.token,
                default_branch=self.config.project.branch,
            )
            
            workflow_result = git_ops.execute_full_workflow(
                proposal_id=proposal.proposal_id,
                changes=changes,
                container_workspace=None,
                test_results=test_results,
                build_results=build_results,
                confidence=decision['confidence'],
                autonomy_level=self.config.autonomy.level,
            )
            
            # Store results in proposal
            proposal.commit_sha = json.dumps({
                **execution_metadata,
                'git_workflow': workflow_result,
            })
```

## Commit Message Format

All commits include rich metadata:

```
SIGMA Proposal 12345: Automated code improvement

This change was proposed by the SIGMA agent system.
Committee confidence: 85.0%
Tests: 42 passed

[SIGMA Metadata]
proposal_id: 12345
confidence: 0.85
test_coverage: 87.5%
tests_passed: 42
autonomy_level: 2
timestamp: 2026-01-15T15:30:00
```

## Pull Request Format

PRs are created with comprehensive information:

```markdown
## 🤖 SIGMA Automated Proposal

**Proposal ID:** `12345`  
**Committee Confidence:** 85.0%  
**Autonomy Level:** 2

### Test Results
- ✅ Tests Passed: 42
- ❌ Tests Failed: 0
- 📊 Coverage: 87.5%
- ⏱️ Execution Time: 15.2s

### Build Results
- Status: ✅ Success
- Build Time: 8.5s

### Files Changed
- `src/main.py`
- `src/utils.py`
- `tests/test_main.py`

---
*This PR was automatically created by SIGMA agent system.*
```

## Error Handling

All operations return result objects with success/error information:

```python
# Check availability before use
from openmemory.app.utils import is_git_operations_available, is_github_operations_available

if not is_git_operations_available():
    print("GitPython not installed")
    
if not is_github_operations_available():
    print("PyGithub not installed")

# Handle operation failures
result = git_ops.create_feature_branch("my-branch")
if not result.success:
    logger.error(f"Branch creation failed: {result.error}")
    # Handle failure...

# Try-except for initialization errors
try:
    git_ops = GitOperations(repo_path, token)
except ValueError as e:
    logger.error(f"Invalid repository: {e}")
```

## Security Considerations

### GitHub Token Permissions

The GitHub token needs these permissions:

- ✅ `repo` - Full control of private repositories
  - `repo:status` - Access commit status
  - `repo_deployment` - Access deployment status
  - `public_repo` - Access public repositories
  - `repo:invite` - Access repository invitations
- ✅ `write:discussion` - Read and write discussions
- ✅ `workflow` - Update GitHub Action workflows

### Token Storage

```python
# NEVER hardcode tokens
# ❌ BAD:
git_ops = GitOperations(path, "ghp_xxxxxxxxxxxx")

# ✅ GOOD: Use environment variables
import os
git_ops = GitOperations(
    path, 
    os.getenv("GITHUB_TOKEN")
)

# ✅ BEST: Use secrets management
from openmemory.app.secrets import get_secret
git_ops = GitOperations(
    path,
    get_secret("GITHUB_TOKEN")
)
```

### Branch Protection

Configure branch protection rules on GitHub:

- Require pull request reviews (for Level 2)
- Require status checks to pass
- Require conversation resolution
- Include administrators (enforce rules for everyone)

This ensures even Level 3 auto-merges respect your CI/CD pipeline.

## Monitoring

### Git Operations Logging

All operations are logged with structured information:

```python
# Logs include:
# - Operation type (branch, commit, push, PR)
# - Success/failure status
# - Timing information
# - Error details if failed

logger.info("✓ Created branch: sigma/proposal-12345")
logger.info("✓ Committed 3 files: abc123d")
logger.info("✓ Pushed 1 commits to origin")
logger.info("✓ Created PR #42: https://github.com/user/repo/pull/42")
logger.warning("Git workflow failed: PR has merge conflicts")
```

### Proposal Tracking

All Git operations are tracked in the `proposals` table:

```python
# commit_sha field stores execution metadata
metadata = json.loads(proposal.commit_sha)

git_workflow = metadata.get('git_workflow', {})
print(f"Branch: {git_workflow['branch_name']}")
print(f"Commit: {git_workflow['commit_sha']}")
print(f"PR: {git_workflow['pr_url']}")
print(f"Merged: {git_workflow['pr_merged']}")
```

## Best Practices

### 1. Always Check Availability
```python
if is_git_operations_available():
    git_ops = GitOperations(...)
else:
    logger.warning("Git operations unavailable")
    # Fallback behavior
```

### 2. Use Full Workflow for Consistency
```python
# ✅ GOOD: Use execute_full_workflow()
workflow_result = git_ops.execute_full_workflow(...)

# ❌ AVOID: Manual step-by-step (unless you need custom logic)
git_ops.create_feature_branch(...)
git_ops.commit_changes(...)
git_ops.push_branch(...)
git_ops.create_pull_request(...)
```

### 3. Cleanup After Operations
```python
# Always cleanup branches after merge
if workflow_result['pr_merged']:
    git_ops.cleanup_branch(
        branch_name,
        remote=True  # Delete from remote too
    )
```

### 4. Handle Merge Conflicts Gracefully
```python
merge_result = git_ops.merge_pull_request(pr_number)

if not merge_result.success:
    if "merge conflicts" in merge_result.error.lower():
        # Flag for manual resolution
        proposal.status = 'needs_resolution'
        proposal.notes = "Merge conflicts detected"
    else:
        # Other error
        logger.error(f"Merge failed: {merge_result.error}")
```

## Limitations

### Current Limitations

1. **No Conflict Resolution**: Cannot auto-resolve merge conflicts
2. **Single Remote**: Only supports 'origin' remote
3. **No Rebase Support**: Only merge and squash strategies
4. **No Multi-PR**: One proposal = one PR (no stacked PRs)

### Future Enhancements

- **Conflict Detection & Resolution**: AI-powered conflict resolution
- **Multi-Remote Support**: Support for multiple remotes (upstream, origin)
- **Rebase Workflows**: Support for rebase merge strategy
- **Stacked PRs**: Dependencies between proposals
- **Branch Policies**: Custom branch naming conventions
- **Commit Signing**: GPG signing for all commits
- **CI/CD Integration**: Wait for CI checks before merge

## Troubleshooting

### "Not a valid git repository"
```python
# Ensure repo_path is correct and initialized
git_ops = GitOperations("/correct/path/to/repo", token)

# Or initialize a new repo
import git
repo = git.Repo.init("/path/to/new/repo")
```

### "GitHub repository not initialized"
```python
# Check token permissions
# Check remote URL format
# Ensure origin remote exists:
cd /path/to/repo
git remote -v
```

### "Push rejected"
```python
# May need to pull first
git_ops.repo.git.pull('origin', branch_name)
git_ops.push_branch(branch_name)

# Or use force push (CAUTION)
git_ops.push_branch(branch_name, force=True)
```

### "PR has merge conflicts"
```python
# Check PR status
status = git_ops.get_pull_request_status(pr_number)
print(f"Mergeable: {status['mergeable']}")
print(f"State: {status['mergeable_state']}")

# Requires manual resolution
```

## Testing

```bash
# Unit tests
pytest test/test_git_operations.py

# Integration tests (requires real repo)
GITHUB_TOKEN=ghp_xxx pytest test/test_git_integration.py -v
```

## Related Documentation

- [Docker Executor README](./README_DOCKER_EXECUTOR.md) - Safe code execution
- [Agent Configuration](../agent_config.py) - Autonomy levels and settings
- [Think Worker](../agents/think_worker.py) - Decision-making and execution
- [GitPython Docs](https://gitpython.readthedocs.io/) - Git operations library
- [PyGithub Docs](https://pygithub.readthedocs.io/) - GitHub API library
