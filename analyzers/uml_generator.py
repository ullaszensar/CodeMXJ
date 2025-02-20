import plantuml
from typing import List, Tuple
from .java_class import JavaClass
import requests

class UMLGenerator:
    def __init__(self):
        self.plantuml = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/img/')

    def generate_class_diagram(self, classes: List[JavaClass]) -> Tuple[str, bytes]:
        """Generate class diagram and return both PlantUML code and PNG image"""
        uml_code = ["@startuml", "skinparam classAttributeIconSize 0"]

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
        diagram_code = "\n".join(uml_code)

        # Get diagram URL and fetch the image
        diagram_url = self.plantuml.get_url(diagram_code)
        response = requests.get(diagram_url)
        if response.status_code == 200:
            return diagram_code, response.content
        else:
            raise Exception(f"Failed to generate diagram image: HTTP {response.status_code}")