"""Improved session state management with user isolation"""
import streamlit as st
import json
import os
import time
import uuid
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
import threading
import logging

logger = logging.getLogger(__name__)


class IsolatedSessionManager:
    """Manages session state with proper user isolation"""
    
    def __init__(self):
        self.session_dir = Path("cache/sessions")
        self.session_dir.mkdir(exist_ok=True)
        
        # Session configuration
        self.session_timeout = 3600  # 1 hour
        self.cleanup_interval = 300  # 5 minutes
        
        # Keys to persist
        self.persistent_keys = {
            'current_document_id',
            'selected_model',
            'current_model',
            'document_info',
            'chunk_size',
            'temperature',
            'max_results',
            'use_streaming',
            'use_web_search',
            'messages',
            'chat_input_key'
        }
        
        # Thread safety
        self._lock = threading.Lock()
        self._last_cleanup = 0
        
    def get_session_id(self) -> str:
        """Get or create a unique session ID for the current user"""
        if 'session_id' not in st.session_state:
            # Generate a unique session ID
            # Use combination of time and random UUID for uniqueness
            session_id = hashlib.sha256(
                f"{time.time()}-{uuid.uuid4()}".encode()
            ).hexdigest()[:16]
            st.session_state.session_id = session_id
            logger.info(f"Created new session ID: {session_id}")
        
        return st.session_state.session_id
    
    def get_session_file(self, session_id: str) -> Path:
        """Get the file path for a specific session"""
        return self.session_dir / f"session_{session_id}.json"
    
    def save_state(self) -> None:
        """Save current session state to user-specific file"""
        session_id = self.get_session_id()
        
        try:
            with self._lock:
                state_to_save = {
                    'session_id': session_id,
                    'timestamp': time.time(),
                    'data': {}
                }
                
                # Save persistent keys
                for key in self.persistent_keys:
                    if key in st.session_state:
                        value = st.session_state[key]
                        # Handle non-serializable objects
                        try:
                            # Test if serializable
                            json.dumps(value)
                            state_to_save['data'][key] = value
                        except (TypeError, ValueError):
                            # Convert to string if not serializable
                            state_to_save['data'][key] = str(value)
                
                # Write to user-specific file
                session_file = self.get_session_file(session_id)
                with open(session_file, 'w') as f:
                    json.dump(state_to_save, f, indent=2)
                
                logger.debug(f"Saved session state for {session_id}")
                
                # Cleanup old sessions if needed
                self._cleanup_old_sessions()
                
        except Exception as e:
            logger.error(f"Error saving session state: {e}")
    
    def load_state(self) -> bool:
        """Load session state from user-specific file"""
        session_id = self.get_session_id()
        session_file = self.get_session_file(session_id)
        
        try:
            if session_file.exists():
                with self._lock:
                    with open(session_file, 'r') as f:
                        saved_state = json.load(f)
                    
                    # Check if session is still valid
                    if time.time() - saved_state['timestamp'] > self.session_timeout:
                        logger.info(f"Session {session_id} expired")
                        session_file.unlink()
                        return False
                    
                    # Restore state
                    for key, value in saved_state['data'].items():
                        if key not in st.session_state:
                            st.session_state[key] = value
                    
                    logger.debug(f"Loaded session state for {session_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Error loading session state: {e}")
        
        return False
    
    def clear_session(self) -> None:
        """Clear the current user's session"""
        session_id = self.get_session_id()
        session_file = self.get_session_file(session_id)
        
        try:
            with self._lock:
                if session_file.exists():
                    session_file.unlink()
                    logger.info(f"Cleared session {session_id}")
                
                # Clear session state
                for key in list(st.session_state.keys()):
                    if key != 'session_id':  # Keep session ID
                        del st.session_state[key]
                        
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
    
    def _cleanup_old_sessions(self) -> None:
        """Remove expired session files"""
        current_time = time.time()
        
        # Only cleanup periodically
        if current_time - self._last_cleanup < self.cleanup_interval:
            return
        
        self._last_cleanup = current_time
        
        try:
            expired_count = 0
            
            for session_file in self.session_dir.glob("session_*.json"):
                try:
                    # Check file age
                    file_age = current_time - session_file.stat().st_mtime
                    if file_age > self.session_timeout:
                        session_file.unlink()
                        expired_count += 1
                except Exception as e:
                    logger.warning(f"Error checking session file {session_file}: {e}")
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
                
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
    
    def get_active_sessions(self) -> int:
        """Get count of active sessions"""
        try:
            current_time = time.time()
            active_count = 0
            
            for session_file in self.session_dir.glob("session_*.json"):
                try:
                    file_age = current_time - session_file.stat().st_mtime
                    if file_age <= self.session_timeout:
                        active_count += 1
                except:
                    continue
                    
            return active_count
            
        except Exception as e:
            logger.error(f"Error counting active sessions: {e}")
            return 0
    
    def migrate_from_old_session(self, old_session_file: Path) -> None:
        """Migrate from old session format to new isolated format"""
        try:
            if old_session_file.exists():
                with open(old_session_file, 'r') as f:
                    old_state = json.load(f)
                
                # Import into current session
                for key, value in old_state.items():
                    if key in self.persistent_keys and key not in st.session_state:
                        st.session_state[key] = value
                
                # Save to new format
                self.save_state()
                
                # Remove old file
                old_session_file.unlink()
                logger.info("Migrated from old session format")
                
        except Exception as e:
            logger.error(f"Error migrating old session: {e}")


# Global instance
session_manager = IsolatedSessionManager()


def initialize_session() -> None:
    """Initialize session with default values"""
    defaults = {
        'messages': [],
        'current_document_id': None,
        'selected_model': 'mistral',
        'current_model': 'mistral',
        'chunk_size': 800,
        'temperature': 0.7,
        'max_results': 5,
        'use_streaming': False,
        'use_web_search': False,
        'chat_input_key': 0
    }
    
    # Load existing session or set defaults
    if not session_manager.load_state():
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value


def save_session() -> None:
    """Save current session state"""
    session_manager.save_state()


def clear_session() -> None:
    """Clear current session"""
    session_manager.clear_session()


def get_session_info() -> Dict[str, Any]:
    """Get information about current session"""
    return {
        'session_id': session_manager.get_session_id(),
        'active_sessions': session_manager.get_active_sessions(),
        'session_timeout_minutes': session_manager.session_timeout / 60
    }