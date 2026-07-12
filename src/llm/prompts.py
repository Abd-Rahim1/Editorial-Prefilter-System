from typing import Dict, Any


def build_prompt_v1(sections: Dict[str, str], features: Dict[str, Any], full_text: str = "", layer1_violations: list = None) -> str:
    layer1_violations = layer1_violations or []
    return f"""
You are an expert scientific editor assisting with manuscript pre-filtering.

Evaluate the manuscript using these criteria:
- abstract_clarity
- structural_completeness
- methodological_strength
- experimental_strength
- argumentative_quality
- scope_alignment
- overall_quality

IMPORTANT:
- All scores MUST be floats between 0.0 and 1.0
- 0.0 = very poor
- 0.5 = average
- 1.0 = excellent
- Do NOT use integers from 1 to 10
- Do NOT use words such as High, Low, Moderate
- Return ONLY valid JSON

Return this JSON schema:
{{
  "abstract_clarity": 0.0,
  "structural_completeness": 0.0,
  "methodological_strength": 0.0,
  "experimental_strength": 0.0,
  "argumentative_quality": 0.0,
  "scope_alignment": 0.0,
  "overall_quality": 0.0,
  "detected_issues": [],
  "evidence_spans": [
    {{"section": "", "reason": ""}}
  ]
}}

Layer 1 detected the following issues:
{layer1_violations}

Full extracted manuscript text sample:
{full_text}

Important instructions:
If Layer 1 marks a section as missing (especially methodology), verify whether equivalent content exists elsewhere.

Possible alternative section names include:
* Method
* Methodology
* Approach
* Proposed Approach
* Model
* Architecture
* Framework
* Algorithm
* Experimental Setup
* Implementation Details

Do NOT blindly repeat Layer 1 findings.
Use the full text sample to confirm or correct them.

TITLE:
{sections.get("title", "")}

ABSTRACT:
{sections.get("abstract", "")}

INTRODUCTION:
{sections.get("introduction", "")}

METHODOLOGY:
{sections.get("methodology", "")}

EXPERIMENTS:
{sections.get("experiments", "")}

CONCLUSIONS:
{sections.get("conclusions", "")}

EDITORIAL FEATURES:
{features}
""".strip()


def build_prompt_v2(sections: Dict[str, str], features: Dict[str, Any], full_text: str = "", layer1_violations: list = None) -> str:
    layer1_violations = layer1_violations or []
    return f"""
You are a strict academic editor performing early editorial screening for a scientific venue.

Evaluate the manuscript using the following criteria:
1. abstract_clarity
2. structural_completeness
3. methodological_strength
4. experimental_strength
5. argumentative_quality
6. scope_alignment
7. overall_quality

Scoring rules:
- All scores MUST be floats between 0.0 and 1.0
- 0.0 = unacceptable
- 0.5 = acceptable but weak
- 1.0 = excellent
- Do NOT use integers from 1 to 10
- Do NOT use labels such as High, Low, Moderate
- Penalize missing or empty critical sections
- Penalize weak methodology, vague experiments, unsupported claims, or inconsistent structure
- Reward clear problem definition, strong method, coherent evidence, and aligned conclusions
- Return ONLY valid JSON

JSON schema:
{{
  "abstract_clarity": 0.0,
  "structural_completeness": 0.0,
  "methodological_strength": 0.0,
  "experimental_strength": 0.0,
  "argumentative_quality": 0.0,
  "scope_alignment": 0.0,
  "overall_quality": 0.0,
  "layer1_verification": {{
    "methodology_missing_confirmed": true,
    "methodology_like_content_found_elsewhere": false,
    "location": "",
    "explanation": ""
  }},
  "detected_issues": [],
  "evidence_spans": [
    {{"section": "", "reason": ""}}
  ]
}}

Layer 1 detected the following issues:
{layer1_violations}

Full extracted manuscript text sample:
{full_text}

Important instructions:
If Layer 1 marks a section as missing (especially methodology), verify whether equivalent content exists elsewhere.

Possible alternative section names include:
* Method
* Methodology
* Approach
* Proposed Approach
* Model
* Architecture
* Framework
* Algorithm
* Experimental Setup
* Implementation Details

Do NOT blindly repeat Layer 1 findings.
Use the full text sample to confirm or correct them.

MANUSCRIPT SECTIONS:
{sections}

EDITORIAL FEATURES:
{features}
""".strip()


