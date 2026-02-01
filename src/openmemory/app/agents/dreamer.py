"""
DreamerMetaAgent

The "dreaming gene" that all workers inherit. Orchestrates experimentation,
learning, and evolution across the entire agent system.

This is the core innovation of SIGMA - enabling autonomous improvement.
"""
import json
import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.sql import func

from ..agent_config import get_agent_config
from ..database import get_db
from ..utils.categorization import get_openai_client


logger = logging.getLogger("sigma.dreamer")


def utc_now() -> str:
    """Get current UTC timestamp as ISO string"""
    return datetime.now(timezone.utc).isoformat()


class DreamerMetaAgent:
    """
    Meta-agent that orchestrates experimentation and learning.
    
    Each worker inherits this capability, allowing the entire system to:
    - Propose novel experiments
    - Track outcomes (success/failure)
    - Promote successful approaches to production
    - Share learnings across workers and projects
    
    The evolution rate (default 15%) determines how often workers experiment
    vs execute their production logic.
    """
    
    def __init__(self):
        self.config = get_agent_config()
        self.evolution_rate = self.config.workers.dream_evolution_rate
        self.experiment_confidence_threshold = self.config.workers.experiment_confidence_threshold
        
        # In-memory caches for performance
        self.successful_patterns: List[Dict[str, Any]] = []
        self.failed_patterns: List[Dict[str, Any]] = []
        self._load_recent_patterns()
        
        logger.info(f"DreamerMetaAgent initialized (evolution_rate={self.evolution_rate})")
    
    def _load_recent_patterns(self):
        """Load recent experiment outcomes from database"""
        try:
            db = next(get_db())
            
            # Load recent successes
            success_rows = db.execute(text("""
                SELECT * FROM experiments 
                WHERE success = TRUE 
                ORDER BY completed_at DESC 
                LIMIT 10
            """)).fetchall()
            
            self.successful_patterns = [
                {
                    "worker_name": row[1],  # worker_name column
                    "experiment_name": row[2],  # experiment_name column
                    "approach": row[4],  # approach column
                    "improvement": row[11],  # improvement column
                    "completed_at": row[10],  # completed_at column
                }
                for row in success_rows
            ]
            
            # Load recent failures
            failure_rows = db.execute(text("""
                SELECT * FROM experiments 
                WHERE success = FALSE 
                ORDER BY completed_at DESC 
                LIMIT 10
            """)).fetchall()
            
            self.failed_patterns = [
                {
                    "worker_name": row[1],  # worker_name column
                    "experiment_name": row[2],  # experiment_name column
                    "approach": row[4],  # approach column
                    "completed_at": row[10],  # completed_at column
                }
                for row in failure_rows
            ]
            
            logger.info(f"Loaded {len(self.successful_patterns)} successes, {len(self.failed_patterns)} failures")
            
        except Exception as e:
            logger.error(f"Failed to load patterns: {e}")
    
    def should_experiment(self) -> bool:
        """
        Decide if this cycle should be experimental.
        
        Returns True ~15% of the time (configurable via evolution_rate)
        """
        return random.random() < self.evolution_rate
    
    def propose_experiment(self, worker_name: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate an experimental approach using LLM.
        
        Args:
            worker_name: Name of the worker requesting experiment
            context: Current context (metrics, recent outcomes, etc.)
        
        Returns:
            Experiment specification or None if generation fails
        """
        try:
            llm = get_openai_client()
            
            # Build prompt for experiment generation
            system = f"""You are the Dreamer for the {worker_name} worker in SIGMA - a self-evolving agent system.

Your role is to propose novel experimental approaches that could improve the worker's performance.

Guidelines:
1. Experiments should be SAFE to try (won't break existing functionality)
2. Must have MEASURABLE outcomes
3. Should have a clear ROLLBACK plan
4. Balance innovation with risk
5. Learn from past successes and failures

Respond in JSON format:
{{
  "experiment_name": "descriptive name",
  "hypothesis": "what you think will happen",
  "approach": "detailed implementation steps",
  "metrics": ["metric1", "metric2"],
  "risk_level": "low|medium|high",
  "rollback_plan": "how to undo if it fails",
  "confidence": 0.0-1.0
}}"""
            
            user = f"""Worker: {worker_name}

Current Context:
{json.dumps(context, indent=2)}

Recent Successes (learn from these):
{json.dumps(self.successful_patterns[:3], indent=2) if self.successful_patterns else "None yet"}

Recent Failures (avoid these):
{json.dumps(self.failed_patterns[:3], indent=2) if self.failed_patterns else "None yet"}

Propose an experiment that could improve {worker_name}'s performance. Be creative but practical."""
            
            # Call LLM
            response = llm.chat.completions.create(
                model=self.config.workers.model if hasattr(self.config.workers, 'model') else "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=0.8,  # Higher temperature for creativity
                max_tokens=1000
            )
            
            # Parse JSON response
            content = response.choices[0].message.content
            
            # Try to extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            experiment = json.loads(content)
            
            # Validate required fields
            required = ["experiment_name", "hypothesis", "approach", "metrics", "risk_level", "rollback_plan"]
            if not all(field in experiment for field in required):
                logger.error(f"Invalid experiment proposal: missing required fields")
                return None
            
            # Check confidence threshold
            confidence = float(experiment.get("confidence", 0.5))
            if confidence < self.experiment_confidence_threshold:
                logger.info(f"Experiment confidence {confidence} below threshold {self.experiment_confidence_threshold}")
                return None
            
            logger.info(f"Proposed experiment for {worker_name}: {experiment['experiment_name']}")
            return experiment
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse experiment JSON: {e}")
            logger.debug(f"Response content: {content if 'content' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"Failed to propose experiment: {e}")
            return None
    
    def record_experiment_start(
        self,
        worker_name: str,
        experiment_name: Optional[str] = None,
        experiment: Optional[Dict[str, Any]] = None,
        hypothesis: Optional[str] = None,
        approach: Optional[str] = None,
        project_id: Optional[int] = None
    ) -> int:
        """
        Record experiment start in database.
        
        Supports both dict-based and keyword argument styles for backwards compatibility.
        
        Returns:
            experiment_id
        """
        try:
            # Handle both calling styles
            if experiment:
                # Dict-based style
                exp_name = experiment.get("experiment_name", experiment_name or "Unknown")
                exp_hypothesis = experiment.get("hypothesis", hypothesis)
                exp_approach = experiment.get("approach", approach)
                exp_metrics = experiment.get("metrics", [])
                exp_risk_level = experiment.get("risk_level", "medium")
                exp_rollback_plan = experiment.get("rollback_plan")
            else:
                # Keyword argument style
                exp_name = experiment_name or "Unknown"
                exp_hypothesis = hypothesis
                exp_approach = approach
                exp_metrics = []
                exp_risk_level = "medium"
                exp_rollback_plan = None
            
            # Serialize list/dict fields to JSON strings for SQLite compatibility
            if isinstance(exp_approach, (list, dict)):
                exp_approach = json.dumps(exp_approach)
            if isinstance(exp_metrics, (list, dict)):
                exp_metrics = json.dumps(exp_metrics)
            elif not exp_metrics:
                exp_metrics = "[]"
            
            db = next(get_db())
            
            cursor = db.execute(text("""
                INSERT INTO experiments (
                    project_id, worker_name, experiment_name, 
                    hypothesis, approach, metrics, risk_level, 
                    rollback_plan, status, started_at
                ) VALUES (:project_id, :worker_name, :experiment_name, 
                         :hypothesis, :approach, :metrics, :risk_level, 
                         :rollback_plan, :status, :started_at)
            """), {
                "project_id": project_id,
                "worker_name": worker_name,
                "experiment_name": exp_name,
                "hypothesis": exp_hypothesis,
                "approach": exp_approach,
                "metrics": exp_metrics,
                "risk_level": exp_risk_level,
                "rollback_plan": exp_rollback_plan,
                "status": "running",
                "started_at": utc_now()
            })
            
            experiment_id = cursor.lastrowid
            db.commit()
            
            logger.info(f"Started experiment {experiment_id}: {exp_name}")
            return experiment_id
            
        except Exception as e:
            logger.error(f"Failed to record experiment start: {e}")
            return -1
    
    def record_outcome(
        self,
        experiment_id: int,
        outcome: Dict[str, Any]
    ):
        """
        Record experiment outcome and update learning.
        
        Args:
            experiment_id: ID of the experiment
            outcome: Results including success, improvement, metrics
        """
        try:
            db = next(get_db())
            
            success = bool(outcome.get("success", False))
            improvement = float(outcome.get("improvement", 0.0))
            
            # Update experiment record
            db.execute(text("""
                UPDATE experiments 
                SET status = :status, 
                    completed_at = :completed_at, 
                    outcome_json = :outcome_json, 
                    success = :success, 
                    improvement = :improvement
                WHERE experiment_id = :experiment_id
            """), {
                "status": "completed",
                "completed_at": utc_now(),
                "outcome_json": json.dumps(outcome),
                "success": success,
                "improvement": improvement,
                "experiment_id": experiment_id
            })
            
            # Get experiment details for learning
            exp_row = db.execute(
                text("SELECT * FROM experiments WHERE experiment_id = :experiment_id"),
                {"experiment_id": experiment_id}
            ).fetchone()
            
            if exp_row:
                # Add to in-memory cache
                exp_data = {
                    "worker_name": exp_row[1],  # worker_name column
                    "experiment_name": exp_row[2],  # experiment_name column
                    "approach": exp_row[4],  # approach column
                    "completed_at": utc_now(),
                }
                
                if success:
                    exp_data["improvement"] = improvement
                    self.successful_patterns.insert(0, exp_data)
                    self.successful_patterns = self.successful_patterns[:10]  # Keep recent 10
                    
                    # Consider promoting to production if highly successful
                    if improvement > 0.20:  # 20%+ improvement
                        self._promote_to_production(experiment_id, exp_row)
                else:
                    self.failed_patterns.insert(0, exp_data)
                    self.failed_patterns = self.failed_patterns[:10]
            
            db.commit()
            
            status = "✅ SUCCESS" if success else "❌ FAILURE"
            logger.info(f"Experiment {experiment_id} {status} (improvement: {improvement:.1%})")
            
        except Exception as e:
            logger.error(f"Failed to record outcome: {e}")
    
    def _promote_to_production(self, experiment_id: int, experiment: Dict[str, Any]):
        """
        Mark highly successful experiment for production adoption.
        
        This signals to the worker that this approach should become the default.
        """
        try:
            db = next(get_db())
            
            db.execute(text("""
                UPDATE experiments 
                SET promoted_to_production = TRUE, promoted_at = :promoted_at
                WHERE experiment_id = :experiment_id
            """), {
                "promoted_at": utc_now(),
                "experiment_id": experiment_id
            })
            
            db.commit()
            
            logger.info(f"🌟 Promoted experiment {experiment_id} to production!")
            
        except Exception as e:
            logger.error(f"Failed to promote experiment: {e}")
    
    def get_promoted_experiments(self, worker_name: str) -> List[Dict[str, Any]]:
        """
        Get experiments promoted to production for a worker.
        
        Workers can query this to adopt successful experimental approaches.
        """
        try:
            db = next(get_db())
            
            rows = db.execute(text("""
                SELECT * FROM experiments 
                WHERE worker_name = :worker_name 
                  AND promoted_to_production = TRUE
                ORDER BY promoted_at DESC
            """), {"worker_name": worker_name}).fetchall()
            
            return [
                {
                    "experiment_id": row[0],  # experiment_id column
                    "experiment_name": row[2],  # experiment_name column
                    "approach": row[4],  # approach column
                    "improvement": row[11],  # improvement column
                    "promoted_at": row[13],  # promoted_at column
                    "outcome_json": json.loads(row[12]) if row[12] else {}
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to get promoted experiments: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dreamer statistics"""
        try:
            db = next(get_db())
            
            # Overall stats
            total = db.execute("SELECT COUNT(*) as count FROM experiments").fetchone()["count"]
            successful = db.execute(
                "SELECT COUNT(*) as count FROM experiments WHERE success = TRUE"
            ).fetchone()["count"]
            promoted = db.execute(
                "SELECT COUNT(*) as count FROM experiments WHERE promoted_to_production = TRUE"
            ).fetchone()["count"]
            
            # Per-worker stats
            worker_stats = {}
            rows = db.execute("""
                SELECT worker_name, 
                       COUNT(*) as total,
                       SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) as successful,
                       AVG(CASE WHEN success = TRUE THEN improvement ELSE 0 END) as avg_improvement
                FROM experiments
                GROUP BY worker_name
            """).fetchall()
            
            for row in rows:
                worker_stats[row["worker_name"]] = {
                    "total_experiments": row["total"],
                    "successful": row["successful"],
                    "success_rate": row["successful"] / row["total"] if row["total"] > 0 else 0,
                    "avg_improvement": row["avg_improvement"] or 0,
                }
            
            return {
                "total_experiments": int(total) if total else 0,
                "successful_experiments": int(successful) if successful else 0,
                "promoted_experiments": int(promoted) if promoted else 0,
                "overall_success_rate": successful / total if total > 0 else 0,
                "evolution_rate": self.evolution_rate,
                "by_worker": worker_stats,
            }
            
        except Exception as e:
            logger.error(f"Failed to get dreamer stats: {e}")
            return {}


# Global dreamer instance
_dreamer: Optional[DreamerMetaAgent] = None


def get_dreamer() -> DreamerMetaAgent:
    """Get the global dreamer instance"""
    global _dreamer
    if _dreamer is None:
        _dreamer = DreamerMetaAgent()
    return _dreamer
