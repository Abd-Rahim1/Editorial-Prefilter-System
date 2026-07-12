from typing import Dict, Any


def run_mock_qwen_scoring(sections: Dict[str, str], features: Dict[str, Any]) -> Dict[str, Any]:
    abstract = sections.get("abstract", "") or ""
    methodology = sections.get("methodology", "") or ""
    experiments = sections.get("experiments", "") or ""

    issues = []
    abstract_score = 0.8 if len(abstract.split()) >= 100 else 0.4
    methodology_score = 0.8 if len(methodology.split()) >= 100 else 0.3
    experiments_score = 0.8 if len(experiments.split()) >= 100 else 0.3

    if abstract_score < 0.5:
        issues.append("weak_abstract_clarity")
    if methodology_score < 0.5:
        issues.append("missing_methodological_detail")
    if experiments_score < 0.5:
        issues.append("weak_experimental_validation")

    structural_completeness = 0.9
    argumentative_quality = 0.7
    scope_alignment = 0.8

    overall_quality = round(
        (
            abstract_score
            + structural_completeness
            + methodology_score
            + experiments_score
            + argumentative_quality
            + scope_alignment
        ) / 6.0,
        3,
    )

    evidence_spans = []
    if "weak_abstract_clarity" in issues:
        evidence_spans.append({
            "section": "abstract",
            "reason": "Abstract is too short or not sufficiently informative."
        })
    if "missing_methodological_detail" in issues:
        evidence_spans.append({
            "section": "methodology",
            "reason": "Methodology section is missing or too weak."
        })
    if "weak_experimental_validation" in issues:
        evidence_spans.append({
            "section": "experiments",
            "reason": "Experimental evidence is missing or limited."
        })

    return {
        "mode": "mock",
        "abstract_clarity": abstract_score,
        "structural_completeness": structural_completeness,
        "methodological_strength": methodology_score,
        "experimental_strength": experiments_score,
        "argumentative_quality": argumentative_quality,
        "scope_alignment": scope_alignment,
        "overall_quality": overall_quality,
        "detected_issues": issues,
        "evidence_spans": evidence_spans,
    }