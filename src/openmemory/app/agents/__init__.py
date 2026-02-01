"""
SIGMA Multi-Agent System

5 specialized workers with dual-mode operation (production + experimental)
"""

from .base_worker import BaseWorker, WorkerController
from .dreamer import DreamerMetaAgent
from .analysis_worker import AnalysisWorker
from .dream_worker import DreamWorker
from .recall_worker import RecallWorker
from .learning_worker import LearningWorker
from .think_worker import ThinkWorker

__all__ = [
    'BaseWorker',
    'WorkerController',
    'DreamerMetaAgent',
    'AnalysisWorker',
    'DreamWorker',
    'RecallWorker',
    'LearningWorker',
    'ThinkWorker'
]
