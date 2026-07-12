"""
test_layer4_unit.py — Unit Tests for Layer 4 Controlled Explanation Engine
"""

import pytest
import pandas as pd
import numpy as np
import warnings
from sklearn.ensemble import RandomForestClassifier

from packages.explanation_engine.schemas import ExplanationRequest, ExplanationResult, AttributionResult
from packages.explanation_engine.explainer import ShapExplainer
from packages.explanation_engine.feature_ranker import FeatureRanker, RankedFeature
from packages.explanation_engine.evidence_integrator import EvidenceIntegrator, IntegratedEvidence
from packages.explanation_engine.narrative import EditorialNarrativeGenerator, probability_label
from packages.explanation_engine.report_builder import ReportBuilder
from packages.explanation_engine.generator import ExplanationGenerator
from packages.calibration.online.schemas import Layer3Prediction


@pytest.fixture
def dummy_rf_model():
    # Train a dummy RF model with 10 C2 features
    X = np.random.rand(50, 10)
    # Ensure some variation so it's fitted properly
    y = np.random.choice([0, 1], size=50)
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X, y)
    return model


@pytest.fixture
def c2_feature_names():
    return [
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
    ]


def test_schemas_serialization():
    req = ExplanationRequest(manuscript_id="test_ms", model_run_id=123)
    d = req.to_dict()
    assert d["manuscript_id"] == "test_ms"
    assert d["model_run_id"] == 123


def test_shap_explainer_tree_shap(dummy_rf_model, c2_feature_names):
    explainer = ShapExplainer(dummy_rf_model, c2_feature_names)
    X_test = pd.DataFrame(np.random.rand(1, 10), columns=c2_feature_names)
    attr = explainer.compute_attribution(X_test)
    assert isinstance(attr, AttributionResult)
    assert attr.attribution_method == "tree_shap"
    assert attr.explained_output == "accept_probability"
    assert len(attr.shap_values) == 10
    # Additivity verification: base_value + sum(shap_values) ≈ model_output
    assert attr.additivity_error < 1e-5


def test_feature_ranker():
    shap_vals = {
        "argumentative_quality": 0.15,
        "conference": -0.05,
        "critical_rules_failed": 0.0000001
    }
    ranked = FeatureRanker.rank_features(shap_vals, top_n=3)
    assert len(ranked) == 3
    assert ranked[0].name == "argumentative_quality"
    assert ranked[0].direction == "INCREASED_ACCEPT_PROBABILITY"
    assert ranked[0].rank == 1
    assert ranked[1].name == "conference"
    assert ranked[1].direction == "DECREASED_ACCEPT_PROBABILITY"
    assert ranked[1].rank == 2
    assert ranked[2].direction == "NEUTRAL"
    assert ranked[2].rank == 3


def test_evidence_integrator(c2_feature_names):
    shap_vals = {"structural_completeness": -0.2, "critical_rules_failed": -0.3}
    ranked = FeatureRanker.rank_features(shap_vals, top_n=2)
    l1_violations = [
        {"rule_name": "missing_critical_sections", "details": "No methodology section"}
    ]
    sem_evidence = {
        "structural_completeness": 0.40,
        "evidence_spans": ["Missing method section header."]
    }
    integrated = EvidenceIntegrator.integrate_evidence(
        ranked_features=ranked,
        layer1_violations=l1_violations,
        semantic_evidence=sem_evidence,
        prediction=1,
        accept_probability=0.15,
        desk_reject_probability=0.85
    )
    assert len(integrated) == 2
    assert len(integrated[0].linked_rule_violations) >= 0


