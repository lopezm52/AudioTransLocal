"""
Main window for AudioTransLocal application
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QMenuBar, 
                              QMessageBox)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QKeySequence, QAction

from app.views.voice_memo_view import VoiceMemoView
from app.views.preferences_window import PreferencesWindow
from app.services.transcription_service import TranscriptionProgress, TranscriptionResult


class MainWindow(QMainWindow):
    """Main application window with menu bar and dependency injection"""
    
    def __init__(self, audio_folder_path, whisper_model_manager, credentials_manager, transcription_service):
        super().__init__()
        self.audio_folder_path = audio_folder_path
        self.whisper_model_manager = whisper_model_manager
        self.credentials_manager = credentials_manager
        self.transcription_service = transcription_service
        self.preferences_window = None
        
        self.setup_ui()
        self.create_menu_bar()
        self.connect_transcription_signals()
        
    def setup_ui(self):
        """Setup the main window UI"""
        self.setWindowTitle("AudioTransLocal")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget with no spacing
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout with minimal spacing
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Add Voice Memo View as the main content
        self.voice_memo_view = VoiceMemoView()
        layout.addWidget(self.voice_memo_view)
        
        central_widget.setLayout(layout)
        
        # Auto-load Voice Memos if we have a valid folder path
        self._load_voice_memos()
        
    def create_menu_bar(self):
        """Create the application menu bar"""
        menubar = self.menuBar()
        
        # Application menu
        app_menu = menubar.addMenu("AudioTransLocal")
        
        # Preferences action
        preferences_action = QAction("Preferences...", self)
        preferences_action.setShortcut(QKeySequence("Ctrl+,"))
        preferences_action.triggered.connect(self.show_preferences)
        app_menu.addAction(preferences_action)
        
        app_menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit AudioTransLocal", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        app_menu.addAction(quit_action)
        
        # Voice Memos menu
        voice_menu = menubar.addMenu("Voice Memos")
        
        # Refresh action
        refresh_action = QAction("Refresh Voice Memos", self)
        refresh_action.setShortcut(QKeySequence("Ctrl+R"))
        refresh_action.triggered.connect(self._refresh_voice_memos)
        voice_menu.addAction(refresh_action)
        
        # Transcribe selected action
        transcribe_action = QAction("Transcribe Selected", self)
        transcribe_action.setShortcut(QKeySequence("Ctrl+T"))
        transcribe_action.triggered.connect(self.transcribe_selected_memo)
        voice_menu.addAction(transcribe_action)
    
    def connect_transcription_signals(self):
        """Connect transcription service signals"""
        self.transcription_service.transcription_started.connect(self.on_transcription_started)
        self.transcription_service.transcription_progress_updated.connect(self.on_transcription_progress_updated)
        self.transcription_service.transcription_completed.connect(self.on_transcription_completed)
    
    def on_transcription_started(self):
        """Handle transcription started signal"""
        print("🎯 Transcription started")
        # Update UI to show transcription is in progress
        if hasattr(self.voice_memo_view, 'update_transcription_status'):
            self.voice_memo_view.update_transcription_status("Starting transcription...")
    
    def on_transcription_progress_updated(self, progress: TranscriptionProgress):
        """Handle transcription progress updates"""
        print(f"📊 Transcription progress: {progress.percentage}% - {progress.current_step}")
        # Update UI with progress
        if hasattr(self.voice_memo_view, 'update_transcription_progress'):
            self.voice_memo_view.update_transcription_progress(progress)
    
    def on_transcription_completed(self, result: TranscriptionResult):
        """Handle transcription completion"""
        if result.success:
            print(f"✅ Transcription completed successfully")
            print(f"📝 Text: {result.text[:100]}...")
            
            # Show success message
            QMessageBox.information(
                self,
                "Transcription Complete",
                f"Transcription completed successfully!\n\n"
                f"Language: {result.language or 'Unknown'}\n"
                f"Duration: {result.duration:.2f}s" if result.duration else "Duration: Unknown"
            )
            
            # Update UI
            if hasattr(self.voice_memo_view, 'update_transcription_result'):
                self.voice_memo_view.update_transcription_result(result)
        else:
            print(f"❌ Transcription failed: {result.error_message}")
            
            # Show error message
            QMessageBox.critical(
                self,
                "Transcription Failed",
                f"Transcription failed:\n\n{result.error_message}"
            )
    
    def transcribe_selected_memo(self):
        """Transcribe the currently selected Voice Memo using the injected service"""
        if not hasattr(self, 'voice_memo_view'):
            return
        
        selected_memo = self.voice_memo_view.get_selected_memo()
        if not selected_memo:
            QMessageBox.information(
                self, 
                "No Selection", 
                "Please select a Voice Memo to transcribe."
            )
            return
        
        # Get the audio file path
        audio_file_path = selected_memo.get_file_path()
        if not audio_file_path or not os.path.exists(audio_file_path):
            QMessageBox.critical(
                self,
                "File Not Found",
                f"Audio file not found:\n{audio_file_path}"
            )
            return
        
        # Start transcription using the injected service
        success = self.transcription_service.start_transcription(audio_file_path)
        if not success:
            QMessageBox.critical(
                self,
                "Transcription Error",
                "Failed to start transcription. Please check that a Whisper model is downloaded."
            )
    
    def _refresh_voice_memos(self):
        """Refresh the Voice Memos list"""
        if hasattr(self, 'voice_memo_view'):
            self.voice_memo_view.refresh_memos()
    
    def show_preferences(self):
        """Show the preferences window"""
        if self.preferences_window is None:
            self.preferences_window = PreferencesWindow(
                whisper_model_manager=self.whisper_model_manager,
                credentials_manager=self.credentials_manager,
                parent=self
            )
            # Connect the folder changed signal
            self.preferences_window.folder_changed.connect(self.update_folder_display)
        
        # Show the preferences window (non-modal)
        self.preferences_window.show()
        self.preferences_window.raise_()
        self.preferences_window.activateWindow()
        
    def _load_voice_memos(self):
        """Load Voice Memos from the configured audio folder"""
        if not self.audio_folder_path:
            return
        
        # Check for Voice Memos database in the user-selected folder
        folder_path = Path(self.audio_folder_path)
        db_path = folder_path / "CloudRecordings.db"
        
        if db_path.exists():
            print(f"📂 Loading Voice Memos from: {db_path}")
            self.voice_memo_view.load_voice_memos(str(db_path))
        else:
            print(f"❌ CloudRecordings.db not found in: {folder_path}")
            # Don't try to access system Voice Memos folder automatically in standalone app
            # The user must explicitly select the folder through preferences
    
    def update_folder_display(self, folder_path):
        """Update the folder display and reload Voice Memos"""
        self.audio_folder_path = folder_path
        self._load_voice_memos()
