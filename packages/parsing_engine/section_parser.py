"""
Section Parsing (Step 3)
"""

import re
from typing import Dict

def segment_sections(text: str) -> Dict[str, str]:
    """Improved section parser that handles ICLR format with flexible keywords"""
    
    SECTION_MAPPING = {
        "abstract": ["abstract"],
        "introduction": ["introduction", "background"],
        "methodology": ["methodology", "method", "methods", "approach", "model", "framework", "architecture"],
        "experiments": ["experiments", "experiment", "results", "evaluation", "setup"],
        "conclusions": ["conclusion", "conclusions", "discussion", "summary"],
        "references": ["references", "bibliography"]
    }
    
    sections = {k: None for k in ["title"] + list(SECTION_MAPPING.keys())}
    
    if not text:
        return sections
    
    lines = text.split('\n')
    
    # Extract title from beginning
    for i, line in enumerate(lines[:20]):
        line = line.strip()
        if not line:
            continue
        if line.upper() == 'ABSTRACT':
            break
        if '@' in line or 'University' in line or 'Google' in line:
            continue
        if 'Published as a conference paper' in line:
            continue
        if len(line) > 15 and len(line) < 200:
            sections['title'] = line
            break
            
    for norm_name, keywords in SECTION_MAPPING.items():
        pattern = '|'.join([re.escape(k) for k in keywords])
        regex = re.compile(rf'^\s*(?:[0-9]+(?:\.[0-9]+)*\.?\s*)?({pattern})\s*$', re.IGNORECASE)
        SECTION_MAPPING[norm_name] = regex

    found_headings = []
    
    for i, line in enumerate(lines):
        line_strip = line.strip()
        if not line_strip:
            continue
            
        matched = False
        for norm_name, regex in SECTION_MAPPING.items():
            if isinstance(regex, list): continue 
            
            match = regex.match(line_strip)
            if match:
                found_headings.append({
                    'index': i,
                    'name': norm_name,
                    'text': line_strip
                })
                matched = True
                break
                
        if matched:
            continue
            
        if len(line_strip.split()) <= 10 and not line_strip.endswith(('.', ',', ';', ':')):
            if any(c.isalpha() for c in line_strip):
                if line_strip.isupper() or re.match(r'^[0-9]+\.\s+[A-Z]', line_strip):
                    found_headings.append({
                        'index': i,
                        'name': 'BOUNDARY',
                        'text': line_strip
                    })

    for idx, heading in enumerate(found_headings):
        if heading['name'] == 'BOUNDARY':
            continue
            
        norm_name = heading['name']
        start_idx = heading['index'] + 1
        
        end_idx = found_headings[idx + 1]['index'] if idx + 1 < len(found_headings) else len(lines)
            
        content = '\n'.join(lines[start_idx:end_idx]).strip()
        
        if content:
            if sections[norm_name]:
                sections[norm_name] += "\n\n" + content[:8000]
            else:
                sections[norm_name] = content[:8000]
                
    return sections
