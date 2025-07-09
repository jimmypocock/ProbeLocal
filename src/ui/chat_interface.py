"""Chat interface UI components"""
import streamlit as st
import requests
import time
from typing import Optional, List, Dict, Any
from .notifications import add_notification
from .streaming_chat import handle_streaming_chat
from .error_display import parse_api_error
from .typing_indicator import render_typing_indicator
from .lazy_loading import VirtualScrollChat
from .retry_button import render_smart_retry, render_retry_button
from .session_manager import save_session


def render_example_questions() -> None:
    """Display example questions for the user"""
    if not st.session_state.messages:
        st.info("💡 **Try these questions:**")
        
        # Different questions for web search vs document mode
        if st.session_state.current_document_id == "web_only":
            example_questions = [
                "What's the latest news in AI?",
                "Explain quantum computing",
                "What are the current trends in technology?",
                "Tell me about climate change solutions"
            ]
        else:
            example_questions = [
                "What is this document about?",
                "Summarize the key points",
                "What are the main findings?",
                "Extract all important dates"
            ]
            
        cols = st.columns(2)
        for i, question in enumerate(example_questions):
            with cols[i % 2]:
                # Make keys unique by including document ID and timestamp
                unique_key = f"example_{st.session_state.current_document_id}_{i}"
                if st.button(f"📝 {question}", key=unique_key, use_container_width=True):
                    # Handle example question without rerun
                    st.session_state.messages.append({"role": "user", "content": question})
                    # Trigger a question submission
                    st.session_state['pending_question'] = question


def display_chat_messages() -> None:
    """Display chat messages with virtual scrolling"""
    # Use virtual scrolling for better performance with many messages
    virtual_scroll = VirtualScrollChat(messages_per_page=20)
    virtual_scroll.render(st.session_state.messages)


def process_question(question: str, document_id: str, model_name: str,
                    max_results: int, temperature: float, use_web_search: bool = False,
                    use_streaming: bool = True, message_placeholder = None) -> Dict[str, Any]:
    """Send question to backend and get response"""
    # Use streaming if enabled
    if use_streaming:
        return handle_streaming_chat(
            prompt=question,
            document_id=document_id,
            model_name=model_name,
            max_results=max_results,
            temperature=temperature,
            use_web_search=use_web_search,
            message_placeholder=message_placeholder
        )
    
    # Non-streaming fallback
    try:
        # Choose endpoint based on web search setting
        if document_id == "web_only" or (use_web_search and not document_id):
            endpoint = "http://localhost:8080/web-search"
        else:
            endpoint = "http://localhost:8080/ask"
        
        response = requests.post(
            endpoint,
            json={
                "question": question,
                "document_id": document_id,
                "max_results": max_results,
                "model_name": model_name,
                "temperature": temperature,
                "use_web_search": use_web_search,
                "stream": False
            },
            timeout=60
        )

        if response.status_code == 200:
            return response.json()
        else:
            # Parse API error for better message
            error_msg = parse_api_error(response.json())
            return {
                "error": True,
                "answer": error_msg
            }
    except requests.exceptions.ConnectionError:
        return {
            "error": True,
            "answer": "🔴 **Cannot Connect to Backend**\n\nPlease ensure the API is running:\n```bash\npython main.py\n```"
        }
    except requests.exceptions.Timeout:
        return {
            "error": True,
            "answer": "⏱️ **Request Timeout**\n\nThe server took too long to respond. Try:\n- Asking a simpler question\n- Reducing context sources in settings"
        }
    except Exception as e:
        return {
            "error": True,
            "answer": f"❌ **Unexpected Error**\n\n{str(e)}"
        }


def handle_pending_question(chat_container) -> None:
    """Process any pending question from example buttons"""
    if 'pending_question' not in st.session_state or not st.session_state.pending_question:
        return

    prompt = st.session_state.pending_question
    st.session_state.pending_question = None

    # Display user message immediately
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get and display response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            start_time = time.time()
            
            # Show typing indicator for streaming mode
            if st.session_state.get('use_streaming', True):
                # Show typing indicator briefly before stream starts
                with message_placeholder.container():
                    render_typing_indicator(f"{st.session_state.current_model} is thinking")
                time.sleep(0.5)  # Brief pause to show indicator
                
                # Process with streaming
                result = process_question(
                    prompt,
                    st.session_state.current_document_id,
                    st.session_state.current_model,
                    st.session_state.max_results,
                    st.session_state.temperature,
                    st.session_state.get('use_web_search', False),
                    st.session_state.get('use_streaming', True),
                    message_placeholder
                )
            else:
                # Non-streaming mode - show spinner
                with st.spinner(f"🤔 {st.session_state.current_model} is thinking..."):
                    result = process_question(
                        prompt,
                        st.session_state.current_document_id,
                        st.session_state.current_model,
                        st.session_state.max_results,
                        st.session_state.temperature,
                        st.session_state.get('use_web_search', False),
                        st.session_state.get('use_streaming', False),
                        message_placeholder
                    )

            response_time = result.get('processing_time', time.time() - start_time)

            if not result.get('error') and result.get('sources'):
                sources_count = len(result['sources'])
                # Show different icons based on source type
                if result.get('used_web_search'):
                    st.caption(f"🌐 Web + 📄 Document sources ({sources_count}) • {response_time:.1f}s")
                elif st.session_state.current_document_id == "web_only":
                    st.caption(f"🌐 Web sources ({sources_count}) • {response_time:.1f}s")
                else:
                    st.caption(f"📄 Document sources ({sources_count}) • {response_time:.1f}s")

            # Add to messages
            st.session_state.messages.append({
                "role": "assistant",
                "content": result['answer']
            })


