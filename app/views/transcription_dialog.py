#!/usr/bin/env python3
"""
Transcription View Dialog for AudioTransLocal

This module provides a dialog for viewing completed transcriptions
with copy/save functionality.

Epic 3: Core Transcription Workflow
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QDialogButtonBox, QMessageBox, QFileDialog, QFrame
)
from PySide6.QtGui import QFont, QIcon


class TranscriptionViewDialog(QDialog):
    """
    Dialog for viewing and managing transcription text.
    
    This dialog displays the completed transcription with options to:
    - Copy text to clipboard
    - Save to a custom location
    - View metadata about the transcription
    """
    
    def __init__(self, memo, transcript_text: str, parent=None):
        super().__init__(parent)
        self.memo = memo
        self.transcript_text = transcript_text
        
        self.setWindowTitle(f"Transcription - {memo.title}")
        self.setMinimumSize(600, 400)
        self.resize(800, 600)
        
        self._setup_ui()
        self._load_transcript()
    
    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Header with memo information in single line (no frame)
        # Build information string: icon + filename - created date - duration
        info_parts = [f"📝 {self.memo.title}"]
        
        if hasattr(self.memo, 'creation_date') and self.memo.creation_date:
            date_str = self.memo.creation_date.strftime("%B %d, %Y at %H:%M")
            info_parts.append(f"Created: {date_str}")
        
        if hasattr(self.memo, 'duration') and self.memo.duration:
            minutes = int(self.memo.duration // 60)
            seconds = int(self.memo.duration % 60)
            info_parts.append(f"Duration: {minutes}:{seconds:02d}")
        
        # Create single line label
        info_text = " - ".join(info_parts)
        header_label = QLabel(info_text)
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(14)
        header_label.setFont(header_font)
        layout.addWidget(header_label)
        
        # Transcript text area
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Arial", 14))  # Increased from 11 to 14
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.text_edit)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.copy_button = QPushButton("📋 Copy to Clipboard")
        self.copy_button.clicked.connect(self._copy_to_clipboard)
        button_layout.addWidget(self.copy_button)
        
        self.save_button = QPushButton("💾 Save As...")
        self.save_button.clicked.connect(self._save_as)
        button_layout.addWidget(self.save_button)
        
        button_layout.addStretch()
        
        # Standard dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
    
    def _load_transcript(self):
        """Load the transcript text into the text editor"""
        if self.transcript_text.strip():
            self.text_edit.setPlainText(self.transcript_text)
        else:
            self.text_edit.setPlainText("No transcript text available.")
            self.copy_button.setEnabled(False)
            self.save_button.setEnabled(False)
        
        # Position cursor at the beginning
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        self.text_edit.setTextCursor(cursor)
    
    def _copy_to_clipboard(self):
        """Copy transcript text to clipboard"""
        try:
            from PySide6.QtGui import QGuiApplication
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(self.transcript_text)
            
            # Show confirmation
            QMessageBox.information(
                self,
                "Copied",
                "Transcript copied to clipboard!"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Copy Error",
                f"Failed to copy to clipboard: {e}"
            )
    
    def _save_as(self):
        """Save transcript to a custom location"""
        try:
            # Suggest filename based on memo title
            suggested_name = f"{self.memo.title}.txt"
            # Clean up filename
            suggested_name = "".join(c for c in suggested_name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Transcription",
                suggested_name,
                "Text Files (*.txt);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.transcript_text)
                
                QMessageBox.information(
                    self,
                    "Saved",
                    f"Transcription saved to:\n{file_path}"
                )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save transcription: {e}"
            )
