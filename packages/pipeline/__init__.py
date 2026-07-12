"""
__init__.py — Shared Pipeline Package Root
"""

from .schemas import PipelineResult
from .exceptions import PipelineError, LayerExecutionError
from .orchestrator import PipelineOrchestrator
from .persistence import create_initial_manuscript, save_pipeline_outputs

__all__ = [
    'PipelineResult',
    'PipelineError',
    'LayerExecutionError',
    'PipelineOrchestrator',
    'create_initial_manuscript',
    'save_pipeline_outputs'
]
