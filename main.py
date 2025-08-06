#!/usr/bin/env python3
"""
AudioTransLocal - Audio transcription application with improved dependency injection architecture
"""

import sys
import logging
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import QSettings

from app.core.service_factory import ServiceContainer, create_container
from app.views.main_window import MainWindow
from app.views.preferences_window import PreferencesWindow
from app.views.welcome_dialog import WelcomeDialog
from app.services.credentials_manager import CredentialsManager
from app.services.macos_bookmarks import BookmarkAwareSettings

logger = logging.getLogger(__name__)


class AudioTransLocalApp:
    """
    Main application controller with improved dependency injection.
    
    Uses the new ServiceContainer for better scalability and maintainability.
    """
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.settings = QSettings("AudioTransLocal", "AudioTransLocal")
        self.bookmark_settings = BookmarkAwareSettings(self.settings)
        
        # Use the new ServiceContainer instead of ServiceFactory
        self.container = create_container()
        
        # Register application-specific services
        self.container.register_singleton("settings", self.settings)
        self.container.register_singleton("bookmark_settings", self.bookmark_settings)
        
        self.main_window = None
        
        logger.info("AudioTransLocal application initialized with ServiceContainer")
        
    def is_first_launch(self):
        """Check if this is the first launch"""
        return not self.settings.contains("audio_folder_path") and not self.settings.contains("audio_folder_bookmark")
        
    def get_audio_folder_path(self):
        """Get the stored audio folder path using security-scoped bookmarks"""
        return self.bookmark_settings.get_folder_path("audio_folder")
        
    def set_audio_folder_path(self, path):
        """Store the audio folder path with security-scoped bookmark"""
        success = self.bookmark_settings.store_folder_path("audio_folder", path)
        if success:
            print(f"✅ Successfully stored folder path with security-scoped bookmark: {path}")
        else:
            print(f"⚠️  Stored folder path without security-scoped bookmark: {path}")
        self.settings.sync()
        
    def show_welcome_dialog(self):
        """Show the welcome dialog for first launch"""
        # Get dependencies from service container
        credentials_manager = self.container.get("credentials_manager")
        
        # Create welcome dialog with dependencies
        dialog = WelcomeDialog(
            credentials_manager=credentials_manager,
            parent=None
        )
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted and dialog.selected_folder:
            # Store the selected folder
            self.set_audio_folder_path(dialog.selected_folder)
            return dialog.selected_folder
        else:
            # User quit or cancelled
            return None
            
    def run(self):
        """Main application entry point"""
        audio_folder_path = None
        
        if self.is_first_launch():
            # First launch - show welcome dialog
            audio_folder_path = self.show_welcome_dialog()
            if not audio_folder_path:
                # User quit during onboarding
                return 1
        else:
            # Not first launch - get stored path
            audio_folder_path = self.get_audio_folder_path()
            
        # Get all required services from the container
        whisper_model_manager = self.container.get("whisper_model_manager")
        credentials_manager = self.container.get("credentials_manager")
        transcription_service = self.container.get("transcription_service")
        
        # Create and show main window with dependency injection
        self.main_window = MainWindow(
            audio_folder_path=audio_folder_path,
            whisper_model_manager=whisper_model_manager,
            credentials_manager=credentials_manager,
            transcription_service=transcription_service
        )
        self.main_window.show()
        
        # Start event loop
        return self.app.exec()


def main():
    """Main entry point of the application"""
    app_controller = AudioTransLocalApp()
    return app_controller.run()


if __name__ == "__main__":
    sys.exit(main())
