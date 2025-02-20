import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from analyzers.code_parser import JavaCodeParser
from analyzers.uml_generator import UMLGenerator
from analyzers.sequence_diagram import SequenceDiagramGenerator
from analyzers.call_graph import CallGraphAnalyzer
from analyzers.db_analyzer import DatabaseAnalyzer
from utils.helpers import display_code_with_syntax_highlighting, create_download_link, show_progress_bar, handle_error

st.set_page_config(
    page_title="Java Code Analyzer",
    page_icon="📊",
    layout="wide"
)

def main():
    st.title("Java Code Analyzer")
    st.sidebar.title("Navigation")
    
    analysis_type = st.sidebar.selectbox(
        "Select Analysis Type",
        ["Code Structure", "UML Diagram", "Sequence Diagram", "Call Graph", "Database Schema"]
    )
    
    # File upload
    uploaded_file = st.file_uploader("Upload Java File", type=["java"])
    
    if uploaded_file is not None:
        code_content = uploaded_file.getvalue().decode("utf-8")
        
        try:
            if analysis_type == "Code Structure":
                analyze_code_structure(code_content)
            elif analysis_type == "UML Diagram":
                generate_uml_diagram(code_content)
            elif analysis_type == "Sequence Diagram":
                generate_sequence_diagram(code_content)
            elif analysis_type == "Call Graph":
                generate_call_graph(code_content)
            elif analysis_type == "Database Schema":
                analyze_database_schema()
        except Exception as e:
            handle_error(e)

def analyze_code_structure(code_content: str):
    st.subheader("Code Structure Analysis")
    
    parser = JavaCodeParser()
    show_progress_bar("Analyzing code structure")
    
    classes = parser.parse_code(code_content)
    
    for java_class in classes:
        with st.expander(f"Class: {java_class.name}"):
            st.write("**Fields:**")
            for field in java_class.fields:
                st.write(f"- {field}")
            
            st.write("**Methods:**")
            for method in java_class.methods:
                st.write(f"- {method}")
            
            if java_class.extends:
                st.write(f"**Extends:** {java_class.extends}")
            
            if java_class.implements:
                st.write("**Implements:**")
                for interface in java_class.implements:
                    st.write(f"- {interface}")

def generate_uml_diagram(code_content: str):
    st.subheader("UML Class Diagram")
    
    parser = JavaCodeParser()
    uml_generator = UMLGenerator()
    
    show_progress_bar("Generating UML diagram")
    
    classes = parser.parse_code(code_content)
    uml_code = uml_generator.generate_class_diagram(classes)
    
    st.text_area("PlantUML Code", uml_code, height=300)
    st.markdown(create_download_link(uml_code, "class_diagram.puml"), unsafe_allow_html=True)

def generate_sequence_diagram(code_content: str):
    st.subheader("Sequence Diagram Generator")
    
    generator = SequenceDiagramGenerator()
    
    method_name = st.text_input("Enter method name to analyze:")
    if method_name:
        show_progress_bar("Generating sequence diagram")
        
        sequence_diagram = generator.analyze_method_calls(code_content, method_name)
        st.text_area("PlantUML Sequence Diagram", sequence_diagram, height=300)
        st.markdown(create_download_link(sequence_diagram, "sequence_diagram.puml"), unsafe_allow_html=True)

def generate_call_graph(code_content: str):
    st.subheader("Function Call Graph")
    
    analyzer = CallGraphAnalyzer()
    show_progress_bar("Generating call graph")
    
    graph = analyzer.analyze_calls(code_content)
    graph_data = analyzer.get_graph_data()
    
    fig, ax = plt.subplots(figsize=(10, 10))
    nx.draw(
        graph,
        pos=nx.spring_layout(graph),
        with_labels=True,
        node_color='lightblue',
        node_size=2000,
        font_size=8,
        font_weight='bold',
        arrows=True,
        ax=ax
    )
    st.pyplot(fig)

def analyze_database_schema():
    st.subheader("Database Schema Analysis")
    
    analyzer = DatabaseAnalyzer()
    show_progress_bar("Analyzing database schema")
    
    try:
        analyzer.connect_to_db()
        schema_info = analyzer.analyze_schema()
        
        for table_name, table_info in schema_info.items():
            with st.expander(f"Table: {table_name}"):
                st.write("**Columns:**")
                for column in table_info['columns']:
                    st.write(f"- {column['name']} ({column['type']}) {'NULL' if column['nullable'] else 'NOT NULL'}")
                
                st.write("**Foreign Keys:**")
                for fk in table_info['foreign_keys']:
                    st.write(f"- References {fk['referred_table']} ({', '.join(fk['referred_columns'])})")
    except Exception as e:
        handle_error(e)

if __name__ == "__main__":
    main()
