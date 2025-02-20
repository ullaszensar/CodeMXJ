import javalang
from typing import List, Dict

class SequenceDiagramGenerator:
    def __init__(self):
        self.interactions = []

    def analyze_method_calls(self, code: str, method_name: str) -> str:
        try:
            tree = javalang.parse.parse(code)
            self.interactions = []
            
            for path, node in tree.filter(javalang.tree.MethodDeclaration):
                if node.name == method_name:
                    self._analyze_method_body(node)
            
            return self._generate_sequence_diagram()
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
        diagram = ["@startuml"]
        
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
