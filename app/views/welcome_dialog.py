#!/usr/bin/env python3
"""
Welcome dialog for AudioTransLocal application
"""

import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTextEdit, QFileDialog, QMessageBox,
                            QApplication)
from PySide6.QtCore import Qt
from resources.styles import apply_style, get_font
from app.services.validation import SettingsValidator


class WelcomeDialog(QDialog):
    """Welcome dialog for first launch and folder selection"""
    
    def __init__(self, credentials_manager, parent=None):
        super().__init__(parent)
        self.credentials_manager = credentials_manager
        self.selected_folder = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the welcome dialog UI"""
        self.setWindowTitle("Welcome to AudioTransLocal")
        self.setModal(True)
        self.setFixedSize(500, 350)
        
        # Main layout
        layout = QVBoxLayout()
        
        # Welcome title
        title = QLabel("Welcome to AudioTransLocal")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(get_font('title_medium'))
        apply_style(title, 'welcome_title')
        
        # Welcome message
        message = QTextEdit()
        message.setReadOnly(True)
        message.setHtml("""
        <div style="font-family: Arial; font-size: 14px; line-height: 1.6;">
            <p><strong>To get started, we need access to your audio files.</strong></p>
            <p>AudioTransLocal helps you transcribe your voice memos and audio recordings. 
            To do this effectively, please select the folder where your audio files are stored.</p>
            <p><strong>Common locations:</strong></p>
            <ul>
                <li>Voice Memos: <code>~/Library/Application Support/com.apple.voicememos/Recordings</code></li>
                <li>Downloads folder: <code>~/Downloads</code></li>
                <li>Custom audio folder of your choice</li>
            </ul>
            <p><em>Note: You can change this folder location later in Settings.</em></p>
        </div>
        """)
        message.setMaximumHeight(180)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        
        # Quit button
        quit_btn = QPushButton("Quit")
        apply_style(quit_btn, 'button_danger')
        quit_btn.clicked.connect(self.quit_application)
        
        # Select folder button
        select_btn = QPushButton("Select Folder...")
        apply_style(select_btn, 'button_primary')
        select_btn.clicked.connect(self.select_folder)
        select_btn.setDefault(True)  # Make this the default button
        
        # Add buttons to layout
        button_layout.addWidget(quit_btn)
        button_layout.addStretch()
        button_layout.addWidget(select_btn)
        
        # Add all components to main layout
        layout.addWidget(title)
        layout.addWidget(message)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def select_folder(self):
        """Handle folder selection with validation"""
        # Get suggested default path (Voice Memos location)
        voice_memos_path = os.path.expanduser("~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings")
        downloads_path = os.path.expanduser("~/Downloads")
        
        # Use Voice Memos path if it exists, otherwise Downloads, otherwise home
        if os.path.exists(voice_memos_path):
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
                
                self.selected_folder = validation_result.data['folder_path']
                self.accept()  # Close dialog with success
            else:
                # Show validation errors
                error_message = "The selected folder is not valid:\n\n" + validation_result.get_error_message() + "\n\nPlease select a different folder."
                QMessageBox.critical(
                    self,
                    "Invalid Folder Selection",
                    error_message
                )
        # If cancelled or invalid, dialog stays open
        
    def quit_application(self):
        """Handle quit button"""
        self.reject()  # Close dialog with cancel
        QApplication.quit()
