"""Style loader utility for loading compiled CSS in Streamlit"""

import streamlit as st
from pathlib import Path
from typing import Optional, Union
import os


class StyleLoader:
    """Handles loading and injecting CSS styles into Streamlit app"""
    
    def __init__(self, css_dir: str = "static/css"):
        self.css_dir = Path(css_dir)
        self._loaded_styles = set()
    
    def load_css(self, filename: str = "main.css", force_reload: bool = False) -> None:
        """
        Load CSS file and inject into Streamlit app
        
        Args:
            filename: CSS filename to load
            force_reload: Force reload even if already loaded
        """
        # Check if already loaded (unless force reload)
        if filename in self._loaded_styles and not force_reload:
            return
        
        css_path = self.css_dir / filename
        
        if not css_path.exists():
            # Try to build SASS if CSS doesn't exist
            if self._build_sass():
                # Try again after building
                if not css_path.exists():
                    st.warning(f"CSS file not found: {css_path}")
                    return
            else:
                st.warning(f"CSS file not found and SASS build failed: {css_path}")
                return
        
        # Load and inject CSS
        with open(css_path, "r") as f:
            css_content = f.read()
        
        # Add unique identifier to prevent duplicate injection
        style_id = f"greg-styles-{filename.replace('.', '-')}"
        
        st.markdown(
            f"""
            <style id="{style_id}">
                {css_content}
            </style>
            """,
            unsafe_allow_html=True
        )
        
        self._loaded_styles.add(filename)
    
    def load_component_css(self, component: str) -> None:
        """
        Load CSS for a specific component
        
        Args:
            component: Component name (e.g., 'chat', 'notifications')
        """
        component_css = f"components/{component}.css"
        self.load_css(component_css)
    
    def inject_custom_css(self, css: str) -> None:
        """
        Inject custom CSS directly
        
        Args:
            css: CSS string to inject
        """
        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True
        )
    
    def load_theme(self, theme: str = "default") -> None:
        """
        Load a specific theme
        
        Args:
            theme: Theme name (default, dark, etc.)
        """
        theme_css = f"themes/{theme}.css"
        self.load_css(theme_css)
    
    def _build_sass(self) -> bool:
        """Try to build SASS files if CSS is missing"""
        try:
            # Check if build script exists
            build_script = Path("scripts/build_sass.py")
            if not build_script.exists():
                return False
            
            # Try to run build script
            import subprocess
            result = subprocess.run(
                ["python", str(build_script), "--compressed"],
                capture_output=True,
                text=True
            )
            
            return result.returncode == 0
            
        except Exception:
            return False
    
    def get_css_variables(self) -> dict:
        """Get CSS variables as Python dict for dynamic use"""
        return {
            # Colors
            "primary_color": "#4A90E2",
            "primary_dark": "#357ABD",
            "primary_light": "#6BA3E8",
            "secondary_color": "#667eea",
            "accent_green": "#2ECC71",
            "accent_red": "#ef4444",
            "accent_orange": "#f59e0b",
            
            # Spacing
            "spacing_xs": "0.25rem",
            "spacing_sm": "0.5rem",
            "spacing_md": "1rem",
            "spacing_lg": "1.5rem",
            "spacing_xl": "2rem",
            
            # Border radius
            "radius_sm": "0.25rem",
            "radius_md": "0.5rem",
            "radius_lg": "0.75rem",
            "radius_xl": "1rem",
            "radius_full": "9999px",
            
            # Shadows
            "shadow_sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
            "shadow_md": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
            "shadow_lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
        }


# Global style loader instance
style_loader = StyleLoader()


def load_app_styles(force_reload: bool = False) -> None:
    """
    Load all application styles
    
    Args:
        force_reload: Force reload all styles
    """
    style_loader.load_css("main.css", force_reload)


def inject_component_styles(component: str) -> None:
    """
    Load styles for a specific component
    
    Args:
        component: Component name
    """
    style_loader.load_component_css(component)


def apply_custom_theme(theme_css: str) -> None:
    """
    Apply custom CSS theme
    
    Args:
        theme_css: CSS string for custom theme
    """
    style_loader.inject_custom_css(theme_css)


def get_style_variables() -> dict:
    """Get CSS variables as Python dict"""
    return style_loader.get_css_variables()


# Development helpers
def reload_styles() -> None:
    """Force reload all styles (useful in development)"""
    load_app_styles(force_reload=True)
    st.success("✅ Styles reloaded!")


def show_style_debug() -> None:
    """Show style debugging information"""
    with st.expander("🎨 Style Debug Info"):
        st.write("**Loaded Styles:**")
        st.write(list(style_loader._loaded_styles))
        
        st.write("**CSS Directory:**")
        st.write(str(style_loader.css_dir))
        
        st.write("**CSS Files:**")
        if style_loader.css_dir.exists():
            css_files = list(style_loader.css_dir.glob("**/*.css"))
            st.write([str(f.relative_to(style_loader.css_dir)) for f in css_files])
        else:
            st.warning("CSS directory not found!")
        
        st.write("**Style Variables:**")
        st.json(get_style_variables())
        
        if st.button("🔄 Reload Styles"):
            reload_styles()