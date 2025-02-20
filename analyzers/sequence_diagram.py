import javalang
from typing import List, Dict, Tuple
import plantuml
import requests

class SequenceDiagramGenerator:
    def __init__(self):
        self.interactions = []
        self.current_class = None
        self.plantuml = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/img/')

    def analyze_method_calls(self, code: str, method_name: str) -> Tuple[str, bytes]:
        try:
            tree = javalang.parse.parse(code)
            self.interactions = []
            self.current_class = None

            # First pass: identify the class containing the target method
            for path, node in tree.filter(javalang.tree.ClassDeclaration):
                for method in node.methods:
                    if method.name == method_name:
                        self.current_class = node.name
                        self._analyze_method_body(method)
                        break
                if self.current_class:
                    break

            if not self.current_class:
                raise Exception(f"Method {method_name} not found in any class")

            diagram_code = self._generate_sequence_diagram()

            # Get diagram URL and fetch the image
            diagram_url = self.plantuml.get_url(diagram_code)
            response = requests.get(diagram_url)
            if response.status_code == 200:
                return diagram_code, response.content
            else:
                raise Exception(f"Failed to generate diagram image: HTTP {response.status_code}")
        except Exception as e:
            raise Exception(f"Failed to analyze method calls: {str(e)}")

    def _analyze_method_body(self, method_node):
        """Analyze method body for method calls with improved context."""
        try:
            if not method_node.body:
                return

            for path, node in method_node.filter(javalang.tree.MethodInvocation):
                if hasattr(node, 'qualifier') and node.qualifier:
                    # If we have a qualifier, use it as the target class
                    target_class = node.qualifier
                else:
                    # If no qualifier, the call is within the same class
                    target_class = self.current_class

                if hasattr(node, 'member'):
                    self.interactions.append({
                        'from': self.current_class,
                        'to': target_class,
                        'message': node.member,
                        'arguments': self._extract_arguments(node)
                    })
        except Exception as e:
            print(f"Warning: Could not analyze method body: {str(e)}")

    def _extract_arguments(self, method_node) -> List[str]:
        """Extract method call arguments for better diagram details."""
        args = []
        if hasattr(method_node, 'arguments'):
            for arg in method_node.arguments:
                if hasattr(arg, 'value'):
                    args.append(str(arg.value))
                else:
                    args.append(str(arg))
        return args

    def _generate_sequence_diagram(self) -> str:
        """Generate PlantUML sequence diagram with improved formatting."""
        diagram = [
            "@startuml",
            "skinparam sequenceMessageAlign center",
            "skinparam responseMessageBelowArrow true",
            "skinparam maxMessageSize 100",
            "skinparam sequence {",
            "    ArrowColor DeepSkyBlue",
            "    LifeLineBorderColor blue",
            "    ParticipantBorderColor DarkBlue",
            "    ParticipantBackgroundColor LightBlue",
            "    ParticipantFontStyle bold",
            "}"
        ]

        # Add participants
        participants = set()
        for interaction in self.interactions:
            participants.add(interaction['from'])
            participants.add(interaction['to'])

        for participant in sorted(participants):
            diagram.append(f'participant "{participant}" as {participant}')

        # Add interactions with arguments
        for interaction in self.interactions:
            args_str = f"({', '.join(interaction['arguments'])})" if interaction['arguments'] else ""
            diagram.append(
                f"{interaction['from']} -> {interaction['to']}: {interaction['message']}{args_str}"
            )

        diagram.append("@enduml")
        return "\n".join(diagram)