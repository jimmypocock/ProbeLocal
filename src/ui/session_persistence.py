"""Session state persistence utilities"""
import streamlit as st
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)


class SessionPersistence:
    """Handles session state persistence across reruns"""
    
    def __init__(self):
        self.session_dir = Path("cache/sessions")
        self.session_dir.mkdir(exist_ok=True)
        self.session_file = self.session_dir / "current_session.json"
        
        # Keys to persist
        self.persistent_keys = [
            'current_document_id',
            'selected_model',
            'current_model',
            'document_info',
            'chunk_size',
            'temperature',
            'max_results',
            'use_streaming',
            'use_web_search'
        ]
    
    def save_state(self) -> None:
        """Save current session state to file"""
        try:
            state_to_save = {}
            for key in self.persistent_keys:
                if key in st.session_state:
                    value = st.session_state[key]
                    # Convert non-serializable objects
                    if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                        state_to_save[key] = value
                    else:
                        state_to_save[key] = str(value)
            
            state_to_save['timestamp'] = time.time()
            
            with open(self.session_file, 'w') as f:
                json.dump(state_to_save, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")
    
    def load_state(self) -> Dict[str, Any]:
        """Load session state from file"""
        try:
            if self.session_file.exists():
                with open(self.session_file, 'r') as f:
                    saved_state = json.load(f)
                
                # Check if state is recent (within 1 hour)
                if 'timestamp' in saved_state:
                    age = time.time() - saved_state['timestamp']
                    if age > 3600:  # 1 hour
                        logger.info("Session state too old, ignoring")
                        return {}
                
                return saved_state
        except Exception as e:
            logger.error(f"Failed to load session state: {e}")
        
        return {}
    
    def restore_state(self) -> None:
        """Restore session state from saved file"""
        saved_state = self.load_state()
        
        for key, value in saved_state.items():
            if key != 'timestamp' and key in self.persistent_keys:
                # Only restore if not already set
                if key not in st.session_state:
                    st.session_state[key] = value
    
    def clear_state(self) -> None:
        """Clear saved session state"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
        except Exception as e:
            logger.error(f"Failed to clear session state: {e}")


# Global instance
session_persistence = SessionPersistence()


def save_session_state() -> None:
    """Save current session state"""
    session_persistence.save_state()


def restore_session_state() -> None:
    """Restore session state from file"""
    session_persistence.restore_state()


def clear_session_state() -> None:
    """Clear saved session state"""
    session_persistence.clear_state()


def auto_save_state() -> None:
    """Auto-save state on important changes"""
    # Monitor important state changes
    important_keys = ['current_document_id', 'selected_model', 'document_info']
    
    # Initialize tracking
    if '_last_saved_state' not in st.session_state:
        st.session_state._last_saved_state = {}
    
    # Check for changes
    current_values = {
        key: st.session_state.get(key)
        for key in important_keys
    }
    
    if current_values != st.session_state._last_saved_state:
        save_session_state()
        st.session_state._last_saved_state = current_values.copy()