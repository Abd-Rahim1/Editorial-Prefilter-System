import json
from src.database.connection import get_connection


def save_manuscript(metadata):
    conn = get_connection()
    cur = conn.cursor()

    query = """
    INSERT INTO manuscripts (filename, num_pages, total_word_count)
    VALUES (%s, %s, %s)
    RETURNING id;
    """

    cur.execute(query, (
        metadata.get("filename"),
        metadata.get("num_pages"),
        metadata.get("total_word_count")
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
    INSERT INTO extracted_sections (manuscript_id, section_name, content, word_count)
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

    # Remove old features for this manuscript to avoid duplicates
    cur.execute(
        "DELETE FROM editorial_features WHERE manuscript_id = %s;",
        (manuscript_id,)
    )

    query = """
    INSERT INTO editorial_features (manuscript_id, feature_name, feature_value)
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

    # Remove old rule checks for this manuscript to avoid duplicates
    cur.execute(
        "DELETE FROM rule_checks WHERE manuscript_id = %s;",
        (manuscript_id,)
    )

    query = """
    INSERT INTO rule_checks (
        manuscript_id, rule_name, severity, passed, description, details
    )
    VALUES (%s, %s, %s, %s, %s, %s);
    """

    for v in violations or []:
        cur.execute(query, (
            manuscript_id,
            v.rule_name,
            v.severity.value if hasattr(v.severity, "value") else str(v.severity),
            False,
            v.description,
            v.details
        ))

    conn.commit()
    cur.close()
    conn.close()


def save_model_run(
    manuscript_id,
    model_version,
    execution_time_ms=None,
    experiment_id=None,
    threshold_profile_id=None,
    prompt_version=None,
    prompt_text=None,
    input_payload=None,
    raw_output=None,
    parsed_output=None,
):
    if not manuscript_id:
        return None

    conn = get_connection()
    cur = conn.cursor()

    query = """
    INSERT INTO model_runs (
        manuscript_id,
        model_version,
        execution_time_ms,
        experiment_id,
        threshold_profile_id,
        prompt_version,
        prompt_text,
        input_payload,
        raw_output,
        parsed_output
    )
    VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s::jsonb, %s::jsonb, %s::jsonb
    )
    RETURNING id;
    """

    cur.execute(query, (
        manuscript_id,
        model_version,
        execution_time_ms,
        experiment_id,
        threshold_profile_id,
        prompt_version,
        prompt_text,
        json.dumps(input_payload, ensure_ascii=False) if input_payload is not None else None,
        json.dumps(raw_output, ensure_ascii=False) if raw_output is not None else None,
        json.dumps(parsed_output, ensure_ascii=False) if parsed_output is not None else None,
    ))

    model_run_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return model_run_id