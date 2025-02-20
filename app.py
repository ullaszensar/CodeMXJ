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
    try:
        with ZipFile(uploaded_file, 'r') as zip_ref:
            for file_info in zip_ref.filelist:
                # Skip directories
                if file_info.filename.endswith('/'):
                    continue
                # Only extract .java files
                if file_info.filename.endswith('.java'):
                    zip_ref.extract(file_info, temp_dir)

        st.session_state.project_files = [
            f for f in os.listdir(temp_dir) 
            if f.endswith('.java') and os.path.isfile(os.path.join(temp_dir, f))
        ]
        return temp_dir
    except Exception as e:
        st.error(f"Error extracting project: {str(e)}")
        return None

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
        # Update file uploader to handle Java files
        uploaded_file = st.file_uploader(
            "Upload Java Project (ZIP file containing .java files)",
            type=["zip"],
            help="Upload a ZIP file containing Java source files (.java)"
        )

        # Add credits at the bottom of sidebar
        st.markdown("---")
        st.markdown("""
        <div style='width: 100%;'>
            <table style='width: 100%; border-collapse: collapse; background-color: #28a745; color: white; border-radius: 5px;'>
                <tr>
                    <th colspan='2' style='padding: 10px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.2);'>
                        Design & Development
                    </th>
                </tr>
                <tr>
                    <td style='padding: 10px; text-align: center;'>Sr Solution Architect</td>
                    <td style='padding: 10px; text-align: center;'>Ullas Krishnan</td>
                </tr>
                <tr>
                    <td colspan='2' style='padding: 10px; text-align: center;'>
                        Zensar Team
                    </td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

        # Create tabs for different analysis views
        structure_tab, diagrams_tab, patterns_tab, demographics_tab, services_tab, api_details_tab, legacy_api_tab, db_tab, analysis_tab = st.tabs([
            "Code Structure", "Diagrams", "Integration Patterns", "Demographics", 
            "Service Graph", "API Details", "Legacy API Analysis", "Database", "Analysis Summary"
        ])

    if uploaded_file is not None:
        try:
            # Extract and analyze project
            project_path = extract_project(uploaded_file)

            # Simplified path info in sidebar
            with st.sidebar:
                st.write("Project Info:")
                st.write("✓ Project loaded successfully")

            # Initialize analyzers
            with st.spinner('Analyzing project structure...'):
                analyzer = ProjectAnalyzer()
                ms_analyzer = MicroserviceAnalyzer()  # Initialize here for all tabs to use
                legacy_analyzer = LegacyTableAnalyzer() # Initialize legacy analyzer here
                demo_analyzer = DemographicsAnalyzer() # Initialize demo analyzer here
                int_analyzer = IntegrationPatternAnalyzer() # Initialize integration analyzer here
                pattern_analyzer = DemographicPatternAnalyzer() # Initialize pattern analyzer here


                java_files = analyzer.analyze_project(project_path)
                if not java_files:
                    st.warning(f"No Java files found in the uploaded project")
                    return

                # Analyze all Java files for microservices and legacy tables
                for file in java_files:
                    file_path = os.path.join(project_path, file.path)
                    service_name = file.path.split('/')[0] if '/' in file.path else 'default'

                    with open(file_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                        ms_analyzer.analyze_code(code, service_name)
                        legacy_analyzer.analyze_code(file_path, code) # Analyze for legacy tables
                        demo_analyzer.analyze_code(file_path, code) # Analyze for demographics
                        int_analyzer.analyze_code(file_path,code) # Analyze for integration patterns
                        pattern_analyzer.analyze_code(file_path, code) # Analyze for design patterns


                project_structure = analyzer.get_project_structure(java_files)

            # Project Structure (only in Code Structure tab)
            with structure_tab:
                # Display Project Overview Tables
                col1, col2 = st.columns([2, 1])
                with col1:
                    display_project_overview_table(project_structure)

                st.divider()

                # Display Project Structure using the new function
                display_project_structure(project_structure)


            # Diagrams Tab
            with diagrams_tab:
                display_diagrams_summary(java_files)
                diagram_type = st.radio(
                    "Select Diagram Type",
                    ["UML Class Diagram"]
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

                elif diagram_type == "Class Dependencies":
                    with st.spinner('Generating class dependency graph...'):
                        analyzer = CallGraphAnalyzer()

                        # Analyze all Java files
                        combined_code = ""
                        for file in java_files:
                            file_path = os.path.join(project_path, file.path)
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    combined_code += f.read() + "\n"
                            except Exception as e:
                                st.error(f"Error reading file {file.path}: {str(e)}")
                                continue

                        try:
                            # Create class dependency graph
                            graph = analyzer.analyze_class_dependencies(combined_code)

                            # Display Class Relationships Tables
                            st.subheader("Class Relationships Analysis")

                            # Split relationships by type
                            inheritance_data = []
                            implementation_data = []
                            association_data = []
                            composition_data = []

                            for source, target, data in graph.edges(data=True):
                                relationship_type = data.get('type', 'Association')
                                relationship_info = {
                                    'Source Class': source,
                                    'Target Class': target,
                                    'Details': data.get('details', '')
                                }

                                if relationship_type == 'Inheritance':
                                    inheritance_data.append(relationship_info)
                                elif relationship_type == 'Implementation':
                                    implementation_data.append(relationship_info)
                                elif relationship_type == 'Composition':
                                    composition_data.append(relationship_info)
                                else:
                                    association_data.append(relationship_info)

                            # Display Inheritance Relationships
                            if inheritance_data:
                                st.markdown("### 🔵 Inheritance Relationships")
                                st.markdown("Shows parent-child relationships between classes")
                                df_inheritance = pd.DataFrame(inheritance_data)
                                st.dataframe(
                                    df_inheritance,
                                    column_config={
                                        'Source Class': st.column_config.TextColumn('Child Class'),
                                        'Target Class': st.column_config.TextColumn('Parent Class'),
                                        'Details': st.column_config.TextColumn('Description')
                                    },
                                    use_container_width=True,
                                    hide_index=True
                                )

                            # Display Interface Implementations
                            if implementation_data:
                                st.markdown("### 🟢 Interface Implementations")
                                st.markdown("Shows which classes implement which interfaces")
                                df_implementation = pd.DataFrame(implementation_data)
                                st.dataframe(
                                    df_implementation,
                                    column_config={
                                        'Source Class': st.column_config.TextColumn('Implementing Class'),
                                        'Target Class': st.column_config.TextColumn('Interface'),
                                        'Details': st.column_config.TextColumn('Description')
                                    },
                                    use_container_width=True,
                                    hide_index=True
                                )

                            # Display Composition Relationships
                            if composition_data:
                                st.markdown("### 🔴 Composition Relationships")
                                st.markdown("Shows strong 'has-a' relationships where one class contains another")
                                df_composition = pd.DataFrame(composition_data)
                                st.dataframe(
                                    df_composition,
                                    column_config={
                                        'Source Class': st.column_config.TextColumn('Container Class'),
                                        'Target Class': st.column_config.TextColumn('Contained Class'),
                                        'Details': st.column_config.TextColumn('Description')
                                    },
                                    use_container_width=True,
                                    hide_index=True
                                )

                            # Display Association Relationships
                            if association_data:
                                st.markdown("### ⚫ Association Relationships")
                                st.markdown("Shows loose coupling between classes (uses, depends on)")
                                df_association = pd.DataFrame(association_data)
                                st.dataframe(
                                    df_association,
                                    column_config={
                                        'Source Class': st.column_config.TextColumn('Using Class'),
                                        'Target Class': st.column_config.TextColumn('Used Class'),
                                        'Details': st.column_config.TextColumn('Description')
                                    },
                                    use_container_width=True,
                                    hide_index=True
                                )

                            # Add relationship type explanations
                            with st.expander("ℹ️ Understanding Class Relationships"):
                                st.markdown("""
                                ### Types of Class Relationships

                                #### 🔵 Inheritance
                                - Represents "is-a" relationships
                                - Child class inherits properties and methods from parent class
                                - Example: `Car extends Vehicle`

                                #### 🟢 Implementation
                                - Shows which classes implement interfaces
                                - Class must provide implementations for interface methods
                                - Example: `Car implements Driveable`

                                #### 🔴 Composition
                                - Represents strong "has-a" relationships
                                - Contained class lifecycle depends on container class
                                - Example: `Car has Engine` (Engine cannot exist without Car)

                                #### ⚫ Association
                                - Represents loose "uses" relationships
                                - Classes are independent but work together
                                - Example: `Driver uses Car` (both can exist independently)
                                """)

                            # Create visualization
                            st.subheader("Class Dependency Visualization")
                            fig, ax = plt.subplots(figsize=(12, 8))
                            pos = nx.spring_layout(graph, k=1, iterations=50)

                            # Draw nodes (classes)
                            nx.draw_networkx_nodes(graph, pos,
                                node_color='lightblue',
                                node_size=3000,
                                alpha=0.7
                            )

                            # Draw edges (dependencies) with different colors based on relationship type
                            edge_colors = {
                                'Inheritance': 'blue',
                                'Implementation': 'green',
                                'Association': 'gray',
                                'Composition': 'red'
                            }

                            for edge in graph.edges(data=True):
                                edge_type = edge[2].get('type', 'Association')
                                nx.draw_networkx_edges(graph, pos,
                                    edgelist=[(edge[0], edge[1])],
                                    edge_color=edge_colors.get(edge_type, 'gray'),
                                    arrows=True,
                                    arrowsize=20
                                )

                            # Add labels
                            nx.draw_networkx_labels(graph, pos,
                                font_size=8,
                                font_weight='bold'
                            )

                            # Add title
                            plt.title("Class Dependencies", pad=20, fontsize=16)

                            # Save plot to BytesIO
                            buf = BytesIO()
                            plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
                            buf.seek(0)
                            plot_image = buf.getvalue()

                            # Display download button for diagram
                            st.download_button(
                                "📥 Download Class Dependency Graph",
                                plot_image,
                                "class_dependencies.png",
                                "image/png",
                                help="Download the class dependency graph as a PNG image"
                            )

                            # Display graph
                            st.image(plot_image, caption="Class Dependency Graph", use_container_width=True)

                            # Display legend
                            st.markdown("""
                            **Legend:**
                            - 🔵 Blue edges: Inheritance relationships
                            - 🟢 Green edges: Interface implementations
                            - ⚫ Gray edges: Associations/Dependencies
                            - 🔴 Red edges: Composition relationships
                            """)

                            # Display statistics
                            st.subheader("Dependency Statistics")
                            stats = analyzer.get_dependency_statistics(graph)

                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Total Classes", stats['total_classes'])
                            with col2:
                                st.metric("Total Dependencies", stats['total_dependencies'])
                            with col3:
                                st.metric("Avg Dependencies per Class", f"{stats['avg_dependencies']:.2f}")
                            with col4:
                                st.metric("Inheritance Depth", stats.get('max_inheritance_depth', 0))

                        except Exception as e:
                            st.error(f"Error generating class dependency graph: {str(e)}")
                            st.info("Please make sure the Java files contain valid code and class definitions.")

            # Legacy Tables Tab
            with legacy_api_tab:
                st.subheader("Legacy API & Table Analysis")

                # Add tabs within the Legacy API tab
                legacy_overview, table_list = st.tabs(["API Overview", "Legacy Tables"])

                with legacy_overview:
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

                with table_list:
                    st.subheader("Legacy Database Tables")
                    try:
                        legacy_tables = legacy_analyzer.get_legacy_tables() # Use legacy_analyzer
                        if legacy_tables:
                            for schema, tables in legacy_tables.items():
                                with st.expander(f"Schema: {schema}", expanded=True):
                                    for table in tables:
                                        st.markdown(f"""
                                        ### {table['name']}
                                        **Description:** {table.get('description', 'No description available')}

                                        **Usage Count:** {table.get('usage_count', 0)} references

                                        **Used By Services:**
                                        {', '.join(table.get('used_by', ['No services']))}
                                        """)
                        else:
                            st.info("No legacy tables found in the analysis")
                    except Exception as e:
                        st.error(f"Error analyzing legacy tables: {str(e)}")

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
                    #demo_analyzer = DemographicsAnalyzer() # already initialized

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

            # New Analysis Summary Tab
            with analysis_tab:
                st.subheader("Code Analysis Summary")

                # Create three columns for different analysis aspects
                patterns_col, demographics_col, integration_col = st.columns(3)

                with patterns_col:
                    st.markdown("### Design Patterns")
                    patterns = pattern_analyzer.get_patterns()
                    if patterns:
                        for pattern in patterns:
                            st.markdown(f"""
                            **{pattern['name']}**
                            - Type: {pattern['type']}
                            - Usage: {pattern['usage_count']} occurrences
                            """)
                    else:
                        st.info("No specific patterns detected")

                with demographics_col:
                    st.markdown("### Demographic Data Usage")
                    demo_patterns = demo_analyzer.get_usage_patterns()
                    if demo_patterns:
                        for category, usages in demo_patterns.items():
                            with st.expander(category):
                                for usage in usages:
                                    st.markdown(f"""
                                    **Field:** {usage['field']}
                                    - Location: {usage['location']}
                                    - Usage Type: {usage['type']}
                                    """)
                    else:
                        st.info("No demographic data patterns found")

                with integration_col:
                    st.markdown("### Integration Patterns")
                    int_patterns = int_analyzer.get_patterns()
                    if int_patterns:
                        for pattern in int_patterns:
                            st.markdown(f"""
                            **{pattern['name']}**
                            - Type: {pattern['type']}
                            - Components: {pattern['components']}
                            """)
                    else:
                        st.info("No integration patterns detected")

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

    # Create data for the table view
    data = []
    for package, files in project_structure.items():
        # Package row
        data.append({
            'Type': 'Package',
            'Name': package,
            'Path': '',
            'Classes': '',
            'Description': f'Package containing {len(files)} files'
        })

        # File rows
        for file in files:
            class_names = [cls['name'] for cls in file['classes']]
            data.append({
                'Type': 'File',
                'Name': os.path.basename(file['path']),
                'Path': file['path'],
                'Classes': ', '.join(class_names),
                'Description': file.get('description', '')
            })

    # Create DataFrame
    df = pd.DataFrame(data)

    # Display as an interactive table
    st.dataframe(
        df,
        column_config={
            'Type': st.column_config.TextColumn(
                'Type',
                help='Package or File'
            ),
            'Name': st.column_config.TextColumn(
                'Name',
                help='Name of the package or file'
            ),
            'Path': st.column_config.TextColumn(
                'Path',
                help='Full path of the file'
            ),
            'Classes': st.column_config.TextColumn(
                'Classes',
                help='Classes defined in the file'
            ),
            'Description': st.column_config.TextColumn(
                'Description',
                help='Additional information'
            )
        },
        use_container_width=True,
        hide_index=True
    )

    # Display tree view without nested expanders
    st.subheader("Detailed Class View")

    # Package selection
    selected_package = st.selectbox(
        "Select Package",
        options=list(project_structure.keys()),
        key="package_selector"
    )

    if selected_package:
        files = project_structure[selected_package]

        # File selection
        file_options = [file['path'] for file in files]
        selected_file = st.selectbox(
            "Select File",
            options=file_options,
            key="file_selector"
        )

        if selected_file:
            # Find the selected file
            file = next((f for f in files if f['path'] == selected_file), None)
            if file:
                # Display classes in the selected file
                st.markdown(f"### Classes in {os.path.basename(selected_file)}")

                for class_info in file['classes']:
                    with st.expander(f"🔷 {class_info['name']}", expanded=True):
                        # Class details
                        if class_info['extends']:
                            st.markdown(f"*Extends:* `{class_info['extends']}`")
                        if class_info['implements']:
                            st.markdown(f"*Implements:* `{', '.join(class_info['implements'])}`")

                        # Fields and Methods
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Fields:**")
                            for field in class_info['fields']:
                                st.markdown(f"- `{field}`")
                        with col2:
                            st.markdown("**Methods:**")
                            for method in class_info['methods']:
                                st.markdown(f"- `{method}`")

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

    method_name = st.text_input("Enter method name toanalyze:")
    if method_name: # Corrected variable name
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

        # Analyze allfiles for SQL queries
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
    col1,col2, col3 = st.columns(3)
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