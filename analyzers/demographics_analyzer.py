import javalang
from typing import Dict, List, Set
from dataclasses import dataclass

@dataclass
class DemographicUsage:
    field_name: str
    category: str
    file_path: str
    class_name: str
    method_name: str
    usage_type: str  # e.g., "Field", "Method", "Parameter"

class DemographicsAnalyzer:
    def __init__(self):
        # Define demographic fields to search for
        self.demographic_fields = {
            "Personal": [
                "customerId", "embossedName", "companyEmbossedName", "gender",
                "dateOfBirth", "dob", "nationality", "maritalStatus", "annualIncome",
                "assets", "employer", "memberSinceDate"
            ],
            "Government IDs": [
                "govId", "governmentId", "ssn", "passport", "drivingLicense"
            ],
            "Business": [
                "businessDbaName", "businessLegalName", "nonProfitIndicator"
            ],
            "Address": [
                "address", "homeAddress", "businessAddress", "alternateAddress",
                "temporaryAddress", "otherAddress", "additionalAddress"
            ],
            "Phone": [
                "phone", "homePhone", "businessPhone", "mobilePhone",
                "alternatePhone", "faxNumber", "attorneyPhone"
            ],
            "Email": [
                "email", "servicingEmail", "eStatementEmail", "businessEmail"
            ],
            "Preferences": [
                "preferenceLanguageCode", "languagePreference", "preferredLanguage"
            ]
        }
        self.usages = []

    def analyze_code(self, file_path: str, code: str) -> None:
        try:
            tree = javalang.parse.parse(code)
            self._analyze_class_fields(tree, file_path)
            self._analyze_method_parameters(tree, file_path)
            self._analyze_variable_declarations(tree, file_path)
        except Exception as e:
            print(f"Error analyzing file {file_path}: {str(e)}")

    def _analyze_class_fields(self, tree, file_path: str) -> None:
        current_class = None

        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            current_class = node.name
            
            for field in node.fields:
                field_name = field.declarators[0].name
                self._check_demographic_field(field_name, file_path, current_class, "N/A", "Field")

    def _analyze_method_parameters(self, tree, file_path: str) -> None:
        for path, node in tree.filter(javalang.tree.MethodDeclaration):
            current_class = self._get_parent_class(path)
            
            for param in node.parameters:
                self._check_demographic_field(param.name, file_path, current_class, node.name, "Parameter")

    def _analyze_variable_declarations(self, tree, file_path: str) -> None:
        for path, node in tree.filter(javalang.tree.LocalVariableDeclaration):
            current_class = self._get_parent_class(path)
            current_method = self._get_parent_method(path)
            
            for declarator in node.declarators:
                self._check_demographic_field(declarator.name, file_path, current_class, current_method, "Variable")

    def _check_demographic_field(self, field_name: str, file_path: str, class_name: str, 
                               method_name: str, usage_type: str) -> None:
        for category, fields in self.demographic_fields.items():
            for field in fields:
                if field.lower() in field_name.lower():
                    self.usages.append(DemographicUsage(
                        field_name=field_name,
                        category=category,
                        file_path=file_path,
                        class_name=class_name,
                        method_name=method_name,
                        usage_type=usage_type
                    ))

    def _get_parent_class(self, path) -> str:
        for node in reversed(path):
            if isinstance(node, javalang.tree.ClassDeclaration):
                return node.name
        return "Unknown"

    def _get_parent_method(self, path) -> str:
        for node in reversed(path):
            if isinstance(node, javalang.tree.MethodDeclaration):
                return node.name
        return "Unknown"

    def get_usage_summary(self) -> Dict[str, List[DemographicUsage]]:
        summary = {}
        for usage in self.usages:
            if usage.category not in summary:
                summary[usage.category] = []
            summary[usage.category].append(usage)
        return summary
