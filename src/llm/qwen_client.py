import json
import re
from typing import Dict, Any

import requests

from src.llm.mock_qwen import run_mock_qwen_scoring
from src.llm.prompts import get_prompt_builder


QWEN_API_URL = "http://sinbad2ia.ujaen.es:8050/api/chat"
QWEN_MODEL = "qwen3.5:35b"


def clean_llm_json(raw_output: str) -> str:
    text = raw_output.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON object found in LLM output")

    return text[start:end + 1]

def parse_llm_output(raw_output: str) -> dict:
    cleaned = clean_llm_json(raw_output)
    return json.loads(cleaned)


def run_qwen_scoring(
    sections: Dict[str, str],
    features: Dict[str, Any],
    mode: str = "mock",
    prompt_version: str = "v2",
    full_text: str = "",
    layer1_violations: list = None,
) -> Dict[str, Any]:
    if mode not in ("mock", "real"):
        raise ValueError(f"Unsupported mode: {mode}")

    layer1_violations = layer1_violations or []
    full_text_sample = full_text[:20000]

    prompt_builder = get_prompt_builder(prompt_version)
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
        "prompt_version": prompt_version,
        "model": QWEN_MODEL,
    }

    if mode == "mock":
        qwen_scores = run_mock_qwen_scoring(sections, features)
        qwen_scores["mode"] = "mock"
        qwen_scores["_meta"] = {
            "mode": "mock",
            "prompt_version": prompt_version,
            "prompt_text": prompt,
            "input_payload": input_payload,
            "raw_output": json.dumps(qwen_scores, ensure_ascii=False),
            "model": QWEN_MODEL,
        }
        return qwen_scores

    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False,
    }

    try:
        response = requests.post(QWEN_API_URL, json=payload, timeout=600)
        response.raise_for_status()
        data = response.json()
        content = data["message"]["content"]
    except requests.exceptions.RequestException as e:
        return {
            "mode": "real",
            "api_error": True,
            "error_message": f"API Request failed: {str(e)}",
            "_meta": {
                "mode": "real",
                "prompt_version": prompt_version,
                "input_payload": input_payload,
                "model": QWEN_MODEL,
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
        parsed["_meta"] = {
            "mode": "real",
            "prompt_version": prompt_version,
            "prompt_text": prompt,
            "input_payload": input_payload,
            "raw_output": content,
            "model": QWEN_MODEL,
        }
        return parsed

    except (json.JSONDecodeError, ValueError):
        return {
            "mode": "real",
            "parse_error": True,
            "raw_output": content,
            "_meta": {
                "mode": "real",
                "prompt_version": prompt_version,
                "prompt_text": prompt,
                "input_payload": input_payload,
                "raw_output": content,
                "model": QWEN_MODEL,
            }
        }