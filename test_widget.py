#!/usr/bin/env python3
"""
Test script for the WhisperModelWidget to verify integration
"""

import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.whisper_model_manager import WhisperModelManager
from app.views.whisper_model_widget import WhisperModelWidget


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Whisper Model Widget Test")
        self.setFixedSize(600, 400)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Create whisper model manager
        self.whisper_model_manager = WhisperModelManager()
        
        # Create and add the widget
        self.whisper_widget = WhisperModelWidget(self.whisper_model_manager, self)
        layout.addWidget(self.whisper_widget)
        
        print("Widget created successfully!")
        print(f"Available models: {self.whisper_model_manager.get_available_models()}")


def main():
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    print("Test window shown. You can test the widget functionality.")
    print("Available features:")
    print("- Model selection dropdown")
    print("- Model status display") 
    print("- Download button (enabled for non-downloaded models)")
    print("- Progress bar (shown during download)")
    print("- Cancel button (shown during download)")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
