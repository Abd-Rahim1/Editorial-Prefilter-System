"""
test_online_modules.py — Unit Tests for Layer 3 Online Submodule
Tests fast online feature building, exact schema preprocessing, alias resolution,
threshold boundary checks, and full `Layer3Service` prediction DTO generation.
Compatible with standard `python -m unittest` and `pytest`.
"""

import math
import unittest
import pandas as pd
from packages.calibration.online.feature_builder import build_raw_features
from packages.calibration.online.feature_preprocessor import preprocess_features
from packages.calibration.online.threshold_policy import ThresholdPolicy
from packages.calibration.online.service import Layer3Service
from packages.calibration.common.exceptions import MissingRequiredFeatureError, ThresholdPolicyError
from packages.calibration.common.contracts import Layer1OutputContract, Layer2OutputContract


class TestOnlineModules(unittest.TestCase):

    def test_build_raw_features_aliases_and_risk_multiplier(self):
        """Verify alias resolution (is_conference -> conference) and risk_multiplier formula."""
        l1 = {"is_conference": 1, "total_failures": 4}
        l2 = {"credibility_score": 0.6, "arg_quality": 3.8}

        raw = build_raw_features(layer1_output=l1, layer2_output=l2)

        self.assertEqual(raw["conference"], 1)
        self.assertEqual(raw["total_rules_failed"], 4)
        self.assertEqual(raw["overall_quality"], 0.6)
        self.assertEqual(raw["argumentative_quality"], 3.8)
        # Formula: (1.0 - 0.6) * 4 = 0.4 * 4 = 1.6
        self.assertTrue(math.isclose(raw["risk_multiplier"], 1.6, rel_tol=1e-5))

    def test_build_raw_features_contracts(self):
        """Verify Layer1OutputContract and Layer2OutputContract integration."""
        l1 = Layer1OutputContract(critical_rules_failed=2, total_rules_failed=5, conference=0)
        l2 = Layer2OutputContract(overall_quality=0.5, argumentative_quality=4.1)

        raw = build_raw_features(layer1_output=l1, layer2_output=l2)
        self.assertEqual(raw["critical_rules_failed"], 2)
        self.assertEqual(raw["total_rules_failed"], 5)
        # Formula: (1.0 - 0.5) * 5 = 2.5
        self.assertTrue(math.isclose(raw["risk_multiplier"], 2.5, rel_tol=1e-5))

    def test_preprocess_features_canonical_ordering_and_defaults(self):
        """Verify that preprocess_features produces exact 1-row DataFrame ordering without sorting alphabetically."""
        raw = {
            "total_rules_failed": 3.0,
            "overall_quality": 0.7,
            "conference": 1,
            "risk_multiplier": 0.9,
        }

        X, fv_dict, ver = preprocess_features(raw, strict_missing_check=False)

        self.assertIsInstance(X, pd.DataFrame)
        self.assertEqual(len(X), 1)
        # Check exact C2 order
        self.assertEqual(list(X.columns), [
            "argumentative_quality",
            "conference",
            "critical_rules_failed",
            "experimental_strength",
            "methodological_strength",
            "overall_quality",
            "risk_multiplier",
            "scope_alignment",
            "structural_completeness",
            "total_rules_failed"
        ])
        # Check default imputation on missing
        self.assertEqual(fv_dict["argumentative_quality"], 3.0)
        self.assertEqual(fv_dict["conference"], 1.0)
        self.assertEqual(fv_dict["total_rules_failed"], 3.0)

    def test_preprocess_features_strict_missing_check_raises(self):
        """Verify MissingRequiredFeatureError when strict_missing_check is True."""
        raw = {"conference": 1}
        with self.assertRaises(MissingRequiredFeatureError):
            preprocess_features(raw, strict_missing_check=True)

    def test_threshold_policy_boundaries(self):
        """Verify exact boundary checking across <= 0.35, 0.35 - 0.65, >= 0.65."""
        policy = ThresholdPolicy(db_session=None)
        prof = {"desk_reject_upper_bound": 0.35, "peer_review_lower_bound": 0.65}

        # 1. Exact desk reject boundaries
        dec, conf, _, _ = policy.evaluate_decision(0.00, profile=prof)
        self.assertEqual(dec, "desk_reject")
        self.assertEqual(conf, "HIGH")

        dec, conf, _, _ = policy.evaluate_decision(0.35, profile=prof)
        self.assertEqual(dec, "desk_reject")

        # 2. Borderline / manual review boundaries
        dec, conf, _, _ = policy.evaluate_decision(0.350001, profile=prof)
        self.assertEqual(dec, "manual_review")
        self.assertEqual(conf, "MODERATE")

        dec, conf, _, _ = policy.evaluate_decision(0.649999, profile=prof)
        self.assertEqual(dec, "manual_review")
        self.assertEqual(conf, "MODERATE")

        # 3. Peer review boundaries
        dec, conf, _, _ = policy.evaluate_decision(0.65, profile=prof)
        self.assertEqual(dec, "peer_review")

        dec, conf, _, _ = policy.evaluate_decision(1.00, profile=prof)
        self.assertEqual(dec, "peer_review")
        self.assertEqual(conf, "HIGH")

    def test_threshold_policy_invalid_bounds_raises(self):
        """Verify exception raised when upper bound exceeds lower bound."""
        policy = ThresholdPolicy(db_session=None)
        prof = {"desk_reject_upper_bound": 0.80, "peer_review_lower_bound": 0.50}
        with self.assertRaises(ThresholdPolicyError):
            policy.evaluate_decision(0.60, profile=prof)

    def test_layer3_service_prediction_dto(self):
        """Verify full end-to-end prediction via Layer3Service returns typed Layer3Prediction DTO with latency."""
        service = Layer3Service()
        pred = service.predict(
            manuscript_id="MS-UNIT-01",
            layer1_result={"total_rules_failed": 0, "conference": 1},
            layer2_result={"overall_quality": 4.5, "argumentative_quality": 4.4}
        )

        self.assertEqual(pred.manuscript_id, "MS-UNIT-01")
        self.assertTrue(0.0 <= pred.accept_probability <= 1.0)
        self.assertTrue(0.0 <= pred.desk_reject_probability <= 1.0)
        self.assertTrue(math.isclose(pred.accept_probability + pred.desk_reject_probability, 1.0, rel_tol=1e-5))
        self.assertIn(pred.decision, ["desk_reject", "manual_review", "peer_review"])
        self.assertIn(pred.classifier, ["Random_Forest", "Random Forest C2"])
        self.assertGreater(pred.inference_time_ms, 0.0)


if __name__ == "__main__":
    unittest.main()
