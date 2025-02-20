import javalang
from typing import List, Dict, Tuple
import plantuml
import requests
import traceback
import logging
import re

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SequenceDiagramGenerator:
    def __init__(self):
        self.interactions = []
        self.current_class = None
        self.plantuml = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/img/')

    def _preprocess_java_code(self, code: str) -> str:
        """Pre-process Java code to handle common parsing issues."""
        try:
            # Remove BOM and normalize line endings
            code = code.replace('\ufeff', '').replace('\r\n', '\n')

            # Remove comments
            code = re.sub(r'/\*[\s\S]*?\*/', '', code)  # Remove multi-line comments
            code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)  # Remove single-line comments

            # Add package declaration if missing
            if not re.search(r'^\s*package\s+[\w.]+;', code, re.MULTILINE):
                code = "package temp;\n" + code

            # Ensure proper class structure
            if not re.search(r'(class|interface|enum)\s+\w+', code, re.MULTILINE):
                logger.warning("No valid class/interface/enum declaration found")
                return ""

            # Clean up any trailing semicolons after class/interface declarations
            code = re.sub(r'(class|interface|enum)\s+\w+\s*{\s*};', r'\1 \2 {}', code)

            # Remove any trailing semicolons after closing braces
            code = re.sub(r'};(\s*)$', r'}\1', code)

            return code.strip()
        except Exception as e:
            logger.error(f"Error preprocessing Java code: {str(e)}")
            return ""

    def _validate_java_code(self, code: str) -> bool:
        """Validate Java code structure."""
        try:
            # Basic structure validation
            if not code or len(code.strip()) == 0:
                logger.warning("Empty code")
                return False

            # Check for basic Java structure
            required_patterns = [
                (r'(class|interface|enum)\s+\w+', "No class/interface/enum declaration found"),
                (r'{', "No opening brace found"),
                (r'}', "No closing brace found")
            ]

            for pattern, message in required_patterns:
                if not re.search(pattern, code):
                    logger.warning(message)
                    return False

            return True
        except Exception as e:
            logger.error(f"Error validating Java code: {str(e)}")
            return False

    def analyze_method_calls(self, code: str, method_name: str) -> Tuple[str, bytes]:
        """Analyze method calls and generate a sequence diagram."""
        try:
            if not code or not method_name:
                raise ValueError("Code and method name must not be empty")

            logger.info(f"Starting analysis for method: {method_name}")
            logger.debug(f"Input code length: {len(code)} characters")

            # Preprocess code
            processed_code = self._preprocess_java_code(code)
            if not self._validate_java_code(processed_code):
                raise ValueError("Invalid Java code structure")

            logger.debug(f"Processed code length: {len(processed_code)} characters")
            logger.debug(f"Processed code sample:\n{processed_code[:200]}...")

            # Try parsing
            try:
                logger.debug("Attempting to tokenize code...")
                tokens = list(javalang.tokenizer.tokenize(processed_code))
                logger.debug(f"Successfully tokenized. Found {len(tokens)} tokens")

                logger.debug("Attempting to parse code...")
                tree = javalang.parse.parse(processed_code)
                logger.debug("Successfully parsed Java code")
            except Exception as parse_error:
                logger.error(f"Failed to parse Java code: {str(parse_error)}")
                logger.debug(f"Parse error details: {traceback.format_exc()}")
                raise ValueError(f"Failed to parse Java code: {str(parse_error)}")

            self.interactions = []
            self.current_class = None
            method_found = False

            # Analyze classes and methods
            for path, node in tree.filter(javalang.tree.ClassDeclaration):
                logger.debug(f"Analyzing class: {node.name}")

                for method in node.methods:
                    if method.name == method_name:
                        self.current_class = node.name
                        logger.info(f"Found method '{method_name}' in class '{node.name}'")
                        self._analyze_method_body(method)
                        method_found = True
                        break

                if method_found:
                    break

            if not method_found:
                raise ValueError(f"Method '{method_name}' not found in any class")

            # Generate sequence diagram
            diagram_code = self._generate_sequence_diagram()
            logger.debug("Generated sequence diagram code")

            # Get diagram image
            try:
                diagram_url = self.plantuml.get_url(diagram_code)
                response = requests.get(diagram_url)

                if response.status_code != 200:
                    raise ValueError(f"Failed to generate diagram image: HTTP {response.status_code}")

                logger.info("Successfully generated sequence diagram")
                return diagram_code, response.content

            except Exception as image_error:
                logger.error(f"Error generating diagram image: {str(image_error)}")
                raise

        except Exception as e:
            logger.error(f"Error in analyze_method_calls: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            raise

    def _analyze_method_body(self, method_node):
        """Analyze method body for method calls."""
        if not method_node.body:
            logger.warning(f"No body found for method {method_node.name}")
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
                    logger.warning(f"Error processing method invocation: {str(node_error)}")

        except Exception as e:
            logger.error(f"Error analyzing method body: {str(e)}")

    def _generate_sequence_diagram(self) -> str:
        """Generate PlantUML sequence diagram."""
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
            participants = {self.current_class}  # Always include current class
            for interaction in self.interactions:
                participants.add(interaction['from'])
                participants.add(interaction['to'])

            for participant in sorted(participants):
                diagram.append(f'participant "{participant}" as {participant}')

            # Add interactions
            for interaction in self.interactions:
                args_str = f"({', '.join(interaction['arguments'])})" if interaction['arguments'] else ""
                message = f"{interaction['message']}{args_str}"
                diagram.append(f"{interaction['from']} -> {interaction['to']}: {message}")

            if not self.interactions:
                diagram.append(f"note over {self.current_class}: No method calls found")

            diagram.append("@enduml")
            return "\n".join(diagram)

        except Exception as e:
            logger.error(f"Error generating sequence diagram: {str(e)}")
            raise

    def _extract_arguments(self, method_node) -> List[str]:
        """Extract method call arguments."""
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

    def _split_java_files(self, code: str) -> List[str]:
        """Split combined Java code into individual files based on package declarations."""
        # Split on package declarations
        files = re.split(r'(?m)^package\s+', code)
        # Add package declaration back to each file except the first empty one
        return [f"package {file}" for file in files[1:] if file.strip()]