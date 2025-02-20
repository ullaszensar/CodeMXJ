import re
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class DemographicMatch:
    category: str
    field_name: str
    file_path: str
    line_number: int
    matched_text: str

class DemographicPatternAnalyzer:
    def __init__(self):
        self.demographic_patterns = {  
            'id': r'\b(customerId|cm_15)\b',
            'name': r'\b(first_name|last_name|full_name|name|amount)\b', 
            'address': r'\b(address|street|city|state|zip|postal_code)\b',  
            'contact': r'\b(phone|email|contact)\b',  
            'identity': r'\b(ssn|social_security|tax_id|passport)\b',  
            'demographics': r'\b(age|gender|dob|date_of_birth|nationality|ethnicity)\b'  
        }
        self.matches = []

    def analyze_file(self, file_path: str, content: str) -> None:
        lines = content.split('\n')
        for line_number, line in enumerate(lines, 1):
            for category, pattern in self.demographic_patterns.items():
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    self.matches.append(DemographicMatch(
                        category=category,
                        field_name=match.group(),
                        file_path=file_path,
                        line_number=line_number,
                        matched_text=match.group()
                    ))

    def get_pattern_summary(self) -> Dict[str, List[DemographicMatch]]:
        summary = {}
        for match in self.matches:
            if match.category not in summary:
                summary[match.category] = []
            summary[match.category].append(match)
        return summary

    def get_statistics(self) -> Dict[str, int]:
        return {category: len([m for m in self.matches if m.category == category])
                for category in self.demographic_patterns.keys()}