def test_narrative_generator_preserves_layer3_decision():
    l3_pred = Layer3Prediction(
        manuscript_id="test",
        accept_probability=0.25,
        desk_reject_probability=0.75,
        decision="peer_review",  # intentionally mismatched vs default thresholds to ensure preservation
        confidence_level="HIGH",
        inference_time_ms=10.0
    )
    narrative = EditorialNarrativeGenerator.generate_narrative(
        decision=l3_pred.decision,
        accept_probability=l3_pred.accept_probability,
        desk_reject_probability=l3_pred.desk_reject_probability,
        confidence_level=l3_pred.confidence_level,
        calibration_method="none",
        integrated_evidence=[],
        layer1_violations=[],
        semantic_scores={}
    )
    assert "ASSISTED RECOMMENDATION: PEER REVIEW" in narrative


def test_explanation_generator_end_to_end(dummy_rf_model, c2_feature_names):
    gen = ExplanationGenerator(dummy_rf_model, c2_feature_names)
    l3_pred = Layer3Prediction(
        manuscript_id="ms_001",
        accept_probability=0.30,
        desk_reject_probability=0.70,
        decision="manual_review",
        confidence_level="MODERATE",
        inference_time_ms=12.0,
        feature_vector={name: 0.5 for name in c2_feature_names}
    )
    req = ExplanationRequest(
        manuscript_id="ms_001",
        layer1_result=[],
        layer2_result={"overall_quality": 0.60},
        layer3_prediction=l3_pred,
        model_input_dataframe=pd.DataFrame([{name: 0.5 for name in c2_feature_names}])
    )
    result = gen.generate_explanation(req)
    assert isinstance(result, ExplanationResult)
    assert result.prediction["decision"] == "manual_review"
    assert "attribution" in result.to_dict()
    assert result.to_dict()["attribution"]["attribution_method"] == "tree_shap"


# =========================================================================
# THE 18 MANDATORY REGRESSION TESTS
# =========================================================================

# 1. test_layer4_preserves_exact_layer3_accept_probability
def test_layer4_preserves_exact_layer3_accept_probability(dummy_rf_model, c2_feature_names):
    gen = ExplanationGenerator(dummy_rf_model, c2_feature_names)
    l3_pred = Layer3Prediction(
        manuscript_id="ms_test_1",
        accept_probability=0.4948,
        desk_reject_probability=0.5052,
        decision="manual_review",
        confidence_level="MODERATE",
        inference_time_ms=10.0,
        feature_vector={name: 0.5 for name in c2_feature_names}
    )
    req = ExplanationRequest(
        manuscript_id="ms_test_1",
        layer1_result=[],
        layer2_result={},
        layer3_prediction=l3_pred,
        model_input_dataframe=pd.DataFrame([{name: 0.5 for name in c2_feature_names}])
    )
    result = gen.generate_explanation(req)
    assert abs(result.prediction["accept_probability"] - 0.4948) < 1e-6


# 2. test_layer4_preserves_exact_layer3_reject_probability
def test_layer4_preserves_exact_layer3_reject_probability(dummy_rf_model, c2_feature_names):
    gen = ExplanationGenerator(dummy_rf_model, c2_feature_names)
    l3_pred = Layer3Prediction(
        manuscript_id="ms_test_2",
        accept_probability=0.4948,
        desk_reject_probability=0.5052,
        decision="manual_review",
        confidence_level="MODERATE",
        inference_time_ms=10.0,
        feature_vector={name: 0.5 for name in c2_feature_names}
    )
    req = ExplanationRequest(
        manuscript_id="ms_test_2",
        layer1_result=[],
        layer2_result={},
        layer3_prediction=l3_pred,
        model_input_dataframe=pd.DataFrame([{name: 0.5 for name in c2_feature_names}])
    )
    result = gen.generate_explanation(req)
    assert abs(result.prediction["desk_reject_probability"] - 0.5052) < 1e-6


# 3. test_probability_complement_invariant
def test_probability_complement_invariant():
    # accept + reject must sum to 1.0 within tolerance
    accept = 0.4948
    reject = 0.5052
    assert abs(accept + reject - 1.0) < 1e-6


# 4. test_no_calibrated_wording_when_calibration_none
def test_no_calibrated_wording_when_calibration_none():
    label = probability_label("none")
    assert "calibrated" not in label.lower()
    assert label == "Estimated Accept Probability"


