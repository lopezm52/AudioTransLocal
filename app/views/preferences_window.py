#!/usr/bin/env python3
"""
Preferences window for AudioTransLocal application
"""

import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                            QWidget, QGroupBox, QFormLayout, QLineEdit, 
                            QPushButton, QLabel, QComboBox, QProgressBar,
                            QMessageBox, QFileDialog)
from PySide6.QtCore import Qt, QSettings, Signal
from resources.styles import apply_style
from app.services.validation import SettingsValidator
from app.services.macos_bookmarks import BookmarkAwareSettings
from app.views.whisper_model_widget import WhisperModelWidget


class PreferencesWindow(QDialog):
    """Preferences window for application settings"""
    
    # Signal emitted when folder path is changed
    folder_changed = Signal(str)
    
    def __init__(self, whisper_model_manager, credentials_manager, parent=None):
        super().__init__(parent)
        self.whisper_model_manager = whisper_model_manager
        self.credentials_manager = credentials_manager
        self.settings = QSettings("AudioTransLocal", "AudioTransLocal")
        self.bookmark_settings = BookmarkAwareSettings(self.settings)
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Setup the preferences window UI"""
        self.setWindowTitle("AudioTransLocal Preferences")
        self.setModal(False)  # Non-modal window
        self.setFixedSize(800, 550)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(15)
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # General tab
        general_tab = QWidget()
        general_layout = QVBoxLayout()
        general_layout.setContentsMargins(15, 15, 15, 15)
        general_layout.setSpacing(15)
        
        # Folder configuration group
        folder_group = QGroupBox("Audio Files Folder")
        folder_layout = QHBoxLayout()  # Changed to HBoxLayout for better alignment
        folder_layout.setSpacing(10)
        
        # Current folder label - aligned to middle
        folder_label = QLabel("Current folder:")
        folder_label.setAlignment(Qt.AlignVCenter)  # Removed right alignment
        folder_label.setMinimumWidth(120)  # Fixed width for alignment
        folder_layout.addWidget(folder_label)
        
        # Current folder path (read-only) - double width
        self.folder_path_field = QLineEdit()
        self.folder_path_field.setReadOnly(True)
        self.folder_path_field.setMinimumWidth(400)  # Double the width
        apply_style(self.folder_path_field, 'input_readonly')
        folder_layout.addWidget(self.folder_path_field)
        
        # Change folder button
        change_folder_btn = QPushButton("Change...")
        change_folder_btn.setFixedHeight(32)  # Standard button height
        apply_style(change_folder_btn, 'button_primary')
        change_folder_btn.clicked.connect(self.change_folder)
        folder_layout.addWidget(change_folder_btn)
        
        folder_layout.addStretch()  # Push everything to the left
        
        # Add main layout to group
        folder_group_layout = QVBoxLayout()
        folder_group_layout.addLayout(folder_layout)
        
        # Add help text
        help_text = QLabel("Select the folder containing your audio files (Voice Memos, recordings, etc.)")
        apply_style(help_text, 'help_text')
        help_text.setWordWrap(True)
        help_text.setContentsMargins(0, 5, 0, 0)  # Removed left margin of 120
        folder_group_layout.addWidget(help_text)
        
        folder_group.setLayout(folder_group_layout)
        general_layout.addWidget(folder_group)
        general_layout.addSpacing(10)  # Reduced spacing
        
        # API Configuration group
        api_group = QGroupBox("API Configuration")
        api_layout = QHBoxLayout()  # Changed to HBoxLayout for better alignment
        api_layout.setSpacing(10)
        
        # n8n API Key label - aligned to middle
        api_label = QLabel("n8n API Key:")
        api_label.setAlignment(Qt.AlignVCenter)  # Removed right alignment
        api_label.setMinimumWidth(120)  # Fixed width for alignment
        api_layout.addWidget(api_label)
        
        # n8n API Key (secure text field) - double width
        self.api_key_field = QLineEdit()
        self.api_key_field.setEchoMode(QLineEdit.Password)
        self.api_key_field.setPlaceholderText("Enter your n8n API key...")
        self.api_key_field.setMinimumWidth(300)  # Double the width
        apply_style(self.api_key_field, 'input_password')
        api_layout.addWidget(self.api_key_field)
        
        # Show/Hide API key button
        self.show_api_key_btn = QPushButton("Show")
        self.show_api_key_btn.setFixedHeight(32)  # Standard button height
        apply_style(self.show_api_key_btn, 'button_secondary')
        self.show_api_key_btn.clicked.connect(self.toggle_api_key_visibility)
        api_layout.addWidget(self.show_api_key_btn)
        
        # Save button for API key
        save_api_key_btn = QPushButton("Save")
        save_api_key_btn.setFixedHeight(32)  # Standard button height
        apply_style(save_api_key_btn, 'button_success')
        save_api_key_btn.clicked.connect(self.save_api_key)
        api_layout.addWidget(save_api_key_btn)
        
        # Clear button for API key
        clear_api_key_btn = QPushButton("Clear")
        clear_api_key_btn.setFixedHeight(32)  # Standard button height
        apply_style(clear_api_key_btn, 'button_danger')
        clear_api_key_btn.clicked.connect(self.clear_api_key)
        api_layout.addWidget(clear_api_key_btn)
        
        api_layout.addStretch()  # Push everything to the left
        
        # Add main layout to group
        api_group_layout = QVBoxLayout()
        api_group_layout.addLayout(api_layout)
        
        # Add API key help text
        api_help_text = QLabel("Your n8n API key is stored securely in the macOS Keychain")
        apply_style(api_help_text, 'help_text')
        api_help_text.setWordWrap(True)
        api_help_text.setContentsMargins(0, 5, 0, 0)  # Align with window
        api_group_layout.addWidget(api_help_text)
        
        api_group.setLayout(api_group_layout)
        general_layout.addWidget(api_group)
        general_layout.addSpacing(10)  # Reduced spacing
        
        # Whisper Model Management widget
        self.whisper_model_widget = WhisperModelWidget(self.whisper_model_manager, self)
        general_layout.addWidget(self.whisper_model_widget)
        
        general_layout.addStretch()
        
        general_tab.setLayout(general_layout)
        tab_widget.addTab(general_tab, "General")
        
        # Close button
        button_layout = QHBoxLayout()
        close_btn = QPushButton("Close")
        apply_style(close_btn, 'button_secondary')
        close_btn.clicked.connect(self.close)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        # Add components to main layout
        main_layout.addWidget(tab_widget)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
    def load_settings(self):
        """Load current settings into the UI"""
        # Load folder path using security-scoped bookmarks
        folder_path = self.bookmark_settings.get_folder_path("audio_folder") or ""
        self.folder_path_field.setText(folder_path)
        
        # Load API key from Keychain
        api_key = self.credentials_manager.get_n8n_api_key()
        self.api_key_field.setText(api_key)
        
        
        
    def save_api_key(self):
        """Save API key to Keychain with validation"""
        api_key = self.api_key_field.text().strip()
        
        # Validate API key
        validation_result = SettingsValidator.validate_api_settings(api_key=api_key)
        
        if validation_result.is_valid:
            # Save the validated API key
            validated_key = validation_result.data.get('api_key')
            
            if self.credentials_manager.set_n8n_api_key(validated_key):
                message = "Your n8n API key has been securely saved to the macOS Keychain."
                
                # Add validation warnings if any
                if validation_result.has_warnings():
                    message += f"\n\nNote: {validation_result.get_warning_message()}"
                
                if validated_key:
                    QMessageBox.information(
                        self,
                        "API Key Saved",
                        message
                    )
                else:
                    QMessageBox.information(
                        self,
                        "API Key Cleared",
                        "Your n8n API key has been removed from the macOS Keychain."
                    )
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to save API key to Keychain. Please try again."
                )
        else:
            # Show validation errors
            QMessageBox.critical(
                self,
                "Invalid API Key",
                f"The API key is not valid:\n\n{validation_result.get_error_message()}\n\nPlease correct the API key and try again."
            )
    
    def clear_api_key(self):
        """Clear API key from both field and Keychain"""
        reply = QMessageBox.question(
            self,
            "Clear API Key",
            "Are you sure you want to clear your n8n API key?\nThis will remove it from the secure Keychain storage.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.api_key_field.clear()
            if self.credentials_manager.delete_n8n_api_key():
                QMessageBox.information(
                    self,
                    "API Key Cleared",
                    "Your n8n API key has been removed from the macOS Keychain."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Warning",
                    "API key cleared from field, but there was an issue removing it from Keychain."
                )
    
    def toggle_api_key_visibility(self):
        """Toggle between showing and hiding the API key"""
        if self.api_key_field.echoMode() == QLineEdit.Password:
            # Currently hidden, show it
            self.api_key_field.setEchoMode(QLineEdit.Normal)
            self.show_api_key_btn.setText("Hide")
        else:
            # Currently shown, hide it
            self.api_key_field.setEchoMode(QLineEdit.Password)
            self.show_api_key_btn.setText("Show")
        
    def change_folder(self):
        """Handle folder change button click with validation"""
        current_path = self.bookmark_settings.get_folder_path("audio_folder") or ""
        
        # Get suggested default path - use the correct Voice Memos location
        voice_memos_path = os.path.expanduser("~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings")
        downloads_path = os.path.expanduser("~/Downloads")
        
        # Use current path if exists, otherwise smart defaults
        if current_path and os.path.exists(current_path):
            default_path = current_path
        elif os.path.exists(voice_memos_path):
            default_path = voice_memos_path
        elif os.path.exists(downloads_path):
            default_path = downloads_path
        else:
            default_path = os.path.expanduser("~")
        
        # Open folder selection dialog
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Audio Files Folder",
            default_path,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder_path:
            # Validate the selected folder
            validation_result = SettingsValidator.validate_audio_folder(folder_path)
            
            if validation_result.is_valid:
                # Show warning if Voice Memos database not found
                if validation_result.has_warnings():
                    reply = QMessageBox.warning(
                        self,
                        "Folder Validation Warning",
                        validation_result.get_warning_message() + "\n\nDo you want to continue with this folder?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply != QMessageBox.Yes:
                        return  # User chose not to continue
                
                # Update settings with validated path using security-scoped bookmarks
                validated_path = validation_result.data['folder_path']
                success = self.bookmark_settings.store_folder_path("audio_folder", validated_path)
                if not success:
                    print(f"Warning: Failed to create security-scoped bookmark for {validated_path}")
                self.settings.sync()
                
                # Update UI
                self.folder_path_field.setText(validated_path)
                
                # Emit signal to notify main window
                self.folder_changed.emit(validated_path)
                
                # Show confirmation
                message = f"Audio folder updated to:\n{validated_path}"
                if validation_result.has_warnings():
                    message += f"\n\nNote: {validation_result.get_warning_message()}"
                
                QMessageBox.information(
                    self,
                    "Folder Updated",
                    message
                )
            else:
                # Show validation errors
                QMessageBox.critical(
                    self,
                    "Invalid Folder Selection",
                    f"The selected folder is not valid:\n\n{validation_result.get_error_message()}\n\nPlease select a different folder."
                )
