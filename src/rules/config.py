"""
Configuration for editorial rules.
"""

RULE_CONFIG = {
    'min_abstract_words': 50,
    'max_abstract_words': 350,
    'min_keywords': 3,
    'max_keywords': 7,
    'min_references': 5,
    'max_references': 100,
    'min_manuscript_words': 1000,
    'max_manuscript_words': 15000,
    'required_sections': ['abstract', 'introduction', 'methodology', 'conclusions', 'references'],
    'max_missing_sections': 2,
    'min_section_words': 100,
    'min_pages': 4,
    'max_pages': 20,
    'advanced_citation_rules': {
        'max_author_self_citations': 5,
        'max_journal_self_citations': 10,
        'min_recent_citation_ratio': 0.2
    }
}
