import os
from typing import List, Dict
from dataclasses import dataclass
from .code_parser import JavaCodeParser

@dataclass
class JavaFile:
    path: str
    package: str
    classes: List[Dict]
    description: str

class ProjectAnalyzer:
    def __init__(self):
        self.parser = JavaCodeParser()
        self.test_patterns = [
            'test', 
            'tests', 
            'Test.java',
            'Tests.java',
            '/test/',
            '/tests/'
        ]

    def is_test_file(self, file_path: str) -> bool:
        """Check if the file is a test file based on patterns"""
        return any(pattern.lower() in file_path.lower() for pattern in self.test_patterns)

    def extract_package_name(self, code: str) -> str:
        """Extract package name from Java code"""
        try:
            tree = self.parser.parse_code(code)
            if hasattr(tree, 'package') and tree.package:
                return tree.package.name
            return "default"
        except:
            return "default"

    def analyze_project(self, project_path: str) -> List[JavaFile]:
        """Analyze all Java files in the project"""
        java_files = []
        
        for root, _, files in os.walk(project_path):
            if self.is_test_file(root):
                continue
                
            for file in files:
                if not file.endswith('.java') or self.is_test_file(file):
                    continue
                    
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                        
                    package = self.extract_package_name(code)
                    classes = self.parser.parse_code(code)
                    
                    description = f"File contains {len(classes)} classes"
                    if classes:
                        description += f": {', '.join(c.name for c in classes)}"
                    
                    java_file = JavaFile(
                        path=os.path.relpath(file_path, project_path),
                        package=package,
                        classes=[{
                            'name': c.name,
                            'methods': c.methods,
                            'fields': c.fields,
                            'extends': c.extends,
                            'implements': c.implements
                        } for c in classes],
                        description=description
                    )
                    java_files.append(java_file)
                    
                except Exception as e:
                    print(f"Error analyzing file {file_path}: {str(e)}")
                    
        return java_files

    def get_project_structure(self, java_files: List[JavaFile]) -> Dict:
        """Organize files by package"""
        structure = {}
        
        for file in java_files:
            if file.package not in structure:
                structure[file.package] = []
            structure[file.package].append({
                'path': file.path,
                'description': file.description,
                'classes': file.classes
            })
            
        return structure
