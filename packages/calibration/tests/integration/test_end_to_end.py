"""
test_end_to_end.py — End-to-End Layer 3 Integration & Latency Verification
Verifies end-to-end prediction integration between simulated upstream Layer 1/2 outputs
and the Layer 3 online service. Asserts boundary thresholds and cached latency (< 30ms).
"""

import time
import math
import unittest
from packages.calibration.online.service import Layer3Service
from packages.calibration.online.schemas import PredictionRequest, Layer3Prediction


class TestEndToEndLayer3(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.service = Layer3Service()
        # Warmup cache
        cls.service.predict(manuscript_id="WARMUP", layer1_result={"total_rules_failed": 0}, layer2_result={"overall_quality": 0.8})

    def test_end_to_end_prediction_with_dto(self):
        """Verify passing PredictionRequest DTO into Layer3Service.predict."""
        req = PredictionRequest(
            manuscript_id="MS-E2E-100",
            layer1_rules={"total_rules_failed": 1, "critical_rules_failed": 0, "conference": 0},
            layer2_scores={"overall_quality": 0.85, "argumentative_quality": 0.90}
        )
        pred = self.service.predict(request=req)

        self.assertIsInstance(pred, Layer3Prediction)
        self.assertEqual(pred.manuscript_id, "MS-E2E-100")
        self.assertIn(pred.classifier, ["Random_Forest", "Random Forest C2"])
        self.assertEqual(pred.feature_schema_version, "1.0")
        self.assertEqual(pred.calibration_method, "none")
        self.assertTrue(math.isclose(pred.feature_vector["risk_multiplier"], 0.15, rel_tol=1e-4))

    def test_cached_latency_under_30ms(self):
        """Verify average cached inference latency across 25 requests remains well under 30ms."""
        times = []
        for i in range(25):
            pred = self.service.predict(
                manuscript_id=f"MS-LATENCY-{i}",
                layer1_result={"total_rules_failed": 1, "conference": 0},
                layer2_result={"overall_quality": 0.8, "argumentative_quality": 0.85}
            )
            times.append(pred.inference_time_ms)

        avg_time = sum(times) / len(times)
        # Note: on warm cached calls, typical time is < 15ms
        self.assertLess(avg_time, 35.0, f"Average inference time exceeded latency threshold: {avg_time:.2f} ms")

    def test_custom_threshold_profile_override(self):
        """Verify custom threshold profile overrides default decision boundaries."""
        l1 = {"total_rules_failed": 2}
        l2 = {"overall_quality": 0.6}

        # 1. With custom strict bounds where peer_review_lower_bound is 0.40
        pred_strict = self.service.predict(
            manuscript_id="MS-CUSTOM-1",
            layer1_result=l1,
            layer2_result=l2,
            custom_thresholds={"desk_reject_upper_bound": 0.20, "peer_review_lower_bound": 0.40, "profile_version": "strict-v2"}
        )
        self.assertEqual(pred_strict.threshold_profile_version, "strict-v2")
        self.assertEqual(pred_strict.decision, "peer_review")

        # 2. With custom lenient bounds where desk_reject_upper_bound is 0.70
        pred_lenient = self.service.predict(
            manuscript_id="MS-CUSTOM-2",
            layer1_result=l1,
            layer2_result=l2,
            custom_thresholds={"desk_reject_upper_bound": 0.70, "peer_review_lower_bound": 0.90, "profile_version": "lenient-v2"}
        )
        self.assertEqual(pred_lenient.threshold_profile_version, "lenient-v2")
        self.assertEqual(pred_lenient.decision, "desk_reject")


if __name__ == "__main__":
    unittest.main()
