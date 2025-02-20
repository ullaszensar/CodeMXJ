import javalang
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class JavaClass:
    name: str
    methods: List[str]
    fields: List[str]
    extends: str = None
    implements: List[str] = None

    @staticmethod
    def dict_to_class(class_dict: Dict[str, Any]) -> 'JavaClass':
        return JavaClass(
            name=class_dict['name'],
            methods=class_dict['methods'],
            fields=class_dict['fields'],
            extends=class_dict['extends'],
            implements=class_dict['implements'] or []
        )

class JavaCodeParser:
    def __init__(self):
        self.tree = None
        self.classes = []

    def parse_code(self, code: str) -> List[JavaClass]:
        try:
            self.tree = javalang.parse.parse(code)
            self.classes = []

            for path, node in self.tree.filter(javalang.tree.ClassDeclaration):
                methods = [m.name for m in node.methods]
                fields = [f.declarators[0].name for f in node.fields]
                extends = node.extends.name if node.extends else None
                implements = [i.name for i in node.implements] if node.implements else []

                java_class = JavaClass(
                    name=node.name,
                    methods=methods,
                    fields=fields,
                    extends=extends,
                    implements=implements
                )
                self.classes.append(java_class)

            return self.classes
        except Exception as e:
            raise Exception(f"Failed to parse Java code: {str(e)}")

    def get_class_relationships(self) -> Dict[str, List[str]]:
        relationships = {}
        for java_class in self.classes:
            related = []
            if java_class.extends:
                related.append(java_class.extends)
            if java_class.implements:
                related.extend(java_class.implements)
            relationships[java_class.name] = related
        return relationships