"""
test_online_import_isolation.py
Verifies that importing packages.calibration or packages.calibration.online
does NOT import offline retraining modules like mlflow, sklearn.model_selection, etc.
"""

import unittest
import sys
import subprocess
from packages.calibration.common.constants import PACKAGE_ROOT


class TestOnlineImportIsolation(unittest.TestCase):

    def test_import_isolation(self):
        # We need to run this in a clean subprocess to verify sys.modules strictly
        script = """
import sys
import packages.calibration
import packages.calibration.online

forbidden_modules = [
    'mlflow',
    'sklearn.model_selection',
    'packages.calibration.offline',
    'packages.calibration.offline.train',
    'packages.calibration.offline.evaluator'
]

for mod in forbidden_modules:
    if mod in sys.modules:
        print(f"FAILED: {mod} was imported.")
        sys.exit(1)

print("SUCCESS")
"""
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        self.assertIn("SUCCESS", result.stdout, f"Import isolation failed: {result.stdout} {result.stderr}")


if __name__ == "__main__":
    unittest.main()
