"""
PDF Ingestion and Text Extraction
Robust Version for Layer 3 Dataset Pipeline
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Tuple
import sys

# Ensure utils is accessible
sys.path.append(str(Path(__file__).parent.parent))

from utils.text_cleaning import clean_text


def extract_text_and_metadata(pdf_path: str) -> Dict:
    """
    Extract text and metadata from PDF safely.

    Returns:
        dict containing 'full_text' and 'metadata' structures
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

            except Exception as page_error:
                print(
                    f"[WARNING] Failed extracting page "
                    f"{page_num} from {pdf_path.name}"
                )
                raw_pages.append("")
                full_text_parts.append("")

        doc.close()

        # ====================================================
        # MERGE TEXT
        # ====================================================
        full_text = "\n\n".join(full_text_parts)

        # ====================================================
        # CLEAN TEXT
        # ====================================================
        full_text = clean_text(full_text)

        # ====================================================
        # VALIDATION
        # ====================================================
        if not full_text:
            full_text = ""

        total_word_count = len(full_text.split())
        calculated_pages = len(raw_pages)

        # ====================================================
        # STRUCTURED METADATA (FIXED KEYS)
        # ====================================================
        metadata = {
            "filename": pdf_path.name,
            "page_count": calculated_pages,  # Kept for backward compatibility
            "num_pages": calculated_pages,   # <--- ADDED THIS: Fixed to match Layer 2 input schemas!
            "total_word_count": total_word_count,
        }

        # Print layout confirmation to terminal for your records
        print(f"[EXTRACTOR] {pdf_path.name} parsed successfully -> Pages detected: {calculated_pages} | Words: {total_word_count}")

        # ====================================================
        # RETURN FORMAT EXPECTED BY PIPELINE
        # ====================================================
        return {
            "full_text": full_text,
            "metadata": metadata,
        }

    except Exception as e:
        raise RuntimeError(
            f"Error during PDF text extraction "
            f"for {pdf_path.name}: {str(e)}"
        )