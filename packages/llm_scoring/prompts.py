from typing import Dict, Any


def build_prompt_v1(sections: Dict[str, str], features: Dict[str, Any] = None, full_text: str = "", layer1_violations: list = None) -> str:
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

Full extracted manuscript text sample:
{full_text[:20000]}

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

import json

class PromptBuilderV5:
    def build(self, text: str, sections: dict, layer1_violations: list) -> str:
        
        # Format the deterministic Layer 1 flags for the LLM to read
        if layer1_violations:
            violations_text = json.dumps(layer1_violations, indent=2)
        else:
            violations_text = "None detected. The document structure is perfectly compliant."

        return f"""You are an objective, expert scientific reviewer for a top-tier conference.
Your task is to evaluate this manuscript for its underlying academic and semantic merit.

### EVALUATION GUIDELINES:
- Evaluate the scientific content independently of minor formatting or layout errors.
- Use the full 0.00 to 1.00 scale objectively. 
  * 0.80 - 1.00: Excellent, highly rigorous, clear baseline comparisons.
  * 0.50 - 0.70: Average to Good, standard academic contribution.
  * 0.00 - 0.40: Poor, lacks scientific rigor, highly vague.
- Our deterministic parser flagged the following structural violations:
{violations_text}
- Do NOT automatically fail the paper for these violations. Instead, check if the content actually exists under different headings (e.g. if 'Methodology' is missing, check for 'Approach' or 'Model' in the text).

### MANUSCRIPT TEXT:
{text[:20000]}

### INSTRUCTIONS:
Provide a JSON response EXACTLY matching the schema below. All scores must be floats between 0.00 and 1.00.
For any score below 0.50, you MUST extract a short direct quote or specific reason and place it in the `evidence_spans` array.

{{
  "abstract_clarity": 0.0,
  "structural_completeness": 0.0,
  "methodological_strength": 0.0,
  "experimental_strength": 0.0,
  "argumentative_quality": 0.0,
  "scope_alignment": 0.0,
  "overall_quality": 0.0,
  "detected_issues": [
    "missing_baseline_comparisons"
  ],
  "evidence_spans": [
    {{
      "section": "experiments",
      "reason": "No baseline model was used for comparison."
    }}
  ]
}}
"""

    def __call__(self, sections: dict, features: dict = None, full_text: str = "", layer1_violations: list = None) -> str:
        """Enables object callable execution compatibility across pipeline clients."""
        return self.build(
            text=full_text,
            sections=sections,
            layer1_violations=layer1_violations
        )

class PromptBuilderFreeText:
    def build(self, text: str, sections: dict, layer1_violations: list = None) -> str:
        return f"""You are an objective, expert scientific reviewer for a top-tier academic conference.
Your task is to write a detailed, natural language critique essay evaluating this manuscript's scientific quality and academic contributions.

### MANUSCRIPT TEXT:
{text[:20000]}

### EVALUATION INSTRUCTIONS:
1. Write a professional academic critique of the manuscript's methodology, experiments, structure, and clarity.
2. Discuss both strengths and weaknesses in detail.
3. At the absolute end of your response, you MUST provide a score block mapping your quantitative ratings (floats between 0.00 and 1.00) using the exact plain-text template below. Do not put any markdown fences around this block.

[SCORES]
abstract_clarity: <score>
structural_completeness: <score>
methodological_strength: <score>
experimental_strength: <score>
argumentative_quality: <score>
scope_alignment: <score>
overall_quality: <score>
[END SCORES]
"""

    def __call__(self, sections: dict, features: dict = None, full_text: str = "", layer1_violations: list = None) -> str:
        return self.build(full_text, sections, layer1_violations)

class PromptBuilderV1:
    def __call__(self, sections: dict, features: dict = None, full_text: str = "", layer1_violations: list = None) -> str:
        return build_prompt_v1(sections, features, full_text, layer1_violations)

def get_prompt_builder(version: str):
    if not version:
        return PromptBuilderV5()
    v_lower = str(version).lower()
    if any(k in v_lower for k in ["v5", "calibrated", "json", "v5.0"]):
        return PromptBuilderV5()
    elif any(k in v_lower for k in ["v1", "v1.0"]):
        return PromptBuilderV1()
    elif any(k in v_lower for k in ["freetext", "freeform", "v6"]):
        return PromptBuilderFreeText()
    # Fallback to V5 instead of raising ValueError if database has a custom name
    return PromptBuilderV5()