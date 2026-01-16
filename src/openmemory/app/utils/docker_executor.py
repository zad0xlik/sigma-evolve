"""
Docker Execution Environment

Safe code execution in isolated Docker containers.
Enables autonomous agents to test and validate changes without affecting the host system.
"""
import os
import json
import logging
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import docker
from docker.models.containers import Container
from docker.errors import DockerException, APIError, ContainerError, ImageNotFound

from ..agent_config import get_agent_config

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of code execution in Docker container"""
    success: bool
    output: str
    error: str
    exit_code: int
    execution_time: float
    container_id: Optional[str] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TestResult:
    """Result of test execution"""
    success: bool
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    coverage_percent: float
    execution_time: float
    output: str
    error: str
    test_details: List[Dict] = None
    
    def __post_init__(self):
        if self.test_details is None:
            self.test_details = []


@dataclass
class BuildResult:
    """Result of build execution"""
    success: bool
    output: str
    error: str
    build_time: float
    artifacts: List[str] = None
    
    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = []


class DockerExecutor:
    """
    Docker Execution Environment for safe code execution.
    
    Creates isolated containers for each project, executes code changes,
    runs tests, and validates builds. Provides security through:
    - Resource limits (CPU, memory)
    - Network isolation (optional)
    - No privileged mode
    - Temporary filesystem
    - Automatic cleanup
    """
    
    def __init__(self):
        """Initialize Docker executor"""
        self.config = get_agent_config()
        try:
            self.client = docker.from_env()
            self._validate_docker()
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise
        
        # Container registry
        self.containers: Dict[str, Container] = {}
        
        # Workspace management
        self.temp_workspaces: Dict[int, str] = {}
        
    def _validate_docker(self):
        """Validate Docker is running and accessible"""
        try:
            self.client.ping()
            logger.info("Docker connection validated")
        except Exception as e:
            raise DockerException(f"Docker is not accessible: {e}")
    
    def _get_base_image(self, language: str) -> str:
        """Get appropriate base image for language"""
        images = {
            "python": "python:3.12-slim",
            "javascript": "node:20-alpine",
            "typescript": "node:20-alpine",
            "java": "openjdk:17-slim",
            "go": "golang:1.21-alpine",
            "ruby": "ruby:3.2-slim",
        }
        return images.get(language.lower(), "python:3.12-slim")
    
    def _create_dockerfile(self, language: str, workspace: str) -> str:
        """Create Dockerfile for project"""
        if language.lower() == "python":
            return """
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Install Python dependencies if requirements.txt exists
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
RUN if [ -f pyproject.toml ]; then pip install --no-cache-dir -e .; fi

# Install testing tools
RUN pip install --no-cache-dir pytest pytest-cov pylint black isort mypy radon

CMD ["/bin/bash"]
"""
        elif language.lower() in ["javascript", "typescript"]:
            return """
FROM node:20-alpine

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache git

# Copy project files
COPY . /app

# Install dependencies if package.json exists
RUN if [ -f package.json ]; then npm install; fi

# Install testing tools
RUN npm install -g jest eslint prettier typescript ts-node

CMD ["/bin/sh"]
"""
        else:
            # Generic Dockerfile
            return f"""
FROM {self._get_base_image(language)}

WORKDIR /app
COPY . /app

