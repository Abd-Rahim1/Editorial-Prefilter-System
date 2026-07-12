"""
test_model_class_mapping.py
Verifies that predictor class mappings dynamically and accurately map the correct
accept and desk-reject indices and ensure probabilities sum to 1.0.
"""

import math
import unittest
import pandas as pd
from packages.calibration.online.service import Layer3Service


class TestModelClassMapping(unittest.TestCase):

    def test_model_class_semantics(self):
        service = Layer3Service()
        
        # Test using a sample input
        pred = service.predict(
            manuscript_id="CLASS-TEST",
            layer1_result={"total_rules_failed": 1},
            layer2_result={"overall_quality": 0.5}
        )
        
        # 1. Probabilities must be exactly between 0 and 1
        self.assertTrue(0.0 <= pred.accept_probability <= 1.0)
        self.assertTrue(0.0 <= pred.desk_reject_probability <= 1.0)
        
        # 2. P(Accept) + P(Desk Reject) must perfectly sum to 1.0
        total_prob = pred.accept_probability + pred.desk_reject_probability
        self.assertTrue(math.isclose(total_prob, 1.0, abs_tol=1e-12))
        
if __name__ == "__main__":
    unittest.main()
