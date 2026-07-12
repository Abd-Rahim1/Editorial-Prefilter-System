"""
SHAP Explainer Module — Layer 4 Explainable AI Engine.

Responsible solely for computing Shapley Additive exPlanations (SHAP) values
from trained machine learning models given tabular feature vectors.

Primary Path (TreeSHAP):
------------------------
For deployed tree ensembles (`RandomForestClassifier`), we use `shap.TreeExplainer(model)`
with `feature_perturbation='tree_path_dependent'`. This exact calculation integrates over
the exact training data distribution captured inside the tree structure, ensuring verified local additivity:
  base_value + sum(feature_attributions) ≈ exact accept_probability P(Accept)

Target Output Explained:
------------------------
Explains `accept_probability` (Class 1 when `model.classes_ == [0, 1]`, where 0 = Desk Reject, 1 = Accept).
Positive SHAP values: INCREASED_ACCEPT_PROBABILITY.
Negative SHAP values: DECREASED_ACCEPT_PROBABILITY.
"""

import logging
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False

from .schemas import AttributionResult

logger = logging.getLogger(__name__)

_SEMANTIC_SCORE_KEYS = {
    "abstract_clarity",
    "structural_completeness",
    "methodological_strength",
    "experimental_strength",
    "argumentative_quality",
    "scope_alignment",
    "overall_quality",
}

_RULE_PASS_SUFFIX = "_passed"
_RULE_FAIL_COUNTERS = {"total_rules_failed", "critical_rules_failed"}


def _build_neutral_baseline(feature_names: List[str]) -> pd.DataFrame:
    """
    Construct a single-row neutral-reference DataFrame for KernelExplainer fallback.
    """
    row: Dict[str, float] = {}
    for name in feature_names:
        if name in _SEMANTIC_SCORE_KEYS:
            row[name] = 0.50
        elif name.endswith(_RULE_PASS_SUFFIX):
            row[name] = 1.0
        elif name in _RULE_FAIL_COUNTERS:
            row[name] = 0.0
        else:
            row[name] = 0.0
    return pd.DataFrame([row], columns=feature_names)


