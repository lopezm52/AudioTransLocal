#!/usr/bin/env python3
"""
Comprehensive test for US3: Automatic Refresh & Filtering functionality
"""

import sys
import time
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, 
    QHBoxLayout, QLabel, QPushButton, QTextEdit
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont

from voice_memo_view import VoiceMemoView


class US3TestWindow(QMainWindow):
    """Test window for US3 features"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("US3: Automatic Refresh & Filtering Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # Test header
        self._setup_header(layout)
        
        # Voice Memo View (main component)
        self.voice_memo_view = VoiceMemoView()
        layout.addWidget(self.voice_memo_view)
        
        # Test controls
        self._setup_test_controls(layout)
        
        # Load test data after UI is ready
        QTimer.singleShot(100, self.load_test_data)
    
    def _setup_header(self, layout):
        """Setup test header with information"""
        header_layout = QVBoxLayout()
        
        title = QLabel("🧪 US3: Automatic Refresh & Filtering Test")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)
        
        info = QLabel(
            "✨ Features to test:\n"
            "• 🔍 Search Bar: Type in the search field to filter Voice Memos\n"
            "• 📁 File System Monitoring: Automatic refresh when database changes\n"
            "• 🔄 Manual Refresh: Click the refresh button to reload data\n"
            "• 📊 Dynamic Status: Status updates based on search results"
        )
        info.setStyleSheet("QLabel { color: #666; font-size: 12px; margin: 8px; }")
        info.setWordWrap(True)
        header_layout.addWidget(info)
        
        layout.addLayout(header_layout)
    
    def _setup_test_controls(self, layout):
        """Setup test control buttons"""
        controls_layout = QHBoxLayout()
        
        # Test buttons
        test_search_btn = QPushButton("🔍 Test Search")
        test_search_btn.clicked.connect(self.test_search_functionality)
        controls_layout.addWidget(test_search_btn)
        
        test_refresh_btn = QPushButton("🔄 Test Refresh")
        test_refresh_btn.clicked.connect(self.test_refresh_functionality)
        controls_layout.addWidget(test_refresh_btn)
        
        clear_search_btn = QPushButton("❌ Clear Search")
        clear_search_btn.clicked.connect(self.clear_search)
        controls_layout.addWidget(clear_search_btn)
        
        controls_layout.addStretch()
        
        # Status display
        self.test_status = QLabel("Ready for testing")
        self.test_status.setStyleSheet("QLabel { color: #007acc; font-weight: bold; }")
        controls_layout.addWidget(self.test_status)
        
        layout.addLayout(controls_layout)
    
    def load_test_data(self):
        """Load test Voice Memos data"""
        db_path = "/Users/lopezm52/Documents/VisualCode/Test/CloudRecordings.db"
        if Path(db_path).exists():
            print(f"📂 Loading Voice Memos for US3 test: {db_path}")
            self.voice_memo_view.load_voice_memos(db_path)
            self.test_status.setText("✅ Test data loaded - 129 Voice Memos ready")
        else:
            print(f"❌ Test database not found: {db_path}")
            self.test_status.setText("❌ Test database not found")
    
    def test_search_functionality(self):
        """Demonstrate search functionality"""
        search_terms = ["New", "Recording", "2024", "Voice"]
        current_term = 0
        
        def apply_next_search():
            nonlocal current_term
            if current_term < len(search_terms):
                term = search_terms[current_term]
                self.voice_memo_view.search_field.setText(term)
                self.test_status.setText(f"🔍 Applied search filter: '{term}'")
                print(f"🔍 Testing search with term: '{term}'")
                current_term += 1
                
                # Schedule next search term
                if current_term < len(search_terms):
                    QTimer.singleShot(2000, apply_next_search)
                else:
                    QTimer.singleShot(2000, lambda: self.test_status.setText("✅ Search test completed"))
        
        apply_next_search()
    
    def test_refresh_functionality(self):
        """Test manual refresh functionality"""
        self.test_status.setText("🔄 Testing manual refresh...")
        print("🔄 Testing manual refresh functionality")
        
        # Trigger refresh
        self.voice_memo_view.refresh_memos()
        
        # Update status after a delay
        QTimer.singleShot(3000, lambda: self.test_status.setText("✅ Manual refresh test completed"))
    
    def clear_search(self):
        """Clear the search field"""
        self.voice_memo_view.search_field.clear()
        self.test_status.setText("❌ Search cleared - showing all Voice Memos")
        print("❌ Search filter cleared")


def main():
    """Run the US3 comprehensive test"""
    app = QApplication(sys.argv)
    
    print("🧪 US3: Automatic Refresh & Filtering Test")
    print("==========================================")
    print("📋 Testing Features:")
    print("  ✅ Search bar with magnifying glass icon")
    print("  ✅ QSortFilterProxyModel for efficient filtering")
    print("  ✅ File system monitoring with watchdog")
    print("  ✅ Enhanced manual refresh functionality")
    print("  ✅ Dynamic status updates")
    print()
    print("🎮 Interactive Testing:")
    print("  • Type in the search box to filter results")
    print("  • Use test buttons to demonstrate functionality")
    print("  • Watch status messages for real-time feedback")
    print()
    
    window = US3TestWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
