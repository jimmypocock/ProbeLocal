"""Streaming chat functionality for Streamlit"""
import streamlit as st
import requests
import json
from typing import Optional, Generator
import time


def process_streaming_response(url: str, payload: dict) -> Generator[dict, None, None]:
    """Process SSE streaming response from API"""
    try:
        # Add streaming flag
        payload['stream'] = True
        
        # Make streaming request
        with requests.post(url, json=payload, stream=True, timeout=60) as response:
            response.raise_for_status()
            
            # Process server-sent events
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # Skip 'data: ' prefix
                            yield data
                        except json.JSONDecodeError:
                            continue
                            
    except requests.exceptions.RequestException as e:
        yield {'error': str(e), 'done': True}


def handle_streaming_chat(
    prompt: str,
    document_id: str,
    model_name: str,
    max_results: int,
    temperature: float,
    use_web_search: bool = False,
    message_placeholder = None
) -> dict:
    """Handle streaming chat response in Streamlit"""
    
    # Choose endpoint
    if document_id == "web_only" or (use_web_search and not document_id):
        url = "http://localhost:8080/web-search"
    else:
        url = "http://localhost:8080/ask"
    
    # Prepare payload
    payload = {
        "question": prompt,
        "document_id": document_id,
        "max_results": max_results,
        "model_name": model_name,
        "temperature": temperature,
        "use_web_search": use_web_search,
        "stream": True  # Explicitly enable streaming
    }
    
    # Create placeholder if not provided
    if message_placeholder is None:
        message_placeholder = st.empty()
    
    full_response = ""
    sources = []
    processing_time = 0
    used_web_search = False
    
    # Stream the response
    for data in process_streaming_response(url, payload):
        if 'error' in data:
            message_placeholder.error(f"❌ Error: {data['error']}")
            return {'answer': f"Error: {data['error']}", 'error': True}
        
        if 'token' in data:
            # Append token and update display
            full_response += data['token']
            message_placeholder.markdown(full_response + "▌")
        
        if data.get('done', False):
            # Final update with complete response
            message_placeholder.markdown(full_response)
            
            # Extract metadata
            sources = data.get('sources', [])
            processing_time = data.get('processing_time', 0)
            used_web_search = data.get('used_web_search', False)
            break
    
    return {
        'answer': full_response,
        'sources': sources,
        'processing_time': processing_time,
        'used_web_search': used_web_search,
        'error': False
    }