import javalang
from typing import List, Dict, Tuple
import plantuml
import requests
import traceback
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SequenceDiagramGenerator:
    def __init__(self):
        self.interactions = []
        self.current_class = None
        self.plantuml = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/img/')

    def analyze_method_calls(self, code: str, method_name: str) -> Tuple[str, bytes]:
        """Analyze method calls and generate a sequence diagram."""
        try:
            if not code or not method_name:
                raise ValueError("Code and method name must not be empty")

            logger.debug(f"Starting analysis for method: {method_name}")
            logger.debug(f"Code length: {len(code)} characters")
            logger.debug(f"Code sample (first 100 chars): {code[:100]}")

            # Pre-process code to handle potential formatting issues
            code = code.strip()
            if not code.endswith("}"):
                logger.warning("Code might be incomplete or malformed")

            try:
                tree = javalang.parse.parse(code)
                logger.debug("Successfully parsed Java code")
            except Exception as parse_error:
                logger.error(f"Failed to parse Java code: {str(parse_error)}")
                logger.debug(f"Parse error details: {traceback.format_exc()}")
                # Try to get more specific error information
                try:
                    tokens = list(javalang.tokenizer.tokenize(code))
                    logger.debug(f"Tokenization successful, found {len(tokens)} tokens")
                except Exception as token_error:
                    logger.error(f"Tokenization failed: {str(token_error)}")
                raise Exception(f"Failed to parse Java code: {str(parse_error)}")

            self.interactions = []
            self.current_class = None

            # First pass: identify the class containing the target method
            class_found = False
            for path, node in tree.filter(javalang.tree.ClassDeclaration):
                logger.debug(f"Analyzing class: {node.name}")
                for method in node.methods:
                    logger.debug(f"Found method: {method.name}")
                    if method.name == method_name:
                        self.current_class = node.name
                        logger.info(f"Found target method '{method_name}' in class: {self.current_class}")
                        self._analyze_method_body(method)
                        class_found = True
                        break
                if class_found:
                    break

            if not self.current_class:
                logger.error(f"Method '{method_name}' not found in any class")
                raise Exception(f"Method '{method_name}' not found in any class")

            # Generate diagram code
            try:
                diagram_code = self._generate_sequence_diagram()
                logger.debug("Successfully generated diagram code")
            except Exception as diagram_error:
                logger.error(f"Failed to generate diagram code: {str(diagram_error)}")
                raise Exception(f"Failed to generate diagram code: {str(diagram_error)}")

            # Get diagram URL and fetch the image
            try:
                logger.debug("Attempting to generate PlantUML diagram")
                diagram_url = self.plantuml.get_url(diagram_code)
                response = requests.get(diagram_url)
                if response.status_code == 200:
                    logger.info("Successfully generated sequence diagram")
                    return diagram_code, response.content
                else:
                    error_msg = f"Failed to generate diagram image: HTTP {response.status_code}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
            except Exception as image_error:
                logger.error(f"PlantUML error: {str(image_error)}")
                raise Exception(f"Error generating diagram image: {str(image_error)}")

        except Exception as e:
            logger.error(f"Failed to analyze method calls: {str(e)}")
            logger.debug(f"Full stack trace: {traceback.format_exc()}")
            raise

    def _analyze_method_body(self, method_node):
        """Analyze method body for method calls with improved context."""
        if not method_node.body:
            logger.warning(f"No method body found for {method_node.name}")
            return

        try:
            for path, node in method_node.filter(javalang.tree.MethodInvocation):
                try:
                    if hasattr(node, 'qualifier') and node.qualifier:
                        target_class = str(node.qualifier)
                    else:
                        target_class = self.current_class

                    if hasattr(node, 'member'):
                        interaction = {
                            'from': self.current_class,
                            'to': target_class,
                            'message': node.member,
                            'arguments': self._extract_arguments(node)
                        }
                        logger.debug(f"Found interaction: {interaction}")
                        self.interactions.append(interaction)
                except Exception as node_error:
                    logger.warning(f"Could not process method invocation: {str(node_error)}")

        except Exception as e:
            logger.error(f"Error analyzing method body: {str(e)}")
            logger.debug(f"Method body analysis stack trace: {traceback.format_exc()}")

    def _extract_arguments(self, method_node) -> List[str]:
        """Extract method call arguments for better diagram details."""
        args = []
        try:
            if hasattr(method_node, 'arguments'):
                for arg in method_node.arguments:
                    if hasattr(arg, 'value'):
                        args.append(str(arg.value))
                    else:
                        args.append(str(arg))
        except Exception as e:
            logger.warning(f"Error extracting arguments: {str(e)}")
        return args

    def _generate_sequence_diagram(self) -> str:
        """Generate PlantUML sequence diagram with improved formatting."""
        try:
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

            result = "\n".join(diagram)
            logger.debug(f"Generated PlantUML diagram code:\n{result}")
            return result

        except Exception as e:
            logger.error(f"Error generating sequence diagram: {str(e)}")
            raise Exception(f"Failed to generate sequence diagram: {str(e)}")