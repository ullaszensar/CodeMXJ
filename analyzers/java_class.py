import dataclasses
from typing import List, Dict, Any

@dataclasses.dataclass
class JavaClass:
    name: str
    methods: List[str]
    fields: List[str]
    extends: str = None
    implements: List[str] = None

    @staticmethod
    def from_dict(class_dict: Dict[str, Any]) -> 'JavaClass':
        return JavaClass(
            name=class_dict['name'],
            methods=class_dict['methods'],
            fields=class_dict['fields'],
            extends=class_dict.get('extends'),
            implements=class_dict.get('implements', [])
        )
