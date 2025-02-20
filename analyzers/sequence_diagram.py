import javalang
from typing import List, Dict, Tuple
import plantuml
import requests
import traceback

class SequenceDiagramGenerator:
    def __init__(self):
        self.interactions = []
        self.current_class = None
        self.plantuml = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/img/')

    def analyze_method_calls(self, code: str, method_name: str) -> Tuple[str, bytes]:
        """Analyze method calls and generate a sequence diagram."""
        try:
            print(f"Analyzing method: {method_name}")  # Debug info
            tree = javalang.parse.parse(code)
            self.interactions = []
            self.current_class = None

            # First pass: identify the class containing the target method
            for path, node in tree.filter(javalang.tree.ClassDeclaration):
                for method in node.methods:
                    print(f"Found method: {method.name}")  # Debug info
                    if method.name == method_name:
                        self.current_class = node.name
                        print(f"Found target method in class: {self.current_class}")  # Debug info
                        self._analyze_method_body(method)
                        break
                if self.current_class:
                    break

            if not self.current_class:
                raise Exception(f"Method '{method_name}' not found in any class")

            # Generate diagram even if no interactions found
            diagram_code = self._generate_sequence_diagram()
            print("Generated diagram code")  # Debug info

            # Get diagram URL and fetch the image
            try:
                diagram_url = self.plantuml.get_url(diagram_code)
                response = requests.get(diagram_url)
                if response.status_code == 200:
                    return diagram_code, response.content
                else:
                    raise Exception(f"Failed to generate diagram image: HTTP {response.status_code}")
            except Exception as e:
                print(f"PlantUML error: {str(e)}")  # Debug info
                raise Exception(f"Error generating diagram image: {str(e)}")

        except Exception as e:
            print(f"Exception stack trace: {traceback.format_exc()}")  # Debug info
            raise Exception(f"Failed to analyze method calls: {str(e)}")

    def _analyze_method_body(self, method_node):
        """Analyze method body for method calls with improved context."""
        try:
            if not method_node.body:
                print(f"Warning: No method body found for {method_node.name}")  # Debug info
                return

            for path, node in method_node.filter(javalang.tree.MethodInvocation):
                if hasattr(node, 'qualifier') and node.qualifier:
                    target_class = str(node.qualifier)  # Convert to string to handle all cases
                else:
                    target_class = self.current_class

                if hasattr(node, 'member'):
                    interaction = {
                        'from': self.current_class,
                        'to': target_class,
                        'message': node.member,
                        'arguments': self._extract_arguments(node)
                    }
                    print(f"Found interaction: {interaction}")  # Debug info
                    self.interactions.append(interaction)

        except Exception as e:
            print(f"Warning: Could not analyze method body: {str(e)}")
            print(f"Method body analysis stack trace: {traceback.format_exc()}")  # Debug info

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

        # If no interactions found, add at least the current class
        if not participants and self.current_class:
            participants.add(self.current_class)

        for participant in sorted(participants):
            diagram.append(f'participant "{participant}" as {participant}')

        # Add interactions with arguments
        for interaction in self.interactions:
            args_str = f"({', '.join(interaction['arguments'])})" if interaction['arguments'] else ""
            diagram.append(
                f"{interaction['from']} -> {interaction['to']}: {interaction['message']}{args_str}"
            )

        # If no interactions, add a note
        if not self.interactions:
            diagram.append(f"note over {self.current_class}: No method calls found")

        diagram.append("@enduml")
        return "\n".join(diagram)