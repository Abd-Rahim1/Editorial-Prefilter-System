"""
Advanced editorial rules placeholders.
"""
import re
from collections import Counter
from datetime import datetime


def detect_keywords_count(sections):
    """Estimate number of keywords from a keywords section string.

    Splits on common delimiters and returns the count of non-empty tokens.
    """
    keywords_text = sections.get('keywords', '')
    if not keywords_text:
        return 0
    # Basic split by common delimiters
    for delimiter in [';', ',', '\n']:
        if delimiter in keywords_text:
            return len([k for k in keywords_text.split(delimiter) if k.strip()])
    return len([k for k in keywords_text.split() if k.strip()])


def estimate_reference_count(references_text):
    """Estimate reference count by counting non-empty lines likely representing references."""
    if not references_text:
        return 0
    return len([line for line in references_text.split('\n') if len(line.strip()) > 10])


def detect_recent_citation_ratio(references_text, recent_years_window: int = 5) -> float:
    """Compute fraction of references that are within the last `recent_years_window` years.

    Scans each reference line for a 4-digit year (1900-2099). If a year is found,
    it's tested against current year minus window. Lines without a year are ignored
    for the ratio denominator.
    """
    if not references_text:
        return 0.0

    current_year = datetime.utcnow().year
    year_pattern = re.compile(r"\b(19|20)\d{2}\b")
    lines = [l.strip() for l in references_text.split('\n') if l.strip()]
    if not lines:
        return 0.0

    total_with_year = 0
    recent_count = 0
    for line in lines:
        match = year_pattern.search(line)
        if match:
            total_with_year += 1
            y = int(match.group(0))
            if y >= (current_year - recent_years_window + 1):
                recent_count += 1

    if total_with_year == 0:
        return 0.0
    return recent_count / total_with_year


def detect_author_self_citations(references_text, authors) -> int:
    """Detect approximate number of author self-citations.

    `authors` may be a list of author full names or dict metadata. We try to
    extract surnames and count how many reference lines include any surname.
    """
    if not references_text:
        return 0

    # Normalize authors input
    surnames = []
    if isinstance(authors, dict):
        # Expecting {'authors': ['First Last', ...]} or similar
        candidate = authors.get('authors') or authors.get('author_list')
        if isinstance(candidate, list):
            authors_list = candidate
        else:
            authors_list = []
    elif isinstance(authors, list):
        authors_list = authors
    else:
        authors_list = []

    for a in authors_list:
        if not a:
            continue
        parts = str(a).strip().split()
        if parts:
            surnames.append(parts[-1].lower())

    if not surnames:
        return 0

    lines = [l.strip() for l in references_text.split('\n') if l.strip()]
    count = 0
    for line in lines:
        low = line.lower()
        if any(s in low for s in surnames):
            count += 1
    return count


def detect_journal_self_citations(references_text, journal_name) -> int:
    """Count references lines that appear to cite `journal_name` (case-insensitive).

    This is a heuristic: we match journal name tokens inside reference lines.
    """
    if not references_text or not journal_name:
        return 0
    jname = journal_name.lower()
    lines = [l.strip() for l in references_text.split('\n') if l.strip()]
    count = 0
    for line in lines:
        if jname in line.lower():
            count += 1
    return count


def detect_max_citations_from_any_journal(references_text) -> int:
    """Heuristic to determine the maximum citations coming from any single journal.

    Attempts to extract a journal-like token from each reference line using a
    loose pattern and returns the highest frequency found. Falls back to zero
    if extraction is unsuccessful.
    """
    if not references_text:
        return 0
    # Try to capture phrases that often represent journal names: text after year or before volume/pages
    lines = [l.strip() for l in references_text.split('\n') if l.strip()]
    candidate_names = []
    year_pattern = re.compile(r"\b(19|20)\d{2}\b")
    for line in lines:
        # Try to slice a segment after the year
        m = year_pattern.search(line)
        segment = line
        if m:
            start = m.end()
            segment = line[start: start + 100]
        # split by common separators and pick a short candidate
        parts = re.split(r"[.,;:\-()\\\/]", segment)
        if parts:
            cand = parts[0].strip()
            if len(cand) > 3 and len(cand) < 100:
                candidate_names.append(cand.lower())

    if not candidate_names:
        return 0

    counts = Counter(candidate_names)
    return max(counts.values())
