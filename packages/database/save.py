import json
from database.connection import get_connection

def save_manuscript(metadata):
    conn = get_connection()
    cur = conn.cursor()

    query = """
    INSERT INTO public.manuscripts (filename, title, num_pages, total_word_count, ground_truth, status)
    VALUES (%s, %s, %s, %s, %s, 'pending')
    RETURNING id;
    """

    cur.execute(query, (
        metadata.get("filename"),
        metadata.get("title"),
        metadata.get("num_pages"),
        metadata.get("total_word_count"),
        metadata.get("ground_truth", False)
    ))

    manuscript_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return manuscript_id


def save_sections(manuscript_id, sections):
    if not manuscript_id or not sections:
        return

    conn = get_connection()
    cur = conn.cursor()

    query = """
    INSERT INTO public.extracted_sections (manuscript_id, section_name, content, word_count)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (manuscript_id, section_name)
    DO UPDATE SET
        content = EXCLUDED.content,
        word_count = EXCLUDED.word_count;
    """

    for sec_name, content in sections.items():
        content = "" if content is None else str(content)
        word_count = len(content.split()) if content else 0
        cur.execute(query, (manuscript_id, sec_name, content, word_count))

    conn.commit()
    cur.close()
    conn.close()


def save_editorial_features(manuscript_id, editorial_features):
    if not manuscript_id or not editorial_features:
        return

    conn = get_connection()
    cur = conn.cursor()

    # Clear previous features to prevent duplicate keys
    cur.execute("DELETE FROM public.editorial_features WHERE manuscript_id = %s;", (manuscript_id,))

    query = """
    INSERT INTO public.editorial_features (manuscript_id, feature_name, feature_value)
    VALUES (%s, %s, %s);
    """

    sections_present = editorial_features.get("sections_present", {})
    quality_indicators = editorial_features.get("quality_indicators", {})

    features_to_save = {}
    for k, v in sections_present.items():
        features_to_save[f"has_{k}"] = 1.0 if v else 0.0

    for k, v in quality_indicators.items():
        if isinstance(v, bool):
            features_to_save[k] = 1.0 if v else 0.0
        elif isinstance(v, (int, float)):
            features_to_save[k] = float(v)

    for f_name, f_val in features_to_save.items():
        cur.execute(query, (manuscript_id, f_name, f_val))

    conn.commit()
    cur.close()
    conn.close()


def save_rule_checks(manuscript_id, violations):
    if not manuscript_id:
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM public.rule_checks WHERE manuscript_id = %s;", (manuscript_id,))

    query = """
    INSERT INTO public.rule_checks (manuscript_id, rule_name, severity, passed, description, details)
    VALUES (%s, %s, %s, %s, %s, %s);
    """

    for v in violations or []:
        # If no explicit critical violations, passed is saved as false for each item inside violations list
        severity_str = v.severity.value if hasattr(v.severity, "value") else str(v.severity)
        cur.execute(query, (
            manuscript_id,
            v.rule_name,
            severity_str,
            False,
            v.description,
            v.details
        ))

    conn.commit()
    cur.close()
    conn.close()


def save_model_run_with_metrics(manuscript_id, model_version, parsed_qwen_json,
                                execution_time_ms=None, experiment_id=None,
                                threshold_profile_id=None):
    """Deprecated wrapper — delegates to the unified save_model_run."""
    return save_model_run(
        manuscript_id=manuscript_id,
        model_version=model_version,
        parsed_output=parsed_qwen_json,
        execution_time_ms=execution_time_ms,
        experiment_id=experiment_id,
        threshold_profile_id=threshold_profile_id,
    )


