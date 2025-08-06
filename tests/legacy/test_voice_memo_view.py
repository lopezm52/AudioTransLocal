#!/usr/bin/env python3
"""
Test script for Voice Memo View UI components

This script demonstrates the Voice Memo browse view with table model,
state management, and user interface components.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer

# Add the current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from voice_memo_view import VoiceMemoView
from voice_memo_model import VoiceMemoStatus


class TestVoiceMemoWindow(QMainWindow):
    """Test window for Voice Memo View components"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AudioTransLocal - Voice Memo Browser Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Create Voice Memo View
        self.voice_memo_view = VoiceMemoView()
        layout.addWidget(self.voice_memo_view)
        
        # Auto-load Voice Memos after a short delay
        QTimer.singleShot(1000, self._load_test_data)
    
    def _load_test_data(self):
        """Load test Voice Memos data"""
        # Use the test database path
        db_path = "/Users/lopezm52/Documents/VisualCode/Test/CloudRecordings.db"
        
        if Path(db_path).exists():
            print(f"📂 Loading Voice Memos from: {db_path}")
            self.voice_memo_view.load_voice_memos(db_path)
            
            # Demo: After 5 seconds, simulate some status changes
            QTimer.singleShot(5000, self._demo_status_changes)
        else:
            print(f"❌ Test database not found: {db_path}")
    
    def _demo_status_changes(self):
        """Demonstrate status changes after loading"""
        print("🔄 Demonstrating status changes...")
        
        # Get the table model to access memos
        model = self.voice_memo_view.table_model
        state_manager = self.voice_memo_view.state_manager
        
        # Change status of first few memos to demonstrate state management
        for i in range(min(3, model.rowCount())):
            memo = model.get_memo_at_row(i)
            if memo:
                memo_id = model._get_memo_id(memo)
                
                if i == 0:
                    state_manager.set_status(memo_id, VoiceMemoStatus.TRANSCRIBING)
                elif i == 1:
                    state_manager.set_status(memo_id, VoiceMemoStatus.TRANSCRIBED)
                elif i == 2:
                    state_manager.set_status(memo_id, VoiceMemoStatus.ERROR)
        
        print("✅ Status changes applied - check the table view!")


def main():
    """Main test function"""
    print("🧪 Voice Memo View Test")
    print("=" * 40)
    
    app = QApplication(sys.argv)
    
    # Create and show test window
    window = TestVoiceMemoWindow()
    window.show()
    
    print("🎬 Test window created - loading Voice Memos...")
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
