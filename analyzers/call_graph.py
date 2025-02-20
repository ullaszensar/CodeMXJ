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

    def analyze_class_dependencies(self, code: str) -> nx.DiGraph:
        """Analyze class dependencies in Java code and build a dependency graph."""
        try:
            tree = javalang.parse.parse(code)
            self.graph = nx.DiGraph()
            self._analyze_class_relationships(tree)
            return self.graph
        except Exception as e:
            raise Exception(f"Failed to analyze class dependencies: {str(e)}")

    def _analyze_class_relationships(self, tree):
        """Analyze relationships between classes in the parse tree."""
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            class_name = node.name

            # Add class as a node
            if class_name not in self.graph:
                self.graph.add_node(class_name)

            # Handle inheritance
            if node.extends:
                parent_class = node.extends.name
                self.graph.add_node(parent_class)
                self.graph.add_edge(class_name, parent_class, type='Inheritance', 
                                  details=f"{class_name} extends {parent_class}")

            # Handle interface implementations
            if node.implements:
                for interface in node.implements:
                    interface_name = interface.name
                    self.graph.add_node(interface_name)
                    self.graph.add_edge(class_name, interface_name, type='Implementation',
                                      details=f"{class_name} implements {interface_name}")

            # Handle composition/association through field declarations
            self._analyze_field_relationships(node, class_name)

            # Handle method parameter and return type relationships
            self._analyze_method_relationships(node, class_name)

    def _analyze_field_relationships(self, class_node, class_name: str):
        """Analyze relationships through field declarations."""
        if hasattr(class_node, 'fields'):
            for field in class_node.fields:
                if hasattr(field.type, 'name'):
                    field_type = field.type.name
                    # Skip primitive types and common Java types
                    if not self._is_primitive_or_common_type(field_type):
                        self.graph.add_node(field_type)
                        # Check for composition vs association
                        is_composition = self._is_composition_relationship(field)
                        edge_type = 'Composition' if is_composition else 'Association'
                        self.graph.add_edge(class_name, field_type, type=edge_type,
                                          details=f"{class_name} {edge_type.lower()} with {field_type}")

    def _analyze_method_relationships(self, class_node, class_name: str):
        """Analyze relationships through method parameters and return types."""
        for method in class_node.methods:
            # Analyze method parameters
            for param in method.parameters:
                if hasattr(param.type, 'name'):
                    param_type = param.type.name
                    if not self._is_primitive_or_common_type(param_type):
                        self.graph.add_node(param_type)
                        self.graph.add_edge(class_name, param_type, type='Association',
                                          details=f"{class_name} uses {param_type}")

            # Analyze return type
            if method.return_type and hasattr(method.return_type, 'name'):
                return_type = method.return_type.name
                if not self._is_primitive_or_common_type(return_type):
                    self.graph.add_node(return_type)
                    self.graph.add_edge(class_name, return_type, type='Association',
                                      details=f"{class_name} returns {return_type}")

    def _is_primitive_or_common_type(self, type_name: str) -> bool:
        """Check if the type is a primitive or common Java type."""
        primitive_types = {'int', 'long', 'float', 'double', 'boolean', 'char', 'byte', 'short'}
        common_types = {'String', 'Integer', 'Long', 'Float', 'Double', 'Boolean', 'Character', 'Byte', 'Short'}
        return type_name in primitive_types or type_name in common_types

    def _is_composition_relationship(self, field) -> bool:
        """Determine if a field represents a composition relationship."""
        # Check for final modifier or private access with no setters
        return any(modifier == 'final' for modifier in field.modifiers)

    def get_dependency_statistics(self, graph: nx.DiGraph) -> Dict:
        """Calculate dependency statistics from the graph."""
        total_classes = len(graph.nodes())
        total_dependencies = len(graph.edges())
        avg_dependencies = total_dependencies / total_classes if total_classes > 0 else 0

        # Calculate maximum inheritance depth
        max_inheritance_depth = 0
        for node in graph.nodes():
            # Find all paths from this node following only inheritance edges
            for target in graph.nodes():
                if node != target:
                    paths = nx.all_simple_paths(graph, node, target)
                    for path in paths:
                        # Check if path consists only of inheritance relationships
                        inheritance_path = all(
                            graph[path[i]][path[i+1]]['type'] == 'Inheritance'
                            for i in range(len(path)-1)
                        )
                        if inheritance_path:
                            max_inheritance_depth = max(max_inheritance_depth, len(path)-1)

        return {
            'total_classes': total_classes,
            'total_dependencies': total_dependencies,
            'avg_dependencies': avg_dependencies,
            'max_inheritance_depth': max_inheritance_depth
        }

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