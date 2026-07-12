"""
PDF Ingestion and Text Extraction
Robust Version for Layer 3 Dataset Pipeline
"""

import fitz  # PyMuPDF
import logging
from pathlib import Path
from typing import Dict, List
import sys

logger = logging.getLogger("PDFExtractor")

sys.path.append(str(Path(__file__).parent.parent))

from parsing_engine.text_cleaning import clean_text


def _extract_title(doc: fitz.Document, raw_pages: List[str]) -> str:
    """
    Extract the manuscript title using a 3-tier fallback strategy.

    Tier 1 — PDF built-in metadata:
        Many PDFs store the title in their XMP/Info dictionary.
        This is the most reliable source when present.

    Tier 2 — Largest font text block on page 1:
        Scientific PDFs typically typeset the title in the largest
        font on the first page.  We read the structured dict from
        PyMuPDF, collect all text spans, sort by font size descending,
        and return the text of the biggest span that is long enough
        to be a plausible title (>= 10 characters, <= 300 characters).

    Tier 3 — First non-trivial line of page 1 plain text:
        Fallback: take the first line of raw page-1 text that has
        at least 10 characters and is not a pure number or URL.

    Args:
        doc:       Open fitz.Document object (must not be closed yet).
        raw_pages: List of plain-text strings, one per page.

    Returns:
        Title string, or empty string if nothing plausible was found.
    """

    try:
        pdf_meta = doc.metadata or {}
        meta_title = (pdf_meta.get("title") or "").strip()
        # Reject generic placeholders inserted by Word / LaTeX
        bad_placeholders = {"untitled", "microsoft word", "unknown", "none", ""}
        if (meta_title
                and meta_title.lower() not in bad_placeholders
                and len(meta_title) >= 5):
            return meta_title
    except Exception:
        pass

    try:
        if len(doc) > 0:
            page = doc[0]
            blocks = page.get_text(
                "dict", flags=fitz.TEXT_PRESERVE_WHITESPACE
            ).get("blocks", [])

            spans_by_size: List[tuple] = []
            for block in blocks:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        size = span.get("size", 0)
                        if text and size > 0:
                            spans_by_size.append((size, text))

            # Sort by font size descending
            spans_by_size.sort(key=lambda x: x[0], reverse=True)

            # Merge contiguous spans within 2pt of the maximum size
            if spans_by_size:
                max_size = spans_by_size[0][0]
                title_parts = []
                for size, text in spans_by_size:
                    if max_size - size <= 2.0:
                        title_parts.append(text)
                    else:
                        break
                candidate = " ".join(title_parts).strip()
                # Reject candidates that look like spaced-out header characters:
                # - must have at least 3 words
                # - spaces must not make up more than 40% of the string length
                # - must be between 10 and 300 chars, not a digit, not a URL
                words = candidate.split()
                space_ratio = candidate.count(" ") / max(len(candidate), 1)
                if (len(words) >= 3
                        and space_ratio <= 0.40
                        and 10 <= len(candidate) <= 300
                        and not candidate.isdigit()
                        and "http" not in candidate.lower()):
                    return candidate
    except Exception:
        pass

    try:
        if raw_pages:
            # Prefixes that are definitely NOT the paper title
            skip_prefixes = (
                "published", "under review", "preprint", "workshop",
                "proceedings", "arxiv", "doi:", "copyright", "submitted",
                "conference", "journal", "volume", "issue", "page",
                "accepted", "rejected", "december", "january", "february",
                "march", "april", "may", "june", "july", "august",
                "september", "october", "november",
            )
            for line in raw_pages[0].splitlines():
                line = line.strip()
                if not line:
                    continue
                line_lower = line.lower()
                if (len(line) >= 10
                        and not line.isdigit()
                        and "http" not in line_lower
                        and "@" not in line
                        and not any(line_lower.startswith(p) for p in skip_prefixes)):
                    return line
    except Exception:
        pass

    return ""


def extract_text_and_metadata(pdf_path: str) -> Dict:
    """
    Extract text and metadata from PDF safely.

    Returns:
        dict containing 'full_text' and 'metadata' structures.
        The 'metadata' dict always contains a 'title' key populated
        by a 3-tier extraction strategy (PDF metadata → largest font
        span on page 1 → first non-trivial line on page 1).
    """

    pdf_path = Path(pdf_path)

    try:
        doc = fitz.open(pdf_path)

        raw_pages = []
        full_text_parts = []

        for page_num in range(len(doc)):
            try:
                page = doc[page_num]

                # safer extraction mode
                page_text = page.get_text("text")

                # handle None
                if page_text is None:
                    page_text = ""

                # truncate extremely large pages
                if len(page_text) > 50000:
                    page_text = page_text[:50000]

                raw_pages.append(page_text)
                full_text_parts.append(page_text)

            except Exception:
                logger.warning(
                    f"Failed extracting page "
                    f"{page_num} from {pdf_path.name}"
                )
                raw_pages.append("")
                full_text_parts.append("")

        title = _extract_title(doc, raw_pages)

        doc.close()

        full_text = "\n\n".join(full_text_parts)
        full_text = clean_text(full_text)
        
        if not full_text:
            full_text = ""

        total_word_count = len(full_text.split())
        calculated_pages = len(raw_pages)

        metadata = {
            "filename":        pdf_path.name,
            "title":           title,
            "page_count":      calculated_pages,   # backward-compat alias
            "num_pages":       calculated_pages,
            "total_word_count": total_word_count,
        }

        title_preview = title[:60] if title else "N/A"
        logger.info(
            f"{pdf_path.name} parsed successfully"
            f" -> Pages: {calculated_pages}"
            f" | Words: {total_word_count}"
            f" | Title: {title_preview}"
        )

        return {
            "full_text": full_text,
            "metadata":  metadata,
        }

    except Exception as e:
        raise RuntimeError(
            f"Error during PDF text extraction "
            f"for {pdf_path.name}: {str(e)}"
        )