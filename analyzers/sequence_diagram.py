import javalang
from typing import List, Dict, Tuple
import plantuml

class SequenceDiagramGenerator:
    def __init__(self):
        self.interactions = []
        self.plantuml = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/img/')

    def analyze_method_calls(self, code: str, method_name: str) -> Tuple[str, bytes]:
        try:
            tree = javalang.parse.parse(code)
            self.interactions = []

            for path, node in tree.filter(javalang.tree.MethodDeclaration):
                if node.name == method_name:
                    self._analyze_method_body(node)

            diagram_code = self._generate_sequence_diagram()
            diagram_image = self.plantuml.get_png(diagram_code)
            return diagram_code, diagram_image
        except Exception as e:
            raise Exception(f"Failed to analyze method calls: {str(e)}")

    def _analyze_method_body(self, method_node):
        for path, node in method_node.filter(javalang.tree.MethodInvocation):
            if hasattr(node, 'qualifier') and node.qualifier:
                self.interactions.append({
                    'from': method_node.name,
                    'to': node.qualifier,
                    'message': node.member
                })

    def _generate_sequence_diagram(self) -> str:
        diagram = ["@startuml", "skinparam sequenceMessageAlign center"]

        # Add participants
        participants = set()
        for interaction in self.interactions:
            participants.add(interaction['from'])
            participants.add(interaction['to'])

        for participant in participants:
            diagram.append(f"participant {participant}")

        # Add interactions
        for interaction in self.interactions:
            diagram.append(f"{interaction['from']} -> {interaction['to']}: {interaction['message']}")

        diagram.append("@enduml")
        return "\n".join(diagram)