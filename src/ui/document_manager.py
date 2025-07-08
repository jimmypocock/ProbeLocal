"""Document management UI components"""
import streamlit as st
import requests
import time
from typing import Optional, List, Dict, Any
from .utils import get_document_info
from .notifications import add_notification
from .error_display import parse_api_error
from .lazy_loading import LazyDocumentList
from .drag_drop import render_drag_drop_upload, render_upload_progress
from .session_manager import save_session


def render_document_status() -> None:
    """Display current document status"""
    if st.session_state.current_document_id:
        doc_info = get_document_info(st.session_state.current_document_id)
        if doc_info:
            st.success(f"📖 Active: {doc_info['filename'][:25]}...")
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"Chunks: {doc_info.get('chunks', 'N/A')}")
            with col2:
                st.caption(f"Pages: {doc_info.get('pages', 'N/A')}")
    else:
        st.info("📋 No document selected")


def handle_file_upload(uploaded_file, current_model: str, chunk_size: int,
                      temperature: float) -> None:
    """Handle file upload with enhanced progress indication"""
    if st.button("📤 Upload & Process", type="primary", use_container_width=True):
        # Use the new upload progress component
        progress_placeholder = st.empty()
        
        # Simulate smooth progress
        for progress in [0.1, 0.3, 0.5, 0.7]:
            with progress_placeholder.container():
                render_upload_progress(uploaded_file.name, progress)
            time.sleep(0.3)

        # Upload
        files = {"file": (uploaded_file.name, uploaded_file, "application/octet-stream")}
        data = {
            "model": current_model or "mistral",
            "chunk_size": chunk_size,
            "temperature": temperature
        }

        try:
            response = requests.post(
                "http://localhost:8080/upload", files=files, data=data, timeout=300
            )

            # Complete progress
            with progress_placeholder.container():
                render_upload_progress(uploaded_file.name, 0.9)
            time.sleep(0.2)

            if response.status_code == 200:
                result = response.json()
                st.session_state.current_document_id = result['document_id']
                add_notification(f"✅ Uploaded {uploaded_file.name} successfully!", "success")
                
                # Save session state after successful upload
                save_session()
                
                # Final progress
                with progress_placeholder.container():
                    render_upload_progress(uploaded_file.name, 1.0)
                time.sleep(0.5)
                progress_placeholder.empty()
                st.rerun()
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                add_notification(f"❌ Upload failed: {error_detail}", "error")
                progress_placeholder.empty()
        except requests.exceptions.ConnectionError:
            add_notification("🔴 Cannot connect to API. Ensure it's running: `python main.py`", "error")
            progress_placeholder.empty()
        except requests.exceptions.HTTPError as e:
            # Try to parse detailed error from response
            error_msg = "❌ Upload failed"
            if e.response is not None:
                try:
                    error_msg = parse_api_error(e.response.json())
                except:
                    error_msg = f"❌ Upload failed: {e.response.status_code}"
            add_notification(error_msg, "error")
            progress_placeholder.empty()
        except Exception as e:
            add_notification(f"❌ Error: {str(e)}", "error")
            progress_placeholder.empty()


def render_document_list(search_query: str = "") -> None:
    """Render the document list with lazy loading"""
    try:
        response = requests.get("http://localhost:8080/documents", timeout=5)
        if response.status_code == 200:
            all_docs = response.json().get('documents', [])

            # Filter documents
            if search_query:
                docs = [doc for doc in all_docs if search_query.lower() in doc['filename'].lower()]
            else:
                docs = all_docs
            
            # Sort by upload date (newest first)
            docs.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
            
            # Use lazy loading component
            lazy_list = LazyDocumentList(items_per_page=10)
            
            def on_select(doc_id):
                st.session_state.current_document_id = doc_id
                st.session_state.messages = []
                # Find and store document info
                for doc in docs:
                    if doc['document_id'] == doc_id:
                        st.session_state.document_info = doc
                        break
                # Save session state after document selection
                save_session()
                st.rerun()
            
            def on_delete(doc_id):
                # Find document name
                doc_name = "document"
                for doc in docs:
                    if doc['document_id'] == doc_id:
                        doc_name = doc['filename']
                        break
                # Set deletion state and rerun to process
                st.session_state.delete_confirmed = doc_id
                st.session_state.delete_doc_name = doc_name
                st.rerun()
            
            lazy_list.render(docs, on_select, on_delete)
            
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Cannot load documents: {str(e)}")
    except (KeyError, ValueError) as e:
        st.error(f"❌ Document data error: {str(e)}")


def process_pending_deletions() -> bool:
    """Process any pending document deletions. Returns True if deletion was processed."""
    if not st.session_state.get('delete_confirmed'):
        return False

    doc_id = st.session_state.delete_confirmed
    doc_name = st.session_state.get('delete_doc_name', 'document')

    # Perform the deletion
    try:
        response = requests.delete(
            f"http://localhost:8080/documents/{doc_id}",
            timeout=10
        )
        if response.status_code == 200:
            # Clear state if this was the current document
            if st.session_state.current_document_id == doc_id:
                st.session_state.current_document_id = None
                st.session_state.messages = []
                # Save session state after document deletion
                save_session()
            add_notification(f"✅ Deleted {doc_name}", "success")
        else:
            add_notification(f"❌ Failed to delete {doc_name}", "error")
    except Exception as e:
        add_notification(f"❌ Error: {str(e)}", "error")

    # Clear the deletion state
    st.session_state.delete_confirmed = None
    st.session_state.delete_doc_name = None
    return True
