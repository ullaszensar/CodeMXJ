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

    def _sanitize_java_code(self, code: str) -> str:
        """Pre-process Java code to handle common parsing issues."""
        # Remove package-info.java content as it can't be parsed
        if "package-info" in code:
            return ""

        # Remove any BOM markers
        code = code.replace('\ufeff', '')

        # Remove multi-line comments
        code = re.sub(r'/\*[\s\S]*?\*/', '', code)

        # Remove single-line comments
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)

        # Ensure proper class structure
        if not re.search(r'(class|interface|enum)\s+\w+', code, re.MULTILINE):
            return ""

        # Remove any trailing semicolons after class closing braces
        code = re.sub(r'};(\s*)$', r'}\1', code)

        # Ensure proper package declaration
        if not code.strip().startswith("package"):
            code = "package temp;\n" + code

        return code.strip()

    def analyze_method_calls(self, code: str, method_name: str) -> Tuple[str, bytes]:
        """Analyze method calls and generate a sequence diagram."""
        try:
            if not code or not method_name:
                raise ValueError("Code and method name must not be empty")

            logger.debug(f"Starting analysis for method: {method_name}")
            logger.debug(f"Original code length: {len(code)} characters")

            # Split code into individual files based on package declarations
            file_contents = self._split_java_files(code)
            logger.debug(f"Split code into {len(file_contents)} files")

            self.interactions = []
            self.current_class = None
            method_found = False

            for file_code in file_contents:
                try:
                    # Pre-process the code
                    processed_code = self._sanitize_java_code(file_code)
                    if not processed_code:
                        logger.debug("Skipping empty/invalid file after sanitization")
                        continue

                    logger.debug(f"Processing file with length: {len(processed_code)}")
                    logger.debug(f"File content sample: {processed_code[:200]}")

                    # Try to tokenize first
                    try:
                        tokens = list(javalang.tokenizer.tokenize(processed_code))
                        logger.debug(f"Successfully tokenized code. Found {len(tokens)} tokens")
                    except Exception as token_error:
                        logger.warning(f"Tokenization failed: {str(token_error)}")
                        continue

                    # Parse the file
                    tree = javalang.parse.parse(processed_code)
                    logger.debug("Successfully parsed Java code")

                    # Look for the target method
                    for path, node in tree.filter(javalang.tree.ClassDeclaration):
                        logger.debug(f"Analyzing class: {node.name}")
                        for method in node.methods:
                            if method.name == method_name:
                                self.current_class = node.name
                                logger.info(f"Found target method '{method_name}' in class: {self.current_class}")
                                self._analyze_method_body(method)
                                method_found = True
                                break
                        if method_found:
                            break

                except Exception as file_error:
                    logger.warning(f"Error processing file: {str(file_error)}")
                    continue

            if not method_found:
                raise Exception(f"Method '{method_name}' not found in any class")

            # Generate diagram
            diagram_code = self._generate_sequence_diagram()
            logger.debug("Successfully generated diagram code")

            # Get diagram image
            try:
                diagram_url = self.plantuml.get_url(diagram_code)
                response = requests.get(diagram_url)
                if response.status_code == 200:
                    logger.info("Successfully generated sequence diagram")
                    return diagram_code, response.content
                else:
                    raise Exception(f"Failed to generate diagram image: HTTP {response.status_code}")
            except Exception as image_error:
                logger.error(f"PlantUML error: {str(image_error)}")
                raise

        except Exception as e:
            logger.error(f"Failed to analyze method calls: {str(e)}")
            logger.debug(f"Full stack trace: {traceback.format_exc()}")
            raise

    def _split_java_files(self, code: str) -> List[str]:
        """Split combined Java code into individual files based on package declarations."""
        # Split on package declarations
        files = re.split(r'(?m)^package\s+', code)
        # Add package declaration back to each file except the first empty one
        return [f"package {file}" for file in files[1:] if file.strip()]

    def _analyze_method_body(self, method_node):
        """Analyze method body for method calls."""
        if not method_node.body:
            logger.warning(f"No method body found for {method_node.name}")
            return None

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
            participants = set()
            for interaction in self.interactions:
                participants.add(interaction['from'])
                participants.add(interaction['to'])

            # If no interactions found, add at least the current class
            if not participants and self.current_class:
                participants.add(self.current_class)

            for participant in sorted(participants):
                diagram.append(f'participant "{participant}" as {participant}')

            # Add interactions
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