def handle_chat_input(chat_container, doc_name: str) -> None:
    """Handle chat input and process user questions"""
    prompt = st.chat_input(f"Ask about {doc_name}...")

    if prompt:
        # Add user message to state and display immediately
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Save session after adding user message
        save_session()

        with chat_container:
            # Display the user message
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get and display assistant response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                start_time = time.time()
                
                # Show typing indicator for streaming mode
                if st.session_state.get('use_streaming', True):
                    # Show typing indicator briefly before stream starts
                    with message_placeholder.container():
                        render_typing_indicator(f"{st.session_state.current_model} is thinking")
                    time.sleep(0.5)  # Brief pause to show indicator
                    
                    # Process with streaming
                    result = process_question(
                        prompt,
                        st.session_state.current_document_id,
                        st.session_state.current_model,
                        st.session_state.max_results,
                        st.session_state.temperature,
                        st.session_state.get('use_web_search', False),
                        st.session_state.get('use_streaming', True),
                        message_placeholder
                    )
                else:
                    # Non-streaming mode - show spinner
                    with st.spinner(f"🤔 {st.session_state.current_model} is thinking..."):
                        result = process_question(
                            prompt,
                            st.session_state.current_document_id,
                            st.session_state.current_model,
                            st.session_state.max_results,
                            st.session_state.temperature,
                            st.session_state.get('use_web_search', False),
                            st.session_state.get('use_streaming', False),
                            message_placeholder
                        )

                response_time = result.get('processing_time', time.time() - start_time)

                if result.get('error'):
                    # Show error with retry option
                    error_type = 'timeout' if 'timeout' in result['answer'].lower() else 'connection' if 'connect' in result['answer'].lower() else 'generic'
                    
                    # Display the error message
                    message_placeholder.markdown(result['answer'])
                    
                    # Show retry button
                    retry_result = render_retry_button(
                        operation_key=f"chat_query_{prompt[:20]}",
                        operation=process_question,
                        operation_args={
                            'question': prompt,
                            'document_id': st.session_state.current_document_id,
                            'model_name': st.session_state.current_model,
                            'max_results': st.session_state.max_results,
                            'temperature': st.session_state.temperature,
                            'use_web_search': st.session_state.get('use_web_search', False),
                            'use_streaming': False,  # Disable streaming for retry
                            'message_placeholder': message_placeholder
                        },
                        button_text="🔄 Retry Question"
                    )
                    
                    if retry_result and not retry_result.get('error'):
                        # Update with successful retry result
                        message_placeholder.markdown(retry_result['answer'])
                        result = retry_result
                
                elif result.get('sources'):
                    sources_count = len(result['sources'])
                    # Show different icons based on source type
                    if result.get('used_web_search'):
                        st.caption(f"🌐 Web + 📄 Document sources ({sources_count}) • {response_time:.1f}s")
                    elif st.session_state.current_document_id == "web_only":
                        st.caption(f"🌐 Web sources ({sources_count}) • {response_time:.1f}s")
                    else:
                        st.caption(f"📄 Document sources ({sources_count}) • {response_time:.1f}s")

                # Add to messages
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result['answer']
                })
                # Save session after adding message
                save_session()


def render_welcome_message() -> None:
    """Display welcome message when no document is selected"""
    st.markdown("### 👋 Welcome to Greg!")
    
    # Show web search option
    if st.session_state.get('use_web_search', False):
        st.success("""
        🌐 **Web Search Mode Active!**
        
        You can ask questions and I'll search the web for answers.
        Try asking about current events, general knowledge, or any topic!
        """)
        
        # Allow web-only chat
        st.session_state.current_document_id = "web_only"
        # Don't render example questions here - it's done in app.py
    else:
        st.info("""
        **Getting Started:**
        1. Upload a document on the left
        2. Select an AI model above
        3. Start asking questions!
        
        **💡 Tip:** Enable "🌐 Search Web" above to search the internet without uploading a document!

        **Supported formats:** PDF, TXT, CSV, Markdown, Word, Excel, Images
        """)
        st.session_state.current_document_id = None
