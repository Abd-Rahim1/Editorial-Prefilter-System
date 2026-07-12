"""
Editorial Features Extraction (Step 5)
"""
from typing import Dict, Optional

def compute_editorial_features(sections: Dict[str, str], metadata: Dict, text: str, db_rules: Optional[Dict] = None) -> Dict:
    """Extract features from sections"""
    features = {
        'sections_present': {},
        'quality_indicators': {
            'total_word_count': 0,
            'missing_critical_sections': 0,
            'reference_count': 0
        }
    }
    
    total_word_count = len((text or "").split())
    features['quality_indicators']['total_word_count'] = total_word_count
    
    for name, content in sections.items():
        if content and len(content) > 50:
            features['sections_present'][name] = True
        else:
            features['sections_present'][name] = False
            
    if db_rules and "required_sections" in db_rules:
        req_sections = db_rules["required_sections"]
    else:
        try:
            from database.config_repository import ConfigRepository
            req_sections = ConfigRepository().get_editorial_rules().get("required_sections", ['abstract', 'introduction', 'methodology', 'conclusions', 'references'])
        except Exception:
            req_sections = ['abstract', 'introduction', 'methodology', 'conclusions', 'references']
    
    missing = [s for s in req_sections if not features['sections_present'].get(s, False)]
    features['quality_indicators']['missing_critical_sections'] = len(missing)
    
    # Count references
    if sections.get('references'):
        ref_lines = [l for l in sections['references'].split('\n') if l.strip()]
        features['quality_indicators']['reference_count'] = len(ref_lines)
    
    features['num_pages'] = metadata.get('num_pages', 0)
    
    return features

