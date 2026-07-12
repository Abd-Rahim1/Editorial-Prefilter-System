"""
test_feature_schema_authority.py — Feature Schema Authority Verification
Verifies that:
artifact_schema.features == CANONICAL_C2_FEATURES == offline training feature order == online preprocessor output columns
"""

import unittest
import json
from pathlib import Path
import pandas as pd
from packages.calibration.common.feature_contract import CANONICAL_C2_FEATURES
from packages.calibration.common.constants import PACKAGE_ROOT
from packages.calibration.offline.dataset import load_dataset_splits
from packages.calibration.online.feature_preprocessor import preprocess_features


class TestFeatureSchemaAuthority(unittest.TestCase):

    def test_feature_schema_exact_equality(self):
        # 1. Load evaluation winner feature_schema.json
        winner_dir = PACKAGE_ROOT.parent.parent / "experiments" / "evaluation_models" / "best_pipeline"
        schema_path = winner_dir / "feature_schema.json"
        
        self.assertTrue(schema_path.exists(), "Evaluation winner feature_schema.json missing.")
        
        with open(schema_path, "r", encoding="utf-8") as f:
            artifact_schema = json.load(f)
            
        artifact_features = artifact_schema.get("ordered_features", [])
        
        # 2. Check against CANONICAL_C2_FEATURES
        self.assertEqual(artifact_features, CANONICAL_C2_FEATURES, "Artifact features do not match canonical C2 contract.")
        self.assertEqual(len(artifact_features), 10, "Feature count is not 10.")
        
        # 3. Check against offline training feature order
        X_train, _, _, _ = load_dataset_splits(test_size=0.2, random_seed=42)
        offline_features = list(X_train.columns)
        self.assertEqual(artifact_features, offline_features, "Offline training order differs from artifact schema.")
        
        # 4. Check against online preprocessor output columns
        raw = {"conference": 0, "total_rules_failed": 0, "overall_quality": 0.5}
        X_online, _, _ = preprocess_features(raw, artifact_schema, strict_missing_check=False)
        online_features = list(X_online.columns)
        self.assertEqual(artifact_features, online_features, "Online preprocessing order differs from artifact schema.")

if __name__ == "__main__":
    unittest.main()
