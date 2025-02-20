import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import os
import tempfile
from zipfile import ZipFile
from analyzers.code_parser import JavaCodeParser
from analyzers.uml_generator import UMLGenerator
from analyzers.sequence_diagram import SequenceDiagramGenerator
from analyzers.call_graph import CallGraphAnalyzer
from analyzers.db_analyzer import DatabaseAnalyzer
from analyzers.project_analyzer import ProjectAnalyzer
from utils.helpers import display_code_with_syntax_highlighting, create_download_link, show_progress_bar, handle_error

st.set_page_config(
    page_title="Java Project Analyzer",
    page_icon="📊",
    layout="wide"
)

def extract_project(uploaded_file):
    """Extract uploaded zip file to temporary directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        with ZipFile(uploaded_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        return temp_dir

def main():
    st.title("Java Project Analyzer")

    # Create tabs in the sidebar
    project_tab, structure_tab, diagrams_tab, db_tab = st.sidebar.tabs([
        "Project", "Structure", "Diagrams", "Database"
    ])

    # Project upload - always visible in the project tab
    with project_tab:
        uploaded_file = st.file_uploader("Upload Java Project (ZIP file)", type=["zip"])

    if uploaded_file is not None:
        try:
            project_path = extract_project(uploaded_file)
            analyzer = ProjectAnalyzer()

            show_progress_bar("Analyzing project structure")
            java_files = analyzer.analyze_project(project_path)
            project_structure = analyzer.get_project_structure(java_files)

            # Project Overview Tab
            with project_tab:
                if st.button("Show Project Overview"):
                    display_project_structure(project_structure)

            # Structure Analysis Tab
            with structure_tab:
                if st.button("Analyze Code Structure"):
                    display_code_structure(project_structure)

            # Diagrams Tab
            with diagrams_tab:
                diagram_type = st.radio(
                    "Select Diagram Type",
                    ["UML Class Diagram", "Sequence Diagram", "Call Graph"]
                )

                if st.button("Generate Diagram"):
                    if diagram_type == "UML Class Diagram":
                        generate_project_uml(java_files)
                    elif diagram_type == "Sequence Diagram":
                        generate_sequence_diagram(project_path)
                    elif diagram_type == "Call Graph":
                        generate_call_graph(project_path)

            # Database Tab
            with db_tab:
                if st.button("Analyze Database Schema"):
                    analyze_database_schema()

        except Exception as e:
            handle_error(e)

def display_project_structure(project_structure):
    st.subheader("Project Structure")

    for package, files in project_structure.items():
        with st.expander(f"Package: {package}"):
            for file in files:
                st.markdown(f"**File:** {file['path']}")
                st.markdown(f"*{file['description']}*")

                for class_info in file['classes']:
                    st.markdown(f"#### Class: {class_info['name']}")

                    if class_info['extends']:
                        st.markdown(f"*Extends:* {class_info['extends']}")

                    if class_info['implements']:
                        st.markdown(f"*Implements:* {', '.join(class_info['implements'])}")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Fields:**")
                        for field in class_info['fields']:
                            st.markdown(f"- {field}")

                    with col2:
                        st.markdown("**Methods:**")
                        for method in class_info['methods']:
                            st.markdown(f"- {method}")
                st.markdown("---")

def display_code_structure(project_structure):
    st.subheader("Code Structure Analysis")

    selected_package = st.selectbox(
        "Select Package",
        options=list(project_structure.keys())
    )

    if selected_package:
        files = project_structure[selected_package]
        for file in files:
            with st.expander(f"File: {file['path']}"):
                for class_info in file['classes']:
                    st.markdown(f"### Class: {class_info['name']}")
                    display_class_details(class_info)

def generate_project_uml(java_files):
    st.subheader("Project UML Class Diagram")

    uml_generator = UMLGenerator()
    all_classes = []

    for file in java_files:
        for class_info in file.classes:
            java_class = JavaCodeParser.dict_to_class(class_info)
            all_classes.append(java_class)

    uml_code = uml_generator.generate_class_diagram(all_classes)
    st.text_area("PlantUML Code", uml_code, height=300)
    st.markdown(create_download_link(uml_code, "project_class_diagram.puml"), unsafe_allow_html=True)

def display_class_details(class_info):
    if class_info['extends']:
        st.markdown(f"**Extends:** {class_info['extends']}")

    if class_info['implements']:
        st.markdown(f"**Implements:**")
        for interface in class_info['implements']:
            st.markdown(f"- {interface}")

    st.markdown("**Fields:**")
    for field in class_info['fields']:
        st.markdown(f"- {field}")

    st.markdown("**Methods:**")
    for method in class_info['methods']:
        st.markdown(f"- {method}")

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

def generate_sequence_diagram(project_path):
    st.subheader("Sequence Diagram Generator")

    generator = SequenceDiagramGenerator()

    method_name = st.text_input("Enter method name to analyze:")
    if method_name:
        show_progress_bar("Generating sequence diagram")

        sequence_diagram = generator.analyze_method_calls(project_path, method_name) #modified to accept project_path
        st.text_area("PlantUML Sequence Diagram", sequence_diagram, height=300)
        st.markdown(create_download_link(sequence_diagram, "sequence_diagram.puml"), unsafe_allow_html=True)

def generate_call_graph(project_path):
    st.subheader("Function Call Graph")

    analyzer = CallGraphAnalyzer()
    show_progress_bar("Generating call graph")

    graph = analyzer.analyze_calls(project_path) #modified to accept project_path
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