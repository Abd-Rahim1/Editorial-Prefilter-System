import os
from pathlib import Path

def validate_pdf(manuscript_pdf: str) -> bool:
    """
    Validates that the provided manuscript_pdf path exists, is a file, 
    and has a valid .pdf extension before further processing.
    """
    path = Path(manuscript_pdf)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {manuscript_pdf}")
        
    if not path.is_file():
        raise ValueError(f"Path is not a file: {manuscript_pdf}")
        
    if path.suffix.lower() != '.pdf':
        raise ValueError(f"Unsupported file type expected .pdf, got: {path.suffix}")
        
    return True