def build_prompt_v3(
    sections: Dict[str, str],
    features: Dict[str, Any],
    full_text: str = "",
    layer1_violations: list = None,
) -> str:
    layer1_violations = layer1_violations or []

    return f"""
You are a strict, skeptical academic reviewer and research-integrity reviewer.

Your goal is NOT to reject the manuscript automatically.
Your goal is to identify editorial, methodological, reproducibility, and integrity concerns.

Think like a human peer reviewer:
- Do not blindly trust Layer 1.
- Do not blindly repeat Layer 1 findings.
- Verify whether missing sections have equivalent content elsewhere.
- Challenge strong claims against the evidence.
- Identify limitations, contradictions, weak methodology, weak experiments, and reproducibility risks.
- Do NOT claim the paper is fake with certainty.

IMPORTANT:
Return ONLY valid JSON.
Do not include markdown.
Do not include explanations outside JSON.

All numeric scores MUST be floats between 0.0 and 1.0.

Score meanings:
- suspicious_score: 0.0 = not suspicious, 1.0 = highly suspicious
- credibility_score: 0.0 = very low credibility, 1.0 = high credibility
- evidence_strength: 0.0 = no useful evidence, 1.0 = strong evidence
- coherence_score: 0.0 = incoherent, 1.0 = highly coherent
- reproducibility_score: 0.0 = not reproducible, 1.0 = highly reproducible
- theoretical_rigor_score: 0.0 = weak theory, 1.0 = strong theory

You MUST analyze these issue types:
- methodology
- experimental_design
- theoretical_rigor
- claim_validity
- reproducibility
- scope_limitations
- structural_clarity
- extraction_artifacts

Return this exact JSON structure:

{{
  "suspicious_score": 0.0,
  "credibility_score": 0.0,
  "evidence_strength": 0.0,
  "coherence_score": 0.0,
  "reproducibility_score": 0.0,
  "theoretical_rigor_score": 0.0,

  "layer1_verification": {{
    "methodology_missing_confirmed": true,
    "methodology_like_content_found_elsewhere": false,
    "locations": [
      {{
        "section": "",
        "role": ""
      }}
    ],
    "explanation": ""
  }},

  "detected_integrity_issues": [
    {{
      "type": "methodology",
      "severity": "low",
      "description": "",
      "impact": ""
    }}
  ],

  "claim_validation": [
    {{
      "claim": "",
      "support_level": 0.0,
      "issue": ""
    }}
  ],

  "evidence_spans": [
    {{
      "section": "",
      "evidence_type": "theoretical",
      "strength": "medium",
      "reason": ""
    }}
  ],

  "recommendation": "manual_review"
}}

Allowed severity values:
- "low"
- "medium"
- "high"

Allowed recommendation values:
- "low_concern"
- "manual_review"
- "high_concern"

Allowed evidence_type values:
- "methodology"
- "theoretical"
- "empirical"
- "structural"
- "reproducibility"
- "claim_validation"

Layer 1 detected the following issues:
{layer1_violations}

Important Layer 1 verification rule:
If Layer 1 marks methodology as missing, search for equivalent methodology-like content in:
- Method
- Methodology
- Approach
- Proposed Approach
- Model
- Architecture
- Framework
- Algorithm
- Experimental Setup
- Implementation Details
- Sections describing equations, algorithms, training procedure, verification procedure, or implementation details

Full extracted manuscript text sample:
{full_text}

MANUSCRIPT SECTIONS:
{sections}

EDITORIAL FEATURES:
{features}
""".strip()
  