def save_model_run(manuscript_id, model_version, prompt_version=None, prompt_text=None,
                   input_payload=None, raw_output=None, parsed_output=None,
                   execution_time_ms=None, experiment_id=None, threshold_profile_id=None):
    """
    Saves a Layer 2 model-run record, populating:
      • Scalar metric columns (abstract_clarity … overall_quality).
      • JSONB payload columns (prompt_version, prompt_text, input_payload,
        raw_output, parsed_output) — these are added by the startup migration.
    """
    if not manuscript_id:
        return None

    conn = get_connection()
    cur = conn.cursor()

    # Extract scalar metrics from parsed_output — try multiple key aliases
    parsed = parsed_output if isinstance(parsed_output, dict) else {}

    query = """
    INSERT INTO public.model_runs (
        manuscript_id,
        model_version,
        experiment_id,
        threshold_profile_id,
        execution_time_ms,
        prompt_version,
        prompt_text,
        input_payload,
        raw_output,
        parsed_output,
        abstract_clarity,
        structural_completeness,
        methodological_strength,
        experimental_strength,
        argumentative_quality,
        scope_alignment,
        overall_quality
    )
    VALUES (
        %s, %s, %s, %s, %s,
        %s, %s,
        %s::jsonb,
        %s,
        %s::jsonb,
        %s, %s, %s, %s, %s, %s, %s
    )
    RETURNING id;
    """

    cur.execute(query, (
        manuscript_id,
        model_version,
        experiment_id,
        threshold_profile_id,
        execution_time_ms,
        prompt_version,
        prompt_text,
        json.dumps(input_payload, ensure_ascii=False, default=str) if input_payload is not None else None,
        str(raw_output) if raw_output is not None else None,
        json.dumps(parsed_output, ensure_ascii=False, default=str) if parsed_output is not None else None,
        # Scalar metrics — try multiple aliases produced by different prompt versions
        parsed.get("abstract_clarity") or parsed.get("abstract_clarity_score"),
        parsed.get("structural_completeness") or parsed.get("structure_validity_score"),
        parsed.get("methodological_strength") or parsed.get("methodological_strength_score"),
        parsed.get("experimental_strength") or parsed.get("experimental_strength_score"),
        parsed.get("argumentative_quality") or parsed.get("argumentative_quality_score"),
        parsed.get("scope_alignment") or parsed.get("scope_alignment_score"),
        parsed.get("overall_quality") or parsed.get("integrity_risk_score"),
    ))

    model_run_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return model_run_id


def save_prediction(model_run_id, predicted_label, desk_reject_probability, confidence=None):
    """Saves Layer 3 calibrated classifier probabilistic predictions outcomes."""
    conn = get_connection()
    cur = conn.cursor()

    query = """
    INSERT INTO public.predictions (model_run_id, predicted_label, desk_reject_probability, confidence)
    VALUES (%s, %s, %s, %s)
    RETURNING id;
    """
    cur.execute(query, (model_run_id, bool(predicted_label), float(desk_reject_probability), confidence))
    prediction_id = cur.fetchone()[0]
    
    conn.commit()
    cur.close()
    conn.close()
    return prediction_id


def save_explanation(model_run_id, explanation_text, detected_issues: list, evidence_spans: list):
    """Saves Layer 4 auditable text generation log with JSON arrays lists."""
    conn = get_connection()
    cur = conn.cursor()

    query = """
    INSERT INTO public.explanations (model_run_id, explanation_text, detected_issues, evidence_spans)
    VALUES (%s, %s, %s::jsonb, %s::jsonb)
    RETURNING id;
    """
    cur.execute(query, (
        model_run_id,
        explanation_text,
        json.dumps(detected_issues, ensure_ascii=False),
        json.dumps(evidence_spans, ensure_ascii=False)
    ))
    explanation_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()
    return explanation_id


def update_manuscript_status(manuscript_id, status):
    if not manuscript_id:
        return None

    conn = get_connection()
    cur = conn.cursor()
    query = """
    UPDATE public.manuscripts
    SET status = %s
    WHERE id = %s
    RETURNING id;
    """
    cur.execute(query, (status, manuscript_id))
    updated = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return updated[0] if updated else None


def update_manuscript_metadata(manuscript_id, num_pages=None, total_word_count=None, title=None):
    if not manuscript_id:
        return
    conn = get_connection()
    cur = conn.cursor()
    updates = []
    params = []
    if num_pages is not None:
        updates.append("num_pages = %s")
        params.append(num_pages)
    if total_word_count is not None:
        updates.append("total_word_count = %s")
        params.append(total_word_count)
    if title is not None:
        updates.append("title = %s")
        params.append(title)
    if not updates:
        cur.close()
        conn.close()
        return
    params.append(manuscript_id)
    query = f"UPDATE public.manuscripts SET {', '.join(updates)} WHERE id = %s;"
    cur.execute(query, tuple(params))
    conn.commit()
    cur.close()
    conn.close()


