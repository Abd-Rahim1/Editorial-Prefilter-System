"""
Layer 1 Console Presenter — Editorial Rule Engine.

Responsible solely for producing the structured, human-readable terminal
report for Layer 1.  Contains no business logic and performs no I/O other
than printing to stdout.

Separation of responsibilities
--------------------------------
* ``print_layer1_report()`` — public entry point called from run_pipeline.py
* All helper ``_print_*`` functions are private to this module
"""

import io
import sys
from typing import Any, Dict, List, Optional

# Ensure UTF-8 stdout on Windows (cp1252 terminals choke on ✓/✗)
if hasattr(sys.stdout, "buffer") and sys.stdout.encoding.lower() not in ("utf-8", "utf-8-sig"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Known rule names that the HardRulesEngine evaluates.
# This list mirrors the exact rule_name strings produced by hard_rules.py.
# It is used to reconstruct the full pass/fail audit trail (including rules
# that were evaluated but NOT violated).
_ALL_RULE_NAMES: List[str] = [
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

# Display labels for every editorial feature key the module may produce.
# Keys not in this dict are printed as-is (title-cased).
_FEATURE_LABELS: Dict[str, str] = {
    "num_pages":                        "Pages",
    "total_word_count":                 "Total words",
    "missing_critical_sections":        "Missing critical sections",
    "reference_count":                  "Reference count",
    "has_abstract":                     "Has abstract",
    "has_introduction":                 "Has introduction",
    "has_methodology":                  "Has methodology",
    "has_experiments":                  "Has experiments",
    "has_conclusion":                   "Has conclusion",
    "has_conclusions":                  "Has conclusions",
    "has_references":                   "Has references",
    "has_related_work":                 "Has related work",
    "keyword_count":                    "Keyword count",
    "abstract_words":                   "Abstract words",
    "recent_citation_ratio":            "Recent citation ratio",
    "journal_self_citations":           "Journal self-citations",
    "max_citations_from_any_journal":   "Max citations from one journal",
    "author_self_citations":            "Author self-citations",
}

_SEP = "-" * 52
_WIDE = "=" * 52



def print_layer1_report(
    *,
    pdf_path: str,
    metadata: Dict[str, Any],
    sections: Dict[str, str],
    editorial_features: Dict[str, Any],
    rules_result: Any,           # HardRulesResult
    rule_violations: List[Any],  # List[RuleViolation]
) -> None:
    """
    Print the full structured Layer 1 report to stdout.

    Args:
        pdf_path:          Path to the input PDF (used for display only).
        metadata:          Dict returned by ``extract_text_and_metadata()``.
        sections:          Dict of section name → text (cleaned).
        editorial_features: Dict returned by ``compute_editorial_features()``.
        rules_result:      ``HardRulesResult`` object.
        rule_violations:   ``rules_result.violations`` list.
    """
    _print_pdf_ingestion(pdf_path, metadata)
    _print_separator()
    _print_manuscript_info(pdf_path, metadata)
    _print_separator()
    _print_extracted_sections(sections)
    _print_separator()
    _print_editorial_features(editorial_features)
    _print_separator()
    _print_rule_checks(rule_violations)
    print()
    print(_WIDE)
    print("  Layer 1 completed successfully")
    print(_WIDE)



def _print_separator() -> None:
    print()
    print(_SEP)
    print()


def _section_word_count(text: Optional[str]) -> int:
    if not text:
        return 0
    return len(text.split())


def _print_pdf_ingestion(pdf_path: str, metadata: Dict[str, Any]) -> None:
    """Print section 1 — PDF ingestion summary."""
    from pathlib import Path
    filename = Path(pdf_path).name
    pages    = metadata.get("num_pages", metadata.get("page_count", "?"))
    words    = metadata.get("total_word_count", "?")

    print()
    print("  1. PDF INGESTION")
    print()
    print(f"  PDF:")
    print(f"  {filename}")
    print()
    print(f"  Pages:")
    print(f"  {pages}")
    print()
    print(f"  Total Words:")
    print(f"  {words}")


def _print_manuscript_info(pdf_path: str, metadata: Dict[str, Any]) -> None:
    """Print section 2 — manuscript information."""
    from pathlib import Path
    filename = Path(pdf_path).name
    title    = metadata.get("title") or "(title not detected)"

    print("  2. MANUSCRIPT INFORMATION")
    print()
    print(f"  Title:")
    print(f"  {title}")
    print()
    print(f"  Filename:")
    print(f"  {filename}")


def _print_extracted_sections(sections: Dict[str, str]) -> None:
    """Print section 3 — extracted section list with word counts."""
    print("  3. EXTRACTED SECTIONS")
    print()

    # Canonical display order; any sections not in this list are appended
    canonical_order = [
        "title", "abstract", "keywords", "introduction",
        "related_work", "methodology", "experiments",
        "conclusion", "conclusions", "references",
    ]
    displayed = set()
    ordered_keys = [k for k in canonical_order if k in sections]
    extra_keys   = [k for k in sections if k not in canonical_order]

    for key in ordered_keys + extra_keys:
        text = sections.get(key, "")
        present = bool(text and len(text.strip()) > 50)
        icon  = "✓" if present else "✗"
        label = key.replace("_", " ").title()
        print(f"  {icon} {label}")
        displayed.add(key)

    print()

    # Word-count breakdown
    col_w = 28
    for key in ordered_keys + extra_keys:
        text  = sections.get(key, "")
        wc    = _section_word_count(text)
        label = key.replace("_", " ").title()
        dots  = "." * max(1, col_w - len(label))
        unit  = "entries" if key == "references" else "words"
        print(f"  {label} {dots} {wc} {unit}")


def _print_editorial_features(editorial_features: Dict[str, Any]) -> None:
    """
    Print section 4 — every editorial feature actually produced by the
    feature extraction module.  Does NOT hardcode any values.
    """
    print("  4. EDITORIAL FEATURES")
    print()

    # Flatten the nested structure returned by compute_editorial_features()
    flat: Dict[str, Any] = {}

    for key, val in editorial_features.items():
        if key == "sections_present" and isinstance(val, dict):
            for sec_name, present in val.items():
                flat[f"has_{sec_name}"] = present
        elif key == "quality_indicators" and isinstance(val, dict):
            flat.update(val)
        else:
            flat[key] = val

    for key, val in flat.items():
        label = _FEATURE_LABELS.get(key, key.replace("_", " ").title())
        # Format booleans as Yes/No, floats to 4 dp, ints as-is
        if isinstance(val, bool):
            display = "Yes" if val else "No"
        elif isinstance(val, float):
            display = f"{val:.4f}"
        else:
            display = str(val)
        col_w = 36
        dots  = "." * max(1, col_w - len(label))
        print(f"  {label} {dots} {display}")


def _print_rule_checks(rule_violations: List[Any]) -> None:
    """
    Print section 5 — every evaluated rule with pass/fail status and totals.
    """
    print("  5. RULE CHECKS")
    print()

    violated_names = {v.rule_name for v in rule_violations}

    for rule_name in _ALL_RULE_NAMES:
        icon = "✗" if rule_name in violated_names else "✓"
        print(f"  {icon} {rule_name}")

    # Any violation rules not in the canonical list (defensive)
    for v in rule_violations:
        if v.rule_name not in _ALL_RULE_NAMES:
            print(f"  ✗ {v.rule_name}")

    print()
    total_evaluated  = len(_ALL_RULE_NAMES)
    total_violated   = len(rule_violations)
    total_passed     = total_evaluated - total_violated
    critical_count   = sum(1 for v in rule_violations if v.severity == "critical")

    print(f"  Rules evaluated  : {total_evaluated}")
    print(f"  Rules passed     : {total_passed}")
    print(f"  Violations       : {total_violated}")
    print(f"  Critical violations: {critical_count}")



def print_db_save_summary(
    manuscript_db_id: int,
    n_sections: int,
    n_features: int,
    n_rule_checks: int,
) -> None:
    """
    Print the database persistence verification block.

    Args:
        manuscript_db_id: Auto-generated PK from the manuscripts table.
        n_sections:       Number of section rows inserted.
        n_features:       Number of editorial_features rows inserted.
        n_rule_checks:    Number of rule_checks rows inserted (ALL rules).
    """
    print()
    print(_WIDE)
    print("  DATABASE PERSISTENCE — LAYER 1")
    print(_WIDE)
    print(f"  ✓  Manuscript saved      (ID = {manuscript_db_id})")
    print(f"  ✓  Sections saved        ({n_sections})")
    print(f"  ✓  Editorial features saved ({n_features})")
    print(f"  ✓  Rule checks saved     ({n_rule_checks})")
    print(_WIDE)
