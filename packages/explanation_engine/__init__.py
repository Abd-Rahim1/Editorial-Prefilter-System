"""
Explanation Engine Package (Layer 4)
"""

from .generator import ExplanationGenerator
from .explainer import ShapExplainer
from .feature_ranker import FeatureRanker, RankedFeature
from .evidence_integrator import EvidenceIntegrator, IntegratedEvidence
from .narrative import EditorialNarrativeGenerator
from .report_builder import ReportBuilder
from .schemas import ExplanationRequest, ExplanationResult, AttributionResult

__all__ = [
    "ExplanationGenerator",
    "ShapExplainer",
    "FeatureRanker",
    "RankedFeature",
    "EvidenceIntegrator",
    "IntegratedEvidence",
    "EditorialNarrativeGenerator",
    "ReportBuilder",
    "ExplanationRequest",
    "ExplanationResult",
    "AttributionResult",
]