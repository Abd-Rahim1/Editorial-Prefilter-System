"""
Text cleaning utilities
"""

import re
import unicodedata

def clean_text(text: str) -> str:
    """
    Clean extracted text from PDFs
    - Remove extra whitespace
    - Fix common PDF artifacts
    - Normalize unicode
    """
    if not text:
        return ""
    
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    
    # Replace common PDF artifacts
    text = text.replace('-\n', '')  # Hyphenation
    text = text.replace('\x00', '')  # Null bytes
    
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines to double
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single
    
    # Remove weird characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,;:!?()\-\[\]{}"\'%@#$&*+/<=>~|\\]', '', text)
    
    return text.strip()

def extract_title_from_first_lines(text: str, max_lines: int = 5) -> str:
    """
    Try to extract title from first few lines
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for i in range(min(max_lines, len(lines))):
        line = lines[i]
        # Title is usually: not too short, not too long, not a section header
        if 20 < len(line) < 200 and not re.match(r'(?i)^(abstract|introduction|1\.)', line):
            return line
    return ""

def is_likely_title(line: str) -> bool:
    """Heuristic to detect if a line looks like a title"""
    if len(line) < 15 or len(line) > 200:
        return False
    # Title words are usually capitalized
    words = line.split()
    if len(words) < 3:
        return False
    # Count capitalized words (excluding common short words)
    cap_count = sum(1 for w in words if w and w[0].isupper() and w.lower() not in ['the', 'and', 'of', 'for', 'in', 'on', 'at', 'to', 'a', 'an'])
    return cap_count / len(words) > 0.4