# CodeMXJ - Java Code Analysis Tool

A comprehensive Java project analysis tool that provides deep insights through advanced parsing and visualization techniques. Built with Python and Streamlit, this tool helps developers understand complex Java codebases through interactive visualizations and detailed analysis.

## Features

- **Class Relationship Analysis**
  - Detailed class relationship tables showing inheritance, implementation, and associations
  - Interactive UML diagrams with inheritance and interface mapping
  - Comprehensive class dependency visualization

- **Code Structure Analysis**
  - Project structure visualization
  - Package organization analysis
  - Code complexity metrics

- **Integration Pattern Detection**
  - Microservice interaction analysis
  - API endpoint mapping
  - Service-to-service communication patterns

- **Legacy Code Analysis**
  - Legacy table usage detection
  - API compatibility checking
  - Database interaction analysis

- **Demographics Analysis**
  - Code usage patterns
  - Component distribution analysis
  - Design pattern recognition

## Installation

### Prerequisites
- Python 3.11 or higher
- Java JDK 11 or higher (for analyzing Java source code)

### Local Setup

1. Clone the repository:
```bash
git clone [repository-url]
cd codemxj
```

2. Install required Python packages:
```bash
pip install -r requirements.txt
```

Required packages:
- streamlit
- javalang
- networkx
- matplotlib
- pandas
- plantuml
- plantuml-markdown

### Running the Application

1. Start the Streamlit server:
```bash
streamlit run app.py
```

2. Access the application at `http://localhost:5000`

## Usage

1. Upload your Java project as a ZIP file through the web interface
2. Navigate through different analysis tabs:
   - Code Structure
   - Diagrams
   - Integration Patterns
   - Demographics
   - Service Graph
   - API Details
   - Legacy API Analysis
   - Database
   - Analysis Summary

## Important Note

This tool runs completely locally and does not rely on any third-party online services. All code analysis, parsing, and visualization are performed on your local machine, ensuring data privacy and security.

## Development Team

- Sr Solution Architect: Ullas Krishnan
- Development: Zensar Team

## License

Proprietary - All rights reserved
