import javalang
import re
from typing import Dict, List, Set, Tuple
import networkx as nx
from dataclasses import dataclass, field

@dataclass
class APIEndpoint:
    path: str
    method: str
    service: str
    class_name: str
    method_name: str
    request_params: List[str]
    response_fields: List[str]
    legacy_tables: List[str]
    client_type: str = "Direct Controller"  # Can be RestTemplate/FeignClient/Direct Controller
    called_services: List[str] = field(default_factory=list)  # Track services called by this endpoint

@dataclass
class SOAPOperation:
    operation_name: str
    interface: str
    wsdl_location: str
    input_params: List[str]
    output_type: str
    service: str

@dataclass
class ServiceDependency:
    source: str
    target: str
    type: str
    details: str
    api_calls: List[str] = field(default_factory=list)

class MicroserviceAnalyzer:
    def __init__(self):
        self.api_endpoints = []
        self.soap_operations = []
        self.service_dependencies = []
        self.service_names = set()
        self.legacy_table_patterns = [
            r'FROM\s+([A-Za-z0-9_]+)',
            r'UPDATE\s+([A-Za-z0-9_]+)',
            r'INSERT\s+INTO\s+([A-Za-z0-9_]+)',
            r'DELETE\s+FROM\s+([A-Za-z0-9_]+)'
        ]

    def analyze_code(self, code: str, service_name: str) -> None:
        try:
            tree = javalang.parse.parse(code)
            self._analyze_rest_controllers(tree, service_name)
            self._analyze_feign_clients(tree, service_name)
            self._analyze_soap_services(tree, service_name)
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
                        # Analyze method body for legacy table usage
                        legacy_tables = self._find_legacy_tables(method)
                        endpoint.legacy_tables = legacy_tables

                        # Extract request parameters
                        request_params = self._extract_request_parameters(method)
                        endpoint.request_params = request_params

                        # Extract response fields
                        response_fields = self._extract_response_fields(method)
                        endpoint.response_fields = response_fields

                        # Analyze service calls within the method
                        called_services = self._analyze_service_calls(method)
                        endpoint.called_services = called_services

                        self.api_endpoints.append(endpoint)

    def _get_request_mapping_path(self, annotations) -> str:
        for annotation in annotations:
            if annotation.name in ["RequestMapping", "GetMapping", "PostMapping", "PutMapping", "DeleteMapping"]:
                if hasattr(annotation, 'element') and annotation.element:
                    for elem in annotation.element:
                        if isinstance(elem, tuple) and len(elem) > 1:
                            # Handle tuple format (name, value)
                            return elem[1].value
                        elif hasattr(elem, 'value') and hasattr(elem.value, 'value'):
                            # Handle object format with nested value
                            return elem.value.value
                        elif hasattr(elem, 'value'):
                            # Handle direct value
                            return elem.value
        return ""

    def _extract_endpoint_info(self, method, base_path: str, service_name: str, class_name: str) -> APIEndpoint:
        http_method = "GET"  # default
        path = ""

        for annotation in method.annotations:
            if annotation.name in ["GetMapping", "PostMapping", "PutMapping", "DeleteMapping"]:
                http_method = annotation.name.replace("Mapping", "").upper()
                if hasattr(annotation, 'element') and annotation.element:
                    for elem in annotation.element:
                        if isinstance(elem, tuple) and len(elem) > 1:
                            path = elem[1].value
                        elif hasattr(elem, 'value') and hasattr(elem.value, 'value'):
                            path = elem.value.value
                        elif hasattr(elem, 'value'):
                            path = elem.value

        if path or base_path:
            full_path = f"{base_path.rstrip('/')}/{path.lstrip('/')}"
            return APIEndpoint(
                path=full_path,
                method=http_method,
                service=service_name,
                class_name=class_name,
                method_name=method.name,
                request_params=[],
                response_fields=[],
                legacy_tables=[]
            )
        return None

    def _analyze_soap_services(self, tree, service_name: str) -> None:
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            if self._has_annotation(node.annotations, "WebService"):
                wsdl_location = self._get_wsdl_location(node.annotations)

                for method in node.methods:
                    if self._has_annotation(method.annotations, "WebMethod"):
                        operation = SOAPOperation(
                            operation_name=method.name,
                            interface=node.name,
                            wsdl_location=wsdl_location or "Not specified",
                            input_params=self._extract_soap_parameters(method),
                            output_type=str(method.return_type) if method.return_type else "void",
                            service=service_name
                        )
                        self.soap_operations.append(operation)

    def get_api_details(self) -> Dict[str, List[Dict]]:
        details = {}
        for endpoint in self.api_endpoints:
            if endpoint.service not in details:
                details[endpoint.service] = []
            details[endpoint.service].append({
                'path': endpoint.path,
                'method': endpoint.method,
                'class': endpoint.class_name,
                'handler': endpoint.method_name,
                'client_type': endpoint.client_type,
                'request_params': endpoint.request_params,
                'response_fields': endpoint.response_fields,
                'legacy_tables': endpoint.legacy_tables,
                'called_services': endpoint.called_services or []
            })
        return details

    def get_rest_api_details(self) -> Dict[str, List[Dict]]:
        return self.get_api_details()

    def get_soap_service_details(self) -> Dict[str, List[Dict]]:
        details = {}
        for operation in self.soap_operations:
            if operation.service not in details:
                details[operation.service] = []
            details[operation.service].append({
                'operation_name': operation.operation_name,
                'interface': operation.interface,
                'wsdl_location': operation.wsdl_location,
                'input_params': operation.input_params,
                'output_type': operation.output_type
            })
        return details

    def _has_annotation(self, annotations, annotation_name: str) -> bool:
        return any(a.name == annotation_name for a in annotations if hasattr(a, 'name'))

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
                            details=f"FeignClient interface: {node.name}",
                            api_calls=[]
                        )
                    )

    def _analyze_service_dependencies(self, tree, service_name: str) -> None:
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            if self._has_annotation(node.annotations, "KafkaListener"):
                topic = self._get_kafka_topic(node.annotations)
                if topic:
                    self.service_dependencies.append(
                        ServiceDependency(
                            source="kafka",
                            target=service_name,
                            type="kafka",
                            details=f"Listens to topic: {topic}",
                            api_calls=[]
                        )
                    )

    def _get_feign_client_name(self, annotations) -> str:
        for annotation in annotations:
            if annotation.name == "FeignClient":
                if hasattr(annotation, 'element') and annotation.element:
                    for elem in annotation.element:
                        if isinstance(elem, tuple) and len(elem) > 1:
                            return elem[1].value
                        elif hasattr(elem, 'value') and hasattr(elem.value, 'value'):
                            return elem.value.value
                        elif hasattr(elem, 'value'):
                            return elem.value
        return None

    def _get_kafka_topic(self, annotations) -> str:
        for annotation in annotations:
            if annotation.name == "KafkaListener":
                if hasattr(annotation, 'element') and annotation.element:
                    for elem in annotation.element:
                        if isinstance(elem, tuple) and len(elem) > 1:
                            return elem[1].value
                        elif hasattr(elem, 'value') and hasattr(elem.value, 'value'):
                            return elem.value.value
                        elif hasattr(elem, 'value'):
                            return elem.value
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

    def _analyze_service_calls(self, method) -> List[str]:
        called_services = []
        if hasattr(method, 'body') and method.body:
            # Look for RestTemplate calls
            for path, node in method.filter(javalang.tree.MethodInvocation):
                if hasattr(node, 'qualifier') and 'restTemplate' in str(node.qualifier).lower():
                    called_services.append("RestTemplate Call")

            # Look for Feign client calls
            for path, node in method.filter(javalang.tree.FieldDeclaration):
                if node.declarators and hasattr(node.type, 'name'):
                    if self._is_feign_client(node.type.name):
                        called_services.append(f"FeignClient: {node.type.name}")

        return called_services

    def _extract_soap_parameters(self, method) -> List[str]:
        params = []
        for param in method.parameters:
            param_type = str(param.type)
            params.append(f"{param_type} {param.name}")
        return params

    def _extract_request_parameters(self, method) -> List[str]:
        params = []
        for param in method.parameters:
            if self._has_annotation(param.annotations, "RequestParam") or \
               self._has_annotation(param.annotations, "PathVariable") or \
               self._has_annotation(param.annotations, "RequestBody"):
                params.append(f"{param.type.name} {param.name}")
        return params

    def _extract_response_fields(self, method) -> List[str]:
        fields = []
        return_type = method.return_type
        if return_type and hasattr(return_type, 'name'):
            # Add basic return type
            fields.append(return_type.name)

            # Look for ResponseEntity type
            if return_type.name == 'ResponseEntity':
                # Try to extract generic type if present
                if hasattr(return_type, 'arguments') and return_type.arguments:
                    fields.extend(arg.type.name for arg in return_type.arguments)
        return fields

    def _find_legacy_tables(self, method) -> List[str]:
        tables = set()
        if hasattr(method, 'body') and method.body:
            code = str(method.body)
            for pattern in self.legacy_table_patterns:
                matches = re.finditer(pattern, code, re.IGNORECASE)
                for match in matches:
                    tables.add(match.group(1))
        return list(tables)

    def _is_feign_client(self, type_name: str) -> bool:
        return "FeignClient" in type_name

    def _get_wsdl_location(self, annotations) -> str:
        for annotation in annotations:
            if annotation.name == "WebService":
                if hasattr(annotation, 'element') and annotation.element:
                    for elem in annotation.element:
                        if isinstance(elem, tuple) and len(elem) > 1 and elem[0] == 'wsdlLocation':
                            return elem[1].value
                        elif hasattr(elem, 'value') and hasattr(elem.value, 'value') and elem.name == 'wsdlLocation':
                            return elem.value.value
        return None