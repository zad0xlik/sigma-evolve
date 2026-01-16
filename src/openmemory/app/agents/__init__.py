"""
SIGMA Multi-Agent System

5 specialized workers with dual-mode operation (production + experimental)
"""

from .base_worker import BaseWorker
from .dreamer import DreamerMetaAgent, WorkerController
from .analysis_worker import AnalysisWorker
from .dream_worker import DreamWorker
from .recall_worker import RecallWorker
from .learning_worker import LearningWorker
from .think_worker import ThinkWorker

__all__ = [
    'BaseWorker',
    'DreamerMetaAgent',
    'WorkerController',
    'AnalysisWorker',
    'DreamWorker',
    'RecallWorker',
    'LearningWorker',
    'ThinkWorker'
]
