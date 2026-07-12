"""
Database Models definitions module.
Re-exports ORM models to ensure seamless discovery across packages and apps.
"""
import sys
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_current_dir))
_api_dir = os.path.join(_project_root, "apps", "api")

if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from config import (
    Base,
    RoleModel,
    UserModel,
    SystemSettings,
    AuditLog,
    Manuscript,
    EditorialFeature,
    Experiment,
    Explanation,
    ExtractedSection,
    LLMEvaluation,
    ModelRun,
    Prediction,
    Report,
    RuleCheck,
    ThresholdProfile,
    TrainedModel,
    ModelRegistry,
    PromptTemplate,
)

__all__ = [
    "Base",
    "RoleModel",
    "UserModel",
    "SystemSettings",
    "AuditLog",
    "Manuscript",
    "EditorialFeature",
    "Experiment",
    "Explanation",
    "ExtractedSection",
    "LLMEvaluation",
    "ModelRun",
    "Prediction",
    "Report",
    "RuleCheck",
    "ThresholdProfile",
    "TrainedModel",
    "ModelRegistry",
    "PromptTemplate",
]

