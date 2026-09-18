import os
import json
import re
import time
import logging
from typing import Dict, Any, Optional

import requests

logger = logging.getLogger("QwenClient")

from llm_scoring.mock_qwen import run_mock_qwen_scoring
from llm_scoring.prompts import get_prompt_builder


QWEN_API_URL = os.getenv("OLLAMA_URL", "http://sinbad2ia.ujaen.es:8050/api/chat")


def get_qwen_model() -> str:
    try:
        from database.config_repository import ConfigRepository
        llm_cfg = ConfigRepository().get_active_llm()
        return llm_cfg.get("model_identifier") or "qwen3:4b"
    except Exception:
        return "qwen3:4b"


class _ModelProxy(str):
    def __new__(cls, *args, **kwargs):
        return str.__new__(cls, get_qwen_model())
    def __str__(self):
        return get_qwen_model()
    def __repr__(self):
        return repr(get_qwen_model())
    def __eq__(self, other):
        return get_qwen_model() == other
    def __hash__(self):
        return hash(get_qwen_model())


QWEN_MODEL = _ModelProxy()


def clean_llm_json(raw_output: str) -> str:
    text = raw_output.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON object found in LLM output")

    return text[start:end + 1]

def try_parse_embedded_json(raw_output: str) -> dict:
    if not raw_output or not isinstance(raw_output, str):
        return {}

    try:
        nested_cleaned = clean_llm_json(raw_output)
        nested = json.loads(nested_cleaned)
        return nested if isinstance(nested, dict) else {}
    except json.JSONDecodeError:
        return {}


def parse_llm_output(raw_output: str) -> dict:
    cleaned = clean_llm_json(raw_output)
    parsed = json.loads(cleaned)

    if isinstance(parsed, dict):
        nested_payload = None
        if isinstance(parsed.get("raw_output"), str):
            nested_payload = parsed["raw_output"]
        elif isinstance(parsed.get("llm_text"), str):
            nested_payload = parsed["llm_text"]

        if nested_payload:
            nested = try_parse_embedded_json(nested_payload)
            if nested:
                parsed.pop("raw_output", None)
                parsed.pop("llm_text", None)
                parsed.update(nested)

    return parsed


