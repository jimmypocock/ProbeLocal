"""Notification system for the UI"""
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Any
from .toast_notifications import toast_success, toast_error, toast_warning, toast_info


def add_notification(message: str, type: str = "info", duration: int = 5, use_toast: bool = True) -> None:
    """Add a notification that persists for a specified duration"""
    # Use toast notifications for quick feedback
    if use_toast:
        if type == "success":
            toast_success(message, duration)
        elif type == "error":
            toast_error(message, duration)
        elif type == "warning":
            toast_warning(message, duration)
        else:
            toast_info(message, duration)
    else:
        # Fallback to traditional notifications
        if 'notifications' not in st.session_state:
            st.session_state.notifications = []

        st.session_state.notifications.append({
            "message": message,
            "type": type,
            "timestamp": datetime.now(),
            "duration": duration
        })


def show_notifications() -> None:
    """Display active notifications"""
    if 'notifications' not in st.session_state:
        return

    current_time = datetime.now()
    active_notifications = []

    for notif in st.session_state.notifications:
        if current_time - notif["timestamp"] < timedelta(seconds=notif["duration"]):
            active_notifications.append(notif)

    st.session_state.notifications = active_notifications

    for notif in active_notifications:
        if notif["type"] == "success":
            st.success(notif["message"])
        elif notif["type"] == "error":
            st.error(notif["message"])
        elif notif["type"] == "warning":
            st.warning(notif["message"])
        else:
            st.info(notif["message"])
