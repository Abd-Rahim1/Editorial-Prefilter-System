"""
schemas.py — Shared Pipeline Schemas
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class PipelineResult:
    manuscript_id: str
    filename: str
    title: str
    sections: Dict[str, str] = field(default_factory=dict)
    
    # Layer 1 result
    layer1_violations: List[Any] = field(default_factory=list)
    editorial_features: Dict[str, float] = field(default_factory=dict)
    
    # Layer 2 result
    layer2_scores: Dict[str, Any] = field(default_factory=dict)
    
    # Layer 3 result
    layer3_prediction: Optional[Any] = None  # Layer3Prediction DTO
    
    # Layer 4 result
    report_json: Dict[str, Any] = field(default_factory=dict)

    def to_master_report_dict(self) -> Dict[str, Any]:
        """Returns the canonical 5-section master report dict."""
        return self.report_json
