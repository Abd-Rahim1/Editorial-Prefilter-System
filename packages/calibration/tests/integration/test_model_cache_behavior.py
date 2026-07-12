"""
test_model_cache_behavior.py
Verifies that the online model loader correctly caches the bundle
and avoids repeated disk I/O on subsequent requests.
"""

import unittest
from packages.calibration.online.service import Layer3Service
from packages.calibration.online.model_loader import _CACHED_BUNDLES


class TestModelCacheBehavior(unittest.TestCase):

    def test_model_cache(self):
        service = Layer3Service()
        
        # Clear cache first to ensure cold start
        service.loader.clear_cache()
        self.assertEqual(len(_CACHED_BUNDLES), 0)
        
        # First load (Cold)
        bundle1 = service.loader.load_active_bundle()
        self.assertEqual(len(_CACHED_BUNDLES), 1)
        
        # Second load (Warm)
        bundle2 = service.loader.load_active_bundle()
        
        # Verify identity (same object in memory)
        self.assertIs(bundle1["model"], bundle2["model"])
        self.assertIs(bundle1["schema"], bundle2["schema"])

if __name__ == "__main__":
    unittest.main()
