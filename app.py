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
from analyzers.project_analyzer import ProjectAnalyzer
from utils.helpers import display_code_with_syntax_highlighting, create_download_link, show_progress_bar, handle_error
from analyzers.java_class import JavaClass # Added import statement
import base64
from io import BytesIO
from analyzers.microservice_analyzer import MicroserviceAnalyzer
from analyzers.legacy_table_analyzer import LegacyTableAnalyzer # Add to imports at the top
from analyzers.demographics_analyzer import DemographicsAnalyzer
from analyzers.integration_pattern_analyzer import IntegrationPatternAnalyzer
from analyzers.demographic_pattern_analyzer import DemographicPatternAnalyzer
import re

st.set_page_config(
    page_title="CodeMXJ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
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
    st.title("CodeMXJ")
    st.markdown("<p style='color: #B8860B;'>Advanced Java Code Analysis & Visualization</p>", unsafe_allow_html=True)

    # File uploader in the sidebar
    with st.sidebar:
        st.header("CodeMXJ Controls")

        # Add refresh button at the top of sidebar
        if st.button("🔄 Refresh App"):
            clear_session_state()
            st.rerun()

        st.header("Upload Project")
        uploaded_file = st.file_uploader("Upload Java Project (ZIP file)", type=["zip"])

    # Create tabs for different analysis views
    structure_tab, diagrams_tab, patterns_tab, demographics_tab, services_tab, api_details_tab, legacy_api_tab, db_tab = st.tabs([
        "Code Structure", "Diagrams", "Integration Patterns", "Demographics", 
        "Service Graph", "API Details", "Legacy API Analysis", "Database"
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

            # Initialize analyzers
            with st.spinner('Analyzing project structure...'):
                analyzer = ProjectAnalyzer()
                ms_analyzer = MicroserviceAnalyzer()  # Initialize here for all tabs to use

                java_files = analyzer.analyze_project(project_path)
                if not java_files:
                    st.warning(f"No Java files found in {project_path}")
                    return

                # Analyze all Java files for microservices
                for file in java_files:
                    file_path = os.path.join(project_path, file.path)
                    service_name = file.path.split('/')[0] if '/' in file.path else 'default'

                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                        ms_analyzer.analyze_code(code, service_name)

                project_structure = analyzer.get_project_structure(java_files)

            # Project Structure (only in Code Structure tab)
            with structure_tab:
                # Display Project Overview Tables
                col1, col2 = st.columns([2, 1])
                with col1:
                    display_project_overview_table(project_structure)

                st.divider()

                # Display Project Structure
                st.subheader("Project Structure")
                for package, files in project_structure.items():
                    st.markdown(f"**Package:** {package}")
                    for file in files:
                        st.markdown(f"- {file['path']}")

                st.divider()

                # Display Detailed Code Structure
                st.subheader("Detailed Code Analysis")
                selected_package = st.selectbox(
                    "Select Package",
                    options=list(project_structure.keys())
                )

                if selected_package:
                    files = project_structure[selected_package]
                    for file in files:
                        st.markdown(f"### File: {file['path']}")
                        for class_info in file['classes']:
                            st.markdown(f"#### Class: {class_info['name']}")

                            # Class details
                            if class_info['extends']:
                                st.markdown(f"*Extends:* {class_info['extends']}")
                            if class_info['implements']:
                                st.markdown(f"*Implements:* {', '.join(class_info['implements'])}")

                            # Display fields and methods in columns
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


            # Diagrams Tab
            with diagrams_tab:
                display_diagrams_summary(java_files)
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

                        # Display diagram first for better visibility
                        st.image(uml_image, caption="Class Diagram", use_container_width=True)

                        # Add download options in a cleaner layout
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="📥 Download Diagram (PNG)",
                                data=uml_image,
                                file_name="class_diagram.png",
                                mime="image/png",
                                help="Download the UML diagram as a PNG image"
                            )
                        with col2:
                            st.download_button(
                                label="📄 Download PlantUML Code",
                                data=uml_code,
                                file_name="class_diagram.puml",
                                mime="text/plain",
                                help="Download the PlantUML source code"
                            )

                        # Show PlantUML code in an expandable section
                        with st.expander("View PlantUML Code"):
                            st.code(uml_code, language="text")

                elif diagram_type == "Sequence Diagram":
                    # Get all available methods
                    available_methods = []
                    for file in java_files:
                        file_path = os.path.join(project_path, file.path)
                        for class_info in file.classes:
                            for method in class_info['methods']:
                                # Create a method identifier with class name
                                method_id = f"{class_info['name']}.{method}"
                                available_methods.append(method_id)

                    # Sort methods alphabetically for easier selection
                    available_methods.sort()

                    # Method selection
                    method_name = st.selectbox(
                        "Select method to analyze:",
                        options=available_methods,
                        format_func=lambda x: x  # Display full method name
                    )

                    if method_name:
                        # Extract just the method name from the class.method format
                        actual_method = method_name.split('.')[-1]

                        with st.spinner('Generating sequence diagram...'):
                            generator = SequenceDiagramGenerator()

                            # Read all Java files and combine their content
                            combined_code = ""
                            for file in java_files:
                                file_path = os.path.join(project_path, file.path)
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    combined_code += f.read() + "\n"

                            try:
                                seq_code, seq_image = generator.analyze_method_calls(combined_code, actual_method)

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
                                st.image(seq_image, caption=f"Sequence Diagram for {method_name}", use_container_width=True)
                                with st.expander("View PlantUML Code"):
                                    st.code(seq_code, language="text")
                            except Exception as e:
                                st.error(f"Error generating sequence diagram: {str(e)}")

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
                        st.image(plot_image, caption="Call Graph", use_container_width=True)


            # Legacy Tables Tab
            with legacy_api_tab:
                st.subheader("Legacy API Analysis")

                try:
                    api_details = ms_analyzer.get_api_details()

                    if not api_details:
                        st.info("No API endpoints found using legacy tables")
                    else:
                        for service, endpoints in api_details.items():
                            with st.expander(f"Service: {service}", expanded=True):
                                for endpoint in endpoints:
                                    if endpoint['legacy_tables']:
                                        st.markdown(f"""
                                        ### {endpoint['method']} {endpoint['path']}
                                        **Handler:** `{endpoint['class']}.{endpoint['handler']}`

                                        **Legacy Tables Used:**
                                        {', '.join(endpoint['legacy_tables'])}

                                        **Request Parameters:**
                                        {', '.join(endpoint['request_params']) if endpoint['request_params'] else 'None'}

                                        **Response Fields:**
                                        {', '.join(endpoint['response_fields']) if endpoint['response_fields'] else 'None'}
                                        """)
                                        st.markdown("---")
                except Exception as e:
                    st.error(f"Error analyzing legacy APIs: {str(e)}")

            # Service Graph Tab
            with services_tab:
                st.subheader("Service-to-Service Interaction Analysis")

                with st.spinner('Analyzing microservice interactions...'):
                    #ms_analyzer = MicroserviceAnalyzer() #already initialized

                    # Create visualization options
                    viz_type = st.radio(
                        "Select Visualization",
                        ["Service Dependency Graph", "API Interaction Map", "Service Matrix"]
                    )

                    if viz_type == "Service Dependency Graph":
                        graph, graph_data = ms_analyzer.generate_service_graph()

                        # Create interactive graph visualization
                        fig, ax = plt.subplots(figsize=(12, 8))
                        pos = graph_data['positions']

                        # Draw nodes with different colors for different service types
                        nx.draw_networkx_nodes(graph, pos, 
                                                    node_color='lightblue',
                                                    node_size=2000)

                        # Draw edges with different colors and styles
                        edge_colors = {
                            'feign': 'blue',
                            'rest': 'green',
                            'kafka': 'red',
                            'database': 'purple'
                        }

                        for u, v, data in graph_data['edges']:
                            edge_type = data.get('type', 'rest')
                            nx.draw_networkx_edges(graph, pos,
                                                        edgelist=[(u, v)],
                                                        edge_color=edge_colors.get(edge_type, 'gray'),
                                                        style='dashed' if edge_type == 'kafka' else 'solid')

                        # Add labels
                        nx.draw_networkx_labels(graph, pos)

                        # Save and display the graph
                        buf = BytesIO()
                        plt.savefig(buf, format='png', bbox_inches='tight')
                        buf.seek(0)
                        st.image(buf, caption="Service Dependency Graph", use_container_width=True)

                        # Display legend
                        st.markdown("""
                        **Legend:**
                        - Blue edges: Feign Client connections
                        - Green edges: REST API calls
                        - Red dashed edges: Kafka events
                        - Purple edges: Database interactions
                        """)

            # API Details Tab
            with api_details_tab:
                st.subheader("API Analysis")

                api_type = st.radio(
                    "Select API Type",
                    ["REST APIs", "SOAP Services"]
                )

                if api_type == "REST APIs":
                    with st.spinner('Analyzing REST APIs...'):
                        rest_details = ms_analyzer.get_rest_api_details()

                        if not rest_details:
                            st.info("No REST APIs found in the project")
                        else:
                            for service, apis in rest_details.items():
                                with st.expander(f"Service: {service}", expanded=True):
                                    for api in apis:
                                        st.markdown(f"""
                                        ### {api['method']} {api['path']}
                                        **Handler:** `{api['class']}.{api['handler']}`

                                        **Client Type:** {api['client_type']}  
                                        (RestTemplate/FeignClient/Direct Controller)

                                        **Request Parameters:**
                                        {', '.join(api['request_params']) if api['request_params'] else 'None'}

                                        **Response Type:**
                                        {', '.join(api['response_fields']) if api['response_fields'] else 'None'}

                                        **Called Services:**
                                        {', '.join(api['called_services']) if api['called_services'] else 'None'}
                                        """)
                                        st.markdown("---")

                else:  # SOAP Services
                    with st.spinner('Analyzing SOAP Services...'):
                        soap_details = ms_analyzer.get_soap_service_details()

                        if not soap_details:
                            st.info("No SOAP services found in the project")
                        else:
                            for service, operations in soap_details.items():
                                with st.expander(f"Service: {service}", expanded=True):
                                    for op in operations:
                                        st.markdown(f"""
                                        ### {op['operation_name']}
                                        **Service Interface:** `{op['interface']}`

                                        **WSDL Location:** {op['wsdl_location']}

                                        **Input Parameters:**
                                        {', '.join(op['input_params']) if op['input_params'] else 'None'}

                                        **Output Type:**
                                        {op['output_type']}
                                        """)
                                        st.markdown("---")

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

                    display_demographics_summary(demo_analyzer)
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
            with patterns_tab:
                st.subheader("Integration Patterns Analysis")
                analysis_type = st.radio(
                    "Select Analysis Type",
                    ["API Endpoints", "Service Dependencies", "Service Graph"]
                )
                with st.spinner('Analyzing microservices...'):
                    #ms_analyzer = MicroserviceAnalyzer() #already initialized

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
                            st.image(plot_image, caption="Service Dependency Graph", use_container_width=True)

                            # Display legend
                            st.markdown("""
                            **Legend:**
                            - Blue edges: Feign Client connections
                            - Green edges: Kafka connections
                            - Red edges: REST template calls
                            """)

            # Database Tab (moved to a function call)
            with db_tab:
                analyze_database_schema(java_files, project_path)

        except Exception as e:
            handle_error(e)
            st.error(f"Error details: {str(e)}")
    else:
        st.info("Please upload a Java project (ZIP file) to begin analysis")

def display_project_overview_table(project_structure):
    """Display project overview in a table format"""
    # Calculate overview metrics
    total_files = sum(len(files) for files in project_structure.values())
    total_packages = len(project_structure)
    total_controllers = 0
    controller_list = []

    # Count controllers and collect controller names
    for package, files in project_structure.items():
        for file in files:
            for class_info in file['classes']:
                if any(ann.get('name') == 'RestController' for ann in class_info.get('annotations', [])):
                    total_controllers += 1
                    controller_list.append(f"{package}.{class_info['name']}")

    # Create overview table
    overview_data = {
        'Metric': ['Total Packages', 'Total Java Files', 'Total Controllers'],
        'Count': [total_packages, total_files, total_controllers]
    }

    # Create and display tables
    st.subheader("Project Overview")
    df_overview = pd.DataFrame(overview_data)
    st.dataframe(df_overview, use_container_width=True)

    if controller_list:
        st.subheader("Controllers")
        df_controllers = pd.DataFrame({'Controller': controller_list})
        st.dataframe(df_controllers, use_container_width=True)

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

def analyze_database_schema(java_files, project_path):
    st.subheader("Legacy Database Analysis")

    analysis_type = st.radio(
        "Select Analysis Type",
        ["Legacy Systems Overview", "SQL Query Analysis"]
    )

    # Initialize analyzer
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

    if analysis_type == "Legacy Systems Overview":
        usage_summary = legacy_analyzer.get_usage_summary()

        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Legacy Systems", len(usage_summary))
        with col2:
            total_tables = sum(len(tables) for tables in usage_summary.values())
            st.metric("Total Tables", total_tables)
        with col3:
            total_usages = sum(len(usages) for usages in usage_summary.values())
            st.metric("Total References", total_usages)

        # Create tabs for each legacy system
        if usage_summary:
            systems = list(usage_summary.keys())
            system_tabs = st.tabs(systems)

            for idx, system in enumerate(systems):
                with system_tabs[idx]:
                    st.subheader(f"{system} System Tables")

                    # Create DataFrame for visualization
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

                        # Add download button
                        csv = df.to_csv(index=False)
                        st.download_button(
                            f"Download {system} Usage Data",
                            csv,
                            f"{system.lower()}_table_usage.csv",
                            "text/csv"
                        )
                    else:
                        st.info(f"No table usage found for {system}")
        else:
            st.info("No legacy system usage found in the codebase")

    else:  # SQL Query Analysis
        st.subheader("SQL Query Analysis")

        # Group queries by type
        sql_types = {
            "SELECT": [],
            "INSERT": [],
            "UPDATE": [],
            "DELETE": []
        }

        # Analyze all files for SQL queries
        for file in java_files:
            file_path = os.path.join(project_path, file.path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                    # Extract SQL queries using regex patterns
                    for query_type in sql_types.keys():
                        pattern = rf'{query_type}\s+[^;]+;'
                        matches = re.finditer(pattern, code, re.IGNORECASE)
                        for match in matches:
                            sql_types[query_type].append({
                                'query': match.group(0),
                                'file': file.path
                            })
            except Exception as e:
                st.error(f"Error analyzing SQL in file {file_path}: {str(e)}")

        # Create tabs for different query types
        query_tabs = st.tabs(list(sql_types.keys()))

        for idx, (query_type, queries) in enumerate(sql_types.items()):
            with query_tabs[idx]:
                if queries:
                    for q in queries:
                        with st.expander(f"Query in {q['file']}", expanded=False):
                            st.code(q['query'], language='sql')
                else:
                    st.info(f"No {query_type} queries found")

def display_code_structure_summary(project_structure):
    col1, col2, col3 = st.columns(3)
    with col1:
        total_classes = sum(len(file['classes']) for files in project_structure.values() for file in files)
        st.metric("Total Classes", total_classes)
    with col2:
        total_methods = sum(len(class_info['methods']) for files in project_structure.values() 
                            for file in files for class_info in file['classes'])
        st.metric("Total Methods", total_methods)
    with col3:
        total_fields = sum(len(class_info['fields']) for files in project_structure.values() 
                            for file in files for class_info in file['classes'])
        st.metric("Total Fields", total_fields)

def display_diagrams_summary(java_files):
    col1, col2, col3 =st.columns(3)
    with col1:
        total_relationships = sum(1 for file in java_files for class_info in file.classes 
                               if class_info['extends'] or class_info['implements'])
        st.metric("Class Relationships", total_relationships)
    with col2:
        inheritance_count = sum(1 for file in java_files for class_info in file.classes 
                              if class_info['extends'])
        st.metric("Inheritance Links", inheritance_count)
    with col3:
        interface_count = sum(1 for file in java_files for class_info in file.classes 
                            if class_info['implements'])
        st.metric("Interface Implementations", interface_count)

def display_legacysummary(legacy_analyzer):
    usage_summary = legacy_analyzer.get_usage_summary()
    col1, col2, col3 = st.columns(3)
    with col1:
        total_systems = len(usage_summary)
        st.metric("Legacy Systems",total_systems)
    with col2:
        total_tables = sum(len(tables) for tables in usage_summary.values())
        st.metric("Tables Referenced", total_tables)
    with col3:
        total_usages = sum(len(usage) for usage in usage_summary.values())
        st.metric("Total References", total_usages)

def display_demographics_summary(demo_analyzer):
    usage_summary = demo_analyzer.get_usage_summary()
    col1, col2, col3 = st.columns(3)
    with col1:
        total_categories = len(usage_summary)
        st.metric("Demographic Categories", total_categories)
    with col2:
        total_fields = sum(len(fields) for fields in usage_summary.values())
        st.metric("Fields Tracked", total_fields)
    with col3:
        total_usages = sum(len(usage) for usage in usage_summary.values())
        st.metric("Total References", total_usages)

def display_integration_summary(ms_analyzer):
    """Display integration summary in a table format"""
    api_summary = ms_analyzer.get_api_summary()
    col1, col2, col3 = st.columns(3)

    with col1:
        total_services = len(api_summary)
        st.metric("Microservices", total_services)

    with col2:
        total_endpoints = sum(len(endpoints) for endpoints in api_summary.values())
        st.metric("Total Endpoints", total_endpoints)

    with col3:
        total_controllers = sum(
            len([ep for ep in endpoints if ep['handler']])
            for endpoints in api_summary.values()
        )
        st.metric("Total Controllers", total_controllers)

if __name__ == "__main__":
    main()