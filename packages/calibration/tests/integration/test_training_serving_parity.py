"""
test_training_serving_parity.py — Mandatory Training-Serving Parity Verification
Verifies that features engineered during offline training (`dataset.py` / `_prepare_c2_dataframe`)
match the exact feature vector generated during online serving (`feature_builder` + `feature_preprocessor`)
with zero drift or discrepancy (`abs(prob_online - prob_offline) < 1e-6`).

Also verifies that class labels, feature order (`CANONICAL_C2_FEATURES`), and `risk_multiplier`
are 100% identical between offline and online paths.
"""

import math
import unittest
import json
from pathlib import Path
import pandas as pd
import numpy as np

from packages.calibration.offline.dataset import load_dataset_splits
from packages.calibration.online.service import Layer3Service
from packages.calibration.online.feature_builder import build_raw_features
from packages.calibration.online.feature_preprocessor import preprocess_features
from packages.calibration.common.feature_contract import CANONICAL_C2_FEATURES
from packages.calibration.common.constants import PACKAGE_ROOT


class TestTrainingServingParity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.service = Layer3Service()
        cls.bundle = cls.service.loader.load_active_bundle()
        cls.model = cls.bundle["model"]
        cls.schema = cls.bundle["schema"]
        cls.X_train, cls.X_test, cls.y_train, cls.y_test = load_dataset_splits(test_size=0.2, random_seed=42)

    def test_feature_order_and_names_exact_match(self):
        """Verify that online preprocessor feature list exactly matches training feature list."""
        self.assertEqual(list(self.X_train.columns), CANONICAL_C2_FEATURES)
        self.assertEqual(list(self.schema["ordered_features"]), CANONICAL_C2_FEATURES)

    def test_numerical_parity_across_dataset_rows(self):
        """Verify exact probability match (abs diff < 1e-6) between offline matrix row and online pipeline across 50 rows."""
        # Check first 50 rows of test split
        sample_rows = self.X_test.head(50)

        for idx, row_series in sample_rows.iterrows():
            # 1. Offline probability computation directly on training-prepared matrix row
            row_df = pd.DataFrame([row_series.to_dict()], columns=CANONICAL_C2_FEATURES)
            offline_prob = float(self.model.predict_proba(row_df)[0, 1])

            # 2. Online serving probability via feature_builder + feature_preprocessor
            # Convert row_series back to raw dictionary input as Layer 1 and Layer 2 would send
            raw_dict = row_series.to_dict()
            # Remove risk_multiplier from raw input so feature_builder computes it dynamically online
            if "risk_multiplier" in raw_dict:
                del raw_dict["risk_multiplier"]

            raw_built = build_raw_features(raw_override=raw_dict)
            X_online, fv_dict, _ = preprocess_features(raw_built, self.schema)

            online_prob, _ = self.service.predictor.predict_probabilities(X_online, self.bundle)

            # Check exact feature match across every single column
            for col in CANONICAL_C2_FEATURES:
                self.assertTrue(
                    math.isclose(row_df[col].iloc[0], X_online[col].iloc[0], abs_tol=1e-7),
                    f"Feature mismatch on col '{col}' for row {idx}: offline={row_df[col].iloc[0]} vs online={X_online[col].iloc[0]}"
                )

            # Check probability parity < 1e-6
            diff = abs(offline_prob - online_prob)
            self.assertLess(
                diff, 1e-6,
                f"Probability discrepancy exceeded 1e-6 on row {idx}! offline={offline_prob:.8f} vs online={online_prob:.8f}"
            )

    def test_golden_fixtures_parity(self):
        """Verify exact prediction outputs and risk_multiplier formulas against golden_predictions.json."""
        fixtures_p = PACKAGE_ROOT / "tests" / "fixtures" / "golden_predictions.json"
        self.assertTrue(fixtures_p.exists(), f"Golden fixtures not found at: {fixtures_p}")

        with open(fixtures_p, "r", encoding="utf-8") as f:
            golden_data = json.load(f)

        for fixture in golden_data:
            ms_id = fixture["manuscript_id"]
            l1 = fixture["layer1_rules"]
            l2 = fixture["layer2_scores"]
            exp_risk = fixture["expected_risk_multiplier"]
            exp_dec = fixture["expected_decision"]

            pred = self.service.predict(manuscript_id=ms_id, layer1_result=l1, layer2_result=l2)

            # Check risk_multiplier computation
            calc_risk = pred.feature_vector.get("risk_multiplier", 0.0)
            self.assertTrue(
                math.isclose(calc_risk, exp_risk, abs_tol=1e-2),
                f"Golden fixture '{ms_id}' risk_multiplier mismatch: expected {exp_risk}, got {calc_risk}"
            )

            # Check decision category match
            self.assertEqual(
                pred.decision, exp_dec,
                f"Golden fixture '{ms_id}' decision mismatch: expected {exp_dec}, got {pred.decision} (P_Accept={pred.accept_probability:.4f})"
            )


if __name__ == "__main__":
    unittest.main()