def build_prompt_v4(
    sections: Dict[str, str],
    features: Dict[str, Any],
    full_text: str = "",
    layer1_violations: list = None,
) -> str:
    layer1_violations = layer1_violations or []

    return f"""
You are a thesis-grade scientific editorial reviewer.

Your task:
Evaluate the manuscript for early editorial pre-filtering using ONLY the provided manuscript text, extracted sections, Layer 1 findings, and editorial features.

Do NOT:
- invent missing information
- hallucinate citations
- claim the paper is fake with certainty
- blindly repeat Layer 1 findings
- reward or penalize based only on section names

You MUST:
- verify whether Layer 1 findings are substantively correct
- distinguish missing section headers from missing methodological content
- identify strengths, weaknesses, limitations, and reproducibility risks
- produce stable numeric scores for downstream machine-learning calibration
- return ONLY valid JSON

Scoring scale:
All scores MUST be floats between 0.0 and 1.0.

Score definitions:
- abstract_clarity: clarity of abstract, problem, contribution, and outcome
- structural_completeness: completeness of manuscript organization and section coverage
- methodological_strength: quality and detail of method, model, algorithm, or approach
- experimental_strength: quality of experiments, baselines, metrics, and evidence
- argumentative_quality: logical connection between claims, evidence, and conclusions
- scope_alignment: fit between paper scope, venue expectations, and claimed contribution
- overall_quality: holistic editorial quality
- suspicious_score: 0.0 = low concern, 1.0 = high concern
- credibility_score: 0.0 = low credibility, 1.0 = high credibility
- evidence_strength: 0.0 = weak evidence, 1.0 = strong evidence
- coherence_score: 0.0 = incoherent, 1.0 = coherent
- reproducibility_score: 0.0 = hard to reproduce, 1.0 = easy to reproduce
- theoretical_rigor_score: 0.0 = weak theory, 1.0 = strong theory

Return this exact JSON structure:

{{
  "abstract_clarity": 0.0,
  "structural_completeness": 0.0,
  "methodological_strength": 0.0,
  "experimental_strength": 0.0,
  "argumentative_quality": 0.0,
  "scope_alignment": 0.0,
  "overall_quality": 0.0,

  "suspicious_score": 0.0,
  "credibility_score": 0.0,
  "evidence_strength": 0.0,
  "coherence_score": 0.0,
  "reproducibility_score": 0.0,
  "theoretical_rigor_score": 0.0,

  "layer1_verification": {{
    "methodology_missing_confirmed": false,
    "methodology_like_content_found_elsewhere": false,
    "locations": [
      {{
        "section": "",
        "role": ""
      }}
    ],
    "explanation": ""
  }},

  "detected_issues": [
    {{
      "type": "methodology",
      "severity": "low",
      "description": "",
      "impact": ""
    }}
  ],

  "claim_validation": [
    {{
      "claim": "",
      "support_level": 0.0,
      "issue": ""
    }}
  ],

  "evidence_spans": [
    {{
      "section": "",
      "evidence_type": "methodology",
      "strength": "medium",
      "reason": ""
    }}
  ],

  "final_layer2_decision": "review_needed",
  "recommendation": "manual_review"
}}

Allowed issue type values:
- methodology
- experimental_design
- theoretical_rigor
- claim_validity
- reproducibility
- scope_limitations
- structural_clarity
- extraction_artifacts
- writing_quality

Allowed severity values:
- low
- medium
- high

Allowed evidence_type values:
- methodology
- theoretical
- empirical
- structural
- reproducibility
- claim_validation

Allowed final_layer2_decision values:
- low_concern
- review_needed
- high_concern

Allowed recommendation values:
- low_concern
- manual_review
- high_concern

Layer 1 detected the following issues:
{layer1_violations}

Layer 1 verification rule:
If Layer 1 marks methodology as missing, check whether equivalent content exists in sections such as:
Method, Methodology, Approach, Proposed Approach, Model, Architecture, Framework, Algorithm, Experimental Setup, Implementation Details, equations, algorithms, training procedures, verification procedures, or implementation details.

If methodology content exists under another name, set:
"methodology_missing_confirmed": false
"methodology_like_content_found_elsewhere": true

Full extracted manuscript text sample:
{full_text}

MANUSCRIPT SECTIONS:
{sections}

EDITORIAL FEATURES:
{features}
""".strip()

