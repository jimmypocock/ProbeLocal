"""Lazy loading and virtual scrolling components"""
import streamlit as st
from typing import List, Dict, Any, Callable
import math


class LazyDocumentList:
    """Lazy loading document list with virtual scrolling"""
    
    def __init__(self, items_per_page: int = 10):
        self.items_per_page = items_per_page
        if 'doc_list_page' not in st.session_state:
            st.session_state.doc_list_page = 0
    
    def render(self, documents: List[Dict[str, Any]], on_select: Callable, on_delete: Callable) -> None:
        """Render document list with pagination"""
        if not documents:
            st.info("📂 No documents uploaded yet")
            return
        
        # Calculate pagination
        total_docs = len(documents)
        total_pages = math.ceil(total_docs / self.items_per_page)
        current_page = st.session_state.doc_list_page
        
        # Ensure current page is valid
        if current_page >= total_pages:
            current_page = total_pages - 1
            st.session_state.doc_list_page = current_page
        
        # Get documents for current page
        start_idx = current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, total_docs)
        page_docs = documents[start_idx:end_idx]
        
        # No header needed since count is in the main sidebar header
        
        # Render documents
        for doc in page_docs:
            self._render_document_item(doc, on_select, on_delete)
        
        # Render pagination controls
        if total_pages > 1:
            self._render_pagination(current_page, total_pages)
    
    def _render_document_item(self, doc: Dict[str, Any], on_select: Callable, on_delete: Callable) -> None:
        """Render a single document item"""
        doc_id = doc['document_id']
        is_selected = doc_id == st.session_state.get('current_document_id')
        
        # Create columns for layout
        col1, col2, col3 = st.columns([1, 4, 1])
        
        with col1:
            # File type icon
            file_ext = doc['filename'].split('.')[-1].lower()
            icon = {
                'pdf': '📕',
                'txt': '📄',
                'csv': '📊',
                'md': '📝',
                'docx': '📘',
                'xlsx': '📈',
                'png': '🖼️',
                'jpg': '🖼️',
                'jpeg': '🖼️'
            }.get(file_ext, '📄')
            st.markdown(f"<div style='font-size: 24px; text-align: center;'>{icon}</div>", 
                       unsafe_allow_html=True)
        
        with col2:
            # Document info with selection
            if is_selected:
                st.markdown(f"""
                <div class="doc-item-selected" style="padding: 10px; border-radius: 10px;">
                    <strong>{doc['filename'][:40]}{'...' if len(doc['filename']) > 40 else ''}</strong><br>
                    <small style="color: #666;">{doc.get('pages', 'N/A')} pages • {doc.get('upload_date', 'N/A')}</small>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Create a clean button with simple key
                button_label = f"{doc['filename'][:40]}{'...' if len(doc['filename']) > 40 else ''}"
                if st.button(
                    button_label,
                    key=f"select_{doc_id}",
                    use_container_width=True,
                    help=f"Click to select {doc['filename']}"
                ):
                    on_select(doc_id)
        
        with col3:
            # Delete button with simple key
            if st.button("🗑️", key=f"lazy_delete_{doc_id}", help="Delete document"):
                on_delete(doc_id)
    
    def _render_pagination(self, current_page: int, total_pages: int) -> None:
        """Render pagination controls"""
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        with col1:
            if st.button("⏮️", disabled=current_page == 0, use_container_width=True):
                st.session_state.doc_list_page = 0
                st.rerun()
        
        with col2:
            if st.button("◀️", disabled=current_page == 0, use_container_width=True):
                st.session_state.doc_list_page = current_page - 1
                st.rerun()
        
        with col3:
            # Page selector
            page_options = [f"Page {i+1}" for i in range(total_pages)]
            selected_page = st.selectbox(
                "Go to page",
                options=range(total_pages),
                format_func=lambda x: page_options[x],
                index=current_page,
                key="page_selector",
                label_visibility="collapsed"
            )
            if selected_page != current_page:
                st.session_state.doc_list_page = selected_page
                st.rerun()
        
        with col4:
            if st.button("▶️", disabled=current_page >= total_pages - 1, use_container_width=True):
                st.session_state.doc_list_page = current_page + 1
                st.rerun()
        
        with col5:
            if st.button("⏭️", disabled=current_page >= total_pages - 1, use_container_width=True):
                st.session_state.doc_list_page = total_pages - 1
                st.rerun()


class VirtualScrollChat:
    """Virtual scrolling for chat messages"""
    
    def __init__(self, messages_per_page: int = 20):
        self.messages_per_page = messages_per_page
        if 'chat_display_count' not in st.session_state:
            st.session_state.chat_display_count = messages_per_page
    
    def render(self, messages: List[Dict[str, str]]) -> None:
        """Render chat messages with virtual scrolling"""
        if not messages:
            return
        
        total_messages = len(messages)
        display_count = min(st.session_state.chat_display_count, total_messages)
        
        # Show recent messages (from the end of the list)
        start_idx = max(0, total_messages - display_count)
        visible_messages = messages[start_idx:]
        
        # Show "load more" button if there are hidden messages
        if start_idx > 0:
            remaining = start_idx
            if st.button(f"📜 Load {min(remaining, self.messages_per_page)} more messages", 
                        use_container_width=True):
                st.session_state.chat_display_count += self.messages_per_page
                st.rerun()
        
        # Render visible messages
        for msg in visible_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        # Auto-scroll to bottom (CSS)
        st.markdown("""
        <script>
        // Auto-scroll to bottom of chat
        const chatContainer = document.querySelector('[data-testid="stVerticalBlock"]');
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        </script>
        """, unsafe_allow_html=True)