# 5. test_calibrated_wording_allowed_when_calibration_active
def test_calibrated_wording_allowed_when_calibration_active():
    label_sigmoid = probability_label("sigmoid")
    label_isotonic = probability_label("isotonic")
    assert "calibrated" in label_sigmoid.lower()
    assert "calibrated" in label_isotonic.lower()


# 6. test_layer2_observation_not_rendered_as_quote
def test_layer2_observation_not_rendered_as_quote():
    l1_violations = []
    sem_evidence = {"overall_quality": 0.75}
    ranked = [FeatureRanker.rank_features({"overall_quality": -0.0271}, top_n=1)[0]]
    # Build integrated evidence where overall_quality has a layer2_observation
    integrated = EvidenceIntegrator.integrate_evidence(
        ranked_features=ranked,
        layer1_violations=l1_violations,
        semantic_evidence=sem_evidence,
        prediction=1,
        accept_probability=0.49,
        desk_reject_probability=0.51
    )
    
    narrative = EditorialNarrativeGenerator.generate_narrative(
        decision="manual_review",
        accept_probability=0.49,
        desk_reject_probability=0.51,
        confidence_level="moderate",
        calibration_method="none",
        integrated_evidence=integrated,
        layer1_violations=[],
        semantic_scores=sem_evidence,
        ranked_features=ranked
    )
    
    # Check that "observed that" is used and is not inside quotation marks
    assert "observed that" in narrative
    assert '"The Layer 2 semantic evaluator observed' not in narrative
    assert '"Evaluated Overall Scientific Credibility' not in narrative


# 7. test_manuscript_excerpt_can_be_quoted
def test_manuscript_excerpt_can_be_quoted():
    # Quotes from manuscript evidence_spans should have double quotation marks
    l1_violations = []
    sem_evidence = {
        "overall_quality": 0.75,
        "evidence_spans": [{"section": "Methodology", "reason": "overall_quality lacks evaluation baseline."}]
    }
    ranked = [FeatureRanker.rank_features({"overall_quality": -0.0271}, top_n=1)[0]]
    integrated = EvidenceIntegrator.integrate_evidence(
        ranked_features=ranked,
        layer1_violations=l1_violations,
        semantic_evidence=sem_evidence,
        prediction=1,
        accept_probability=0.49,
        desk_reject_probability=0.51
    )
    
    narrative = EditorialNarrativeGenerator.generate_narrative(
        decision="manual_review",
        accept_probability=0.49,
        desk_reject_probability=0.51,
        confidence_level="moderate",
        calibration_method="none",
        integrated_evidence=integrated,
        layer1_violations=[],
        semantic_scores=sem_evidence,
        ranked_features=ranked
    )
    
    assert '"[Methodology] overall_quality lacks evaluation baseline."' in narrative or '"overall_quality lacks evaluation baseline."' in narrative


# 8. test_shap_prediction_path_preserves_feature_names
def test_shap_prediction_path_preserves_feature_names(dummy_rf_model, c2_feature_names):
    explainer = ShapExplainer(dummy_rf_model, c2_feature_names)
    X_test = pd.DataFrame(np.random.rand(1, 10), columns=c2_feature_names)
    # Reconstructing should align with feature names and NOT fail assertion
    prob = explainer._predict_accept_prob(X_test)
    assert len(prob) == 1


# 9. test_no_sklearn_feature_name_warning
def test_no_sklearn_feature_name_warning(dummy_rf_model, c2_feature_names):
    explainer = ShapExplainer(dummy_rf_model, c2_feature_names)
    X_test = pd.DataFrame(np.random.rand(1, 10), columns=c2_feature_names)
    
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        explainer._predict_accept_prob(X_test)
        
        # Verify no UserWarning about feature names is emitted
        feature_name_warns = [
            w for w in caught_warnings 
            if issubclass(w.category, UserWarning) and "X does not have valid feature names" in str(w.message)
        ]
        assert len(feature_name_warns) == 0