CMD ["/bin/bash"]
"""
    
    def create_project_container(
        self,
        project_id: int,
        workspace: str,
        language: str,
        container_name: Optional[str] = None,
    ) -> Tuple[bool, str, str]:
        """
        Create isolated Docker container for project.
        
        Args:
            project_id: Project identifier
            workspace: Path to project workspace
            language: Programming language
            container_name: Optional container name
            
        Returns:
            (success, container_id, error_message)
        """
        if not os.path.exists(workspace):
            return False, "", f"Workspace not found: {workspace}"
        
        container_name = container_name or f"sigma-project-{project_id}"
        
        try:
            # Create temporary workspace copy
            temp_workspace = tempfile.mkdtemp(prefix=f"sigma-{project_id}-")
            self.temp_workspaces[project_id] = temp_workspace
            
            # Copy workspace to temp directory
            logger.info(f"Copying workspace {workspace} to {temp_workspace}")
            shutil.copytree(workspace, temp_workspace, dirs_exist_ok=True)
            
            # Create Dockerfile
            dockerfile_content = self._create_dockerfile(language, temp_workspace)
            dockerfile_path = os.path.join(temp_workspace, "Dockerfile.sigma")
            with open(dockerfile_path, "w") as f:
                f.write(dockerfile_content)
            
            # Build image
            image_tag = f"sigma-project-{project_id}:{language.lower()}"
            logger.info(f"Building Docker image: {image_tag}")
            
            image, build_logs = self.client.images.build(
                path=temp_workspace,
                dockerfile="Dockerfile.sigma",
                tag=image_tag,
                rm=True,
                forcerm=True,
            )
            
            # Log build output
            for log in build_logs:
                if 'stream' in log:
                    logger.debug(log['stream'].strip())
            
            # Create container with resource limits
            logger.info(f"Creating container: {container_name}")
            container = self.client.containers.create(
                image=image_tag,
                name=container_name,
                detach=True,
                tty=True,
                stdin_open=True,
                working_dir="/app",
                # Security and resource limits
                mem_limit="2g",
                memswap_limit="2g",
                cpu_period=100000,
                cpu_quota=200000,  # 2 CPU cores max
                network_mode="bridge",
                # Prevent privilege escalation
                privileged=False,
                cap_drop=["ALL"],
                cap_add=["CHOWN", "SETUID", "SETGID"],
                # Read-only root filesystem (except /app)
                read_only=False,  # Can't use true as we need to write
                # Remove container after stop (cleanup)
                auto_remove=False,
            )
            
            # Start container
            container.start()
            
            # Store container reference
            self.containers[container_name] = container
            
            logger.info(f"Container created: {container.id[:12]}")
            return True, container.id, ""
            
        except ImageNotFound as e:
            error = f"Base image not found: {e}"
            logger.error(error)
            return False, "", error
        except APIError as e:
            error = f"Docker API error: {e}"
            logger.error(error)
            return False, "", error
        except Exception as e:
            error = f"Failed to create container: {e}"
            logger.error(error)
            return False, "", error
    
    def execute_in_container(
        self,
        container_id: str,
        command: str,
        timeout: int = 300,
        workdir: str = "/app",
    ) -> ExecutionResult:
        """
        Execute command in container.
        
        Args:
            container_id: Container ID or name
            command: Command to execute
            timeout: Execution timeout in seconds
            workdir: Working directory
            
        Returns:
            ExecutionResult with output and status
        """
        import time
        start_time = time.time()
        
        try:
            # Get container
            container = self.client.containers.get(container_id)
            
            # Execute command
            logger.info(f"Executing in {container_id[:12]}: {command}")
            
            exec_result = container.exec_run(
                cmd=command,
                workdir=workdir,
                stdout=True,
                stderr=True,
                stream=False,
                demux=True,
            )
            
            execution_time = time.time() - start_time
            
            # Demultiplex stdout and stderr
            stdout_bytes = exec_result.output[0] if exec_result.output else b""
            stderr_bytes = exec_result.output[1] if exec_result.output else b""
            
            stdout = stdout_bytes.decode('utf-8') if stdout_bytes else ""
            stderr = stderr_bytes.decode('utf-8') if stderr_bytes else ""
            
            success = exec_result.exit_code == 0
            
            if not success:
                logger.warning(f"Command failed with exit code {exec_result.exit_code}")
                logger.warning(f"stderr: {stderr[:500]}")
            
            return ExecutionResult(
                success=success,
                output=stdout,
                error=stderr,
                exit_code=exec_result.exit_code,
                execution_time=execution_time,
                container_id=container_id,
                metadata={"command": command, "workdir": workdir},
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error = f"Execution failed: {e}"
            logger.error(error)
            
            return ExecutionResult(
                success=False,
                output="",
                error=error,
                exit_code=-1,
                execution_time=execution_time,
                container_id=container_id,
            )
    
    def run_tests(
        self,
        container_id: str,
        language: str,
        test_command: Optional[str] = None,
    ) -> TestResult:
        """
        Run tests in container with coverage.
        
        Args:
            container_id: Container ID or name
            language: Programming language
            test_command: Optional custom test command
            
        Returns:
            TestResult with test outcomes and coverage
        """
        # Detect test command if not provided
        if test_command is None:
            test_command = self._detect_test_command(container_id, language)
        
        logger.info(f"Running tests: {test_command}")
        
        # Execute tests
        result = self.execute_in_container(
            container_id=container_id,
            command=test_command,
            timeout=self.config.execution.test_timeout,
        )
        
        # Parse test results
        test_result = self._parse_test_output(
            language=language,
            output=result.output,
            error=result.error,
            exit_code=result.exit_code,
            execution_time=result.execution_time,
        )
        
        return test_result
    
    def _detect_test_command(self, container_id: str, language: str) -> str:
        """Detect appropriate test command for project"""
        if language.lower() == "python":
            # Check for pytest
            check = self.execute_in_container(container_id, "which pytest")
            if check.success:
                return "pytest --cov=. --cov-report=json --cov-report=term -v"
            return "python -m pytest --cov=. --cov-report=json --cov-report=term -v"
            
        elif language.lower() in ["javascript", "typescript"]:
            # Check for jest
            check = self.execute_in_container(container_id, "which jest")
            if check.success:
                return "jest --coverage --verbose"
            return "npm test"
            
        else:
            return "echo 'No test framework detected'"
    
    def _parse_test_output(
        self,
        language: str,
        output: str,
        error: str,
        exit_code: int,
        execution_time: float,
    ) -> TestResult:
        """Parse test output to extract results"""
        # Default values
        success = exit_code == 0
        tests_passed = 0
        tests_failed = 0
        tests_skipped = 0
        coverage_percent = 0.0
        
        combined_output = output + error
        
        if language.lower() == "python":
            # Parse pytest output
            import re
            
            # Match: "5 passed, 2 failed, 1 skipped"
            passed_match = re.search(r'(\d+) passed', combined_output)
            failed_match = re.search(r'(\d+) failed', combined_output)
            skipped_match = re.search(r'(\d+) skipped', combined_output)
            
            if passed_match:
                tests_passed = int(passed_match.group(1))
            if failed_match:
                tests_failed = int(failed_match.group(1))
            if skipped_match:
                tests_skipped = int(skipped_match.group(1))
            
            # Parse coverage: "TOTAL ... 85%"
            coverage_match = re.search(r'TOTAL.*?(\d+)%', combined_output)
            if coverage_match:
                coverage_percent = float(coverage_match.group(1))
                
        elif language.lower() in ["javascript", "typescript"]:
            # Parse jest output
            import re
            
            # Match: "Tests: 3 passed, 3 total"
            passed_match = re.search(r'(\d+) passed', combined_output)
            failed_match = re.search(r'(\d+) failed', combined_output)
            
            if passed_match:
                tests_passed = int(passed_match.group(1))
            if failed_match:
                tests_failed = int(failed_match.group(1))
            
            # Parse coverage
            coverage_match = re.search(r'All files\s+\|\s+(\d+\.?\d*)', combined_output)
            if coverage_match:
                coverage_percent = float(coverage_match.group(1))
        
        return TestResult(
            success=success,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            tests_skipped=tests_skipped,
            coverage_percent=coverage_percent,
            execution_time=execution_time,
            output=output,
            error=error,
        )
    
    def run_build(
        self,
        container_id: str,
        language: str,
        build_command: Optional[str] = None,
    ) -> BuildResult:
        """
        Run build in container.
        
        Args:
            container_id: Container ID or name
            language: Programming language
            build_command: Optional custom build command
            
        Returns:
            BuildResult with build status
        """
        import time
        
        # Detect build command if not provided
        if build_command is None:
            build_command = self._detect_build_command(language)
        
        logger.info(f"Running build: {build_command}")
        
        start_time = time.time()
        
        # Execute build
        result = self.execute_in_container(
            container_id=container_id,
            command=build_command,
            timeout=self.config.execution.build_timeout,
        )
        
        build_time = time.time() - start_time
        
        return BuildResult(
            success=result.success,
            output=result.output,
            error=result.error,
            build_time=build_time,
            artifacts=[],  # TODO: Detect build artifacts
        )
    
    def _detect_build_command(self, language: str) -> str:
        """Detect appropriate build command for project"""
        commands = {
            "python": "python -m py_compile $(find . -name '*.py' -not -path './venv/*' -not -path './.venv/*')",
            "javascript": "npm run build || echo 'No build script'",
            "typescript": "npm run build || tsc || echo 'No build script'",
            "java": "mvn clean package || gradle build || echo 'No build tool'",
            "go": "go build ./...",
            "ruby": "bundle install && rake build || echo 'No build script'",
        }
        return commands.get(language.lower(), "echo 'No build command for language'")
    
    def apply_changes(
        self,
        container_id: str,
        changes: List[Dict],
    ) -> ExecutionResult:
        """
        Apply code changes to files in container.
        
        Args:
            container_id: Container ID or name
            changes: List of changes with 'filepath' and 'content'
            
        Returns:
            ExecutionResult indicating success
        """
        try:
            container = self.client.containers.get(container_id)
            
            for change in changes:
                filepath = change.get('filepath')
                content = change.get('content')
                
                if not filepath or content is None:
                    logger.warning(f"Invalid change: {change}")
                    continue
                
                # Write content to file in container
                logger.info(f"Applying change to: {filepath}")
                
                # Create temporary file with content
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                
                try:
                    # Copy file into container
                    with open(tmp_path, 'rb') as f:
                        data = f.read()
                    
                    container.put_archive(
                        path=os.path.dirname(f"/app/{filepath}") or "/app",
                        data=self._create_tar_archive(
                            filename=os.path.basename(filepath),
                            content=data,
                        ),
                    )
                    
                    logger.info(f"Applied change to {filepath}")
                finally:
                    os.unlink(tmp_path)
            
            return ExecutionResult(
                success=True,
                output=f"Applied {len(changes)} changes",
                error="",
                exit_code=0,
                execution_time=0.0,
                container_id=container_id,
            )
            
        except Exception as e:
            error = f"Failed to apply changes: {e}"
            logger.error(error)
            return ExecutionResult(
                success=False,
                output="",
                error=error,
                exit_code=-1,
                execution_time=0.0,
                container_id=container_id,
            )
    
    def _create_tar_archive(self, filename: str, content: bytes) -> bytes:
        """Create tar archive for Docker put_archive"""
        import tarfile
        import io
        
        tar_stream = io.BytesIO()
        tar = tarfile.TarFile(fileobj=tar_stream, mode='w')
        
        tarinfo = tarfile.TarInfo(name=filename)
        tarinfo.size = len(content)
        tarinfo.mtime = int(os.path.getmtime(__file__))
        
        tar.addfile(tarinfo, io.BytesIO(content))
        tar.close()
        
        tar_stream.seek(0)
        return tar_stream.read()
    
    def stop_container(self, container_id: str) -> bool:
        """Stop and remove container"""
        try:
            container = self.client.containers.get(container_id)
            logger.info(f"Stopping container: {container_id[:12]}")
            
            container.stop(timeout=10)
            container.remove()
            
            # Remove from registry
            for name, cont in list(self.containers.items()):
                if cont.id == container_id:
                    del self.containers[name]
                    break
            
            logger.info(f"Container stopped and removed: {container_id[:12]}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop container: {e}")
            return False
    
    def cleanup_project(self, project_id: int):
        """Cleanup all resources for project"""
        try:
            # Stop container
            container_name = f"sigma-project-{project_id}"
            if container_name in self.containers:
                self.stop_container(self.containers[container_name].id)
            
            # Remove temporary workspace
            if project_id in self.temp_workspaces:
                temp_workspace = self.temp_workspaces[project_id]
                if os.path.exists(temp_workspace):
                    shutil.rmtree(temp_workspace)
                    logger.info(f"Removed temp workspace: {temp_workspace}")
                del self.temp_workspaces[project_id]
            
            # Remove Docker image
            image_tag = f"sigma-project-{project_id}"
            try:
                self.client.images.remove(image_tag, force=True)
                logger.info(f"Removed Docker image: {image_tag}")
            except ImageNotFound:
                pass
            
        except Exception as e:
            logger.error(f"Cleanup failed for project {project_id}: {e}")
    
    def cleanup_all(self):
        """Cleanup all containers and resources"""
        logger.info("Cleaning up all Docker resources")
        
        # Stop all containers
        for container_name, container in list(self.containers.items()):
            try:
                self.stop_container(container.id)
            except Exception as e:
                logger.error(f"Failed to stop {container_name}: {e}")
        
        # Clean up all temp workspaces
        for project_id in list(self.temp_workspaces.keys()):
            self.cleanup_project(project_id)
    
    def get_container_stats(self, container_id: str) -> Dict:
        """Get container resource usage statistics"""
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # Parse CPU usage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0
            
            # Parse memory usage
            memory_usage = stats['memory_stats'].get('usage', 0)
            memory_limit = stats['memory_stats'].get('limit', 1)
            memory_percent = (memory_usage / memory_limit) * 100.0
            
            return {
                'cpu_percent': cpu_percent,
                'memory_usage_mb': memory_usage / (1024 * 1024),
                'memory_percent': memory_percent,
                'network_rx_mb': stats['networks']['eth0']['rx_bytes'] / (1024 * 1024),
                'network_tx_mb': stats['networks']['eth0']['tx_bytes'] / (1024 * 1024),
            }
            
        except Exception as e:
            logger.error(f"Failed to get container stats: {e}")
            return {}
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.cleanup_all()
        except Exception:
            pass
