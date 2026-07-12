"""
Layer 1: Hard Editorial Rules
Detects clear desk rejection signals using dynamic configuration rows from the database.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from editorial_rules.advanced_rules import (
    detect_keywords_count,
    detect_recent_citation_ratio,
    detect_author_self_citations,
    detect_journal_self_citations,
    detect_max_citations_from_any_journal,
    estimate_reference_count,
)
from editorial_rules.editorial_features import compute_editorial_features


@dataclass
class RuleViolation:
    """Represents a single rule violation matching database schemas"""
    rule_name: str
    severity: str
    description: str
    details: Optional[str] = None


@dataclass
class HardRulesResult:
    """Result of running hard editorial rules"""
    passed: bool  
    violations: List[RuleViolation] = field(default_factory=list)


class HardRulesEngine:
    """
    Evaluates paper content against threshold rules loaded dynamically from the database.
    """

    def run(self, sections: Dict[str, str], features: Dict, db_rules: Optional[Dict] = None) -> HardRulesResult:
        """
        Runs validations using a rule dictionary fetched from ConfigRepository / public.threshold_profiles.
        """
        if not db_rules:
            try:
                from database.config_repository import ConfigRepository
                db_rules = ConfigRepository().get_editorial_rules()
            except Exception:
                db_rules = {}

        violations: List[RuleViolation] = []

        # 1. Abstract Word Counts
        abstract_text = sections.get("abstract", "")
        abstract_words = len(abstract_text.split()) if abstract_text else 0
        min_abs = int(db_rules.get("min_abstract_words", 150))
        max_abs = int(db_rules.get("max_abstract_words", 240))

        if abstract_words < min_abs:
            violations.append(RuleViolation(
                rule_name="min_abstract_words",
                severity="warning",
                description=f"Abstract word count ({abstract_words}) is below the minimum threshold.",
                details=f"Required: {min_abs}"
            ))
        elif abstract_words > max_abs:
            violations.append(RuleViolation(
                rule_name="max_abstract_words",
                severity="warning",
                description=f"Abstract word count ({abstract_words}) exceeds the maximum allowed.",
                details=f"Allowed: {max_abs}"
            ))

        # 2. Keywords Count
        keywords_count = detect_keywords_count(sections)
        min_k = int(db_rules.get("min_keywords", 3))
        max_k = int(db_rules.get("max_keywords", 8))
        if keywords_count < min_k:
            violations.append(RuleViolation(
                rule_name="min_keywords",
                severity="warning",
                description=f"Keyword count ({keywords_count}) is below the required minimum.",
                details=f"Minimum required: {min_k}"
            ))
        elif keywords_count > max_k:
            violations.append(RuleViolation(
                rule_name="max_keywords",
                severity="warning",
                description=f"Keyword count ({keywords_count}) exceeds normal guidelines.",
                details=f"Maximum guidelines: {max_k}"
            ))

        # 3. References & Citation Analytics
        references_text = sections.get("references", "")
        ref_count = estimate_reference_count(references_text)
        min_refs = int(db_rules.get("min_references", 15))
        max_refs = int(db_rules.get("max_references", 50))

        if ref_count < min_refs:
            violations.append(RuleViolation(
                rule_name="min_references",
                severity="critical",
                description=f"Reference density too thin ({ref_count} references found).",
                details=f"Minimum required: {min_refs}"
            ))
        elif ref_count > max_refs:
            violations.append(RuleViolation(
                rule_name="max_references",
                severity="warning",
                description=f"Reference count ({ref_count}) exceeds standard baseline limitations.",
                details=f"Maximum guideline: {max_refs}"
            ))

        # Journal Self Citations
        # Journal self-citations: caller should supply target journal if available via db_rules
        target_journal = db_rules.get("target_journal") or db_rules.get("journal_name") or ""
        journal_self_citations = 0
        if target_journal:
            journal_self_citations = detect_journal_self_citations(references_text, target_journal)

        min_jsc = int(db_rules.get("min_journal_self_citations", 2))
        max_jsc = int(db_rules.get("max_journal_self_citations", 4))
        if journal_self_citations and journal_self_citations < min_jsc:
            violations.append(RuleViolation(
                rule_name="min_journal_self_citations",
                severity="warning",
                description=f"Journal self-citations ({journal_self_citations}) are below expected minimum.",
                details=f"Expected min: {min_jsc}"
            ))
        elif journal_self_citations and journal_self_citations > max_jsc:
            violations.append(RuleViolation(
                rule_name="max_journal_self_citations",
                severity="warning",
                description=f"Excessive journal self-citation detected ({journal_self_citations} matches).",
                details=f"Maximum allowed: {max_jsc}"
            ))

        # Check maximum citations from any single journal
        max_from_any = detect_max_citations_from_any_journal(references_text)
        if max_from_any > int(db_rules.get("max_citations_from_any_journal", 0)) and int(db_rules.get("max_citations_from_any_journal", 0)) > 0:
            violations.append(RuleViolation(
                rule_name="max_citations_from_any_journal",
                severity="warning",
                description=f"Excessive citations from a single source ({max_from_any}).",
                details=f"Limit: {db_rules.get('max_citations_from_any_journal')}"
            ))

        # Author Self Citations
        # Author self-citations: try to infer authors from features
        authors_candidate = features.get('authors') or features.get('metadata', {}).get('authors') or features.get('quality_indicators', {}).get('authors') or []
        author_self_citations = detect_author_self_citations(references_text, authors_candidate)
        if author_self_citations > int(db_rules.get("max_self_citations_by_authors", 4)):
            violations.append(RuleViolation(
                rule_name="max_self_citations_by_authors",
                severity="warning",
                description=f"High rate of author self-citations detected ({author_self_citations} occurrences).",
                details=f"Limit capped at: {db_rules.get('max_self_citations_by_authors')}"
            ))

        # Recent Citation Ratio Check
        recent_window = int(db_rules.get("recent_years_window", 5))
        recent_ratio = detect_recent_citation_ratio(references_text, recent_window)
        if recent_ratio < float(db_rules.get("min_ratio_recent_citations", 0.3)):
            violations.append(RuleViolation(
                rule_name="min_ratio_recent_citations",
                severity="warning",
                description=f"Outdated bibliography distribution (Recent citation ratio is {recent_ratio:.2f}).",
                details=f"Required ratio: {db_rules.get('min_ratio_recent_citations')}"
            ))

        # 4. Global Text Word Limits
        total_word_count = features.get("quality_indicators", {}).get("total_word_count", 0)
        if total_word_count < int(db_rules.get("min_manuscript_words", 8000)):
            violations.append(RuleViolation(
                rule_name="min_manuscript_words",
                severity="critical",
                description=f"Manuscript body text is too short ({total_word_count} words).",
                details=f"Minimum required words: {db_rules.get('min_manuscript_words')}"
            ))
        elif total_word_count > int(db_rules.get("max_manuscript_words", 15000)):
            violations.append(RuleViolation(
                rule_name="max_manuscript_words",
                severity="critical",
                description=f"Manuscript body text is too long ({total_word_count} words).",
                details=f"Maximum allowed limit: {db_rules.get('max_manuscript_words')}"
            ))

        # 5. Section structural mapping anomalies
        required_sections = db_rules.get("required_sections", ['abstract', 'introduction', 'methodology', 'conclusions', 'references'])
        sections_present = features.get("sections_present", {})
        missing_sections = [s for s in required_sections if not sections_present.get(s, False)]
        
        if len(missing_sections) > int(db_rules.get("max_missing_sections", 2)):
            violations.append(RuleViolation(
                rule_name="max_missing_sections",
                severity="critical",
                description=f"Critical architecture structural failure. Too many missing components: {missing_sections}.",
                details=f"Maximum tolerable missing: {db_rules.get('max_missing_sections')}"
            ))

        # Per-section minimum word checks (optional)
        min_section_words = int(db_rules.get('min_section_words', 0))
        if min_section_words > 0:
            for sec in required_sections:
                content = sections.get(sec, '') or ''
                wc = len(content.split()) if content else 0
                if wc < min_section_words:
                    violations.append(RuleViolation(
                        rule_name='min_section_words',
                        severity='warning',
                        description=f"Section '{sec}' is too short ({wc} words).",
                        details=f"Minimum words: {min_section_words}"
                    ))

        # 6. Physical Page Limitations
        num_pages = features.get("num_pages", 0)
        if num_pages < int(db_rules.get("min_pages", 4)):
            violations.append(RuleViolation(
                rule_name="min_pages",
                severity="critical",
                description=f"Physical item thickness subnormal ({num_pages} pages).",
                details=f"Minimum page bound: {db_rules.get('min_pages')}"
            ))
        elif num_pages > int(db_rules.get("max_pages", 20)):
            violations.append(RuleViolation(
                rule_name="max_pages",
                severity="critical",
                description=f"Physical item thickness overflow ({num_pages} pages).",
                details=f"Maximum page bound: {db_rules.get('max_pages')}"
            ))

        # Determine structural validation check output flag
        has_critical_error = any(v.severity == "critical" for v in violations)
        passed = not has_critical_error

        return HardRulesResult(passed=passed, violations=violations)


def run_editorial_rules(sections: Dict[str, str], metadata: Dict, full_text: str, db_rules: Optional[Dict] = None):
    """Legacy wrapper to support older imports and expected return tuple."""
    if not db_rules:
        try:
            from database.config_repository import ConfigRepository
            db_rules = ConfigRepository().get_editorial_rules()
        except Exception:
            db_rules = {}

    engine = HardRulesEngine()
    result = engine.run(sections, compute_editorial_features(sections, metadata, full_text, db_rules=db_rules), db_rules)
    decision = "accept" if result.passed else "reject"
    probability = 0.0 if result.passed else 1.0
    return result.violations, decision, probability