def build_prompt_v5(
    sections: Dict[str, str],
    features: Dict[str, Any],
    full_text: str = "",
    layer1_violations: list = None,
) -> str:
    layer1_violations = layer1_violations or []

    return f"""
You are a strict scientific integrity reviewer and PDF validity checker.

Your task:
Evaluate whether the submitted PDF appears to be a real scientific research paper and whether it contains enough academic content for editorial review.

Important:
- Do NOT claim the paper is fake with certainty.
- Only identify risk signals.
- Base all judgments ONLY on the provided text, sections, Layer 1 findings, and editorial features.
- Do NOT hallucinate missing content.
- Return ONLY valid JSON.
- Do not use markdown.

All scores MUST be floats between 0.0 and 1.0.

Score meanings:
- research_paper_likelihood: 0.0 = unlikely research paper, 1.0 = clearly research paper
- integrity_risk_score: 0.0 = low risk, 1.0 = high risk
- pdf_extraction_quality: 0.0 = unusable extraction, 1.0 = clean extraction
- structure_validity_score: 0.0 = invalid structure, 1.0 = valid academic structure
- equation_quality_score: 0.0 = equations absent/broken/unexplained, 1.0 = equations meaningful and explained
- citation_quality_score: 0.0 = weak/fake-looking references, 1.0 = credible academic citation structure
- content_coherence_score: 0.0 = incoherent, 1.0 = coherent
- reproducibility_signal_score: 0.0 = no reproducibility information, 1.0 = strong reproducibility details

Return this exact JSON structure:

{{
  "research_paper_likelihood": 0.0,
  "integrity_risk_score": 0.0,
  "pdf_extraction_quality": 0.0,
  "structure_validity_score": 0.0,
  "equation_quality_score": 0.0,
  "citation_quality_score": 0.0,
  "content_coherence_score": 0.0,
  "reproducibility_signal_score": 0.0,

  "is_probably_research_paper": true,

  "layer1_verification": {{
    "methodology_missing_confirmed": false,
    "methodology_like_content_found_elsewhere": false,
    "locations": [
      {{
        "section": "",
        "role": ""
      }}
    ],
    "explanation": ""
  }},

  "integrity_flags": [
    {{
      "type": "structure_issue",
      "severity": "low",
      "description": "",
      "evidence": ""
    }}
  ],

  "equation_analysis": {{
    "equations_detected": false,
    "equations_referenced_in_text": false,
    "variables_explained": false,
    "issues": []
  }},

  "citation_analysis": {{
    "references_detected": false,
    "in_text_citations_detected": false,
    "issues": []
  }},

  "research_paper_checks": {{
    "has_title": false,
    "has_abstract": false,
    "has_introduction": false,
    "has_method_or_approach": false,
    "has_experiments_or_results": false,
    "has_conclusion": false,
    "has_references": false
  }},

  "final_integrity_decision": "review_needed",
  "recommendation": "manual_review"
}}

Allowed integrity flag types:
- structure_issue
- extraction_artifact
- equation_issue
- citation_issue
- coherence_issue
- reproducibility_issue
- suspicious_content
- non_research_document

Allowed severity values:
- low
- medium
- high

Allowed final_integrity_decision values:
- valid_research_paper
- review_needed
- high_integrity_risk
- not_research_paper

Allowed recommendation values:
- low_concern
- manual_review
- high_concern

Layer 1 detected the following issues:
{layer1_violations}

Layer 1 verification rule:
If Layer 1 marks methodology as missing, check whether equivalent content exists in:
Method, Methodology, Approach, Proposed Approach, Model, Architecture, Framework, Algorithm, Experimental Setup, Implementation Details, equations, algorithms, training procedures, or implementation details.

If methodology content exists under another name, set:
"methodology_missing_confirmed": false
"methodology_like_content_found_elsewhere": true

PDF / manuscript text:
{full_text}

MANUSCRIPT SECTIONS:
{sections}

EDITORIAL FEATURES:
{features}
""".strip()

def get_prompt_builder(version: str):
    builders = {
        "v1": build_prompt_v1,
        "v2": build_prompt_v2,
        "v3": build_prompt_v3,
        "v4": build_prompt_v4,
        "v5": build_prompt_v5,
    }

    if version not in builders:
        raise ValueError(f"Unknown prompt version: {version}")

    return builders[version]