class ShapExplainer:
    """
    Computes local SHAP attribution values for a single manuscript prediction.
    Explains `accept_probability` relative to the model baseline.
    """

    def __init__(self, model: Any, feature_names: List[str]) -> None:
        self.model = model
        self.feature_names: List[str] = list(feature_names)
        self._neutral_baseline: pd.DataFrame = _build_neutral_baseline(self.feature_names)

        # Resolve exact accept class index
        self.accept_class_index = 1
        if hasattr(self.model, "classes_"):
            classes = list(self.model.classes_)
            # If classes_ = [0, 1], 1 is Accept (0 is Desk Reject)
            if 1 in classes:
                self.accept_class_index = classes.index(1)
            elif len(classes) == 2:
                self.accept_class_index = 1

    def _predict_accept_prob(self, x_input: Any) -> np.ndarray:
        """Return the accept probability for each row."""
        if isinstance(x_input, np.ndarray):
            df_temp = pd.DataFrame(x_input, columns=self.feature_names)
        else:
            df_temp = x_input

        if self.feature_names:
            df_temp = df_temp.reindex(columns=self.feature_names, fill_value=0.0)

        # Enforce exact match verification
        if hasattr(self.model, "feature_names_in_"):
            assert list(df_temp.columns) == list(self.model.feature_names_in_), \
                f"Feature columns mismatch: {list(df_temp.columns)} vs {list(self.model.feature_names_in_)}"

        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(df_temp)
            if probs.shape[1] > self.accept_class_index:
                return probs[:, self.accept_class_index]
            return probs[:, -1]

        preds = self.model.predict(df_temp)
        return preds.astype(float)

    def compute_attribution(self, X: pd.DataFrame) -> AttributionResult:
        """
        Compute full structured SHAP attributions and additivity verification.
        """
        if not isinstance(X, pd.DataFrame):
            raise TypeError("Input X must be a pandas DataFrame.")

        # Ensure columns align
        if list(X.columns) != self.feature_names:
            X = X.reindex(columns=self.feature_names, fill_value=0.0)

        model_output = float(self._predict_accept_prob(X)[0])

        if not HAS_SHAP:
            logger.warning("SHAP library not installed. Returning heuristic attribution.")
            h_vals = self._heuristic_attribution(X)
            recon = 0.5 + sum(h_vals.values())
            add_err = abs(recon - model_output)
            return AttributionResult(
                shap_values=h_vals,
                attribution_method="heuristic_fallback",
                explained_output="accept_probability",
                class_label=1,
                class_index=self.accept_class_index,
                base_value=0.5,
                model_output=model_output,
                attribution_sum=sum(h_vals.values()),
                reconstructed_output=recon,
                additivity_error=add_err,
                additivity_status="FAIL",
                background_strategy="heuristic",
                degraded_mode=True,
                warning="SHAP library not available; heuristic fallback used."
            )

        is_tree_model = (
            type(self.model).__name__ in ("RandomForestClassifier", "DecisionTreeClassifier", "ExtraTreesClassifier", "GradientBoostingClassifier")
            or hasattr(self.model, "estimators_")
            or hasattr(self.model, "tree_")
        )

        if is_tree_model:
            try:
                explainer = shap.TreeExplainer(self.model, feature_perturbation='tree_path_dependent')
                shap_obj = explainer.shap_values(X)

                # Extract TreeSHAP base_value
                ev = explainer.expected_value
                if isinstance(ev, (list, np.ndarray)):
                    base_value = float(ev[self.accept_class_index]) if len(ev) > self.accept_class_index else float(ev[-1])
                else:
                    base_value = float(ev)

                # Extract shap values array for accept class
                if isinstance(shap_obj, list):
                    impacts = np.asarray(shap_obj[self.accept_class_index])[0]
                elif isinstance(shap_obj, np.ndarray) and shap_obj.ndim == 3:
                    impacts = shap_obj[0, :, self.accept_class_index]
                elif isinstance(shap_obj, np.ndarray) and shap_obj.ndim == 2:
                    impacts = shap_obj[0]
                else:
                    impacts = np.asarray(shap_obj).flatten()

                shap_dict = {
                    name: round(float(val), 6)
                    for name, val in zip(self.feature_names, impacts)
                }
                attr_sum_raw = float(np.sum(impacts))
                recon = base_value + attr_sum_raw
                additivity_error = abs(recon - model_output)
                add_status = "PASS" if additivity_error < 1e-8 else "FAIL"
                is_degraded = additivity_error >= 1e-8
                warn_msg = "Attribution additivity validation failed." if is_degraded else None

                return AttributionResult(
                    shap_values=shap_dict,
                    attribution_method="tree_shap",
                    explained_output="accept_probability",
                    class_label=1,
                    class_index=self.accept_class_index,
                    base_value=round(base_value, 6),
                    model_output=round(model_output, 6),
                    attribution_sum=round(attr_sum_raw, 6),
                    reconstructed_output=round(recon, 6),
                    additivity_error=round(additivity_error, 8),
                    additivity_status=add_status,
                    background_strategy="tree_path_dependent",
                    degraded_mode=is_degraded,
                    warning=warn_msg
                )
            except Exception as tree_exc:
                logger.warning("TreeExplainer failed (%s). Falling back to KernelExplainer.", tree_exc)

        try:
            explainer = shap.KernelExplainer(self._predict_accept_prob, self._neutral_baseline)
            shap_raw = explainer.shap_values(X, nsamples=100, l1_reg="aic")

            base_value = float(explainer.expected_value) if not isinstance(explainer.expected_value, (list, np.ndarray)) else float(explainer.expected_value[-1])

            if isinstance(shap_raw, np.ndarray) and shap_raw.ndim == 2:
                impacts: np.ndarray = shap_raw[0]
            elif isinstance(shap_raw, list):
                impacts = np.asarray(shap_raw[-1])[0]
            else:
                impacts = np.asarray(shap_raw).flatten()

            shap_dict = {
                name: round(float(val), 6)
                for name, val in zip(self.feature_names, impacts)
            }
            attr_sum_raw = float(np.sum(impacts))
            recon = base_value + attr_sum_raw
            additivity_error = abs(recon - model_output)
            add_status = "PASS" if additivity_error < 1e-8 else "FAIL"
            is_degraded = additivity_error >= 1e-8
            warn_msg = "Attribution additivity validation failed." if is_degraded else None

            return AttributionResult(
                shap_values=shap_dict,
                attribution_method="kernel_shap",
                explained_output="accept_probability",
                class_label=1,
                class_index=self.accept_class_index,
                base_value=round(base_value, 6),
                model_output=round(model_output, 6),
                attribution_sum=round(attr_sum, 6),
                reconstructed_output=round(recon, 6),
                additivity_error=round(additivity_error, 8),
                additivity_status=add_status,
                background_strategy="neutral_baseline",
                degraded_mode=is_degraded,
                warning=warn_msg
            )
        except Exception as kernel_exc:
            logger.warning("KernelExplainer failed (%s). Using heuristic fallback.", kernel_exc)
            h_vals = self._heuristic_attribution(X)
            recon = 0.5 + sum(h_vals.values())
            add_err = abs(recon - model_output)
            return AttributionResult(
                shap_values=h_vals,
                attribution_method="heuristic_fallback",
                explained_output="accept_probability",
                class_label=1,
                class_index=self.accept_class_index,
                base_value=0.5,
                model_output=model_output,
                attribution_sum=sum(h_vals.values()),
                reconstructed_output=recon,
                additivity_error=add_err,
                additivity_status="FAIL",
                background_strategy="heuristic",
                degraded_mode=True,
                warning=f"SHAP explanation failed ({kernel_exc}); heuristic used."
            )

    def compute_shap(self, X: pd.DataFrame) -> Dict[str, float]:
        """Backward-compatible wrapper returning only the dict of feature attributions."""
        return self.compute_attribution(X).shap_values

    def _heuristic_attribution(self, X: pd.DataFrame) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for name in self.feature_names:
            val = float(X[name].iloc[0]) if name in X.columns else 0.0
            neutral_val = float(self._neutral_baseline[name].iloc[0]) if name in self._neutral_baseline.columns else 0.5

            if name in _SEMANTIC_SCORE_KEYS:
                result[name] = round((val - neutral_val) * 0.15, 6)
            elif name.endswith(_RULE_PASS_SUFFIX):
                result[name] = round((val - neutral_val) * 0.10, 6)
            elif name in _RULE_FAIL_COUNTERS:
                result[name] = round(-val * 0.05, 6)
            else:
                result[name] = round((val - neutral_val) * 0.01, 6)
        return result