def get_manuscript_complete_history(manuscript_id):
    """
    Retrieves the complete data structure across all 4 layers to deliver 
    a single JSON payload structure back to the Next.js Frontend.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT 
        m.id AS manuscript_id, m.filename, m.title, m.status, m.upload_date, m.num_pages, m.total_word_count,
        mr.id AS model_run_id, mr.model_version, mr.execution_time_ms,
        mr.abstract_clarity, mr.structural_completeness, mr.methodological_strength,
        mr.experimental_strength, mr.argumentative_quality, mr.scope_alignment, mr.overall_quality,
        p.predicted_label, p.desk_reject_probability, p.confidence,
        e.explanation_text, e.detected_issues, e.evidence_spans
    FROM public.manuscripts m
    LEFT JOIN public.model_runs mr ON m.id = mr.manuscript_id
    LEFT JOIN public.predictions p ON mr.id = p.model_run_id
    LEFT JOIN public.explanations e ON mr.id = e.model_run_id
    WHERE m.id = %s
    ORDER BY mr.id DESC
    LIMIT 1;
    """

    cur.execute(query, (manuscript_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return None

    columns = [desc[0] for desc in cur.description]
    data = dict(zip(columns, row))

    # Fetch extracted sections
    cur.execute("SELECT section_name, content, word_count FROM public.extracted_sections WHERE manuscript_id = %s;", (manuscript_id,))
    data["extracted_sections"] = [
        {"section_name": r[0], "content": r[1], "word_count": r[2]} for r in cur.fetchall()
    ]

    # Fetch rule checks
    cur.execute("SELECT rule_name, passed, severity, description, details FROM public.rule_checks WHERE manuscript_id = %s;", (manuscript_id,))
    rule_checks = [
        {"rule_name": r[0], "passed": r[1], "severity": r[2], "description": r[3], "details": r[4]} for r in cur.fetchall()
    ]
    data["rule_checks"] = rule_checks

    if not data.get("detected_issues"):
        data["detected_issues"] = [rc["description"] or rc["rule_name"] for rc in rule_checks if not rc["passed"]]

    # Infer or set stage progress
    status_lower = str(data.get("status") or "").lower()
    if status_lower in ("complete", "reviewed", "success"):
        data["stage_progress"] = {
            "stage_0": "completed",
            "stage_1": "completed",
            "stage_2": "completed",
            "stage_3": "completed",
            "stage_4": "completed",
        }
    else:
        sec_done = len(data["extracted_sections"]) > 0
        rule_done = len(rule_checks) > 0
        mr_done = data.get("model_run_id") is not None
        pred_done = data.get("predicted_label") is not None
        exp_done = data.get("explanation_text") is not None

        data["stage_progress"] = {
            "stage_0": "completed" if sec_done else "active",
            "stage_1": "completed" if rule_done else ("active" if sec_done else "pending"),
            "stage_2": "completed" if mr_done else ("active" if rule_done else "pending"),
            "stage_3": "completed" if pred_done else ("active" if mr_done else "pending"),
            "stage_4": "completed" if exp_done else ("active" if pred_done else "pending"),
        }

    cur.close()
    conn.close()
    return data


def get_manuscript_with_latest_run(manuscript_id):
    """Fetch manuscript details together with its latest model run."""
    return get_manuscript_complete_history(manuscript_id)



# Canonical list of every rule the HardRulesEngine evaluates.
# This mirrors layer1_presenter._ALL_RULE_NAMES and hard_rules.py.
_ALL_LAYER1_RULE_NAMES = [
    "min_abstract_words",
    "max_abstract_words",
    "min_keywords",
    "max_keywords",
    "min_references",
    "max_references",
    "min_journal_self_citations",
    "max_journal_self_citations",
    "max_citations_from_any_journal",
    "max_self_citations_by_authors",
    "min_ratio_recent_citations",
    "min_manuscript_words",
    "max_manuscript_words",
    "max_missing_sections",
    "min_section_words",
    "min_pages",
    "max_pages",
]


def save_layer1_results(
    *,
    pdf_filename: str,
    metadata: dict,
    sections: dict,
    editorial_features: dict,
    rule_violations: list,
    user_id: int = None,
) -> dict:
    """
    Persist all Layer 1 outputs to PostgreSQL in a **single transaction**.

    If any insert fails the entire operation is rolled back so the database
    never contains a partial Layer 1 result.

    Four tables are written:

    1. ``manuscripts``       — one row (filename, title, pages, words, status)
    2. ``extracted_sections`` — one row per non-empty section
    3. ``editorial_features`` — one row per feature key (flattened)
    4. ``rule_checks``        — one row per evaluated rule (ALL rules,
                                 both passed and failed)

    Args:
        pdf_filename:       Filename shown in the manuscripts table.
        metadata:           Dict from ``extract_text_and_metadata()``.
        sections:           Cleaned section dict from ``segment_sections()``.
        editorial_features: Dict from ``compute_editorial_features()``.
        rule_violations:    List of ``RuleViolation`` objects (failures only).
        user_id:            Optional FK to the users table.

    Returns:
        Dict with keys ``manuscript_id``, ``n_sections``, ``n_features``,
        ``n_rule_checks`` describing what was inserted.

    Raises:
        Exception: Re-raises any database exception after rolling back.
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        title           = metadata.get("title") or None
        num_pages       = metadata.get("num_pages", metadata.get("page_count")) or None
        total_word_count = metadata.get("total_word_count") or None

        cur.execute(
            """
            INSERT INTO public.manuscripts
                (filename, title, num_pages, total_word_count, status, user_id)
            VALUES (%s, %s, %s, %s, 'pending', %s)
            RETURNING id;
            """,
            (pdf_filename, title, num_pages, total_word_count, user_id),
        )
        manuscript_id = cur.fetchone()[0]

        n_sections = 0
        for sec_name, content in sections.items():
            content = content or ""
            if not content.strip():
                continue  # skip genuinely empty / missing sections
            word_count = len(content.split())
            cur.execute(
                """
                INSERT INTO public.extracted_sections
                    (manuscript_id, section_name, content, word_count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (manuscript_id, section_name)
                DO UPDATE SET content = EXCLUDED.content,
                              word_count = EXCLUDED.word_count;
                """,
                (manuscript_id, sec_name, content, word_count),
            )
            n_sections += 1

        # Flatten the nested structure returned by compute_editorial_features()
        flat_features: dict = {}
        for key, val in editorial_features.items():
            if key == "sections_present" and isinstance(val, dict):
                for sec_name, present in val.items():
                    flat_features[f"has_{sec_name}"] = 1.0 if present else 0.0
            elif key == "quality_indicators" and isinstance(val, dict):
                for qk, qv in val.items():
                    if isinstance(qv, bool):
                        flat_features[qk] = 1.0 if qv else 0.0
                    elif isinstance(qv, (int, float)):
                        flat_features[qk] = float(qv)
                    # skip non-numeric quality indicators
            else:
                # Top-level scalar (e.g. num_pages)
                if isinstance(val, bool):
                    flat_features[key] = 1.0 if val else 0.0
                elif isinstance(val, (int, float)):
                    flat_features[key] = float(val)

        # Clear previous features for idempotency
        cur.execute(
            "DELETE FROM public.editorial_features WHERE manuscript_id = %s;",
            (manuscript_id,),
        )

        n_features = 0
        for f_name, f_val in flat_features.items():
            cur.execute(
                """
                INSERT INTO public.editorial_features
                    (manuscript_id, feature_name, feature_value)
                VALUES (%s, %s, %s);
                """,
                (manuscript_id, f_name, f_val),
            )
            n_features += 1

        # Build a lookup from violation list
        violation_map: dict = {v.rule_name: v for v in (rule_violations or [])}

        # Delete previous checks for idempotency
        cur.execute(
            "DELETE FROM public.rule_checks WHERE manuscript_id = %s;",
            (manuscript_id,),
        )

        n_rule_checks = 0

        # First: every canonical rule (pass or fail)
        for rule_name in _ALL_LAYER1_RULE_NAMES:
            if rule_name in violation_map:
                v = violation_map[rule_name]
                severity    = v.severity.value if hasattr(v.severity, "value") else str(v.severity)
                passed      = False
                description = v.description
                details     = v.details
            else:
                severity    = "info"
                passed      = True
                description = f"Rule '{rule_name}' passed."
                details     = None

            cur.execute(
                """
                INSERT INTO public.rule_checks
                    (manuscript_id, rule_name, severity, passed, description, details)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (manuscript_id, rule_name, severity, passed, description, details),
            )
            n_rule_checks += 1

        # Then: any extra violations whose rule_name isn't in the canonical list
        for v in (rule_violations or []):
            if v.rule_name not in _ALL_LAYER1_RULE_NAMES:
                severity = v.severity.value if hasattr(v.severity, "value") else str(v.severity)
                cur.execute(
                    """
                    INSERT INTO public.rule_checks
                        (manuscript_id, rule_name, severity, passed, description, details)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (manuscript_id, v.rule_name, severity, False, v.description, v.details),
                )
                n_rule_checks += 1

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    return {
        "manuscript_id": manuscript_id,
        "n_sections":    n_sections,
        "n_features":    n_features,
        "n_rule_checks": n_rule_checks,
    }