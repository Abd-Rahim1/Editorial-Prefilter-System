"""
test_risk_multiplier_historical_parity.py
Verify that the online feature builder produces the EXACT same risk_multiplier
as the one stored historically in the dataset.
"""

import unittest
import math
import pandas as pd
from packages.calibration.common.constants import PACKAGE_ROOT
from packages.calibration.online.feature_builder import build_raw_features


class TestRiskMultiplierHistoricalParity(unittest.TestCase):

    def test_risk_multiplier_parity(self):
        dataset_path = PACKAGE_ROOT.parent.parent / "data" / "prepared" / "dataset" / "dataset.csv"
        if not dataset_path.exists():
            self.skipTest("Historical dataset.csv not found.")
            
        df = pd.read_csv(dataset_path)
        
        # Test up to 50 rows
        for idx, row in df.head(50).iterrows():
            historical_risk = row.get("risk_multiplier", 0.0)
            
            # Reconstruct Layer 1 and Layer 2 dictionary
            l1 = {
                "total_rules_failed": row.get("total_rules_failed", 0.0),
                "critical_rules_failed": row.get("critical_rules_failed", 0.0),
                "conference": row.get("conference", 0.0)
            }
            l2 = {
                "overall_quality": row.get("overall_quality", 0.0),
                "argumentative_quality": row.get("argumentative_quality", 0.0),
                "experimental_strength": row.get("experimental_strength", 0.0),
                "methodological_strength": row.get("methodological_strength", 0.0),
                "scope_alignment": row.get("scope_alignment", 0.0),
                "structural_completeness": row.get("structural_completeness", 0.0)
            }
            
            raw_built = build_raw_features(layer1_output=l1, layer2_output=l2)
            online_risk = raw_built.get("risk_multiplier", 0.0)
            
            diff = abs(historical_risk - online_risk)
            self.assertTrue(diff < 1e-9, f"Row {idx} mismatch: Historical={historical_risk}, Online={online_risk}, Diff={diff}")

if __name__ == "__main__":
    unittest.main()
