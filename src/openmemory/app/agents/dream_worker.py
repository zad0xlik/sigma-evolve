"""
Dream Worker - Generates creative code improvement proposals.

Production Mode: LLM-powered proposals based on analysis results
Experimental Mode: Novel proposal generation strategies, multi-agent reasoning
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging

from .base_worker import BaseWorker
from ..agent_config import get_agent_config
from ..models import Project, CodeSnapshot, Proposal
from ..database import get_db
from ..utils.categorization import get_openai_client
from ..utils.graphiti import get_graphiti_client_sync, search_decisions

logger = logging.getLogger(__name__)


class DreamWorker(BaseWorker):
    """Generates creative proposals for code improvements."""
    
    def __init__(self, db_session, dreamer, project_id=None):
        super().__init__(db_session, dreamer, project_id)
        self.project_id = project_id
        self.config = get_agent_config()
        self.current_strategy = "single_agent_proposals"
    
    def get_interval(self) -> int:
        """Dream runs every 4 minutes by default"""
        return self.config.workers.dream_interval
    
    def _production_cycle(self):
        """
        Production Mode: Generate proposals based on recent analysis
        
        Steps:
        1. Get latest code snapshot from Analysis Worker
        2. If issues found, generate improvement proposals using LLM
        3. Score proposals using confidence metrics
        4. Store proposals in DB with status='pending'
        5. Later, Think Worker will decide which to execute
        """
        try:
            # Check for promoted strategies
            self._check_for_promoted_strategies()
            
            # Get latest analysis results
            latest_snapshot = self._get_latest_snapshot()
            if not latest_snapshot:
                logger.info("No analysis results available for dreaming")
                return
            
            # Skip if no issues found
            if latest_snapshot.issues_found == 0:
                logger.info("No issues found in latest analysis, skipping proposals")
                return
            
            logger.info(f"Generating proposals for {latest_snapshot.issues_found} issues")
            
            # Generate proposals using LLM
            proposals = self._generate_proposals(latest_snapshot)
            
            # Store proposals
            for proposal_data in proposals:
                self._store_proposal(latest_snapshot.project_id, proposal_data)
            
            logger.info(f"Generated {len(proposals)} proposals")
            
        except Exception as e:
            logger.error(f"Production dreaming failed: {e}")
            raise
    
    def _experimental_cycle(self):
        """
        Experimental Mode: Try novel proposal generation strategies
        
        Experiments:
        - Multi-agent reasoning (architect + reviewer consensus)
        - Chain-of-thought prompting
        - Few-shot learning with successful past proposals
        - Temperature/creativity variations
        - Structured vs freeform proposal formats
        
        Metrics tracked:
        - Proposal quality (acceptance rate by Think Worker)
        - Execution success rate
        - Innovation score (novelty of approach)
        - Confidence calibration
        """
        try:
            latest_snapshot = self._get_latest_snapshot()
            if not latest_snapshot or latest_snapshot.issues_found == 0:
                return
            
            # Get baseline performance
            context = self._get_current_performance()
            
            # Ask DreamerMetaAgent for experimental approach
            experiment = self.dreamer.propose_experiment("dream", context)
            
            if not experiment:
                logger.info("No suitable experiment proposed")
                return
            
            logger.info(f"🧪 Starting experiment: {experiment['experiment_name']}")
            
            # Record experiment start
            exp_id = self.dreamer.record_experiment_start(
                worker_name="dream",
                experiment_name=experiment["experiment_name"],
                hypothesis=experiment["hypothesis"],
                approach=experiment["approach"]
            )
            
            # Execute experimental approach
            start_time = time.time()
            result = self._try_experimental_approach(
                latest_snapshot,
                experiment["approach"]
            )
            elapsed = time.time() - start_time
            
            # Calculate improvement vs baseline
            improvement = self._calculate_improvement(result, context)
            
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
            
        except Exception as e:
            logger.error(f"Experimental dreaming failed: {e}")
    
    def _get_latest_snapshot(self) -> Optional[CodeSnapshot]:
        """Get the most recent code analysis snapshot"""
        return self.db.query(CodeSnapshot)\
            .order_by(CodeSnapshot.created_at.desc())\
            .first()
    
    def _generate_proposals(self, snapshot: CodeSnapshot) -> List[Dict]:
        """
        Generate code improvement proposals using LLM
        
        Returns list of proposals, each containing:
            {
                'title': str,
                'description': str,
                'agents': Dict,  # Multi-agent committee scores
                'changes': Dict,  # Proposed code changes
                'confidence': float,
                'critic_score': float
            }
        """
        # Parse issues from snapshot metrics
        metrics = json.loads(snapshot.metrics_json)
        issues = metrics.get('issues', [])
        
        if not issues:
            return []
        
        proposals = []
        
        # Group issues by severity
        error_issues = [i for i in issues if i.get('severity') == 'error']
        warning_issues = [i for i in issues if i.get('severity') == 'warning']
        
        # Generate proposals for errors (high priority)
        if error_issues:
            proposal = self._generate_error_fix_proposal(error_issues, snapshot)
            if proposal:
                proposals.append(proposal)
        
        # Generate proposals for warnings (lower priority)
        if warning_issues and len(warning_issues) <= 10:  # Batch small warning sets
            proposal = self._generate_warning_fix_proposal(warning_issues, snapshot)
            if proposal:
                proposals.append(proposal)
        
        # Generate refactoring proposals if complexity is high
        if snapshot.complexity > 10:
            proposal = self._generate_refactoring_proposal(snapshot)
            if proposal:
                proposals.append(proposal)
        
        # Broadcast proposal quality metrics
        if proposals:
            avg_confidence = sum(p['confidence'] for p in proposals) / len(proposals)
            
            self._broadcast_knowledge(
                knowledge_type='proposal_quality',
                content={
                    'proposal_count': len(proposals),
                    'avg_confidence': avg_confidence,
                    'issue_count': snapshot.issues_found,
                    'change_types': list(set(p['changes']['change_type'] for p in proposals))
                },
                urgency='low'
            )
        
        return proposals
    
    def _generate_error_fix_proposal(self, issues: List[Dict], snapshot: CodeSnapshot) -> Optional[Dict]:
        """Generate proposal to fix error-level issues using LLM with Graphiti knowledge"""
        try:
            # Get project details
            project = self.db.query(Project).filter(Project.project_id == snapshot.project_id).first()
            if not project:
                logger.error(f"Project {snapshot.project_id} not found")
                return None
            
            # Limit to top 5 most critical issues
            top_issues = issues[:5]
            
            # Read affected file contents
            file_contents = self._read_affected_files(project.workspace_path, top_issues)
            
            # Query Graphiti for successful fix patterns
            historical_context = self._query_historical_fix_patterns(top_issues)
            
            # Build LLM prompt with historical context
            system_prompt = """You are an expert software engineer specialized in fixing code issues.
