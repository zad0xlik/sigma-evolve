# Docker Executor Documentation

## Overview

The Docker Executor provides safe, isolated code execution for the SIGMA agent system. It creates temporary Docker containers for each project, allowing autonomous agents to apply code changes, run tests, and validate builds without affecting the host system.

## Features

### Security
- **Resource Limits**: CPU (2 cores max) and memory (2GB) constraints
- **No Privileged Mode**: Containers run without elevated privileges
- **Capability Restrictions**: Only essential capabilities enabled (CHOWN, SETUID, SETGID)
- **Network Isolation**: Bridge networking (can be further restricted)
- **Automatic Cleanup**: Containers and temp files removed after use

### Language Support
- **Python**: Full support with pytest, coverage, linting tools
- **JavaScript/TypeScript**: Node.js with Jest, ESLint, Prettier
- **Java**: OpenJDK with Maven/Gradle
- **Go**: Golang compiler and tools
- **Ruby**: Ruby runtime with Bundler, Rake

### Capabilities
1. **Container Creation**: Build custom images from project workspaces
2. **Code Execution**: Run arbitrary commands with timeout support
3. **Test Execution**: Auto-detect and run test frameworks with coverage
4. **Build Validation**: Run builds with configurable timeouts
5. **Code Changes**: Apply file modifications safely in containers
6. **Resource Monitoring**: Track CPU, memory, and network usage

## Usage Examples

### Basic Container Creation

```python
from openmemory.app.utils import DockerExecutor

executor = DockerExecutor()

# Create container for Python project
success, container_id, error = executor.create_project_container(
    project_id=1,
    workspace="/path/to/project",
    language="python",
)

if success:
    print(f"Container created: {container_id[:12]}")
else:
    print(f"Failed: {error}")
```

### Executing Commands

```python
# Run command in container
result = executor.execute_in_container(
    container_id=container_id,
    command="python -m pylint src/",
    timeout=300,
)

print(f"Exit code: {result.exit_code}")
print(f"Output: {result.output}")
print(f"Time: {result.execution_time:.2f}s")
```

### Running Tests

```python
# Auto-detect and run tests
test_result = executor.run_tests(
    container_id=container_id,
    language="python",
)

print(f"Tests passed: {test_result.tests_passed}")
print(f"Tests failed: {test_result.tests_failed}")
print(f"Coverage: {test_result.coverage_percent:.1f}%")
```

### Applying Code Changes

```python
# Apply changes to multiple files
changes = [
    {
        'filepath': 'src/main.py',
        'content': 'def main():\n    print("Hello!")\n'
    },
    {
        'filepath': 'src/utils.py',
        'content': 'def helper():\n    return 42\n'
    }
]

result = executor.apply_changes(
    container_id=container_id,
    changes=changes,
)

if result.success:
    print(f"Applied {len(changes)} changes")
```

### Running Builds

```python
# Run build validation
build_result = executor.run_build(
    container_id=container_id,
    language="python",
)

print(f"Build {'succeeded' if build_result.success else 'failed'}")
print(f"Build time: {build_result.build_time:.1f}s")
```

### Cleanup

```python
# Stop and remove container
executor.stop_container(container_id)

# Cleanup all project resources
executor.cleanup_project(project_id=1)

# Cleanup everything
executor.cleanup_all()
```

## Integration with Think Worker

The Think Worker uses the Docker Executor to safely execute proposals:

```python
class ThinkWorker(BaseWorker):
    def __init__(self, db_session, dreamer):
        super().__init__(db_session, dreamer)
        self.docker_executor = DockerExecutor()
    
    def _execute_proposal(self, proposal, decision):
        # Create container
        success, container_id, _ = self.docker_executor.create_project_container(
            project_id=proposal.project_id,
            workspace=project.workspace_path,
            language=project.language,
        )
        
        try:
            # Apply changes
            changes = json.loads(proposal.changes_json)
            self.docker_executor.apply_changes(container_id, changes)
            
            # Run tests
            test_result = self.docker_executor.run_tests(
                container_id, project.language
            )
            
            if test_result.success:
                # Tests passed, mark proposal as executed
                proposal.status = 'executed'
                return True
            else:
                # Tests failed, reject proposal
                proposal.status = 'rejected'
                return False
        finally:
            # Always cleanup
            self.docker_executor.stop_container(container_id)
            self.docker_executor.cleanup_project(proposal.project_id)
```

## Configuration

Configure via environment variables in `.env`:

```bash
# Docker Execution
DOCKER_ENABLED=true
DOCKER_REGISTRY=docker.io
DOCKER_IMAGE_PREFIX=sigma-project

# Testing
AUTO_TEST=true
TEST_TIMEOUT=300
MIN_TEST_COVERAGE=0.70

# Building
AUTO_BUILD=true
BUILD_TIMEOUT=600
```

## Test Framework Detection

The executor automatically detects and runs appropriate test frameworks:

### Python
- Detects: pytest
- Command: `pytest --cov=. --cov-report=json --cov-report=term -v`
- Parses: Pass/fail counts, coverage percentage

### JavaScript/TypeScript
- Detects: jest, npm test
- Command: `jest --coverage --verbose` or `npm test`
- Parses: Pass/fail counts, coverage percentage

### Custom Commands
```python
# Override with custom test command
test_result = executor.run_tests(
    container_id=container_id,
    language="python",
    test_command="python -m unittest discover"
)
```

## Resource Monitoring

Track container resource usage:

```python
stats = executor.get_container_stats(container_id)

print(f"CPU: {stats['cpu_percent']:.1f}%")
print(f"Memory: {stats['memory_usage_mb']:.1f}MB ({stats['memory_percent']:.1f}%)")
print(f"Network RX: {stats['network_rx_mb']:.2f}MB")
print(f"Network TX: {stats['network_tx_mb']:.2f}MB")
```

## Error Handling

All methods return structured results with error information:

```python
result = executor.execute_in_container(container_id, "invalid-command")

if not result.success:
    print(f"Error: {result.error}")
    print(f"Exit code: {result.exit_code}")
    print(f"Stderr: {result.error}")
```

## Best Practices

1. **Always use try/finally**: Ensure cleanup even if execution fails
2. **Set appropriate timeouts**: Prevent infinite loops/hangs
3. **Monitor resource usage**: Track container stats for optimization
4. **Check test results**: Don't just check exit code, parse actual results
5. **Validate inputs**: Check workspace exists before creating containers
6. **Handle Docker unavailable**: Gracefully degrade if Docker not running

## Limitations

- **Docker required**: Must have Docker daemon running
- **Resource overhead**: Each container requires ~200MB-500MB overhead
- **Build time**: Initial container creation takes 1-3 minutes
- **Network**: Limited to bridge networking (no host network access)
- **File system**: Changes in container don't persist to host automatically

## Future Enhancements

- [ ] Container pooling for faster execution
- [ ] Support for custom Dockerfiles per project
- [ ] Parallel container execution
- [ ] Persistent container caching
- [ ] Integration with container registries
- [ ] Support for GPU workloads
- [ ] More granular security policies
- [ ] Network policy enforcement