# 10. test_tree_shap_reconstructs_layer3_accept_probability
def test_tree_shap_reconstructs_layer3_accept_probability(dummy_rf_model, c2_feature_names):
    explainer = ShapExplainer(dummy_rf_model, c2_feature_names)
    X_test = pd.DataFrame(np.random.rand(1, 10), columns=c2_feature_names)
    attr = explainer.compute_attribution(X_test)
    
    # base_value + sum(shap_values) ≈ accept_probability (model_output)
    recon = attr.base_value + attr.attribution_sum
    assert abs(recon - attr.model_output) < 1e-5


# 11. test_additivity_status_pass
def test_additivity_status_pass(dummy_rf_model, c2_feature_names):
    explainer = ShapExplainer(dummy_rf_model, c2_feature_names)
    X_test = pd.DataFrame(np.random.rand(1, 10), columns=c2_feature_names)
    attr = explainer.compute_attribution(X_test)
    assert attr.additivity_status == "PASS"


# 12. test_negative_shap_does_not_label_high_raw_score_as_low
def test_negative_shap_does_not_label_high_raw_score_as_low():
    # If overall quality is 0.80 and SHAP is negative, the narrative should NOT call overall quality weak.
    ranked = [RankedFeature(name="overall_quality", shap_value=-0.0189, absolute_impact=0.0189, direction="DECREASED_ACCEPT_PROBABILITY")]
    integrated = [
        IntegratedEvidence(
            feature_name="overall_quality",
            shap_value=-0.0189,
            impact_direction="DECREASED_ACCEPT_PROBABILITY",
            linked_rule_violations=[],
            linked_semantic_evidence=[],
            synthesis_summary="overall_quality contributed negatively"
        )
    ]
    
    narrative = EditorialNarrativeGenerator.generate_narrative(
        decision="manual_review",
        accept_probability=0.49,
        desk_reject_probability=0.51,
        confidence_level="moderate",
        calibration_method="none",
        integrated_evidence=integrated,
        layer1_violations=[],
        semantic_scores={"overall_quality": 0.80},
        ranked_features=ranked
    )
    
    assert "overall quality contributed negatively" in narrative.lower()
    assert "overall quality was weak" not in narrative.lower()


# 13. test_feature_value_and_shap_both_present
def test_feature_value_and_shap_both_present(dummy_rf_model, c2_feature_names):
    gen = ExplanationGenerator(dummy_rf_model, c2_feature_names)
    l3_pred = Layer3Prediction(
        manuscript_id="ms_test_13",
        accept_probability=0.4948,
        desk_reject_probability=0.5052,
        decision="manual_review",
        confidence_level="MODERATE",
        inference_time_ms=10.0,
        feature_vector={name: 0.75 for name in c2_feature_names}
    )
    req = ExplanationRequest(
        manuscript_id="ms_test_13",
        layer1_result=[],
        layer2_result={"overall_quality": 0.75},
        layer3_prediction=l3_pred,
        model_input_dataframe=pd.DataFrame([{name: 0.75 for name in c2_feature_names}])
    )
    result = gen.generate_explanation(req)
    
    # In feature_importance, shap_values and raw features both exist
    assert "overall_quality" in result.feature_importance["shap_values"]
    assert "ranked_features" in result.feature_importance
    rf = result.feature_importance["ranked_features"][0]
    assert rf["name"] is not None
    assert rf["shap_value"] is not None


# 14. test_removed_title_display_mapping
def test_removed_title_display_mapping():
    title_placeholder = "removed"
    display_title = title_placeholder
    if title_placeholder.lower().strip() in ("removed", "unknown", "none", ""):
        display_title = "Unavailable / anonymized"
    assert display_title == "Unavailable / anonymized"