Your task is to analyze code issues and generate specific code fixes, learning from historical patterns.

Respond with a JSON object containing:
{
  "title": "Brief title for the fix",
  "description": "Detailed explanation of what will be fixed and why",
  "confidence": 0.0-1.0,
  "changes": [
    {
      "file": "path/to/file.py",
      "original": "code to be replaced",
      "fixed": "corrected code",
      "explanation": "why this fixes the issue"
    }
  ],
  "testing_strategy": "How to verify the fix works",
  "historical_lessons": "What was learned from similar past fixes"
}"""
            
            user_prompt = f"""Project: {project.repo_url}
Language: {project.language}
Framework: {project.framework or 'N/A'}

Critical Issues to Fix:
"""
            for issue in top_issues:
                user_prompt += f"\n{issue['file']}:{issue['line']} - {issue['message']}\n"
                if issue['file'] in file_contents:
                    lines = file_contents[issue['file']].split('\n')
                    start = max(0, issue['line'] - 5)
                    end = min(len(lines), issue['line'] + 5)
                    context = '\n'.join(f"{i+1}: {line}" for i, line in enumerate(lines[start:end], start=start))
                    user_prompt += f"Context:\n```\n{context}\n```\n"
            
            # Add historical knowledge if available
            if historical_context.get('successful_patterns'):
                user_prompt += "\n\nHistorical Context from Similar Fixes:\n"
                for pattern in historical_context['successful_patterns'][:3]:
                    user_prompt += f"- {pattern}\n"
            
            if historical_context.get('pitfalls'):
                user_prompt += "\n\nCommon Pitfalls to Avoid:\n"
                for pitfall in historical_context['pitfalls'][:3]:
                    user_prompt += f"- {pitfall}\n"
            
            user_prompt += "\n\nGenerate specific code fixes for these issues, considering historical patterns."
            
            # Call LLM
            llm = get_openai_client()
            model = os.getenv("MODEL", "gpt-4o-mini")
            
            response = llm.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2500
            )
            
            # Parse response
            content = response.choices[0].message.content
            
            # Extract JSON from markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            # Adjust confidence based on historical success rate
            historical_success_rate = historical_context.get('success_rate', 0.5)
            base_confidence = float(result.get('confidence', 0.85))
            
            # Increase confidence if historical success is high, decrease if low
            if historical_success_rate > 0.7:
                adjusted_confidence = min(base_confidence + 0.1, 0.95)
            elif historical_success_rate < 0.3:
                adjusted_confidence = max(base_confidence - 0.1, 0.5)
            else:
                adjusted_confidence = base_confidence
            
            # Build committee scores
            agents = {
                'architect': 0.85,
                'reviewer': 0.80,
                'tester': 0.90,
                'security': 0.75,
                'optimizer': 0.70
            }
            
            return {
                'title': result.get('title', f"Fix {len(issues)} Critical Error(s)"),
                'description': result.get('description', ''),
                'agents': agents,
                'changes': {
                    'files_affected': list(set(i['file'] for i in top_issues)),
                    'change_type': 'bug_fix',
                    'code_changes': result.get('changes', []),
                    'testing_strategy': result.get('testing_strategy', ''),
                    'historical_lessons': result.get('historical_lessons', '')
                },
                'confidence': adjusted_confidence,
                'critic_score': 0.80
            }
            
        except Exception as e:
            logger.error(f"Failed to generate LLM proposal for errors: {e}")
            # Fall back to simple placeholder
            issue_summary = "\n".join([
                f"- {issue['file']}:{issue['line']}: {issue['message']}"
                for issue in issues[:5]
            ])
            return {
                'title': f"Fix {len(issues)} Critical Error(s)",
                'description': f"Resolve the following critical errors:\n{issue_summary}",
                'agents': {'architect': 0.85, 'reviewer': 0.80, 'tester': 0.90, 'security': 0.75, 'optimizer': 0.70},
                'changes': {'files_affected': list(set(i['file'] for i in issues)), 'change_type': 'bug_fix'},
                'confidence': 0.75,
                'critic_score': 0.70
            }
    
    def _generate_warning_fix_proposal(self, issues: List[Dict], snapshot: CodeSnapshot) -> Optional[Dict]:
        """Generate proposal to fix warning-level issues using LLM"""
        try:
            # Get project details
            project = self.db.query(Project).filter(Project.project_id == snapshot.project_id).first()
            if not project:
                logger.error(f"Project {snapshot.project_id} not found")
                return None
            
            # Limit to reasonable batch size
            top_issues = issues[:10]
            
            # Read affected file contents
            file_contents = self._read_affected_files(project.workspace_path, top_issues)
            
            # Build LLM prompt
            system_prompt = """You are an expert software engineer specialized in code quality improvements.
