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
from ..log_broadcaster import broadcast_worker_log
from ..utils.graphiti import get_graphiti_client_sync, search_decisions

logger = logging.getLogger(__name__)


class AnalysisWorker(BaseWorker):
    """Analyzes code quality, complexity metrics, and potential issues."""
    
    def __init__(self, db_session, dreamer, project_id=None):
        super().__init__(db_session, dreamer, project_id)
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
                broadcast_worker_log("analysis", "warning", "⚠️ No project configured for analysis")
                return
            
            logger.info(f"Analyzing project: {project.workspace_path}")
            broadcast_worker_log(
                "analysis",
                "info",
                f"📊 Analyzing project: {Path(project.workspace_path).name}",
                {"workspace": project.workspace_path, "project_id": project.project_id}
            )
            
            # Check if promoted experiments exist
            self._check_for_promoted_strategies()
            
            # Run analysis using current production strategy
            snapshot = self._analyze_codebase(project.workspace_path, project.language)
            
            # Store results
            self._store_snapshot(project.project_id, snapshot)
            
            logger.info(f"Analysis complete: complexity={snapshot['complexity']:.2f}, "
                       f"issues={snapshot['issues_found']}")
            broadcast_worker_log(
                "analysis",
                "info",
                f"✅ Analysis complete",
                {
                    "complexity": round(snapshot['complexity'], 2),
                    "maintainability": round(snapshot['maintainability'], 2),
                    "issues_found": snapshot['issues_found'],
                    "files_analyzed": snapshot['files_analyzed'],
                    "lines_of_code": snapshot['lines_of_code']
                }
            )
            
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
                broadcast_worker_log("analysis", "warning", "⚠️ No suitable experiment proposed by Dreamer")
                return
            
            logger.info(f"🧪 Starting experiment: {experiment['experiment_name']}")
            broadcast_worker_log(
                "analysis",
                "experiment",
                f"🧪 Experiment: {experiment['experiment_name']}",
                {"approach": experiment.get("approach", "unknown")}
            )
            
            # Record experiment start
            exp_id = self.dreamer.record_experiment_start(
                worker_name="analysis",
                experiment=experiment,
                project_id=self.project_id
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
                outcome={
                    "success": improvement > 0,
                    "improvement": improvement,
                    "result_metrics": result,
                    "baseline_metrics": context,
                    "elapsed_time": elapsed
                }
            )
            
            logger.info(f"Experiment complete: improvement={improvement:.2%}")
            
            if improvement > 0:
                broadcast_worker_log(
                    "analysis",
                    "experiment",
                    f"🎉 Experiment success! Improvement: {improvement:.1%}",
                    {"improvement": improvement, "elapsed": f"{elapsed:.2f}s"}
                )
            else:
                broadcast_worker_log(
                    "analysis",
                    "experiment",
                    f"📉 Experiment showed no improvement: {improvement:.1%}",
                    {"improvement": improvement}
                )
            
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
        if language.lower() != "python":
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
        
        snapshot = {
            'complexity': avg_complexity,
            'maintainability': avg_maintainability,
            'test_coverage': 0.0,  # TODO: integrate with pytest-cov
            'issues_found': len(issues),
            'files_analyzed': analyzed_files,
            'lines_of_code': total_loc,
            'issues': issues
        }
        
        # Broadcast issue patterns if found
        if snapshot['issues_found'] > 0:
            issue_types = {}
            for issue in snapshot.get('issues', []):
                # Extract issue type from message
                message = issue['message'].lower()
                if 'mutable default' in message:
                    issue_type = 'mutable_default'
                elif 'bare except' in message:
                    issue_type = 'bare_except'
                elif 'type hint' in message:
                    issue_type = 'missing_type_hint'
                else:
                    issue_type = 'other'
                
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
            
            # Broadcast aggregated issue patterns
            for issue_type, count in issue_types.items():
                if count >= 3:  # Only broadcast common patterns
                    self._broadcast_knowledge(
                        knowledge_type='issue_pattern',
                        content={
                            'issue_type': issue_type,
                            'count': count,
                            'severity': issue.get('severity', 'warning'),
                            'files_affected': list(set(i['file'] for i in snapshot['issues']))
                        },
                        urgency='low'
                    )
        
        # Broadcast complexity trend if high
        if snapshot['complexity'] > 12:
            self._broadcast_knowledge(
                knowledge_type='complexity_trend',
                content={
                    'current_complexity': snapshot['complexity'],
                    'threshold': 12,
                    'files_analyzed': snapshot['files_analyzed']
                },
                urgency='medium'
            )
        
        return snapshot
    
    def _detect_issues(self, tree: ast.AST, filepath: Path, code: str) -> List[Dict]:
        """Detect common code issues using AST analysis, enhanced with Graphiti knowledge"""
        issues = []
        
        # Query Graphiti for historical issue patterns and their outcomes
        graphiti_context = self._query_issue_history(str(filepath))
        
        for node in ast.walk(tree):
            # Check for missing type hints on functions
            if isinstance(node, ast.FunctionDef):
                if node.returns is None and node.name not in ['__init__', '__str__']:
                    # Assess severity based on historical data
                    severity = self._assess_issue_severity(
                        'missing_type_hint',
                        graphiti_context,
                        filepath,
                        node.lineno
                    )
                    
                    issues.append({
                        'file': str(filepath),
                        'line': node.lineno,
                        'severity': severity,
                        'message': f"Function '{node.name}' missing return type hint"
                    })
            
            # Check for bare except clauses
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    severity = self._assess_issue_severity(
                        'bare_except',
                        graphiti_context,
                        filepath,
                        node.lineno
                    )
                    
                    issues.append({
                        'file': str(filepath),
                        'line': node.lineno,
                        'severity': severity,
                        'message': 'Bare except clause - should specify exception type'
                    })
            
            # Check for mutable default arguments
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        severity = self._assess_issue_severity(
                            'mutable_default',
                            graphiti_context,
                            filepath,
                            node.lineno
                        )
                        
                        issues.append({
                            'file': str(filepath),
                            'line': node.lineno,
                            'severity': severity,
                            'message': f"Function '{node.name}' has mutable default argument"
                        })
        
        # Learn from analysis results
        if issues:
            self._learn_from_issues(issues, filepath, graphiti_context)
        
        return issues
    
    def _query_issue_history(self, filepath: str) -> Dict:
        """
        Query Graphiti knowledge graph for historical issue patterns
        
        Returns:
            Dict with issue patterns, severity ratings, and outcomes
        """
        try:
            client = get_graphiti_client_sync()
            
            if not client:
                logger.debug("Graphiti client not available, skipping issue history query")
                return {
                    'issue_patterns': [],
                    'severity_map': {},
                    'outcome_stats': {},
                    'query_status': 'unavailable'
                }
            
            # Build search query for issues in this file or similar files
            import asyncio
            
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Search for issues in similar contexts
            search_queries = [
                f"issue in {Path(filepath).name}",
                "mutable default argument",
                "bare except clause",
                "missing type hint"
            ]
            
            all_results = []
            for query in search_queries:
                try:
                    results = loop.run_until_complete(
                        search_decisions(
                            query=query,
                            limit=5
                        )
                    )
                    all_results.extend(results)
                except Exception as e:
                    logger.debug(f"Query failed for '{query}': {e}")
            
            # Analyze results to build severity map and outcome stats
            severity_map = {}
            outcome_stats = {}
            
            for result in all_results:
                fact = result.get('fact', '').lower()
                
                # Extract issue type and severity
                if 'error' in fact or 'critical' in fact:
                    issue_type = self._extract_issue_type(fact)
                    if issue_type:
                        severity_map[issue_type] = 'error'
                elif 'warning' in fact or 'moderate' in fact:
                    issue_type = self._extract_issue_type(fact)
                    if issue_type:
                        severity_map[issue_type] = 'warning'
                elif 'info' in fact or 'minor' in fact:
                    issue_type = self._extract_issue_type(fact)
                    if issue_type:
                        severity_map[issue_type] = 'info'
                
                # Track outcomes
                if 'failed' in fact or 'bug' in fact:
                    issue_type = self._extract_issue_type(fact)
                    if issue_type:
                        outcome_stats[issue_type] = outcome_stats.get(issue_type, {'fail': 0, 'success': 0})
                        outcome_stats[issue_type]['fail'] += 1
                elif 'fixed' in fact or 'resolved' in fact:
                    issue_type = self._extract_issue_type(fact)
                    if issue_type:
                        outcome_stats[issue_type] = outcome_stats.get(issue_type, {'fail': 0, 'success': 0})
                        outcome_stats[issue_type]['success'] += 1
            
            logger.info(
                f"Issue history query complete: "
                f"found {len(all_results)} historical issues, "
                f"{len(severity_map)} issue types mapped"
            )
            
            return {
                'issue_patterns': all_results,
                'severity_map': severity_map,
                'outcome_stats': outcome_stats,
                'query_status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error querying issue history: {e}")
            return {
                'issue_patterns': [],
                'severity_map': {},
                'outcome_stats': {},
                'query_status': 'error',
                'error': str(e)
            }
    
    def _assess_issue_severity(self, issue_type: str, graphiti_context: Dict, filepath: Path, lineno: int) -> str:
        """
        Assess issue severity based on historical data from Graphiti
        
        Factors:
        - Historical severity for this issue type
        - Failure rate of similar issues
        - Context (file type, project)
        """
        severity_map = graphiti_context.get('severity_map', {})
        outcome_stats = graphiti_context.get('outcome_stats', {})
        
        # Default severity
        default_severity = 'warning'
        
        # Override based on historical data
        if issue_type in severity_map:
            historical_severity = severity_map[issue_type]
            # If historically this was an error, keep it as error
            # If historically this was a warning, keep it as warning
            return historical_severity
        
        # Check failure rate for this issue type
        if issue_type in outcome_stats:
            stats = outcome_stats[issue_type]
            total = stats['fail'] + stats['success']
            if total > 0:
                failure_rate = stats['fail'] / total
                if failure_rate > 0.5:
                    # More than 50% failure rate - escalate severity
                    return 'error'
                elif failure_rate > 0.3:
                    # 30-50% failure rate - keep as warning
                    return 'warning'
        
        # Check if this is a known problematic file or pattern
        filepath_str = str(filepath)
        if any(pattern in filepath_str for pattern in ['test', 'spec']):
            # Test files are less critical
            return 'info'
        
        return default_severity
    
    def _extract_issue_type(self, fact_text: str) -> Optional[str]:
        """Extract issue type from fact text"""
        fact_lower = fact_text.lower()
        
        if 'mutable default' in fact_lower:
            return 'mutable_default'
        elif 'bare except' in fact_lower:
            return 'bare_except'
        elif 'type hint' in fact_lower or 'missing type' in fact_lower:
            return 'missing_type_hint'
        elif 'syntax error' in fact_lower:
            return 'syntax_error'
        elif 'unused import' in fact_lower:
            return 'unused_import'
        elif 'long function' in fact_lower or 'complex function' in fact_lower:
            return 'complex_function'
        
        return None
    
    def _learn_from_issues(self, issues: List[Dict], filepath: Path, graphiti_context: Dict):
        """
        Learn from detected issues and store knowledge in Graphiti
        
        This helps build a knowledge base of which issues lead to problems
        """
        try:
            client = get_graphiti_client_sync()
            
            if not client:
                logger.debug("Graphiti client not available, skipping issue learning")
                return
            
            # Categorize issues by type and severity
            issue_counts = {}
            for issue in issues:
                # Extract issue type from message
                message = issue['message'].lower()
                if 'mutable default' in message:
                    issue_type = 'mutable_default'
                elif 'bare except' in message:
                    issue_type = 'bare_except'
                elif 'type hint' in message:
                    issue_type = 'missing_type_hint'
                else:
                    issue_type = 'other'
                
                severity = issue['severity']
                issue_counts[issue_type] = issue_counts.get(issue_type, {'error': 0, 'warning': 0, 'info': 0})
                issue_counts[issue_type][severity] += 1
            
            # Store learning in Graphiti (would require a store_facts function)
            # For now, log what we would store
            for issue_type, counts in issue_counts.items():
                total = sum(counts.values())
                logger.debug(
                    f"Learned about {issue_type}: {total} instances "
                    f"(errors: {counts.get('error', 0)}, warnings: {counts.get('warning', 0)})"
                )
            
            # Log comprehensive analysis summary
            logger.info(
                f"Issue analysis learned: {len(issue_counts)} issue types, "
                f"{len(issues)} total issues detected"
            )
            
        except Exception as e:
            logger.error(f"Error learning from issues: {e}")
    
    def _store_analysis_in_graphiti(self, snapshot: Dict, project: Project):
        """
        Store analysis results in Graphiti knowledge graph
        
        This helps track code quality trends and patterns over time
        """
        try:
            client = get_graphiti_client_sync()
            
            if not client:
                logger.debug("Graphiti client not available, skipping analysis storage")
                return
            
            # Create facts about analysis results
            facts = []
            
            # Overall metrics
            if snapshot['complexity'] > 15:
                facts.append(f"High complexity detected in {project.project_name}: {snapshot['complexity']:.1f}")
            elif snapshot['complexity'] > 10:
                facts.append(f"Moderate complexity in {project.project_name}: {snapshot['complexity']:.1f}")
            
            if snapshot['issues_found'] > 50:
                facts.append(f"Many issues found in {project.project_name}: {snapshot['issues_found']}")
            
            # Issue type breakdown
            for issue in snapshot.get('issues', [])[:10]:  # Limit to first 10
                issue_type = issue['severity']
                facts.append(f"{issue_type} issue in {project.project_name}: {issue['message'][:100]}")
            
            # Store in Graphiti (would require a store_facts function)
            for fact in facts:
                logger.debug(f"Would store fact in Graphiti: {fact}")
            
            logger.info(f"Would store {len(facts)} analysis facts in Graphiti")
            
        except Exception as e:
            logger.error(f"Error storing analysis in Graphiti: {e}")
    
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
        project = self.db.get(Project, project_id)
        if project:
            project.last_analyzed = datetime.now()
            self.db.commit()
    
    def _get_experiment_context(self) -> Dict:
        """Get context for experiment proposal"""
        return self._get_current_performance()
    
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
        
        if promoted and promoted[0]["experiment_name"] != self.current_strategy:
            logger.info(f"🎉 Adopting promoted strategy: {promoted[0]['experiment_name']}")
            broadcast_worker_log(
                "analysis",
                "info",
                f"🎉 Adopting new strategy: {promoted[0]['experiment_name']}",
                {"old_strategy": self.current_strategy, "new_strategy": promoted[0]["experiment_name"]}
            )
            self.current_strategy = promoted[0]["experiment_name"]
            # TODO: Actually implement strategy switching
