import streamlit as st
from typing import Any
import base64

def display_code_with_syntax_highlighting(code: str):
    st.code(code, language='java')

def create_download_link(content: str, filename: str) -> str:
    b64 = base64.b64encode(content.encode()).decode()
    return f'<a href="data:text/plain;base64,{b64}" download="{filename}">Download {filename}</a>'

def show_progress_bar(text: str):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(100):
        progress_bar.progress(i + 1)
        status_text.text(f"{text}: {i+1}%")
    
    status_text.text(f"{text}: Complete!")
    progress_bar.empty()

def handle_error(error: Exception):
    st.error(f"Error: {str(error)}")
