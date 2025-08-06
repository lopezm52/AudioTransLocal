#!/usr/bin/env python3
"""
AudioTransLocal - Native macOS styling system
This module provides native macOS appearance for maximum visual fidelity and user confidence.
"""

# Native macOS styling approach - minimal custom styling to preserve native look
NATIVE_STYLES = {
    # Only override essential spacing and layout, preserve native macOS appearance
    'native_button': """
        QPushButton {
            min-height: 28px;
            padding: 4px 12px;
        }
    """,
    
    'native_input': """
        QLineEdit {
            min-height: 22px;
            padding: 4px 8px;
        }
    """,
    
    'native_readonly_input': """
        QLineEdit {
            min-height: 22px;
            padding: 4px 8px;
        }
        QLineEdit[readOnly="true"] {
            background-color: palette(button);
            color: palette(dark);
        }
    """,
    
    'native_dropdown': """
        QComboBox {
            min-height: 26px;
            padding: 4px 8px;
        }
    """,
    
    'native_progress': """
        QProgressBar {
            min-height: 20px;
        }
    """,
    
    # Minimal spacing adjustments for better layout without affecting native appearance
    'system_font': """
        QWidget {
            font-family: 'Helvetica Neue', 'Helvetica Neue', Arial, sans-serif;
        }
    """,
    
    # Welcome dialog - keep native but ensure proper sizing
    'welcome_title': """
        QLabel {
            font-family: 'Helvetica Neue', 'Helvetica Neue', Arial, sans-serif;
            font-weight: 600;
        }
    """,
    
    # Help text - use system secondary text color
    'help_text': """
        QLabel {
            color: palette(dark);
            font-family: 'Helvetica Neue', 'Helvetica Neue', Arial, sans-serif;
            font-size: 11px;
        }
    """,
    
    # Status info - minimal styling, rely on native appearance
    'status_info': """
        QLabel {
            font-family: 'Helvetica Neue', 'Helvetica Neue', Arial, sans-serif;
        }
    """,
    
    # Status success - use system colors
    'status_success': """
        QLabel {
            color: palette(dark);
            font-family: 'Helvetica Neue', 'Helvetica Neue', Arial, sans-serif;
        }
    """,
    
    # Instructions text
    'instructions': """
        QLabel {
            color: palette(dark);
            font-family: 'Helvetica Neue', 'Helvetica Neue', Arial, sans-serif;
        }
    """,
    
    # Folder info display
    'folder_info': """
        QLabel {
            background-color: palette(window);
            padding: 12px;
            border-radius: 6px;
            border: 1px solid palette(mid);
            font-family: 'Helvetica Neue', 'Helvetica Neue', Arial, sans-serif;
        }
    """,
    
    # Status label for model info
    'status_label': """
        QLabel {
            font-family: 'Helvetica Neue', 'Helvetica Neue', Arial, sans-serif;
            font-size: 12px;
            padding: 4px 8px;
        }
    """,
}

def apply_native_style(widget, style_name):
    """Apply minimal native-friendly styling to preserve macOS appearance"""
    style = NATIVE_STYLES.get(style_name, '')
    if style:
        widget.setStyleSheet(style)

# Convenience function for backward compatibility
def apply_style(widget, style_name):
    """Apply native styling (backward compatibility wrapper)"""
    # Map old style names to native equivalents
    style_mapping = {
        'button_primary': 'native_button',
        'button_success': 'native_button', 
        'button_danger': 'native_button',
        'button_secondary': 'native_button',
        'button_info': 'native_button',
        'input_readonly': 'native_readonly_input',
        'input_password': 'native_input',
        'dropdown': 'native_dropdown',
        'progress_bar': 'native_progress',
        'welcome_title': 'welcome_title',
        'help_text': 'help_text',
        'status_success': 'status_success',
        'instructions': 'instructions',
        'folder_info': 'folder_info',
        'status_label': 'status_label',
    }
    
    native_style = style_mapping.get(style_name, style_name)
    apply_native_style(widget, native_style)

def get_native_font(font_type='body'):
    """Get native macOS system fonts"""
    from PySide6.QtGui import QFont
    
    # Use system fonts that match macOS design guidelines
    font_configs = {
        'title_large': ('Helvetica Neue', 28, False),    # macOS Large Title
        'title_medium': ('Helvetica Neue', 20, True),    # macOS Title 1
        'title_small': ('Helvetica Neue', 17, False),    # macOS Title 2  
        'body': ('Helvetica Neue', 13, False),              # macOS Body
        'caption': ('Helvetica Neue', 11, False),           # macOS Caption
    }
    
    config = font_configs.get(font_type, font_configs['body'])
    font_family, size, bold = config
    
    # Create system font
    font = QFont()
    font.setFamily(font_family)
    font.setPointSize(size)
    font.setBold(bold)
    
    return font

# Convenience function for backward compatibility
def get_font(font_type='body'):
    """Get native system font (backward compatibility wrapper)"""
    return get_native_font(font_type)

# Native macOS appearance achieved by removing all custom colors and styles
# This ensures buttons, dropdowns, and other controls use the system appearance
