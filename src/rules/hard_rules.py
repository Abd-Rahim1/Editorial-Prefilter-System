"""
Layer 1: Hard Editorial Rules
Detects clear desk rejection signals without LLM
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.rules.config import RULE_CONFIG
from src.rules.advanced_rules import (
    detect_keywords_count,
    detect_recent_citation_ratio,
    detect_author_self_citations,
    detect_journal_self_citations,
)


class RuleSeverity(Enum):
    HIGH = "high"      # Immediate desk reject
    MEDIUM = "medium"  # Strong flag for rejection
    LOW = "low"        # Warning only


@dataclass
class RuleViolation:
    """Represents a single rule violation"""
    rule_name: str
    severity: RuleSeverity
    description: str
    details: Optional[str] = None


@dataclass
class HardRulesResult:
    """Result of running hard editorial rules"""
    passed: bool  # True if no HIGH severity violations
    violations: List[RuleViolation] = field(default_factory=list)
    desk_reject_probability: float = 0.0

    def should_desk_reject(self) -> bool:
        return any(v.severity == RuleSeverity.HIGH for v in self.violations)

    def get_rejection_reasons(self) -> List[str]:
        return [
            v.description
            for v in self.violations
            if v.severity in [RuleSeverity.HIGH, RuleSeverity.MEDIUM]
        ]


def check_methodology_presence(sections: Dict[str, str]) -> Tuple[bool, str]:
    """
    Detect methodology ONLY from explicit section names.
    No flexible keyword inference from body text.
    """
    explicit_method_sections = {
        "methodology",
        "method",
        "methods",
        "materials and methods",
        "experimental design",
    }

    present_sections = {str(k).strip().lower() for k in sections.keys()}

    for section_name in explicit_method_sections:
        if section_name in present_sections:
            return True, f"Explicit methodology section found: '{section_name}'"

    return False, "No explicit methodology section detected."


def run_editorial_rules(
    sections: Dict[str, str],
    metadata: Dict,
    text: str
) -> Tuple[List[RuleViolation], str, float]:
    """
    Executes hard rules evaluating desk reject signals.
    Returns: violations, decision, probability
    """
    from src.features.editorial_features import compute_editorial_features

    engine = HardRulesEngine()
    features = compute_editorial_features(sections, metadata, text)

    result = engine.evaluate(sections, features, text)
    decision = "reject" if result.should_desk_reject() else "accept"

    return result.violations, decision, result.desk_reject_probability


class HardRulesEngine:
    """Layer 1: Hard editorial rules engine"""

    def __init__(self, journal_config: Optional[Dict] = None):
        self.config = journal_config or RULE_CONFIG

    def evaluate(
        self,
        sections: Dict[str, str],
        structural_features: Dict,
        full_text: str = ""
    ) -> HardRulesResult:
        """
        Evaluate manuscript against hard editorial rules.

        Args:
            sections: Dictionary of section name -> content
            structural_features: Features from compute_editorial_features()
            full_text: Full manuscript text (currently not used for methodology)
        """
        violations: List[RuleViolation] = []

        self._check_abstract(sections, structural_features, violations)
        self._check_page_count(structural_features, violations)
        self._check_length(structural_features, violations)
        self._check_references(structural_features, violations)
        self._check_keywords(sections, violations)
        self._check_required_sections(sections, structural_features, violations)
        self._check_section_minimum_words(sections, violations)
        self._check_methodology_experiments(sections, structural_features, violations)
        self._check_advanced_references(sections, violations)

        desk_reject_prob = self._calculate_probability(violations)
        passed = not any(v.severity == RuleSeverity.HIGH for v in violations)

        return HardRulesResult(
            passed=passed,
            violations=violations,
            desk_reject_probability=desk_reject_prob
        )

    def _safe_text(self, value) -> str:
        """Convert None or non-string values to safe string."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return str(value)

    def _check_abstract(self, sections: Dict, features: Dict, violations: List[RuleViolation]):
        """Check abstract length and existence."""
        abstract_text = self._safe_text(sections.get("abstract", ""))
        abstract_len = len(abstract_text.split())
        min_words = self.config.get("min_abstract_words", 50)
        max_words = self.config.get("max_abstract_words", float("inf"))

        if not abstract_text.strip() or abstract_len < min_words:
            violations.append(RuleViolation(
                rule_name="missing_or_short_abstract",
                severity=RuleSeverity.HIGH,
                description=f"Abstract is missing or too short (< {min_words} words)",
                details=f"Abstract length: {abstract_len} words"
            ))
        elif abstract_len > max_words:
            violations.append(RuleViolation(
                rule_name="long_abstract",
                severity=RuleSeverity.LOW,
                description=f"Abstract is too long (> {max_words} words)",
                details=f"Abstract length: {abstract_len} words"
            ))

    def _check_references(self, features: Dict, violations: List[RuleViolation]):
        """Check if manuscript has sufficient references."""
        ref_count = features.get("quality_indicators", {}).get("reference_count", 0)
        min_refs = self.config.get("min_references", 5)
        max_refs = self.config.get("max_references", float("inf"))

        if ref_count == 0:
            violations.append(RuleViolation(
                rule_name="no_references",
                severity=RuleSeverity.HIGH,
                description="No references found in manuscript",
                details="Manuscript appears to have no citations"
            ))
        elif ref_count < min_refs:
            violations.append(RuleViolation(
                rule_name="few_references",
                severity=RuleSeverity.MEDIUM,
                description=f"Very few references ({ref_count} < {min_refs})",
                details=f"Minimum recommended: {min_refs} references"
            ))
        elif ref_count > max_refs:
            violations.append(RuleViolation(
                rule_name="many_references",
                severity=RuleSeverity.LOW,
                description=f"High number of references ({ref_count} > {max_refs})",
                details=f"Maximum recommended: {max_refs} references"
            ))

    def _check_length(self, features: Dict, violations: List[RuleViolation]):
        """Check manuscript word count."""
        word_count = features.get("quality_indicators", {}).get("total_word_count", 0)

        if word_count < self.config["min_manuscript_words"]:
            violations.append(RuleViolation(
                rule_name="too_short",
                severity=RuleSeverity.HIGH,
                description=f"Manuscript too short ({word_count} words)",
                details=f"Minimum expected: {self.config['min_manuscript_words']} words"
            ))
        elif word_count > self.config["max_manuscript_words"]:
            violations.append(RuleViolation(
                rule_name="too_long",
                severity=RuleSeverity.LOW,
                description=f"Manuscript unusually long ({word_count} words)",
                details=f"Maximum recommended: {self.config['max_manuscript_words']} words"
            ))

    def _check_page_count(self, features: Dict, violations: List[RuleViolation]):
        """Check if manuscript adheres to page limits."""
        num_pages = features.get("num_pages")

        if num_pages is not None:
            if num_pages < self.config["min_pages"]:
                violations.append(RuleViolation(
                    rule_name="too_few_pages",
                    severity=RuleSeverity.HIGH,
                    description=f"Manuscript too short in pages ({num_pages})",
                    details=f"Minimum expected: {self.config['min_pages']} pages"
                ))
            elif num_pages > self.config["max_pages"]:
                violations.append(RuleViolation(
                    rule_name="too_many_pages",
                    severity=RuleSeverity.MEDIUM,
                    description=f"Manuscript too long in pages ({num_pages})",
                    details=f"Maximum recommended: {self.config['max_pages']} pages"
                ))

    def _check_required_sections(self, sections: Dict, features: Dict, violations: List[RuleViolation]):
        """Check for missing required sections."""
        sections_present = features.get("sections_present", {})
        required = self.config["required_sections"]

        missing = [s for s in required if not sections_present.get(s, False)]

        if len(missing) > self.config["max_missing_sections"]:
            violations.append(RuleViolation(
                rule_name="missing_sections",
                severity=RuleSeverity.HIGH,
                description=f"Multiple missing sections: {', '.join(missing)}",
                details=f"Required sections: {', '.join(required)}"
            ))
        elif missing:
            violations.append(RuleViolation(
                rule_name="missing_sections",
                severity=RuleSeverity.MEDIUM,
                description=f"Missing sections: {', '.join(missing)}",
                details="Consider adding these sections"
            ))

    def _check_methodology_experiments(
        self,
        sections: Dict,
        features: Dict,
        violations: List[RuleViolation],
    ):
        """Check for explicit methodology section and experiments section."""
        sections_present = features.get("sections_present", {})
        has_experiments = sections_present.get("experiments", False)
        word_count = features.get("quality_indicators", {}).get("total_word_count", 0)

        has_method, method_reason = check_methodology_presence(sections)

        if not has_method and word_count > 500:
            violations.append(RuleViolation(
                rule_name="missing_methodology",
                severity=RuleSeverity.HIGH,
                description="Missing explicit methodology section",
                details=method_reason
            ))

        if not has_experiments and word_count > 2000:
            violations.append(RuleViolation(
                rule_name="missing_experiments",
                severity=RuleSeverity.MEDIUM,
                description="Experiments/Results section is missing",
                details="Expected to see experimental validation"
            ))

    def _check_keywords(self, sections: Dict, violations: List[RuleViolation]):
        """Check keyword count if a keywords section exists."""
        if "keywords" not in sections:
            return

        kw_count = detect_keywords_count(sections)
        min_kw = self.config.get("min_keywords", 0)
        max_kw = self.config.get("max_keywords", 100)

        if kw_count < min_kw:
            violations.append(RuleViolation(
                rule_name="few_keywords",
                severity=RuleSeverity.LOW,
                description=f"Too few keywords ({kw_count} < {min_kw})",
                details=f"Minimum expected: {min_kw} keywords"
            ))
        elif kw_count > max_kw:
            violations.append(RuleViolation(
                rule_name="many_keywords",
                severity=RuleSeverity.LOW,
                description=f"Too many keywords ({kw_count} > {max_kw})",
                details=f"Maximum expected: {max_kw} keywords"
            ))

    def _check_section_minimum_words(self, sections: Dict, violations: List[RuleViolation]):
        """Check that required sections have a minimum number of words."""
        for section_name in self.config["required_sections"]:
            content = self._safe_text(sections.get(section_name, ""))

            if content.strip():
                words = len(content.split())

                if words < self.config["min_section_words"]:
                    violations.append(RuleViolation(
                        rule_name=f"{section_name}_too_short",
                        severity=RuleSeverity.LOW,
                        description=f"Section '{section_name}' is too short ({words} words)",
                        details=f"Minimum expected: {self.config['min_section_words']} words"
                    ))

    def _check_advanced_references(self, sections: Dict, violations: List[RuleViolation]):
        """
        Advanced citation checks kept as LOW severity.
        These are placeholders/heuristics for now.
        """
        references_text = self._safe_text(sections.get("references", ""))
        if not references_text.strip():
            return

        min_recent = self.config.get("min_ratio_recent_citations", 0.0)
        recent_ratio = detect_recent_citation_ratio(references_text)
        if min_recent > 0 and recent_ratio < min_recent:
            violations.append(RuleViolation(
                rule_name="few_recent_citations",
                severity=RuleSeverity.LOW,
                description=f"Low ratio of recent citations ({recent_ratio:.2f} < {min_recent})",
                details="Consider citing more recent literature"
            ))

        author_self_cites = detect_author_self_citations(references_text, {})
        max_author_cites = self.config.get("max_self_citations_by_authors", 100)
        if author_self_cites > max_author_cites:
            violations.append(RuleViolation(
                rule_name="many_author_self_citations",
                severity=RuleSeverity.LOW,
                description=f"High author self-citations ({author_self_cites} > {max_author_cites})",
                details="Consider reducing self-citations"
            ))

        journal_self_cites = detect_journal_self_citations(references_text, "Current Journal")
        max_journal_cites = self.config.get("max_journal_self_citations", 100)
        if journal_self_cites > max_journal_cites:
            violations.append(RuleViolation(
                rule_name="many_journal_self_citations",
                severity=RuleSeverity.LOW,
                description=f"High journal self-citations ({journal_self_cites} > {max_journal_cites})",
                details="Consider citing a broader range of venues"
            ))

    def _calculate_probability(self, violations: List[RuleViolation]) -> float:
        """Calculate desk reject probability from violations."""
        if not violations:
            return 0.0

        weights = {
            RuleSeverity.HIGH: 0.35,
            RuleSeverity.MEDIUM: 0.15,
            RuleSeverity.LOW: 0.05,
        }

        total_weight = sum(weights[v.severity] for v in violations)
        return min(0.95, total_weight)

    def get_summary_report(self, result: HardRulesResult) -> str:
        """Generate human-readable summary of rule violations."""
        if result.passed and not result.violations:
            return "✅ No hard rule violations detected. Proceed to LLM evaluation."

        lines = []
        lines.append("=" * 50)
        lines.append("HARD EDITORIAL RULES - SUMMARY")
        lines.append("=" * 50)

        if result.should_desk_reject():
            lines.append("\n RECOMMENDATION: DESK REJECT")
            lines.append(f"   Probability: {result.desk_reject_probability:.0%}")
        else:
            lines.append("\n No immediate desk reject required")
            lines.append(f"   Issues found: {len(result.violations)}")

        if result.violations:
            lines.append("\nVIOLATIONS:")
            for v in result.violations:
                severity_icon = {
                    RuleSeverity.HIGH: " HIGH",
                    RuleSeverity.MEDIUM: " MEDIUM",
                    RuleSeverity.LOW: " LOW",
                }.get(v.severity, "")
                lines.append(f"  [{severity_icon}] {v.description}")
                if v.details:
                    lines.append(f"       → {v.details}")

        return "\n".join(lines)


if __name__ == "__main__":
    engine = HardRulesEngine()

    good_sections = {
        "abstract": " ".join(["abstract"] * 180),
        "introduction": " ".join(["intro"] * 300),
        "methodology": " ".join(["method"] * 300),
        "experiments": " ".join(["exp"] * 300),
        "conclusions": " ".join(["conclusion"] * 150),
        "references": "\n".join([f"[{i}] Ref {i}" for i in range(1, 21)]),
    }

    good_features = {
        "num_pages": 12,
        "sections_present": {
            "abstract": True,
            "introduction": True,
            "methodology": True,
            "experiments": True,
            "conclusions": True,
            "references": True,
        },
        "quality_indicators": {
            "total_word_count": 9000,
            "reference_count": 20,
        },
    }

    result = engine.evaluate(good_sections, good_features)
    print(engine.get_summary_report(result))