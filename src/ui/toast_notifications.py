"""Toast notification component for temporary success/error messages"""
import streamlit as st
import time
from typing import Literal, Optional, Dict, List
import uuid


class ToastManager:
    """Manages toast notifications with auto-dismiss and styling"""
    
    def __init__(self):
        if 'toast_notifications' not in st.session_state:
            st.session_state.toast_notifications = []
        if 'toast_shown' not in st.session_state:
            st.session_state.toast_shown = set()
    
    def show(
        self,
        message: str,
        type: Literal["success", "error", "warning", "info"] = "info",
        duration: int = 3,
        icon: Optional[str] = None
    ) -> None:
        """Show a toast notification"""
        # Auto-select icon based on type if not provided
        if icon is None:
            icon = {
                "success": "✅",
                "error": "❌",
                "warning": "⚠️",
                "info": "ℹ️"
            }.get(type, "📢")
        
        # Create notification
        notification = {
            'id': str(uuid.uuid4()),
            'message': message,
            'type': type,
            'icon': icon,
            'created_at': time.time(),
            'duration': duration
        }
        
        # Add to notifications
        st.session_state.toast_notifications.append(notification)
        
        # Limit to last 5 notifications
        if len(st.session_state.toast_notifications) > 5:
            st.session_state.toast_notifications = st.session_state.toast_notifications[-5:]
    
    def render(self) -> None:
        """Render all active toast notifications"""
        if not st.session_state.toast_notifications:
            return
        
        # Clean expired notifications
        current_time = time.time()
        active_notifications = []
        
        for notif in st.session_state.toast_notifications:
            if current_time - notif['created_at'] < notif['duration']:
                active_notifications.append(notif)
        
        st.session_state.toast_notifications = active_notifications
        
        # Render notifications
        if active_notifications:
            
            # Render toast container
            toast_html = '<div class="toast-container">'
            
            for notif in reversed(active_notifications):  # Show newest on top
                # Calculate fade out timing
                time_left = notif['duration'] - (current_time - notif['created_at'])
                fade_class = "toast-fade-out" if time_left < 0.5 else ""
                
                toast_html += f'''
                <div class="toast toast-{notif['type']} {fade_class}">
                    <span>{notif['icon']}</span>
                    <span>{notif['message']}</span>
                </div>
                '''
            
            toast_html += '</div>'
            st.markdown(toast_html, unsafe_allow_html=True)


# Global toast manager instance
toast_manager = ToastManager()


def show_toast(
    message: str,
    type: Literal["success", "error", "warning", "info"] = "info",
    duration: int = 3,
    icon: Optional[str] = None
) -> None:
    """Show a toast notification"""
    toast_manager.show(message, type, duration, icon)


def render_toasts() -> None:
    """Render all active toast notifications"""
    toast_manager.render()


# Convenience functions
def toast_success(message: str, duration: int = 3) -> None:
    """Show a success toast"""
    show_toast(message, "success", duration)


def toast_error(message: str, duration: int = 4) -> None:
    """Show an error toast"""
    show_toast(message, "error", duration)


def toast_warning(message: str, duration: int = 3) -> None:
    """Show a warning toast"""
    show_toast(message, "warning", duration)


def toast_info(message: str, duration: int = 3) -> None:
    """Show an info toast"""
    show_toast(message, "info", duration)


# Integration with existing notification system
def migrate_notification_to_toast(notification_type: str, message: str) -> None:
    """Convert traditional notifications to toast format"""
    if notification_type == "success":
        toast_success(message)
    elif notification_type == "error":
        toast_error(message)
    elif notification_type == "warning":
        toast_warning(message)
    else:
        toast_info(message)