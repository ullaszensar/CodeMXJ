import networkx as nx
import javalang
from typing import Dict, Set

class CallGraphAnalyzer:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.methods = set()

    def analyze_calls(self, code: str) -> nx.DiGraph:
        try:
            tree = javalang.parse.parse(code)
            self._build_call_graph(tree)
            return self.graph
        except Exception as e:
            raise Exception(f"Failed to analyze call graph: {str(e)}")

    def _build_call_graph(self, tree):
        current_method = None
        
        for path, node in tree.filter(javalang.tree.MethodDeclaration):
            current_method = node.name
            self.methods.add(current_method)
            
            # Analyze method body for method calls
            for _, call_node in node.filter(javalang.tree.MethodInvocation):
                if hasattr(call_node, 'member'):
                    called_method = call_node.member
                    self.methods.add(called_method)
                    self.graph.add_edge(current_method, called_method)

    def get_graph_data(self) -> Dict:
        pos = nx.spring_layout(self.graph)
        return {
            'nodes': list(self.graph.nodes()),
            'edges': list(self.graph.edges()),
            'positions': {node: [pos[node][0], pos[node][1]] for node in self.graph.nodes()}
        }
