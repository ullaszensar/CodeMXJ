import networkx as nx
import javalang
from typing import Dict, Set, List
import re
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class CallGraphAnalyzer:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.methods = set()
        self.current_class = None

    def analyze_calls(self, code: str) -> nx.DiGraph:
        """Analyze method calls in Java code and build a call graph."""
        try:
            if not code:
                raise ValueError("Code cannot be empty")

            logger.debug("Starting Java code analysis")
            try:
                tree = javalang.parse.parse(code)
                logger.debug("Successfully parsed Java code")
            except Exception as parse_error:
                logger.error(f"Failed to parse Java code: {str(parse_error)}")
                raise Exception(f"Failed to parse Java code: {str(parse_error)}")

            self._analyze_classes(tree)
            logger.info(f"Analysis complete. Found {len(self.methods)} methods")
            return self.graph
        except Exception as e:
            logger.error(f"Failed to analyze call graph: {str(e)}")
            raise Exception(f"Failed to analyze call graph: {str(e)}")

    def _analyze_classes(self, tree):
        """Analyze all classes in the parse tree."""
        try:
            for path, node in tree.filter(javalang.tree.ClassDeclaration):
                logger.debug(f"Analyzing class: {node.name}")
                self.current_class = node.name
                self._analyze_methods(node)
        except Exception as e:
            logger.error(f"Error analyzing classes: {str(e)}")
            raise

    def _analyze_methods(self, class_node):
        """Analyze all methods in a class."""
        try:
            for method in class_node.methods:
                current_method = f"{self.current_class}.{method.name}"
                logger.debug(f"Analyzing method: {current_method}")
                self.methods.add(current_method)

                if method.body:
                    self._analyze_method_body(method.body, current_method)
        except Exception as e:
            logger.error(f"Error analyzing methods in class {self.current_class}: {str(e)}")
            raise

    def _analyze_method_body(self, body, current_method: str):
        """Analyze method body for method calls."""
        try:
            for _, node in body.filter(javalang.tree.MethodInvocation):
                try:
                    if hasattr(node, 'member'):
                        called_method = node.member
                        # If we have qualifier, it's likely a method call on another class
                        if hasattr(node, 'qualifier') and node.qualifier:
                            called_method = f"{node.qualifier}.{called_method}"
                        else:
                            # If no qualifier, assume it's a method in the current class
                            called_method = f"{self.current_class}.{called_method}"

                        logger.debug(f"Found method call: {current_method} -> {called_method}")
                        self.methods.add(called_method)
                        self.graph.add_edge(current_method, called_method)
                except Exception as node_error:
                    logger.warning(f"Could not process method invocation in {current_method}: {str(node_error)}")
        except Exception as e:
            logger.error(f"Error analyzing method body for {current_method}: {str(e)}")
            raise

    def get_graph_data(self) -> Dict:
        """Get graph data in a format suitable for visualization."""
        try:
            pos = nx.spring_layout(self.graph)
            data = {
                'nodes': list(self.graph.nodes()),
                'edges': list(self.graph.edges()),
                'positions': {node: [pos[node][0], pos[node][1]] for node in self.graph.nodes()}
            }
            logger.debug(f"Generated graph data with {len(data['nodes'])} nodes and {len(data['edges'])} edges")
            return data
        except Exception as e:
            logger.error(f"Error generating graph data: {str(e)}")
            raise

    def get_method_list(self) -> List[str]:
        """Get a sorted list of all methods in the analyzed code."""
        return sorted(list(self.methods))