import networkx as nx
import javalang
from typing import Dict, Set, List
import re

class CallGraphAnalyzer:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.methods = set()
        self.current_class = None

    def analyze_calls(self, code: str) -> nx.DiGraph:
        """Analyze method calls in Java code and build a call graph."""
        try:
            tree = javalang.parse.parse(code)
            self._analyze_classes(tree)
            return self.graph
        except Exception as e:
            raise Exception(f"Failed to analyze call graph: {str(e)}")

    def _analyze_classes(self, tree):
        """Analyze all classes in the parse tree."""
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            self.current_class = node.name
            self._analyze_methods(node)

    def _analyze_methods(self, class_node):
        """Analyze all methods in a class."""
        for method in class_node.methods:
            current_method = f"{self.current_class}.{method.name}"
            self.methods.add(current_method)

            if method.body:
                self._analyze_method_body(method.body, current_method)

    def _analyze_method_body(self, body, current_method: str):
        """Analyze method body for method calls."""
        try:
            for _, node in body.filter(javalang.tree.MethodInvocation):
                if hasattr(node, 'member'):
                    called_method = node.member
                    # If we have qualifier, it's likely a method call on another class
                    if hasattr(node, 'qualifier'):
                        called_method = f"{node.qualifier}.{called_method}"
                    else:
                        # If no qualifier, assume it's a method in the current class
                        called_method = f"{self.current_class}.{called_method}"

                    self.methods.add(called_method)
                    self.graph.add_edge(current_method, called_method)
        except Exception as e:
            print(f"Warning: Could not analyze method body for {current_method}: {str(e)}")

    def get_graph_data(self) -> Dict:
        """Get graph data in a format suitable for visualization."""
        pos = nx.spring_layout(self.graph)
        return {
            'nodes': list(self.graph.nodes()),
            'edges': list(self.graph.edges()),
            'positions': {node: [pos[node][0], pos[node][1]] for node in self.graph.nodes()}
        }

    def get_method_list(self) -> List[str]:
        """Get a sorted list of all methods in the analyzed code."""
        return sorted(list(self.methods))