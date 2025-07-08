"""Drag and drop file upload component"""
import streamlit as st
import streamlit.components.v1 as components
from typing import Optional, List
import base64
import json


def render_drag_drop_upload() -> Optional[List[bytes]]:
    """Render a drag-and-drop file upload area with custom styling"""
    
    # JavaScript for drag-drop functionality
    drag_drop_js = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const dropArea = document.querySelector('.drag-drop-area');
        if (!dropArea) return;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight(e) {
            dropArea.classList.add('dragging');
        }
        
        function unhighlight(e) {
            dropArea.classList.remove('dragging');
        }
        
        dropArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        }
        
        function handleFiles(files) {
            // Trigger file input programmatically
            const fileInput = document.querySelector('input[type="file"]');
            if (fileInput) {
                // Create a new FileList (workaround)
                const dataTransfer = new DataTransfer();
                Array.from(files).forEach(file => dataTransfer.items.add(file));
                fileInput.files = dataTransfer.files;
                
                // Trigger change event
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        }
    });
    </script>
    """
    
    # Render the drag-drop area
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("""
        <div class="drag-drop-area" onclick="document.querySelector('input[type=file]').click()">
            <div class="drop-icon">📁</div>
            <h3>Drag & Drop your files here</h3>
            <p>or click to browse</p>
            <p class="file-types">
                Supported: PDF, TXT, CSV, MD, DOCX, XLSX, PNG, JPG
            </p>
            <div class="upload-progress"></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Hidden file uploader
        uploaded_files = st.file_uploader(
            "Upload files",
            accept_multiple_files=True,
            type=['pdf', 'txt', 'csv', 'md', 'docx', 'xlsx', 'png', 'jpg', 'jpeg'],
            label_visibility="collapsed",
            key="drag_drop_uploader"
        )
    
    # Add the JavaScript
    components.html(drag_drop_js, height=0)
    
    return uploaded_files


def render_upload_progress(filename: str, progress: float) -> None:
    """Render upload progress bar"""
    progress_int = int(progress * 100)
    
    st.markdown(f"""
    <div class="upload-progress-container">
        <div class="progress-header">
            <div class="filename">
                <span>📄</span>
                <span>{filename}</span>
            </div>
            <div class="percentage">{progress_int}%</div>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" data-progress="{progress_int}"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)