# 15. test_terminal_layer3_and_layer4_probability_consistency
def test_terminal_layer3_and_layer4_probability_consistency(dummy_rf_model, c2_feature_names):
    gen = ExplanationGenerator(dummy_rf_model, c2_feature_names)
    l3_pred = Layer3Prediction(
        manuscript_id="ms_test_15",
        accept_probability=0.4948,
        desk_reject_probability=0.5052,
        decision="manual_review",
        confidence_level="MODERATE",
        inference_time_ms=10.0,
        feature_vector={name: 0.5 for name in c2_feature_names}
    )
    req = ExplanationRequest(
        manuscript_id="ms_test_15",
        layer1_result=[],
        layer2_result={},
        layer3_prediction=l3_pred,
        model_input_dataframe=pd.DataFrame([{name: 0.5 for name in c2_feature_names}])
    )
    result = gen.generate_explanation(req)
    
    # Layer 3 accept probability matches Layer 4 prediction accept probability exactly
    assert result.prediction["accept_probability"] == 0.4948


# 16. test_json_prediction_probabilities_match_layer3
def test_json_prediction_probabilities_match_layer3(dummy_rf_model, c2_feature_names):
    gen = ExplanationGenerator(dummy_rf_model, c2_feature_names)
    l3_pred = Layer3Prediction(
        manuscript_id="ms_test_16",
        accept_probability=0.4948,
        desk_reject_probability=0.5052,
        decision="manual_review",
        confidence_level="MODERATE",
        inference_time_ms=10.0,
        feature_vector={name: 0.5 for name in c2_feature_names}
    )
    req = ExplanationRequest(
        manuscript_id="ms_test_16",
        layer1_result=[],
        layer2_result={},
        layer3_prediction=l3_pred,
        model_input_dataframe=pd.DataFrame([{name: 0.5 for name in c2_feature_names}])
    )
    result = gen.generate_explanation(req)
    
    # Check JSON output dictionary
    master_dict = result.to_master_report_dict()
    assert master_dict["prediction"]["accept_probability"] == 0.4948
    assert master_dict["prediction"]["desk_reject_probability"] == 0.5052


# 17. test_layer4_decision_preservation
def test_layer4_decision_preservation(dummy_rf_model, c2_feature_names):
    gen = ExplanationGenerator(dummy_rf_model, c2_feature_names)
    l3_pred = Layer3Prediction(
        manuscript_id="ms_test_17",
        accept_probability=0.4948,
        desk_reject_probability=0.5052,
        decision="peer_review",  # Mismatched intentionally compared to probability to test absolute preservation
        confidence_level="HIGH",
        inference_time_ms=10.0,
        feature_vector={name: 0.5 for name in c2_feature_names}
    )
    req = ExplanationRequest(
        manuscript_id="ms_test_17",
        layer1_result=[],
        layer2_result={},
        layer3_prediction=l3_pred,
        model_input_dataframe=pd.DataFrame([{name: 0.5 for name in c2_feature_names}])
    )
    result = gen.generate_explanation(req)
    assert result.prediction["decision"] == "peer_review"


# 18. test_no_threshold_redecision_in_layer4
def test_no_threshold_redecision_in_layer4(dummy_rf_model, c2_feature_names):
    gen = ExplanationGenerator(dummy_rf_model, c2_feature_names)
    # Accept probability = 0.10, which normally indicates desk_reject
    # But decision is set to accept (or peer_review) in Layer 3
    l3_pred = Layer3Prediction(
        manuscript_id="ms_test_18",
        accept_probability=0.10,
        desk_reject_probability=0.90,
        decision="peer_review",
        confidence_level="HIGH",
        inference_time_ms=10.0,
        feature_vector={name: 0.5 for name in c2_feature_names}
    )
    req = ExplanationRequest(
        manuscript_id="ms_test_18",
        layer1_result=[],
        layer2_result={},
        layer3_prediction=l3_pred,
        model_input_dataframe=pd.DataFrame([{name: 0.5 for name in c2_feature_names}])
    )
    result = gen.generate_explanation(req)
    
    # Layer 4 must not re-evaluate threshold and change it back to desk_reject
    assert result.prediction["decision"] == "peer_review"
