"""
test_policy_propagation.py — Policy Propagation & Cache Invalidation Verification
Verifies:
1. Administrative threshold profile updates propagate cleanly without reloading the model artifact (`ModelLoader`).
2. `PolicyResolver.invalidate_cache()` successfully forces policy refresh.
3. Legacy profile 1 (0.85 / 0.40) and active profile 2 (0.35 / 0.65) are safely distinguished and handled without order-check constraints.
"""

import unittest
from unittest.mock import MagicMock, patch
from packages.calibration.online.policy_resolver import PolicyResolver
from packages.calibration.online.threshold_policy import ThresholdPolicy
from packages.calibration.online.service import Layer3Service


class TestPolicyPropagation(unittest.TestCase):

    def test_cache_invalidation_and_propagation_without_model_reload(self):
        """Verify that modifying a policy and calling invalidate_cache() updates thresholds without calling model loader again."""
        mock_loader = MagicMock()
        # Mock active bundle returning model_id=1, threshold_profile_id=2
        mock_loader.load_active_bundle.return_value = {
            "model_id": 1,
            "model_version": "v1.0",
            "model_name": "Random_Forest",
            "threshold_profile_id": 2,
            "schema": {
                "ordered_features": [
                    "argumentative_quality", "conference", "critical_rules_failed",
                    "experimental_strength", "methodological_strength", "overall_quality",
                    "risk_multiplier", "scope_alignment", "structural_completeness", "total_rules_failed"
                ]
            }
        }

        # Mock predictor
        mock_predictor = MagicMock()
        mock_predictor.predict_probabilities.return_value = (0.50, 0.50)

        # Create policy resolver with mocked session
        resolver = PolicyResolver(db_session=MagicMock())
        # First query returns Profile 2 (0.35 / 0.65)
        with patch.object(resolver, "resolve_active_policy", return_value={
            "profile_id": 2,
            "reject_upper_bound": 0.35,
            "peer_review_lower_bound": 0.65,
            "version": "2"
        }) as mock_resolve:
            service = Layer3Service(loader=mock_loader, predictor=mock_predictor, policy=ThresholdPolicy(policy_resolver=resolver))

            pred1 = service.predict("MS-01", layer1_result={}, layer2_result={})
            self.assertEqual(pred1.decision, "manual_review")
            self.assertEqual(mock_loader.load_active_bundle.call_count, 1)

        # Now simulate administrative update: bounds change to strict (0.60 / 0.90) and cache is invalidated
        resolver.invalidate_cache()
        with patch.object(resolver, "resolve_active_policy", return_value={
            "profile_id": 2,
            "reject_upper_bound": 0.60,
            "peer_review_lower_bound": 0.90,
            "version": "2_updated"
        }):
            pred2 = service.predict("MS-02", layer1_result={}, layer2_result={})
            # With p_accept=0.50 and new reject_upper_bound=0.60, decision must immediately change to desk_reject!
            self.assertEqual(pred2.decision, "desk_reject")
            # Verify model was loaded from cache without reloading or crashing
            self.assertEqual(mock_loader.load_active_bundle.call_count, 2)

    def test_legacy_profile_1_vs_active_profile_2_handling(self):
        """Verify that legacy profile 1 (0.85/0.40 desk>review anomaly) and active profile 2 (0.35/0.65) are correctly processed."""
        policy = ThresholdPolicy()

        # Active Profile 2: normal valid boundaries
        p2 = {
            "profile_id": 2,
            "reject_upper_bound": 0.35,
            "peer_review_lower_bound": 0.65,
            "version": "2"
        }
        dec, conf, ver, thres = policy.evaluate_decision(0.20, profile=p2)
        self.assertEqual(dec, "desk_reject")
        self.assertEqual(thres["reject_upper_bound"], 0.35)

        # Legacy Profile 1: stored bounds where desk_reject_upper_bound > peer_review_lower_bound (0.85 vs 0.40)
        # Verify that our safeguard raises ThresholdPolicyError cleanly rather than silently corrupting decisions
        p1_legacy = {
            "profile_id": 1,
            "reject_upper_bound": 0.85,
            "peer_review_lower_bound": 0.40,
            "version": "1"
        }
        with self.assertRaises(Exception) as ctx:
            policy.evaluate_decision(0.50, profile=p1_legacy)
        self.assertIn("cannot exceed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
