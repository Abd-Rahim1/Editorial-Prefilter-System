"""
exceptions.py — Shared Pipeline Exceptions
"""

class PipelineError(Exception):
    """Base exception for all pipeline errors."""
    pass


class LayerExecutionError(PipelineError):
    """Raised when an individual layer fails."""
    def __init__(self, layer: int, message: str, original_exception: Exception = None):
        super().__init__(f"Layer {layer} failed: {message}")
        self.layer = layer
        self.original_exception = original_exception
