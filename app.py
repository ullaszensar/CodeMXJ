import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import os
import tempfile
import pandas as pd # Added import for pandas
from zipfile import ZipFile
from analyzers.code_parser import JavaCodeParser
from analyzers.uml_generator import UMLGenerator
from analyzers.sequence_diagram import SequenceDiagramGenerator
from analyzers.call_graph import CallGraphAnalyzer
from analyzers.db_analyzer import DatabaseAnalyzer
from analyzers.project_analyzer import ProjectAnalyzer
from utils.helpers import display_code_with_syntax_highlighting, create_download_link, show_progress_bar, handle_error
from analyzers.java_class import JavaClass # Added import statement
import base64
from io import BytesIO
from analyzers.microservice_analyzer import MicroserviceAnalyzer
from analyzers.legacy_table_analyzer import LegacyTableAnalyzer # Add to imports at the top
from analyzers.demographics_analyzer import DemographicsAnalyzer

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

    # Add refresh button at the top
    if st.button("🔄 Refresh App"):
        clear_session_state()
        st.rerun()

    # File uploader in the sidebar
    with st.sidebar:
        st.header("Upload Project")
        uploaded_file = st.file_uploader("Upload Java Project (ZIP file)", type=["zip"])

    # Create tabs for different analysis views
    structure_tab, diagrams_tab, legacy_tab, demographics_tab, integration_tab = st.tabs([
        "Code Structure", "Diagrams", "Legacy Tables", "Demographics", "Integration Patterns"
    ])

    if uploaded_file is not None:
        try:
            # Extract and analyze project
            project_path = extract_project(uploaded_file)

            # Debug information in sidebar
            with st.sidebar:
                st.write("Debug Info:")
                st.write(f"Project path: {project_path}")
                st.write(f"Java files found: {st.session_state.get('project_files', [])}")

            analyzer = ProjectAnalyzer()

            # Show progress while analyzing
            with st.spinner('Analyzing project structure...'):
                java_files = analyzer.analyze_project(project_path)
                if not java_files:
                    st.warning(f"No Java files found in {project_path}")
                    return

                project_structure = analyzer.get_project_structure(java_files)

            # Project Structure (always visible in main content)
            st.header("Project Overview")
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
                    with st.spinner('Generating class diagram...'):
                        uml_generator = UMLGenerator()
                        all_classes = []

                        for file in java_files:
                            for class_info in file.classes:
                                java_class = JavaClass.from_dict(class_info)
                                all_classes.append(java_class)

                        uml_code, uml_image = uml_generator.generate_class_diagram(all_classes)

                        # Display and download options
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                "Download Diagram (PNG)",
                                uml_image,
                                "class_diagram.png",
                                "image/png"
                            )
                        with col2:
                            st.download_button(
                                "Download PlantUML Code",
                                uml_code,
                                "class_diagram.puml",
                                "text/plain"
                            )

                        # Display diagram
                        st.image(uml_image, caption="Class Diagram", use_column_width=True)
                        st.code(uml_code, language="text")

                elif diagram_type == "Sequence Diagram":
                    method_name = st.text_input("Enter method name to analyze:")
                    if method_name:
                        with st.spinner('Generating sequence diagram...'):
                            generator = SequenceDiagramGenerator()

                            # Read all Java files and combine their content
                            combined_code = ""
                            for file in java_files:
                                file_path = os.path.join(project_path, file.path)
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    combined_code += f.read() + "\n"

                            seq_code, seq_image = generator.analyze_method_calls(combined_code, method_name)

                            # Display and download options
                            col1, col2 = st.columns(2)
                            with col1:
                                st.download_button(
                                    "Download Diagram (PNG)",
                                    seq_image,
                                    "sequence_diagram.png",
                                    "image/png"
                                )
                            with col2:
                                st.download_button(
                                    "Download PlantUML Code",
                                    seq_code,
                                    "sequence_diagram.puml",
                                    "text/plain"
                                )

                            # Display diagram
                            st.image(seq_image, caption="Sequence Diagram", use_column_width=True)
                            st.code(seq_code, language="text")

                elif diagram_type == "Call Graph":
                    with st.spinner('Generating call graph...'):
                        analyzer = CallGraphAnalyzer()

                        # Analyze all Java files
                        combined_code = ""
                        for file in java_files:
                            file_path = os.path.join(project_path, file.path)
                            with open(file_path, 'r', encoding='utf-8') as f:
                                combined_code += f.read() + "\n"

                        graph = analyzer.analyze_calls(combined_code)
                        graph_data = analyzer.get_graph_data()

                        # Create matplotlib figure
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

                        # Save plot to BytesIO
                        buf = BytesIO()
                        plt.savefig(buf, format='png', bbox_inches='tight')
                        buf.seek(0)
                        plot_image = buf.getvalue()

                        # Display and download options
                        st.download_button(
                            "Download Call Graph (PNG)",
                            plot_image,
                            "call_graph.png",
                            "image/png"
                        )

                        # Display graph
                        st.image(plot_image, caption="Call Graph", use_column_width=True)

            # Legacy Tables Tab
            with legacy_tab:
                st.subheader("Legacy Table Analysis")

                with st.spinner('Analyzing legacy table usage...'):
                    legacy_analyzer = LegacyTableAnalyzer()

                    # Analyze all Java files
                    for file in java_files:
                        file_path = os.path.join(project_path, file.path)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                code = f.read()
                                legacy_analyzer.analyze_code(file_path, code)
                        except Exception as e:
                            st.error(f"Error analyzing file {file_path}: {str(e)}")

                    usage_summary = legacy_analyzer.get_usage_summary()

                    if not usage_summary:
                        st.info("No legacy table usage found in the codebase")
                    else:
                        # Create a tab for each legacy system
                        legacy_systems = list(usage_summary.keys())
                        system_tabs = st.tabs(legacy_systems)

                        for idx, system in enumerate(legacy_systems):
                            with system_tabs[idx]:
                                st.subheader(f"{system} System Tables")

                                # Create a DataFrame for better visualization
                                data = []
                                for usage in usage_summary[system]:
                                    data.append({
                                        'Table': usage.table_name,
                                        'File': usage.file_path,
                                        'Class': usage.class_name,
                                        'Method': usage.method_name,
                                        'Usage Type': usage.usage_type
                                    })

                                if data:
                                    df = pd.DataFrame(data)
                                    st.dataframe(df, use_container_width=True)

                                    # Add download button for CSV export
                                    csv = df.to_csv(index=False)
                                    st.download_button(
                                        f"Download {system} Usage Data",
                                        csv,
                                        f"{system.lower()}_table_usage.csv",
                                        "text/csv"
                                    )
                                else:
                                    st.info(f"No table usage found for {system}")

            # Demographics Tab
            with demographics_tab:
                st.subheader("Demographics Analysis")

                with st.spinner('Analyzing demographic data usage...'):
                    demo_analyzer = DemographicsAnalyzer()

                    # Analyze all Java files
                    for file in java_files:
                        file_path = os.path.join(project_path, file.path)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                code = f.read()
                                demo_analyzer.analyze_code(file_path, code)
                        except Exception as e:
                            st.error(f"Error analyzing file {file_path}: {str(e)}")

                    usage_summary = demo_analyzer.get_usage_summary()

                    if not usage_summary:
                        st.info("No demographic data usage found in the codebase")
                    else:
                        # Create a tab for each demographic category
                        categories = list(usage_summary.keys())
                        category_tabs = st.tabs(categories)

                        for idx, category in enumerate(categories):
                            with category_tabs[idx]:
                                st.subheader(f"{category} Fields")

                                # Create a DataFrame for better visualization
                                data = []
                                for usage in usage_summary[category]:
                                    data.append({
                                        'Field': usage.field_name,
                                        'File': usage.file_path,
                                        'Class': usage.class_name,
                                        'Method': usage.method_name,
                                        'Usage Type': usage.usage_type
                                    })

                                if data:
                                    df = pd.DataFrame(data)
                                    st.dataframe(df, use_container_width=True)

                                    # Add download button for CSV export
                                    csv = df.to_csv(index=False)
                                    st.download_button(
                                        f"Download {category} Usage Data",
                                        csv,
                                        f"{category.lower()}_demographics.csv",
                                        "text/csv"
                                    )
                                else:
                                    st.info(f"No field usage found for {category}")

            # Integration Patterns Tab
            with integration_tab:
                st.subheader("Integration Patterns Analysis")

                analysis_type = st.radio(
                    "Select Analysis Type",
                    ["API Endpoints", "Service Dependencies", "Service Graph"]
                )

                with st.spinner('Analyzing microservices...'):
                    ms_analyzer = MicroserviceAnalyzer()

                    # Analyze all Java files
                    for file in java_files:
                        file_path = os.path.join(project_path, file.path)
                        # Extract service name from path (assuming standard Spring Boot structure)
                        service_name = file.path.split('/')[0] if '/' in file.path else 'default'

                        with open(file_path, 'r', encoding='utf-8') as f:
                            code = f.read()
                            ms_analyzer.analyze_code(code, service_name)

                    if analysis_type == "API Endpoints":
                        api_summary = ms_analyzer.get_api_summary()
                        for service, endpoints in api_summary.items():
                            with st.expander(f"Service: {service}", expanded=True):
                                for endpoint in endpoints:
                                    st.markdown(f"""
                                    **{endpoint['method']} {endpoint['path']}**  
                                    Handler: `{endpoint['class']}.{endpoint['handler']}`
                                    """)

                    elif analysis_type == "Service Dependencies":
                        for dep in ms_analyzer.service_dependencies:
                            st.markdown(f"""
                            **{dep.source}** → **{dep.target}**  
                            Type: {dep.type}  
                            Details: {dep.details}
                            """)

                    elif analysis_type == "Service Graph":
                        with st.spinner('Generating service graph...'):
                            graph, graph_data = ms_analyzer.generate_service_graph()

                            # Create matplotlib figure
                            fig, ax = plt.subplots(figsize=(12, 8))
                            pos = graph_data['positions']

                            # Draw nodes
                            nx.draw_networkx_nodes(graph, pos, 
                                                     node_color='lightblue',
                                                     node_size=2000)

                            # Draw edges with different colors based on type
                            edge_colors = {'feign': 'blue', 'kafka': 'green', 'rest': 'red'}
                            for u, v, data in graph_data['edges']:
                                edge_type = data.get('type', 'rest')
                                nx.draw_networkx_edges(graph, pos,
                                                         edgelist=[(u, v)],
                                                         edge_color=edge_colors.get(edge_type, 'gray'))

                            # Add labels
                            nx.draw_networkx_labels(graph, pos)

                            # Save and display the graph
                            buf = BytesIO()
                            plt.savefig(buf, format='png', bbox_inches='tight')
                            buf.seek(0)
                            plot_image = buf.getvalue()

                            # Download button
                            st.download_button(
                                "Download Service Graph (PNG)",
                                plot_image,
                                "service_graph.png",
                                "image/png"
                            )

                            # Display graph
                            st.image(plot_image, caption="Service Dependency Graph", use_column_width=True)

                            # Display legend
                            st.markdown("""
                            **Legend:**
                            - Blue edges: Feign Client connections
                            - Green edges: Kafka connections
                            - Red edges: REST template calls
                            """)

            # Database Tab (moved to a function call)
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
                java_class = JavaClass.from_dict(class_info)
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
    st.subheader("Database Analysis")

    analysis_type = st.radio(
        "Select Analysis Type",
        ["Schema Analysis", "Legacy Table Usage"]
    )

    if analysis_type == "Schema Analysis":
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

    elif analysis_type == "Legacy Table Usage":
        with st.spinner('Analyzing legacy table usage...'):
            legacy_analyzer = LegacyTableAnalyzer()

            # Analyze all Java files
            for file in java_files:
                file_path = os.path.join(project_path, file.path)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                        legacy_analyzer.analyze_code(file_path, code)
                except Exception as e:
                    st.error(f"Error analyzing file {file_path}: {str(e)}")

            usage_summary = legacy_analyzer.get_usage_summary()

            if not usage_summary:
                st.info("No legacy table usage found in the codebase")
                return

            # Create a tab for each legacy system
            legacy_systems = list(usage_summary.keys())
            if legacy_systems:
                system_tabs = st.tabs(legacy_systems)

                for idx, system in enumerate(legacy_systems):
                    with system_tabs[idx]:
                        st.subheader(f"{system} System Tables")

                        # Create a DataFrame for better visualization
                        data = []
                        for usage in usage_summary[system]:
                            data.append({
                                'Table': usage.table_name,
                                'File': usage.file_path,
                                'Class': usage.class_name,
                                'Method': usage.method_name,
                                'Usage Type': usage.usage_type
                            })

                        if data:
                            df = pd.DataFrame(data)
                            st.dataframe(df, use_container_width=True)

                            # Add download button for CSV export
                            csv = df.to_csv(index=False)
                            st.download_button(
                                f"Download {system} Usage Data",
                                csv,
                                f"{system.lower()}_table_usage.csv",
                                "text/csv"
                            )
                        else:
                            st.info(f"No table usage found for {system}")


if __name__ == "__main__":
    main()