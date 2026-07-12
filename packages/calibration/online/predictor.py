"""
predictor.py — Pure Online Inference Engine
Executes fast probability inference given a preprocessed feature DataFrame X and a loaded model bundle.
Inspects `classes_` to ensure correct positive-class probability extraction (`P(Accept)`).
Explicitly computes `P(Desk Reject) = 1.0 - P(Accept)` and verifies probability bounds `[0.0, 1.0]`.
"""

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

from ..common.exceptions import Layer3Error


class Predictor:
    """Pure model probability predictor with strict class mapping checking and bound validation."""

    def predict_probabilities(self, X: pd.DataFrame, bundle: Dict[str, Any]) -> Tuple[float, float]:
        """Runs inference on DataFrame X using the model inside `bundle`.

        Args:
            X: 1-row feature DataFrame ordered exactly according to `feature_schema.json`.
            bundle: Loaded bundle descriptor from `ModelLoader.load_active_bundle()`.

        Returns:
            Tuple[float, float]: `(accept_probability, desk_reject_probability)` bounded within `[0.0, 1.0]`.
        """
        model = bundle.get("model")
        if not model:
            raise Layer3Error("[Predictor Error] No valid model object present inside bundle descriptor.")

        classes = getattr(model, "classes_", np.array([0, 1]))
        
        # Determine positive class (1 or True or 'accept'/'1') index inside classes_
        pos_idx = 1
        if len(classes) > 1:
            for idx, c in enumerate(classes):
                c_str = str(c).lower().strip()
                if c_str in ["1", "1.0", "true", "accept", "accepted", "positive"]:
                    pos_idx = idx
                    break

        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X)
            if probs.shape[1] > pos_idx:
                p_accept = float(probs[0, pos_idx])
            else:
                p_accept = float(probs[0, -1])
        elif hasattr(model, "decision_function"):
            score = float(model.decision_function(X)[0])
            p_accept = float(1.0 / (1.0 + np.exp(-score)))
        else:
            pred = model.predict(X)[0]
            p_accept = 1.0 if str(pred).lower() in ["1", "true", "accept", "1.0"] else 0.0

        # Enforce strict probability bounds [0.0, 1.0]
        p_accept = max(0.0, min(1.0, p_accept))
        p_reject = max(0.0, min(1.0, 1.0 - p_accept))

        return p_accept, p_reject
