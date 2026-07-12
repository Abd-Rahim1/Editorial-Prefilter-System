from typing import TypedDict

class Metadata(TypedDict):
    """
    Standard layout schema for extracted pipeline metadata representations.
    """
    filename: str
    num_pages: int
    total_word_count: int
