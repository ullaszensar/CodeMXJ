import javalang
from typing import Dict, List, Set
from dataclasses import dataclass

@dataclass
class LegacyTableUsage:
    table_name: str
    system: str
    file_path: str
    class_name: str
    method_name: str
    usage_type: str  # e.g., "SELECT", "JOIN", "Reference"

class LegacyTableAnalyzer:
    def __init__(self):
        # Define legacy systems and their tables
        self.legacy_systems = {
            "CRPS": ["CRPS_CUSTOMER", "CRPS_ACCOUNT", "CRPS_PORTFOLIO"],
            "CRIF": ["CRIF_MEMBER", "CRIF_RECORD", "CRIF_HISTORY"],
            "GNAT": ["GNAT_NAME", "GNAT_ADDRESS", "GNAT_TELEPHONE"],
            "Globestar": ["GLOBESTAR_TRANSACTION", "GLOBESTAR_ACCOUNT"],
            "Triumph": ["TRIUMPH_DATA", "TRIUMPH_HISTORY"],
            "CARS": ["CARS_RECORD", "CARS_TRANSACTION"],
            "MNS": ["MNS_NOTIFICATION", "MNS_TEMPLATE"],
            "CARE": ["CARE_CASE", "CARE_INTERACTION"]
        }
        self.table_usages = []

    def analyze_code(self, file_path: str, code: str) -> None:
        try:
            tree = javalang.parse.parse(code)
            self._analyze_sql_queries(tree, file_path)
            self._analyze_entity_annotations(tree, file_path)
        except Exception as e:
            print(f"Error analyzing file {file_path}: {str(e)}")

    def _analyze_sql_queries(self, tree, file_path: str) -> None:
        current_class = None
        current_method = None

        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            current_class = node.name
            
            for method in node.methods:
                current_method = method.name
                
                # Look for string literals that might contain SQL
                for _, string_node in method.filter(javalang.tree.String):
                    sql = string_node.value.upper()
                    self._check_sql_for_tables(sql, file_path, current_class, current_method)

    def _analyze_entity_annotations(self, tree, file_path: str) -> None:
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            if self._has_annotation(node.annotations, "Entity"):
                # Check @Table annotation
                table_name = self._get_table_name_from_annotation(node.annotations)
                if table_name:
                    self._add_table_usage(table_name, file_path, node.name, "Entity Class", "JPA Entity")

    def _check_sql_for_tables(self, sql: str, file_path: str, class_name: str, method_name: str) -> None:
        for system, tables in self.legacy_systems.items():
            for table in tables:
                if table in sql:
                    usage_type = "SELECT" if "SELECT" in sql else "Other"
                    if "JOIN" in sql:
                        usage_type = "JOIN"
                    
                    self._add_table_usage(table, file_path, class_name, method_name, usage_type)

    def _add_table_usage(self, table_name: str, file_path: str, class_name: str, 
                        method_name: str, usage_type: str) -> None:
        system = self._get_system_for_table(table_name)
        if system:
            self.table_usages.append(LegacyTableUsage(
                table_name=table_name,
                system=system,
                file_path=file_path,
                class_name=class_name,
                method_name=method_name,
                usage_type=usage_type
            ))

    def _get_system_for_table(self, table_name: str) -> str:
        for system, tables in self.legacy_systems.items():
            if any(table_name.startswith(table) for table in tables):
                return system
        return None

    def _has_annotation(self, annotations, annotation_name: str) -> bool:
        return any(a.name == annotation_name for a in annotations if hasattr(a, 'name'))

    def _get_table_name_from_annotation(self, annotations) -> str:
        for annotation in annotations:
            if annotation.name == "Table":
                if hasattr(annotation, 'element') and annotation.element:
                    for elem in annotation.element:
                        if elem.name == "name" and elem.value.value:
                            return elem.value.value
        return None

    def get_usage_summary(self) -> Dict[str, List[LegacyTableUsage]]:
        summary = {}
        for usage in self.table_usages:
            if usage.system not in summary:
                summary[usage.system] = []
            summary[usage.system].append(usage)
        return summary
