from sqlalchemy import create_engine, inspect
from typing import Dict, List
import os

class DatabaseAnalyzer:
    def __init__(self):
        self.engine = None
        self.inspector = None

    def connect_to_db(self):
        try:
            database_url = os.getenv('DATABASE_URL')
            self.engine = create_engine(database_url)
            self.inspector = inspect(self.engine)
        except Exception as e:
            raise Exception(f"Failed to connect to database: {str(e)}")

    def analyze_schema(self) -> Dict[str, List[Dict]]:
        if not self.inspector:
            raise Exception("Database connection not initialized")

        schema_info = {}
        
        try:
            for table_name in self.inspector.get_table_names():
                columns = []
                for column in self.inspector.get_columns(table_name):
                    columns.append({
                        'name': column['name'],
                        'type': str(column['type']),
                        'nullable': column['nullable']
                    })
                
                foreign_keys = []
                for fk in self.inspector.get_foreign_keys(table_name):
                    foreign_keys.append({
                        'referred_table': fk['referred_table'],
                        'referred_columns': fk['referred_columns'],
                        'constrained_columns': fk['constrained_columns']
                    })
                
                schema_info[table_name] = {
                    'columns': columns,
                    'foreign_keys': foreign_keys
                }
                
            return schema_info
        except Exception as e:
            raise Exception(f"Failed to analyze database schema: {str(e)}")
