"""
test_model_resolver.py — Model & Policy Resolver Environment Fallback & Active Constraints
Verifies:
1. Production environment (`APP_ENV=production`) raises `NoActiveModelError` when no active DB model (`is_active=True`) is found.
2. Development environment (`APP_ENV=development`) allows local filesystem fallback (`best_pipeline.joblib`).
3. Multiple active DB models raise `MultipleActiveModelsError`.
4. Policy resolution strictly uses `trained_models.threshold_profile_id`.
"""

import unittest
from unittest.mock import MagicMock, patch
from packages.calibration.online.model_resolver import ModelResolver
from packages.calibration.online.policy_resolver import PolicyResolver
from packages.calibration.common.exceptions import (
    NoActiveModelError,
    MultipleActiveModelsError,
    ModelLoadError
)


class TestModelResolver(unittest.TestCase):

    def test_production_environment_no_active_model_raises(self):
        """Verify that production environment raises NoActiveModelError when DB returns 0 active models."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        resolver = ModelResolver(db_session=mock_session, env="production")
        with self.assertRaises(NoActiveModelError) as ctx:
            resolver.resolve_active_model_record()
        self.assertIn("Local fallback is forbidden in production", str(ctx.exception))

    def test_development_environment_fallback_allowed(self):
        """Verify that development environment falls back to local filesystem when DB returns 0 active models."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        resolver = ModelResolver(db_session=mock_session, env="development")
        record = resolver.resolve_active_model_record()
        self.assertEqual(record["source"], "local_filesystem")
        self.assertEqual(record["threshold_profile_id"], 2)

    def test_multiple_active_models_raises(self):
        """Verify that multiple active rows (is_active=True) raise MultipleActiveModelsError immediately."""
        mock_session = MagicMock()
        mock_m1 = MagicMock(id=1)
        mock_m2 = MagicMock(id=2)
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_m1, mock_m2]

        resolver = ModelResolver(db_session=mock_session, env="development")
        with self.assertRaises(MultipleActiveModelsError) as ctx:
            resolver.resolve_active_model_record()
        self.assertIn("Exactly one active model must be configured", str(ctx.exception))

    def test_policy_resolver_uses_model_threshold_profile_id(self):
        """Verify that PolicyResolver queries the threshold profile pointed to by trained_models.threshold_profile_id."""
        mock_model_resolver = MagicMock()
        mock_model_resolver.resolve_active_model_record.return_value = {
            "id": 1,
            "threshold_profile_id": 42
        }

        pr = PolicyResolver(db_session=MagicMock(), model_resolver=mock_model_resolver)
        # With target ID = 42, check what resolve_active_policy does
        with patch.object(pr, "_get_session", return_value=(None, False)):
            policy = pr.resolve_active_policy()
            self.assertEqual(policy["profile_id"], 42)
            mock_model_resolver.resolve_active_model_record.assert_called_once()


if __name__ == "__main__":
    unittest.main()
