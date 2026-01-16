"""
Analysis Worker - Continuously monitors code quality and metrics.

Production Mode: AST parsing, complexity analysis, issue detection
Experimental Mode: Novel parsing strategies, new linters, detection heuristics
"""

import os
import ast
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

from radon.complexity import cc_visit
from radon.metrics import mi_visit

from .base_worker import BaseWorker
from ..agent_config import get_agent_config
from ..models import Project, CodeSnapshot
from ..database import get_db

logger = logging.getLogger(__name__)


class AnalysisWorker(BaseWorker):
    """Analyzes code quality, complexity metrics, and potential issues."""
    
    def __init__(self, db_session, dreamer):
        super().__init__(db_session, dreamer)
        self.config = get_agent_config()
        self.current_strategy = "default_ast_radon"
    
    def get_interval(self) -> int:
        """Analysis runs every 5 minutes by default"""
        return self.config.workers.analysis_interval
    
    def _production_cycle(self):
        """
        Production Mode: Efficient, proven analysis approach
        
        Steps:
        1. Get current project from DB
        2. Parse Python files using AST
        3. Compute complexity metrics (cyclomatic, maintainability) using radon
        4. Detect common issues (syntax errors, unused imports, type hints)
        5. Store snapshot in code_snapshots table
        """
        try:
            project = self._get_current_project()
            if not project:
                logger.info("No project configured for analysis")
                return
            
            logger.info(f"Analyzing project: {project.workspace_path}")
            
            # Check if promoted experiments exist
            self._check_for_promoted_strategies()
            
            # Run analysis using current production strategy
            snapshot = self._analyze_codebase(project.workspace_path, project.language)
            
            # Store results
            self._store_snapshot(project.project_id, snapshot)
            
            logger.info(f"Analysis complete: complexity={snapshot['complexity']:.2f}, "
                       f"issues={snapshot['issues_found']}")
            
        except Exception as e:
            logger.error(f"Production analysis failed: {e}")
            raise
    
    def _experimental_cycle(self):
        """
        Experimental Mode: Try novel analysis approaches
        
        Experiments:
        - Different AST parsers (ast vs tree-sitter)
        - Multiple linters (pylint, flake8, mypy)
        - ML-based issue detection
        - Custom complexity heuristics
        
        Metrics tracked:
        - Accuracy (true issues found)
        - False positive rate
        - Performance (analysis time)
        - Coverage (% of code analyzed)
        """
        try:
            project = self._get_current_project()
            if not project:
                return
            
            # Get current performance baseline
            context = self._get_current_performance()
            
            # Ask DreamerMetaAgent for experimental approach
            experiment = self.dreamer.propose_experiment("analysis", context)
            
            if not experiment:
                logger.info("No suitable experiment proposed")
                return
            
            logger.info(f"🧪 Starting experiment: {experiment['experiment_name']}")
            
            # Record experiment start
            exp_id = self.dreamer.record_experiment_start(
                worker_name="analysis",
                experiment_name=experiment["experiment_name"],
                hypothesis=experiment["hypothesis"],
                approach=experiment["approach"]
            )
            
            # Execute experimental approach
            start_time = time.time()
            result = self._try_experimental_approach(
                project.workspace_path,
                project.language,
                experiment["approach"]
            )
            elapsed = time.time() - start_time
            
            # Calculate improvement vs baseline
            improvement = self._calculate_improvement(result, context, elapsed)
            
            # Record outcome
            self.dreamer.record_outcome(
                experiment_id=exp_id,
                success=improvement > 0,
                improvement=improvement,
                details={
                    "result_metrics": result,
                    "baseline_metrics": context,
                    "elapsed_time": elapsed
                }
            )
            
            logger.info(f"Experiment complete: improvement={improvement:.2%}")
            
        except Exception as e:
            logger.error(f"Experimental analysis failed: {e}")
    
    def _get_current_project(self) -> Optional[Project]:
        """Get the currently configured project"""
        # For now, get the first project or create one if none exists
        project = self.db.query(Project).first()
        
        if not project and self.config.project.repo_url:
            # Create project from config
            project = Project(
                repo_url=self.config.project.repo_url,
                branch=self.config.project.branch,
                workspace_path=self.config.project.workspace,
                language="python",  # TODO: detect from config
                framework=None,
                domain=None,
                created_at=datetime.now(),
                last_analyzed=None
            )
            self.db.add(project)
            self.db.commit()
            logger.info(f"Created new project: {project.project_id}")
        
        return project
    
    def _analyze_codebase(self, workspace: str, language: str) -> Dict:
        """
        Analyze codebase using production strategy
        
        Returns:
            {
                'complexity': float,  # Average cyclomatic complexity
                'maintainability': float,  # Maintainability index
                'test_coverage': float,  # Test coverage % (0 if unknown)
                'issues_found': int,  # Number of issues detected
                'files_analyzed': int,
                'lines_of_code': int,
                'issues': List[Dict]  # Detailed issue list
            }
        """
        if language != "python":
            logger.warning(f"Analysis not yet implemented for {language}")
            return self._empty_snapshot()
        
        workspace_path = Path(workspace)
        if not workspace_path.exists():
            logger.warning(f"Workspace not found: {workspace}")
            return self._empty_snapshot()
        
        # Find all Python files
        python_files = list(workspace_path.rglob("*.py"))
        
        total_complexity = 0
        total_maintainability = 0
        analyzed_files = 0
        total_loc = 0
        issues = []
        
        for filepath in python_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Parse with AST
                tree = ast.parse(code, filename=str(filepath))
                
                # Count lines of code
                loc = len(code.splitlines())
                total_loc += loc
                
                # Compute complexity with radon
                complexity_results = cc_visit(code)
                for result in complexity_results:
                    total_complexity += result.complexity
                
                # Compute maintainability index
                mi_results = mi_visit(code, multi=True)
                if mi_results:
                    total_maintainability += mi_results
                
                # Detect issues
                file_issues = self._detect_issues(tree, filepath, code)
                issues.extend(file_issues)
                
                analyzed_files += 1
                
            except SyntaxError as e:
                issues.append({
                    'file': str(filepath),
                    'line': e.lineno,
                    'severity': 'error',
                    'message': f'Syntax error: {e.msg}'
                })
            except Exception as e:
                logger.warning(f"Could not analyze {filepath}: {e}")
        
        # Calculate averages
        avg_complexity = total_complexity / max(analyzed_files, 1)
        avg_maintainability = total_maintainability / max(analyzed_files, 1)
        
        return {
            'complexity': avg_complexity,
            'maintainability': avg_maintainability,
            'test_coverage': 0.0,  # TODO: integrate with pytest-cov
            'issues_found': len(issues),
            'files_analyzed': analyzed_files,
            'lines_of_code': total_loc,
            'issues': issues
        }
    
    def _detect_issues(self, tree: ast.AST, filepath: Path, code: str) -> List[Dict]:
        """Detect common code issues using AST analysis"""
        issues = []
        
        for node in ast.walk(tree):
            # Check for missing type hints on functions
            if isinstance(node, ast.FunctionDef):
                if node.returns is None and node.name not in ['__init__', '__str__']:
                    issues.append({
                        'file': str(filepath),
                        'line': node.lineno,
                        'severity': 'warning',
                        'message': f"Function '{node.name}' missing return type hint"
                    })
            
            # Check for bare except clauses
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append({
                        'file': str(filepath),
                        'line': node.lineno,
                        'severity': 'warning',
                        'message': 'Bare except clause - should specify exception type'
                    })
            
            # Check for mutable default arguments
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append({
                            'file': str(filepath),
                            'line': node.lineno,
                            'severity': 'error',
                            'message': f"Function '{node.name}' has mutable default argument"
                        })
        
        return issues
    
    def _empty_snapshot(self) -> Dict:
        """Return empty snapshot for error cases"""
        return {
            'complexity': 0.0,
            'maintainability': 0.0,
            'test_coverage': 0.0,
            'issues_found': 0,
            'files_analyzed': 0,
            'lines_of_code': 0,
            'issues': []
        }
    
    def _store_snapshot(self, project_id: int, snapshot: Dict):
        """Store analysis snapshot in database"""
        db_snapshot = CodeSnapshot(
            project_id=project_id,
            complexity=snapshot['complexity'],
            test_coverage=snapshot['test_coverage'],
            issues_found=snapshot['issues_found'],
            metrics_json=json.dumps({
                'maintainability': snapshot['maintainability'],
                'files_analyzed': snapshot['files_analyzed'],
                'lines_of_code': snapshot['lines_of_code'],
                'issues': snapshot['issues']
            }),
            created_at=datetime.now()
        )
        self.db.add(db_snapshot)
        self.db.commit()
        
        # Update project's last_analyzed timestamp
        project = self.db.query(Project).get(project_id)
        if project:
            project.last_analyzed = datetime.now()
            self.db.commit()
    
    def _get_current_performance(self) -> Dict:
        """Get recent performance metrics for experiment baseline"""
        # Get last 5 snapshots
        recent_snapshots = self.db.query(CodeSnapshot)\
            .order_by(CodeSnapshot.created_at.desc())\
            .limit(5)\
            .all()
        
        if not recent_snapshots:
            return {
                'avg_complexity': 10.0,
                'avg_issues': 50,
                'avg_analysis_time': 10.0,
                'false_positive_rate': 0.3,
                'current_strategy': self.current_strategy
            }
        
        # Calculate averages
        avg_complexity = sum(s.complexity for s in recent_snapshots) / len(recent_snapshots)
        avg_issues = sum(s.issues_found for s in recent_snapshots) / len(recent_snapshots)
        
        return {
            'avg_complexity': avg_complexity,
            'avg_issues': avg_issues,
            'avg_analysis_time': 10.0,  # TODO: track actual times
            'false_positive_rate': 0.3,  # TODO: track from user feedback
            'current_strategy': self.current_strategy
        }
    
    def _try_experimental_approach(self, workspace: str, language: str, approach: str) -> Dict:
        """
        Execute experimental analysis approach
        
        For now, this is a simplified version that runs the same analysis
        but could be extended to try different strategies based on the approach string
        """
        # TODO: Parse approach string and apply different strategies
        # For now, just run standard analysis as proof of concept
        return self._analyze_codebase(workspace, language)
    
    def _calculate_improvement(self, result: Dict, baseline: Dict, elapsed: float) -> float:
        """
        Calculate improvement percentage over baseline
        
        Factors:
        - More issues found (if they're valid) = better
        - Lower false positive rate = better
        - Faster analysis = better
        """
        # For now, simple metric: improvement in issue detection
        # TODO: Incorporate false positive rate and performance
        baseline_issues = baseline.get('avg_issues', 1)
        result_issues = result.get('issues_found', 0)
        
        if baseline_issues == 0:
            return 0.0
        
        improvement = (result_issues - baseline_issues) / baseline_issues
        
        # Penalize if analysis was much slower
        if elapsed > baseline.get('avg_analysis_time', 10) * 1.5:
            improvement -= 0.1
        
        return improvement
    
    def _check_for_promoted_strategies(self):
        """Check if any experiments have been promoted to production"""
        promoted = self.dreamer.get_promoted_experiments("analysis")
        
        if promoted and promoted[0].experiment_name != self.current_strategy:
            logger.info(f"🎉 Adopting promoted strategy: {promoted[0].experiment_name}")
            self.current_strategy = promoted[0].experiment_name
            # TODO: Actually implement strategy switching
