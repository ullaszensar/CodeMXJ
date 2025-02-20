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

def clear_session_state():
    """Clear all session state variables"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]

def extract_project(uploaded_file):
    """Extract uploaded zip file to temporary directory"""
    # Create a temporary directory that persists during the session
    if 'temp_dir' not in st.session_state:
        st.session_state.temp_dir = tempfile.mkdtemp()

    temp_dir = st.session_state.temp_dir

    # Clear previous contents
    for root, dirs, files in os.walk(temp_dir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

    # Extract new files
    with ZipFile(uploaded_file, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    st.session_state.project_files = [f for f in os.listdir(temp_dir) if f.endswith('.java')]
    return temp_dir

def main():
    st.title("Java Project Analyzer")

    # Create tabs in the sidebar
    project_tab, structure_tab, diagrams_tab, db_tab = st.sidebar.tabs([
        "Project", "Structure", "Diagrams", "Database"
    ])

    # Add refresh button at the top of the sidebar
    if st.sidebar.button("🔄 Refresh App"):
        clear_session_state()
        st.rerun()

    # Project upload - always visible in the project tab
    with project_tab:
        uploaded_file = st.file_uploader("Upload Java Project (ZIP file)", type=["zip"])

    if uploaded_file is not None:
        try:
            # Extract and analyze project
            project_path = extract_project(uploaded_file)

            # Debug information
            st.sidebar.write("Debug Info:")
            st.sidebar.write(f"Project path: {project_path}")
            st.sidebar.write(f"Java files found: {st.session_state.get('project_files', [])}")

            analyzer = ProjectAnalyzer()

            # Show progress while analyzing
            with st.spinner('Analyzing project structure...'):
                java_files = analyzer.analyze_project(project_path)
                if not java_files:
                    st.warning(f"No Java files found in {project_path}")
                    return

                project_structure = analyzer.get_project_structure(java_files)

            # Project Overview Tab
            with project_tab:
                display_project_structure(project_structure)

            # Structure Analysis Tab
            with structure_tab:
                display_code_structure(project_structure)

            # Diagrams Tab
            with diagrams_tab:
                diagram_type = st.radio(
                    "Select Diagram Type",
                    ["UML Class Diagram", "Sequence Diagram", "Call Graph"]
                )

                if diagram_type == "UML Class Diagram":
                    generate_project_uml(java_files)
                elif diagram_type == "Sequence Diagram":
                    generate_sequence_diagram(project_path)
                elif diagram_type == "Call Graph":
                    generate_call_graph(project_path)

            # Database Tab
            with db_tab:
                analyze_database_schema()

        except Exception as e:
            handle_error(e)
            st.error(f"Error details: {str(e)}")
    else:
        st.info("Please upload a Java project (ZIP file) to begin analysis")

def display_project_structure(project_structure):
    st.subheader("Project Structure")

    if not project_structure:
        st.warning("No Java files found in the project")
        return

    total_files = sum(len(files) for files in project_structure.values())
    total_packages = len(project_structure)
    st.markdown(f"**Project Summary:**")
    st.markdown(f"- Total Packages: {total_packages}")
    st.markdown(f"- Total Java Files: {total_files}")

    for package, files in project_structure.items():
        with st.expander(f"Package: {package}", expanded=True):
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

    if not project_structure:
        st.warning("No Java files found in the project")
        return

    selected_package = st.selectbox(
        "Select Package",
        options=list(project_structure.keys())
    )

    if selected_package:
        files = project_structure[selected_package]
        for file in files:
            with st.expander(f"File: {file['path']}", expanded=True):
                for class_info in file['classes']:
                    st.markdown(f"### Class: {class_info['name']}")
                    display_class_details(class_info)

def generate_project_uml(java_files):
    st.subheader("Project UML Class Diagram")

    if not java_files:
        st.warning("No Java files found to generate UML diagram")
        return

    with st.spinner('Generating UML diagram...'):
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

def generate_sequence_diagram(project_path):
    st.subheader("Sequence Diagram Generator")

    generator = SequenceDiagramGenerator()

    method_name = st.text_input("Enter method name to analyze:")
    if method_name:
        with st.spinner('Generating sequence diagram...'):
            sequence_diagram = generator.analyze_method_calls(project_path, method_name)
            st.text_area("PlantUML Sequence Diagram", sequence_diagram, height=300)
            st.markdown(create_download_link(sequence_diagram, "sequence_diagram.puml"), unsafe_allow_html=True)

def generate_call_graph(project_path):
    st.subheader("Function Call Graph")

    with st.spinner('Generating call graph...'):
        analyzer = CallGraphAnalyzer()
        graph = analyzer.analyze_calls(project_path)
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

    with st.spinner('Analyzing database schema...'):
        analyzer = DatabaseAnalyzer()

        try:
            analyzer.connect_to_db()
            schema_info = analyzer.analyze_schema()

            if not schema_info:
                st.warning("No database schema found")
                return

            for table_name, table_info in schema_info.items():
                with st.expander(f"Table: {table_name}", expanded=True):
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