Your task is to analyze code warnings and suggest improvements.

Respond with a JSON object containing:
{
  "title": "Brief title for the improvements",
  "description": "Detailed explanation of what will be improved",
  "confidence": 0.0-1.0,
  "changes": [
    {
      "file": "path/to/file.py",
      "original": "code to be improved",
      "improved": "better code",
      "explanation": "why this is better"
    }
  ],
  "testing_strategy": "How to verify improvements don't break anything"
}"""
            
            user_prompt = f"""Project: {project.repo_url}
Language: {project.language}
Framework: {project.framework or 'N/A'}

Code Quality Warnings to Address:
"""
            for issue in top_issues:
                user_prompt += f"\n{issue['file']}:{issue['line']} - {issue['message']}\n"
                if issue['file'] in file_contents:
                    lines = file_contents[issue['file']].split('\n')
                    start = max(0, issue['line'] - 3)
                    end = min(len(lines), issue['line'] + 3)
                    context = '\n'.join(f"{i+1}: {line}" for i, line in enumerate(lines[start:end], start=start))
                    user_prompt += f"Context:\n```\n{context}\n```\n"
            
            user_prompt += "\nGenerate code improvements for these warnings."
            
            # Call LLM
            llm = get_openai_client()
            model = os.getenv("MODEL", "gpt-4o-mini")
            
            response = llm.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            agents = {
                'architect': 0.70,
                'reviewer': 0.85,
                'tester': 0.75,
                'security': 0.65,
                'optimizer': 0.80
            }
            
            return {
                'title': result.get('title', f"Address {len(issues)} Code Warning(s)"),
                'description': result.get('description', ''),
                'agents': agents,
                'changes': {
                    'files_affected': list(set(i['file'] for i in top_issues)),
                    'change_type': 'code_quality',
                    'code_changes': result.get('changes', []),
                    'testing_strategy': result.get('testing_strategy', '')
                },
                'confidence': float(result.get('confidence', 0.75)),
                'critic_score': 0.70
            }
            
        except Exception as e:
            logger.error(f"Failed to generate LLM proposal for warnings: {e}")
            issue_summary = "\n".join([f"- {issue['file']}:{issue['line']}: {issue['message']}" for issue in issues[:5]])
            return {
                'title': f"Address {len(issues)} Code Warning(s)",
                'description': f"Improve code quality by addressing:\n{issue_summary}",
                'agents': {'architect': 0.70, 'reviewer': 0.85, 'tester': 0.75, 'security': 0.65, 'optimizer': 0.80},
                'changes': {'files_affected': list(set(i['file'] for i in issues)), 'change_type': 'code_quality'},
                'confidence': 0.70,
                'critic_score': 0.65
            }
    
    def _generate_refactoring_proposal(self, snapshot: CodeSnapshot) -> Optional[Dict]:
        """Generate proposal to refactor complex code"""
        return {
            'title': f"Refactor High Complexity Code",
            'description': f"Current average complexity: {snapshot.complexity:.2f}. "
                          f"Refactor to reduce complexity and improve maintainability.",
            'agents': {
                'architect': 0.90,
                'reviewer': 0.75,
                'tester': 0.80,
                'security': 0.70,
                'optimizer': 0.95
            },
            'changes': {
                'files_affected': [],  # Would be determined from analysis
                'change_type': 'refactoring',
                'estimated_lines': 50
            },
            'confidence': 0.70,
            'critic_score': 0.75
        }
    
    def _store_proposal(self, project_id: int, proposal_data: Dict):
        """Store proposal in database"""
        # Calculate weighted confidence from agent committee
        agents = proposal_data['agents']
        committee_config = self.config.committee

        weighted_confidence = (
            agents['architect'] * committee_config.weights['architect'] +
            agents['reviewer'] * committee_config.weights['reviewer'] +
            agents['tester'] * committee_config.weights['tester'] +
            agents['security'] * committee_config.weights['security'] +
            agents['optimizer'] * committee_config.weights['optimizer']
        )
        
        proposal = Proposal(
            project_id=project_id,
            title=proposal_data['title'],
            description=proposal_data['description'],
            agents_json=json.dumps(proposal_data['agents']),
            changes_json=json.dumps(proposal_data['changes']),
            confidence=weighted_confidence,
            critic_score=proposal_data['critic_score'],
            status='pending',
            created_at=datetime.now()
        )
        
        self.db.add(proposal)
        self.db.commit()
        
        logger.info(f"Stored proposal: '{proposal.title}' (confidence={weighted_confidence:.2f})")
    
    def _get_experiment_context(self) -> Dict:
        """Get context for experiment proposal"""
        return self._get_current_performance()
    
    def _get_current_performance(self) -> Dict:
        """Get recent performance metrics for experiment baseline"""
        # Get recent proposals
        recent_proposals = self.db.query(Proposal)\
            .order_by(Proposal.created_at.desc())\
            .limit(20)\
            .all()
        
        if not recent_proposals:
            return {
                'avg_confidence': 0.75,
                'acceptance_rate': 0.60,
                'execution_success_rate': 0.70,
                'avg_proposals_per_run': 2.0,
                'current_strategy': self.current_strategy
            }
        
        # Calculate metrics
        executed = [p for p in recent_proposals if p.status == 'executed']
        approved = [p for p in recent_proposals if p.status in ['approved', 'executed']]
        
        return {
            'avg_confidence': sum(p.confidence for p in recent_proposals) / len(recent_proposals),
            'acceptance_rate': len(approved) / len(recent_proposals) if recent_proposals else 0.0,
            'execution_success_rate': len(executed) / max(len(approved), 1),
            'avg_proposals_per_run': len(recent_proposals) / 10,  # Last 10 runs
            'current_strategy': self.current_strategy
        }
    
    def _try_experimental_approach(self, snapshot: CodeSnapshot, approach: str) -> Dict:
        """
        Execute experimental proposal generation approach
        
        Could try:
        - Different prompting strategies
        - Multi-agent reasoning
        - Few-shot learning
        - Different LLM models/temperatures
        """
        # For now, just run standard generation
        proposals = self._generate_proposals(snapshot)
        
        return {
            'proposals_generated': len(proposals),
            'avg_confidence': sum(p['confidence'] for p in proposals) / max(len(proposals), 1),
            'proposal_quality_score': 0.75  # Would be determined by Think Worker acceptance
        }
    
    def _calculate_improvement(self, result: Dict, baseline: Dict) -> float:
        """
        Calculate improvement percentage over baseline
        
        Factors:
        - Higher confidence proposals = better
        - More proposals generated = better (up to a point)
        - Better acceptance rate = better (requires tracking)
        """
        result_confidence = result.get('avg_confidence', 0.75)
        baseline_confidence = baseline.get('avg_confidence', 0.75)
        
        confidence_improvement = (result_confidence - baseline_confidence) / max(baseline_confidence, 0.1)
        
        # Bonus for generating more proposals (but diminishing returns)
        result_count = result.get('proposals_generated', 2)
        baseline_count = baseline.get('avg_proposals_per_run', 2)
        count_improvement = (result_count - baseline_count) / max(baseline_count, 1)
        count_improvement = min(count_improvement, 0.5)  # Cap at 50% bonus
        
        total_improvement = confidence_improvement * 0.7 + count_improvement * 0.3
        
        return total_improvement
    
    def _check_for_promoted_strategies(self):
        """Check if any experiments have been promoted to production"""
        promoted = self.dreamer.get_promoted_experiments("dream")

        if promoted and promoted[0]["experiment_name"] != self.current_strategy:
            logger.info(f"🎉 Adopting promoted strategy: {promoted[0]['experiment_name']}")
            self.current_strategy = promoted[0]["experiment_name"]
            # TODO: Actually implement strategy switching
    
    def _read_affected_files(self, workspace_path: str, issues: List[Dict]) -> Dict[str, str]:
        """
        Read the contents of files affected by issues.
        
        Args:
            workspace_path: Path to project workspace
            issues: List of issues with 'file' keys
        
        Returns:
            Dict mapping file paths to their contents
        """
        file_contents = {}
        unique_files = set(issue['file'] for issue in issues)
        
        for file_path in unique_files:
            try:
                full_path = Path(workspace_path) / file_path
                if full_path.exists() and full_path.is_file():
                    with open(full_path, 'r', encoding='utf-8') as f:
                        file_contents[file_path] = f.read()
                    logger.debug(f"Read file: {file_path}")
                else:
                    logger.warning(f"File not found: {full_path}")
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
        
        return file_contents
    
    def _query_historical_fix_patterns(self, issues: List[Dict]) -> Dict:
        """
        Query Graphiti for successful fix patterns and historical context
        
        Returns:
            Dict with successful patterns, pitfalls, and success rate
        """
        try:
            client = get_graphiti_client_sync()
            
            if not client:
                logger.debug("Graphiti client not available, skipping historical patterns query")
                return {
                    'successful_patterns': [],
                    'pitfalls': [],
                    'success_rate': 0.5
                }
            
            # Build search queries based on issue types
            search_queries = []
            for issue in issues[:3]:  # Limit to top 3 issues
                message = issue.get('message', '').lower()
                
                if 'syntax error' in message:
                    search_queries.append('syntax error fix pattern')
                elif 'type hint' in message:
                    search_queries.append('type hint addition pattern')
                elif 'mutable default' in message:
                    search_queries.append('mutable default argument pattern')
                elif 'bare except' in message:
                    search_queries.append('bare except clause pattern')
            
            if not search_queries:
                # Generic search for bug fixes
                search_queries.append('bug fix pattern')
            
            import asyncio
            
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Search for patterns
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
            
            # Analyze results
            successful_patterns = []
            pitfalls = []
            success_count = 0
            total_count = len(all_results)
            
            for result in all_results:
                fact = result.get('fact', '').lower()
                
                # Classify as success or pitfall
                if 'success' in fact or 'worked' in fact or 'effective' in fact:
                    successful_patterns.append(result.get('fact', ''))
                    success_count += 1
                elif 'failed' in fact or 'error' in fact or 'bug' in fact:
                    pitfalls.append(result.get('fact', ''))
            
            success_rate = success_count / total_count if total_count > 0 else 0.5
            
            logger.info(
                f"Historical fix pattern query complete: "
                f"found {total_count} patterns, "
                f"success_rate={success_rate:.1%}"
            )
            
            return {
                'successful_patterns': successful_patterns,
                'pitfalls': pitfalls,
                'success_rate': success_rate
            }
            
        except Exception as e:
            logger.error(f"Error querying historical fix patterns: {e}")
            return {
                'successful_patterns': [],
                'pitfalls': [],
                'success_rate': 0.5
            }
