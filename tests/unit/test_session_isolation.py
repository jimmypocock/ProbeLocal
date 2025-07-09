#!/usr/bin/env python3
"""Test session isolation functionality"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import hashlib
import uuid
from pathlib import Path
from src.ui.session_manager import IsolatedSessionManager, session_manager
try:
    import streamlit as st
except ImportError:
    # Create a mock Streamlit module for testing
    class MockStreamlit:
        class session_state:
            data = {}
            
            @classmethod
            def __getitem__(cls, key):
                return cls.data[key]
            
            @classmethod
            def __setitem__(cls, key, value):
                cls.data[key] = value
            
            @classmethod
            def __contains__(cls, key):
                return key in cls.data
            
            @classmethod
            def get(cls, key, default=None):
                return cls.data.get(key, default)
            
            @classmethod
            def clear(cls):
                cls.data.clear()
    
    st = MockStreamlit()

def test_session_isolation():
    """Test that different sessions are isolated"""
    print("Testing session isolation...")
    
    # Initialize manager
    manager = IsolatedSessionManager()
    
    # Simulate two different sessions
    session1_id = hashlib.sha256(f"{time.time()}-session1".encode()).hexdigest()[:16]
    session2_id = hashlib.sha256(f"{time.time()}-session2".encode()).hexdigest()[:16]
    
    print(f"Session 1 ID: {session1_id}")
    print(f"Session 2 ID: {session2_id}")
    
    # Save data for session 1
    session1_file = manager.session_dir / f"session_{session1_id}.json"
    session1_data = {
        'session_id': session1_id,
        'timestamp': time.time(),
        'data': {
            'current_document_id': 'doc123',
            'messages': [{'role': 'user', 'content': 'Hello from session 1'}],
            'selected_model': 'mistral'
        }
    }
    with open(session1_file, 'w') as f:
        json.dump(session1_data, f)
    
    # Save data for session 2
    session2_file = manager.session_dir / f"session_{session2_id}.json"
    session2_data = {
        'session_id': session2_id,
        'timestamp': time.time(),
        'data': {
            'current_document_id': 'doc456',
            'messages': [{'role': 'user', 'content': 'Hello from session 2'}],
            'selected_model': 'llama2'
        }
    }
    with open(session2_file, 'w') as f:
        json.dump(session2_data, f)
    
    # Test loading session 1
    print("\nLoading session 1 data...")
    with open(session1_file, 'r') as f:
        loaded_session1 = json.load(f)
    
    assert loaded_session1['data']['current_document_id'] == 'doc123'
    assert loaded_session1['data']['messages'][0]['content'] == 'Hello from session 1'
    assert loaded_session1['data']['selected_model'] == 'mistral'
    print("✅ Session 1 data loaded correctly")
    
    # Test loading session 2
    print("\nLoading session 2 data...")
    with open(session2_file, 'r') as f:
        loaded_session2 = json.load(f)
    
    assert loaded_session2['data']['current_document_id'] == 'doc456'
    assert loaded_session2['data']['messages'][0]['content'] == 'Hello from session 2'
    assert loaded_session2['data']['selected_model'] == 'llama2'
    print("✅ Session 2 data loaded correctly")
    
    # Test cleanup of old sessions
    print("\nTesting cleanup of expired sessions...")
    
    # Create an old session file
    old_session_id = hashlib.sha256(f"{time.time()}-old".encode()).hexdigest()[:16]
    old_session_file = manager.session_dir / f"session_{old_session_id}.json"
    old_session_data = {
        'session_id': old_session_id,
        'timestamp': time.time() - 7200,  # 2 hours old
        'data': {'current_document_id': 'old_doc'}
    }
    with open(old_session_file, 'w') as f:
        json.dump(old_session_data, f)
    
    # Modify file time to be old
    os.utime(old_session_file, (time.time() - 7200, time.time() - 7200))
    
    # Force cleanup
    manager._last_cleanup = 0
    manager._cleanup_old_sessions()
    
    # Check that old file was deleted
    assert not old_session_file.exists()
    print("✅ Old sessions cleaned up correctly")
    
    # Count active sessions
    active_count = manager.get_active_sessions()
    print(f"\nActive sessions: {active_count}")
    assert active_count >= 2  # At least our two test sessions
    
    # Clean up test files
    if session1_file.exists():
        session1_file.unlink()
    if session2_file.exists():
        session2_file.unlink()
    
    print("\n✅ All session isolation tests passed!")

import pytest

def test_session_persistence():
    """Test session state persistence and restoration"""
    print("\nTesting session persistence...")
    
    # Clear any existing session state
    if hasattr(st.session_state, 'clear'):
        st.session_state.clear()
    elif hasattr(st.session_state, 'data'):
        st.session_state.data.clear()
    
    try:
        # Create a test session ID
        st.session_state['session_id'] = 'test_session_123'
        
        # Set some test data
        st.session_state['current_document_id'] = 'test_doc'
        st.session_state['messages'] = [
            {'role': 'user', 'content': 'Test message'},
            {'role': 'assistant', 'content': 'Test response'}
        ]
        st.session_state['selected_model'] = 'test_model'
        st.session_state['temperature'] = 0.5
        
        # Save state
        session_manager.save_state()
        
        # Clear session state
        if hasattr(st.session_state, 'clear'):
            st.session_state.clear()
        elif hasattr(st.session_state, 'data'):
            st.session_state.data.clear()
        st.session_state['session_id'] = 'test_session_123'
        
        # Load state
        loaded = session_manager.load_state()
        
        assert loaded == True
        assert st.session_state['current_document_id'] == 'test_doc'
        assert len(st.session_state['messages']) == 2
        assert st.session_state['selected_model'] == 'test_model'
        assert st.session_state['temperature'] == 0.5
        
        print("✅ Session persistence working correctly")
        
        # Clean up
        session_file = session_manager.get_session_file('test_session_123')
        if session_file.exists():
            session_file.unlink()
        
    finally:
        # Clean up session state
        if hasattr(st.session_state, 'clear'):
            st.session_state.clear()
        elif hasattr(st.session_state, 'data'):
            st.session_state.data.clear()

if __name__ == "__main__":
    test_session_isolation()
    test_session_persistence()
    print("\n✅ All tests passed!")