#!/usr/bin/env python3
"""
Simple test for Voice Memo search and filtering functionality
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer

from voice_memo_view import VoiceMemoView


class SearchTestWindow(QMainWindow):
    """Test window for search functionality"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Memo Search Test")
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout
        layout = QVBoxLayout(central_widget)
        
        # Voice Memo View
        self.voice_memo_view = VoiceMemoView()
        layout.addWidget(self.voice_memo_view)
        
        # Load test data after UI is ready
        QTimer.singleShot(100, self.load_test_data)
    
    def load_test_data(self):
        """Load test Voice Memos data"""
        db_path = "/Users/lopezm52/Documents/VisualCode/Test/CloudRecordings.db"
        if Path(db_path).exists():
            print(f"🔍 Loading Voice Memos for search test: {db_path}")
            self.voice_memo_view.load_voice_memos(db_path)
        else:
            print(f"❌ Test database not found: {db_path}")


def main():
    """Run the search test"""
    app = QApplication(sys.argv)
    
    print("🔍 Voice Memo Search & Filter Test")
    print("=====================================")
    print("✅ Testing search functionality with proxy model")
    print("📝 Try typing in the search box to filter results")
    
    window = SearchTestWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