def run_qwen_scoring(
    sections: Dict[str, str],
    features: Dict[str, Any],
    mode: str = "real",
    prompt_version: Optional[str] = None,
    full_text: str = "",
    layer1_violations: list = None,
    model: Optional[str] = None,
    llm_config: Optional[Dict] = None,
    prompt_config: Optional[Dict] = None,
    timeout_sec: int = 120,
    max_retries: int = 3,
) -> Dict[str, Any]:
    if mode not in ("mock", "real"):
        raise ValueError(f"Unsupported mode: {mode}")

    if not llm_config and not model:
        try:
            from database.config_repository import ConfigRepository
            llm_config = ConfigRepository().get_active_llm()
        except Exception:
            llm_config = {}

    if not prompt_config and (not prompt_version or prompt_version == "v5"):
        try:
            from database.config_repository import ConfigRepository
            prompt_config = ConfigRepository().get_active_prompt()
        except Exception:
            prompt_config = {}

    active_model = model or (llm_config.get("model_identifier") if llm_config else None) or get_qwen_model()
    active_prompt_ver = prompt_version
    if prompt_config:
        active_prompt_ver = prompt_config.get("name") or prompt_config.get("version") or prompt_version or "v5"
    if not active_prompt_ver:
        active_prompt_ver = "v5"

    layer1_violations = layer1_violations or []
    full_text_sample = full_text[:20000]

    prompt_builder = get_prompt_builder(active_prompt_ver)
    prompt = prompt_builder(
        sections, 
        features, 
        full_text=full_text_sample, 
        layer1_violations=layer1_violations
    )

    input_payload = {
        "sections": sections,
        "features": features,
        "full_text_sample": full_text_sample,
        "layer1_violations": layer1_violations,
        "prompt_version": active_prompt_ver,
        "model": active_model,
    }

    if mode == "mock":
        qwen_scores = run_mock_qwen_scoring(sections, features)
        qwen_scores["mode"] = "mock"
        qwen_scores["_meta"] = {
            "mode": "mock",
            "prompt_version": active_prompt_ver,
            "prompt_text": prompt,
            "input_payload": input_payload,
            "raw_output": json.dumps(qwen_scores, ensure_ascii=False),
            "model": active_model,
        }
        return qwen_scores

    payload = {
        "model": active_model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False,
    }

    delay_sec = 5
    last_error = None
    content = None

    prompt_char_len = len(prompt)
    prompt_token_est = prompt_char_len // 4
    logger.info(
        f"Qwen request started | Model: {active_model} | Prompt length: {prompt_char_len} chars (~{prompt_token_est} tokens) | Timeout: {timeout_sec}s | Max retries: {max_retries}"
    )

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Sending Qwen request | Attempt {attempt} of {max_retries}...")
            response = requests.post(QWEN_API_URL, json=payload, timeout=timeout_sec)
            response.raise_for_status()
            data = response.json()
            content = data["message"]["content"]
            logger.info(f"Qwen request succeeded on attempt {attempt} | Raw response length: {len(content)} chars")
            logger.debug(f"Raw response received:\n{content}")
            break
        except requests.exceptions.RequestException as e:
            last_error = e
            logger.warning(f"Qwen request attempt {attempt}/{max_retries} failed: {str(e)}")
            if attempt < max_retries:
                logger.info(f"Waiting {delay_sec} seconds before retry attempt {attempt + 1}...")
                time.sleep(delay_sec)

    if content is None:
        err_msg = f"API Request failed after {max_retries} attempts. Last error: {str(last_error)}"
        logger.error(f"{err_msg} | Returning exact fallback 0.50 scores with api_error=True and format_failure=True")
        return {
            "mode": "real",
            "api_error": True,
            "format_failure": True,
            "error_message": err_msg,
            # Neutral defaults so callers always have a complete score structure (not hidden!)
            "integrity_risk_score": 0.50,
            "structure_validity_score": 0.50,
            "content_coherence_score": 0.50,
            "citation_quality_score": 0.50,
            "abstract_clarity": 0.50,
            "structural_completeness": 0.50,
            "methodological_strength": 0.50,
            "experimental_strength": 0.50,
            "argumentative_quality": 0.50,
            "scope_alignment": 0.50,
            "overall_quality": 0.50,
            "recommendation": "LLM scoring unavailable — manual review required.",
            "_meta": {
                "mode": "real",
                "prompt_version": active_prompt_ver,
                "input_payload": input_payload,
                "model": active_model,
                "timeout_used": timeout_sec,
                "retries_attempted": max_retries,
            }
        }

    try:
        parsed = parse_llm_output(content)
        
        # Enforce consistency rule
        if "layer1_verification" in parsed:
            l1_v = parsed["layer1_verification"]
            if l1_v.get("methodology_like_content_found_elsewhere"):
                l1_v["methodology_missing_confirmed"] = False
                
        parsed["mode"] = "real"
        
        # Check if all critical semantic scores are present and numeric
        score_keys = [
            "abstract_clarity", "structural_completeness", "methodological_strength",
            "experimental_strength", "argumentative_quality", "scope_alignment", "overall_quality"
        ]
        missing_or_invalid = [k for k in score_keys if not isinstance(parsed.get(k), (int, float))]
        if missing_or_invalid or parsed.get("format_failure"):
            parsed["format_failure"] = True
            logger.warning(f"Parsed Qwen output has missing/invalid score keys ({missing_or_invalid}) or format_failure=True. Ensuring fallback defaults for missing keys.")
            for k in score_keys:
                if not isinstance(parsed.get(k), (int, float)):
                    parsed[k] = 0.50
        else:
            if "format_failure" not in parsed:
                parsed["format_failure"] = False

        parsed["_meta"] = {
            "mode": "real",
            "prompt_version": active_prompt_ver,
            "prompt_text": prompt,
            "input_payload": input_payload,
            "raw_output": content,
            "model": active_model,
        }

        # Log clear summary of parsed scores and format_failure
        parsed_summary = {k: parsed.get(k) for k in score_keys if k in parsed}
        logger.info(
            f"Qwen scoring successfully completed | format_failure: {parsed.get('format_failure')} | Parsed scores: {parsed_summary}"
        )

        return parsed

    except (json.JSONDecodeError, ValueError) as parse_exc:
        logger.error(
            f"Failed to parse Qwen JSON output | parse_error: {str(parse_exc)} | format_failure=True | Raw output snippet: {content[:300]}..."
        )
        return {
            "mode": "real",
            "parse_error": True,
            "format_failure": True,
            "parse_error_detail": str(parse_exc),
            "raw_output": content,
            # Neutral defaults so callers always have a complete score structure.
            "integrity_risk_score": 0.50,
            "structure_validity_score": 0.50,
            "content_coherence_score": 0.50,
            "citation_quality_score": 0.50,
            "abstract_clarity": 0.50,
            "structural_completeness": 0.50,
            "methodological_strength": 0.50,
            "experimental_strength": 0.50,
            "argumentative_quality": 0.50,
            "scope_alignment": 0.50,
            "overall_quality": 0.50,
            "recommendation": "LLM response could not be parsed — manual review required.",
            "_meta": {
                "mode": "real",
                "prompt_version": active_prompt_ver,
                "prompt_text": prompt,
                "input_payload": input_payload,
                "raw_output": content,
                "model": active_model,
            }
        }