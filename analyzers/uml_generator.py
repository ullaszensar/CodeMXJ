import plantuml
from typing import List
from .code_parser import JavaClass

class UMLGenerator:
    def __init__(self):
        self.plantuml = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/img/')

    def generate_class_diagram(self, classes: List[JavaClass]) -> str:
        uml_code = ["@startuml"]

        for java_class in classes:
            uml_code.append(f"class {java_class.name} {{")

            # Add fields
            for field in java_class.fields:
                uml_code.append(f"  {field}")

            # Add methods
            for method in java_class.methods:
                uml_code.append(f"  +{method}()")

            uml_code.append("}")

            # Add inheritance
            if java_class.extends:
                uml_code.append(f"{java_class.name} --|> {java_class.extends}")

            # Add implementations
            if java_class.implements:
                for interface in java_class.implements:
                    uml_code.append(f"{java_class.name} ..|> {interface}")

        uml_code.append("@enduml")
        return "\n".join(uml_code)