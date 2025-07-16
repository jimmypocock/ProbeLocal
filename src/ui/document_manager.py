"""Read-only document display components"""
import streamlit as st
import requests
from typing import Optional, List, Dict, Any
from .utils import get_document_info


def render_document_status() -> None:
    """Display total documents and chunks in context"""
    try:
        response = requests.get("http://localhost:8080/documents", timeout=5)
        if response.status_code == 200:
            docs = response.json().get('documents', [])
            if docs:
                total_chunks = sum(doc.get('chunks', 0) for doc in docs)
                total_pages = sum(doc.get('pages', 0) for doc in docs)
                st.caption(f"{len(docs)} documents in context • {total_pages} pages • {total_chunks} chunks")
    except:
        pass


def render_document_list() -> None:
    """Display read-only list of documents in context"""
    
    # Fetch documents
    try:
        response = requests.get("http://localhost:8080/documents", timeout=5)
        if response.status_code != 200:
            st.error("❌ Cannot load documents")
            return
            
        docs = response.json().get('documents', [])
        
        if not docs:
            st.info("📂 No documents in context. Add documents to the /documents folder and restart.")
            return
        
        # Sort by filename for consistent display
        docs.sort(key=lambda x: x.get('filename', ''))

        icons = {
            'pdf': '📕', 'txt': '📄', 'csv': '📊', 'md': '📝',
            'docx': '📘', 'xlsx': '📈', 'png': '🖼️', 'jpg': '🖼️', 'jpeg': '🖼️'
        }
        
        # Render each document
        for doc in docs:
            col1, col2 = st.columns([1, 11])
            
            with col1:
                file_ext = doc['filename'].split('.')[-1].lower()
                icon = icons.get(file_ext, '📄')
                st.markdown(icon)
            
            with col2:
                st.markdown(doc['filename'])
                st.caption(f"{doc.get('pages', 'N/A')} pages • {doc.get('chunks', 'N/A')} chunks")
                    
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Cannot load documents: {str(e)}")
    except (KeyError, ValueError) as e:
        st.error(f"❌ Document data error: {str(e)}")