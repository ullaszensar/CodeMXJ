import javalang
from typing import Dict, List, Set, Tuple
import networkx as nx
from dataclasses import dataclass

@dataclass
class APIEndpoint:
    path: str
    method: str
    service: str
    class_name: str
    method_name: str

@dataclass
class ServiceDependency:
    source: str
    target: str
    type: str  # 'feign', 'rest', 'kafka', etc.
    details: str

class MicroserviceAnalyzer:
    def __init__(self):
        self.api_endpoints = []
        self.service_dependencies = []
        self.service_names = set()

    def analyze_code(self, code: str, service_name: str) -> None:
        try:
            tree = javalang.parse.parse(code)
            self._analyze_rest_controllers(tree, service_name)
            self._analyze_feign_clients(tree, service_name)
            self._analyze_service_dependencies(tree, service_name)
            self.service_names.add(service_name)
        except Exception as e:
            raise Exception(f"Failed to analyze microservice code: {str(e)}")

    def _analyze_rest_controllers(self, tree, service_name: str) -> None:
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            if self._has_annotation(node.annotations, "RestController"):
                base_path = self._get_request_mapping_path(node.annotations)
                
                for method in node.methods:
                    endpoint = self._extract_endpoint_info(method, base_path, service_name, node.name)
                    if endpoint:
                        self.api_endpoints.append(endpoint)

    def _analyze_feign_clients(self, tree, service_name: str) -> None:
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            if self._has_annotation(node.annotations, "FeignClient"):
                target_service = self._get_feign_client_name(node.annotations)
                if target_service:
                    self.service_dependencies.append(
                        ServiceDependency(
                            source=service_name,
                            target=target_service,
                            type="feign",
                            details=f"FeignClient interface: {node.name}"
                        )
                    )

    def _analyze_service_dependencies(self, tree, service_name: str) -> None:
        # Look for Kafka listeners/producers
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            if self._has_annotation(node.annotations, "KafkaListener"):
                topic = self._get_kafka_topic(node.annotations)
                if topic:
                    self.service_dependencies.append(
                        ServiceDependency(
                            source="kafka",
                            target=service_name,
                            type="kafka",
                            details=f"Listens to topic: {topic}"
                        )
                    )

    def _has_annotation(self, annotations, annotation_name: str) -> bool:
        return any(a.name == annotation_name for a in annotations if hasattr(a, 'name'))

    def _get_request_mapping_path(self, annotations) -> str:
        for annotation in annotations:
            if annotation.name in ["RequestMapping", "GetMapping", "PostMapping", "PutMapping", "DeleteMapping"]:
                if hasattr(annotation, 'element') and annotation.element:
                    for elem in annotation.element:
                        if elem.value.value:
                            return elem.value.value
        return ""

    def _extract_endpoint_info(self, method, base_path: str, service_name: str, class_name: str) -> APIEndpoint:
        http_method = "GET"  # default
        path = ""

        for annotation in method.annotations:
            if annotation.name in ["GetMapping", "PostMapping", "PutMapping", "DeleteMapping"]:
                http_method = annotation.name.replace("Mapping", "").upper()
                if hasattr(annotation, 'element') and annotation.element:
                    for elem in annotation.element:
                        if elem.value.value:
                            path = elem.value.value

        if path or base_path:
            full_path = f"{base_path.rstrip('/')}/{path.lstrip('/')}"
            return APIEndpoint(
                path=full_path,
                method=http_method,
                service=service_name,
                class_name=class_name,
                method_name=method.name
            )
        return None

    def _get_feign_client_name(self, annotations) -> str:
        for annotation in annotations:
            if annotation.name == "FeignClient":
                if hasattr(annotation, 'element') and annotation.element:
                    for elem in annotation.element:
                        if elem.value.value:
                            return elem.value.value
        return None

    def _get_kafka_topic(self, annotations) -> str:
        for annotation in annotations:
            if annotation.name == "KafkaListener":
                if hasattr(annotation, 'element') and annotation.element:
                    for elem in annotation.element:
                        if elem.value.value:
                            return elem.value.value
        return None

    def generate_service_graph(self) -> Tuple[nx.DiGraph, Dict]:
        G = nx.DiGraph()
        
        # Add all services as nodes
        for service in self.service_names:
            G.add_node(service)
        
        # Add dependencies as edges
        for dep in self.service_dependencies:
            if dep.source not in G:
                G.add_node(dep.source)
            if dep.target not in G:
                G.add_node(dep.target)
            G.add_edge(dep.source, dep.target, type=dep.type, details=dep.details)

        pos = nx.spring_layout(G)
        return G, {
            'positions': pos,
            'nodes': list(G.nodes()),
            'edges': [(u, v, d) for u, v, d in G.edges(data=True)]
        }

    def get_api_summary(self) -> Dict[str, List[Dict]]:
        summary = {}
        for endpoint in self.api_endpoints:
            if endpoint.service not in summary:
                summary[endpoint.service] = []
            summary[endpoint.service].append({
                'path': endpoint.path,
                'method': endpoint.method,
                'class': endpoint.class_name,
                'handler': endpoint.method_name
            })
        return summary
