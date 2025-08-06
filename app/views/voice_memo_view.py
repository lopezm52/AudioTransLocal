#!/usr/bin/env python3
"""
Voice Memo Browse View Widget for AudioTransLocal

This module implements the main UI view for browsing and managing Voice Memos
using QTableView with the custom model and state management.

Epic 2: Voice Memo Browse & Management  
US2: UI View & State Management
US3: Automatic Refresh & Filtering
"""

import asyncio
import re
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import logging
import os

from PySide6.QtCore import QTimer, QThread, Signal, QObject, Qt, QSortFilterProxyModel, QThreadPool
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton, 
    QLabel, QProgressBar, QHeaderView, QMessageBox, QFrame,
    QSplitter, QTextEdit, QGroupBox, QLineEdit, QDialog
)
from PySide6.QtGui import QFont, QIcon

# File system monitoring
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.services.voice_memo_parser import VoiceMemoParser, VoiceMemoModel
from app.services.voice_memo_model import (
    VoiceMemoTableModel, VoiceMemoStateManager, VoiceMemoStatusDelegate,
    VoiceMemoStatus
)
from app.workers.transcription_worker import TranscriptionWorker
from app.views.transcription_delegates import TranscriptionActionsDelegate, TranscriptionStatusDelegate
from app.views.transcription_dialog import TranscriptionViewDialog
from app.services.whisper_model_manager import WhisperModelManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceMemoFilterProxyModel(QSortFilterProxyModel):
    """
    Proxy model for filtering Voice Memos based on search criteria.
    
    This handles all the filtering logic efficiently without needing
    to maintain separate filtered data structures.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterKeyColumn(-1)  # Search across all columns - ensures custom filterAcceptsRow is used
        
    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        """
        Custom filtering logic for Voice Memos.
        This method is called for every row when filtering is applied.
        """
        try:
            source_model = self.sourceModel()
            if not source_model:
                return True
            
            # Get the current filter regular expression
            filter_regex = self.filterRegularExpression()
            if not filter_regex.pattern():
                return True  # No filter, show all rows
            
            # Get the memo for this row
            memo = source_model.get_memo_at_row(source_row)
            if not memo:
                return False
            
            # Search in title, file path, and date
            search_fields = [
                memo.get_display_title().lower(),
                str(memo.file_path).lower() if memo.file_path else "",  # Convert PosixPath to string
                memo.creation_date.strftime("%Y-%m-%d %H:%M").lower(),
                memo.creation_date.strftime("%d-%b-%y").lower(),  # Also search in formatted date
            ]
            
            # Apply the filter - check if any field matches
            pattern_lower = filter_regex.pattern().lower()
            return any(pattern_lower in field for field in search_fields if field)
            
        except Exception as e:
            # Log error but don't crash - show the row in case of error
            logger.warning(f"Error in filterAcceptsRow: {e}")
            return True


class VoiceMemoFileWatcher(QObject):
    """
    File system watcher for automatic Voice Memo refresh.
    
    Uses watchdog to monitor the Voice Memos directory for changes
    and automatically triggers refresh when new recordings are added.
    """
    
    # Signals
    file_changed = Signal(str)  # File path that changed
    refresh_needed = Signal()   # General refresh needed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.observer = None  # Observer instance
        self.watch_path = None  # Currently watched path
        self._event_handler = VoiceMemoEventHandler(self)
    
    def start_watching(self, db_path: str):
        """Start monitoring the Voice Memos directory"""
        if self.observer and self.observer.is_alive():
            self.stop_watching()
        
        # Extract directory from database path
        db_file = Path(db_path)
        if db_file.name == "CloudRecordings.db":
            watch_dir = db_file.parent
        else:
            watch_dir = db_file
        
        self.watch_path = str(watch_dir)
        
        try:
            self.observer = Observer()
            self.observer.schedule(
                self._event_handler,
                self.watch_path,
                recursive=False  # Don't watch subdirectories
            )
            self.observer.start()
            logger.info(f"📁 Started monitoring: {self.watch_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start file watching: {e}")
            self.observer = None
    
    def stop_watching(self):
        """Stop monitoring the directory"""
        try:
            if self.observer and self.observer.is_alive():
                self.observer.stop()
                self.observer.join(timeout=2.0)  # Add timeout
                logger.info(f"📁 Stopped monitoring: {self.watch_path}")
        except Exception as e:
            logger.warning(f"Error stopping file observer: {e}")
        finally:
            self.observer = None
            self.watch_path = None
    
    def is_watching(self) -> bool:
        """Check if currently watching a directory"""
        return self.observer is not None and self.observer.is_alive()


class VoiceMemoEventHandler(FileSystemEventHandler):
    """Event handler for file system changes in Voice Memos directory"""
    
    def __init__(self, watcher: VoiceMemoFileWatcher):
        super().__init__()
        self.watcher = watcher
        # Debounce timer to avoid too frequent refreshes
        self.refresh_timer = QTimer()
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self._emit_refresh)
        
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # Check if this is the CloudRecordings.db file
        if Path(file_path).name == "CloudRecordings.db":
            logger.debug(f"📝 Voice Memos database modified: {file_path}")
            self._schedule_refresh()
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # Check for new voice memo files or database changes
        if file_path.endswith(('.m4a', '.wav', '.mp3')) or Path(file_path).name == "CloudRecordings.db":
            logger.debug(f"📄 New file detected: {file_path}")
            self._schedule_refresh()
    
    def _schedule_refresh(self):
        """Schedule a refresh with debouncing"""
        # Restart timer to debounce multiple rapid changes
        self.refresh_timer.stop()
        self.refresh_timer.start(1000)  # 1 second delay
        
    def _emit_refresh(self):
        """Emit the refresh signal"""
        self.watcher.refresh_needed.emit()


class VoiceMemoLoader(QObject):
    """
    Background worker for loading Voice Memos asynchronously.
    
    This runs the async Voice Memo parsing in a separate thread
    to keep the UI responsive during database operations.
    """
    
    # Signals
    loading_started = Signal()
    loading_progress = Signal(str)  # status message
    loading_finished = Signal(list)  # List[VoiceMemoModel]
    loading_error = Signal(str)  # error message
    
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
    
    def load_voice_memos(self):
        """Load Voice Memos in background thread"""
        try:
            self.loading_started.emit()
            self.loading_progress.emit("Connecting to Voice Memos database...")
            
            # Extract folder path if we got a full database path
            db_path = Path(self.db_path)
            if db_path.name == "CloudRecordings.db":
                # We were passed the full database path, use parent folder
                folder_path = db_path.parent
            else:
                # We were passed a folder path
                folder_path = db_path
            
            # Create parser with folder path (it will append CloudRecordings.db internally)
            parser = VoiceMemoParser(folder_path)
            
            # Run the async function in this thread's event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                self.loading_progress.emit("Fetching Voice Memo records...")
                memos = loop.run_until_complete(parser.load_voice_memos())
                
                self.loading_progress.emit(f"Loaded {len(memos)} Voice Memos successfully")
                self.loading_finished.emit(memos)
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"❌ Failed to load Voice Memos: {e}")
            self.loading_error.emit(str(e))


class VoiceMemoDetailPanel(QWidget):
    """
    Detail panel showing information about the selected Voice Memo.
    
    This panel displays detailed information about the currently selected
    memo, including metadata and transcription status.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._current_memo: Optional[VoiceMemoModel] = None
    
    def _setup_ui(self):
        """Set up the detail panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 8)  # More compact margins
        layout.setSpacing(8)  # Reduced spacing
        
        # Title
        self.title_label = QLabel("Select a Voice Memo")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)
        
        # Metadata group
        metadata_group = QGroupBox("Metadata")
        metadata_layout = QVBoxLayout(metadata_group)
        
        self.date_label = QLabel("Date: -")
        self.duration_label = QLabel("Duration: -")
        self.size_label = QLabel("File Size: -")
        self.path_label = QLabel("File Path: -")
        self.path_label.setWordWrap(True)
        
        metadata_layout.addWidget(self.date_label)
        metadata_layout.addWidget(self.duration_label)
        metadata_layout.addWidget(self.size_label)
        metadata_layout.addWidget(self.path_label)
        
        layout.addWidget(metadata_group)
        
        # Status group
        status_group = QGroupBox("Processing Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Status: -")
        status_font = QFont()
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        
        layout.addWidget(status_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.transcribe_button = QPushButton("Start Transcription")
        self.transcribe_button.setEnabled(False)
        self.transcribe_button.clicked.connect(self._on_transcribe_button_clicked)
        button_layout.addWidget(self.transcribe_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Transcription results (placeholder)
        results_group = QGroupBox("Transcription Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setPlaceholderText("Transcription results will appear here...")
        self.results_text.setMaximumHeight(200)
        
        results_layout.addWidget(self.results_text)
        layout.addWidget(results_group)
        
        layout.addStretch()
    
    def set_memo(self, memo: Optional[VoiceMemoModel], status: VoiceMemoStatus = VoiceMemoStatus.NEW):
        """Update the detail panel with information about the selected memo"""
        self._current_memo = memo
        
        if memo is None:
            self._clear_details()
            return
        
        # Update title
        self.title_label.setText(memo.get_display_title())
        
        # Update metadata
        # Convert UTC to CEST (UTC+2 for summer time) and use consistent format
        utc_time = memo.creation_date
        local_time = utc_time + timedelta(hours=2)
        self.date_label.setText(f"Date: {local_time.strftime('%d-%b-%y %H:%M')} CEST")
        
        if memo.duration:
            minutes = int(memo.duration // 60)
            seconds = int(memo.duration % 60)
            self.duration_label.setText(f"Duration: {minutes}:{seconds:02d} ({memo.duration:.1f} seconds)")
        else:
            self.duration_label.setText("Duration: Unknown")
        
        if memo.file_size:
            if memo.file_size > 1024 * 1024:
                size_mb = memo.file_size / (1024 * 1024)
                size_text = f"File Size: {size_mb:.1f} MB ({memo.file_size:,} bytes)"
            elif memo.file_size > 1024:
                size_kb = memo.file_size / 1024
                size_text = f"File Size: {size_kb:.1f} KB ({memo.file_size:,} bytes)"
            else:
                size_text = f"File Size: {memo.file_size} bytes"
            self.size_label.setText(size_text)
        else:
            self.size_label.setText("File Size: Unknown")
        
        if memo.file_path:
            file_exists = "✅" if memo.file_exists else "❌"
            self.path_label.setText(f"File Path: {file_exists} {memo.file_path}")
        else:
            self.path_label.setText("File Path: Unknown")
        
        # Update status
        self._update_status(status)
        
        # Enable transcribe button if memo is ready
        self.transcribe_button.setEnabled(status == VoiceMemoStatus.NEW and memo.file_exists)
        
        # Load existing transcription if available
        self._load_existing_transcription(memo)
    
    def _clear_details(self):
        """Clear all detail information"""
        self.title_label.setText("Select a Voice Memo")
        self.date_label.setText("Date: -")
        self.duration_label.setText("Duration: -")
        self.size_label.setText("File Size: -")
        self.path_label.setText("File Path: -")
        self.status_label.setText("Status: -")
        self.progress_bar.setVisible(False)
        self.transcribe_button.setEnabled(False)
        self.results_text.clear()
    
    def _update_status(self, status: VoiceMemoStatus):
        """Update the status display"""
        status_texts = {
            VoiceMemoStatus.NEW: "📄 Ready for transcription",
            VoiceMemoStatus.TRANSCRIBING: "🔄 Transcribing...",
            VoiceMemoStatus.TRANSCRIBED: "✅ Transcription complete",
            VoiceMemoStatus.ERROR: "❌ Error occurred",
            VoiceMemoStatus.PROCESSING: "⚙️ Processing..."
        }
        
        self.status_label.setText(f"Status: {status_texts.get(status, status.value)}")
        
        # Show/hide progress bar for active states
        show_progress = status in [VoiceMemoStatus.TRANSCRIBING, VoiceMemoStatus.PROCESSING]
        self.progress_bar.setVisible(show_progress)
        
        if show_progress:
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
    
    def _load_existing_transcription(self, memo: VoiceMemoModel):
        """Load existing transcription text if available"""
        try:
            # Check if transcription file exists based on memo UUID
            transcription_dir = Path.home() / "Library" / "Application Support" / "AudioTransLocal" / "transcriptions"
            transcription_file = transcription_dir / f"{memo.uuid}.txt"
            
            if transcription_file.exists():
                with open(transcription_file, 'r', encoding='utf-8') as f:
                    transcription_text = f.read()
                
                self.results_text.setPlainText(transcription_text)
                logger.info(f"📄 Loaded existing transcription: {len(transcription_text)} characters")
                
                # Update memo status to transcribed and notify parent view
                memo.transcription_status = "transcribed"
                memo.transcription_file_path = transcription_file
                
                # Find parent view and update status
                parent = self.parent()
                while parent and not hasattr(parent, 'state_manager'):
                    parent = parent.parent()
                if parent and hasattr(parent, 'state_manager'):
                    from app.services.voice_memo_model import VoiceMemoStatus
                    parent.state_manager.set_status(memo.uuid, VoiceMemoStatus.TRANSCRIBED)
                    
            else:
                self.results_text.clear()
                self.results_text.setPlaceholderText("Transcription results will appear here...")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load existing transcription: {e}")
            self.results_text.clear()
            self.results_text.setPlaceholderText("Transcription results will appear here...")
    
    def _on_transcribe_button_clicked(self):
        """Handle transcribe button click from detail panel"""
        if self._current_memo:
            # Emit signal to parent view to handle transcription
            parent = self.parent()
            while parent and not hasattr(parent, '_on_transcribe_requested'):
                parent = parent.parent()
            if parent and hasattr(parent, '_on_transcribe_requested'):
                parent._on_transcribe_requested(self._current_memo.uuid)
        else:
            QMessageBox.warning(
                self,
                "No Memo Selected", 
                "Please select a voice memo to transcribe."
            )


class VoiceMemoView(QWidget):
    """
    Main Voice Memo Browse View widget.
    
    This is the primary UI component that displays the list of Voice Memos
    using a QTableView with efficient model/view architecture and filtering.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize state management
        self.state_manager = VoiceMemoStateManager(self)
        self.table_model = VoiceMemoTableModel(self.state_manager, self)
        self.status_delegate = VoiceMemoStatusDelegate(self)
        
        # Initialize transcription components (Epic 3)
        self.thread_pool = QThreadPool()
        self.actions_delegate = TranscriptionActionsDelegate(self)
        self.transcription_status_delegate = TranscriptionStatusDelegate(self)
        
        # Initialize model manager for centralized model path management
        self.model_manager = WhisperModelManager(self)
        
        # Connect transcription signals
        self.actions_delegate.transcribe_requested.connect(self._on_transcribe_requested)
        self.actions_delegate.view_transcription_requested.connect(self._on_view_transcription_requested)
        
        # Initialize proxy model for filtering
        self.proxy_model = VoiceMemoFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.table_model)
        
        # Set up default sorting: newest on top (descending by date)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setDynamicSortFilter(True)
        
        # Initialize file watcher
        self.file_watcher = VoiceMemoFileWatcher(self)
        self.file_watcher.refresh_needed.connect(self._on_auto_refresh)
        
        # Track current database path for refresh and monitoring
        self.current_db_path = None
        
        # UI setup
        self._setup_ui()
        self._connect_signals()
        
        # Background loading
        self._loader_thread = None
        self._loader = None
        
        logger.info("✅ Voice Memo View initialized")
    
    def _setup_ui(self):
        """Set up the main UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 8)  # Further reduced top margin
        layout.setSpacing(4)  # Minimal spacing between elements
        
        # Header with title and controls
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Voice Memos")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # Status label (moved from below to header)
        self.status_label = QLabel("Ready to load Voice Memos")
        self.status_label.setStyleSheet("QLabel { color: #666; font-size: 12px; margin-left: 16px; }")
        header_layout.addWidget(self.status_label)
        
        header_layout.addStretch()
        
        # Search bar with magnifying glass icon
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 8, 0)  # Small margin before refresh button
        
        search_label = QLabel("🔍")  # Magnifying glass emoji
        search_label.setStyleSheet("QLabel { font-size: 16px; }")
        search_layout.addWidget(search_label)
        
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search voice memos by title, date, or path...")
        self.search_field.setMaximumWidth(250)  # Slightly wider for better UX
        self.search_field.setStyleSheet("""
            QLineEdit {
                padding: 6px 12px;
                border: 1px solid #ccc;
                border-radius: 6px;
                font-size: 13px;
                background-color: #fafafa;
            }
            QLineEdit:focus {
                border-color: #007acc;
                background-color: white;
            }
            QLineEdit:hover {
                border-color: #999;
            }
        """)
        search_layout.addWidget(self.search_field)
        
        # Clear search button (only visible when there's text)
        self.clear_search_btn = QPushButton("✕")
        self.clear_search_btn.setFixedSize(24, 24)
        self.clear_search_btn.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 12px;
                background-color: #ddd;
                color: #666;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ccc;
            }
            QPushButton:pressed {
                background-color: #bbb;
            }
        """)
        self.clear_search_btn.setVisible(False)
        self.clear_search_btn.clicked.connect(self._clear_search)
        search_layout.addWidget(self.clear_search_btn)
        
        header_layout.addLayout(search_layout)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_memos)
        header_layout.addWidget(self.refresh_button)
        
        layout.addLayout(header_layout)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(3)  # Even thinner progress bar
        layout.addWidget(self.progress_bar)
        
        # Main content splitter (no extra spacing)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setContentsMargins(0, 0, 0, 0)  # No margins on splitter
        
        # Table view (left side) - now uses proxy model
        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)  # Use proxy model instead of table_model
        
        # Set up custom delegates for transcription features
        self.table_view.setItemDelegateForColumn(
            VoiceMemoTableModel.COL_STATUS, 
            self.transcription_status_delegate
        )
        self.table_view.setItemDelegateForColumn(
            VoiceMemoTableModel.COL_ACTIONS,
            self.actions_delegate
        )
        
        # Configure table appearance
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.setSortingEnabled(True)  # Enable column sorting
        
        # Set column widths
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(VoiceMemoTableModel.COL_TITLE, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(VoiceMemoTableModel.COL_DATE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(VoiceMemoTableModel.COL_DURATION, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(VoiceMemoTableModel.COL_SIZE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(VoiceMemoTableModel.COL_STATUS, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(VoiceMemoTableModel.COL_ACTIONS, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(VoiceMemoTableModel.COL_STATUS, 180)
        header.resizeSection(VoiceMemoTableModel.COL_ACTIONS, 140)
        
        # Set default sort (most recent first)
        self.table_view.sortByColumn(VoiceMemoTableModel.COL_DATE, Qt.DescendingOrder)
        
        # Detail panel (right side)
        self.detail_panel = VoiceMemoDetailPanel()
        
        # Add to splitter
        splitter.addWidget(self.table_view)
        splitter.addWidget(self.detail_panel)
        splitter.setSizes([600, 400])  # Initial sizes
        
        layout.addWidget(splitter)
    
    def _connect_signals(self):
        """Connect UI signals"""
        # Table selection changes
        selection = self.table_view.selectionModel()
        selection.currentRowChanged.connect(self._on_selection_changed)
        
        # State manager signals
        self.state_manager.status_changed.connect(self._on_status_changed)
        
        # Search field changes
        self.search_field.textChanged.connect(self._on_search_changed)
    
    def _on_search_changed(self, text: str):
        """
        Handle search field changes with robust, professional filtering.
        Uses regex escaping to prevent crashes from special characters.
        """
        try:
            # Import regex module for safe escaping
            import re
            
            # 1. Escape special characters to prevent regex errors (e.g., from '(' or '*')
            safe_text = re.escape(text.strip()) if text.strip() else ""
            
            # 2. Set the escaped text as a regular expression on our custom proxy model
            self.proxy_model.setFilterRegularExpression(safe_text)
            
            # Show/hide clear button based on whether there's text
            self.clear_search_btn.setVisible(bool(text.strip()))
            
            # Update status label with search results
            if text.strip():
                visible_count = self.proxy_model.rowCount()
                total_count = self.table_model.rowCount()
                self.status_label.setText(f"🔍 Showing {visible_count} of {total_count} Voice Memos")
            else:
                total_count = self.table_model.rowCount()
                self.status_label.setText(f"✅ Loaded {total_count} Voice Memos")
                
        except Exception as e:
            logger.error(f"Error in search handling: {e}")
            # Fallback to showing all items if search fails
            self.proxy_model.setFilterRegularExpression("")
            self.status_label.setText("⚠️ Search error - showing all Voice Memos")
    
    def _clear_search(self):
        """Clear the search field"""
        self.search_field.clear()  # This will trigger _on_search_changed with empty text
    
    def _on_auto_refresh(self):
        """Handle automatic refresh triggered by file watcher"""
        logger.info("🔄 Auto-refresh triggered by file system changes")
        self.refresh_memos()
    
    def _on_selection_changed(self, current, previous):
        """Handle table selection changes"""
        if current.isValid():
            # Convert proxy index to source index
            source_index = self.proxy_model.mapToSource(current)
            memo = self.table_model.get_memo_at_row(source_index.row())
            if memo:
                # Get memo ID and current status
                memo_id = self.table_model._get_memo_id(memo)
                status = self.state_manager.get_status(memo_id)
                
                # Update detail panel
                self.detail_panel.set_memo(memo, status)
                
                logger.debug(f"📋 Selected memo: {memo.get_display_title()}")
        else:
            self.detail_panel.set_memo(None)
    
    def _on_status_changed(self, memo_id: str, new_status: VoiceMemoStatus):
        """Handle status changes from state manager"""
        # If the changed memo is currently selected, update detail panel
        current = self.table_view.selectionModel().currentIndex()
        if current.isValid():
            # Convert proxy index to source index
            source_index = self.proxy_model.mapToSource(current)
            memo = self.table_model.get_memo_at_row(source_index.row())
            if memo and self.table_model._get_memo_id(memo) == memo_id:
                self.detail_panel.set_memo(memo, new_status)
    
    def load_voice_memos(self, db_path: str):
        """Load Voice Memos from database path"""
        if self._loader_thread and self._loader_thread.isRunning():
            logger.warning("⚠️ Voice Memo loading already in progress")
            return
        
        # Store the database path for refresh and monitoring
        self.current_db_path = db_path
        
        # Create background loader
        self._loader_thread = QThread()
        self._loader = VoiceMemoLoader(db_path)
        self._loader.moveToThread(self._loader_thread)
        
        # Connect signals
        self._loader.loading_started.connect(self._on_loading_started)
        self._loader.loading_progress.connect(self._on_loading_progress)
        self._loader.loading_finished.connect(self._on_loading_finished)
        self._loader.loading_error.connect(self._on_loading_error)
        
        # Start loading
        self._loader_thread.started.connect(self._loader.load_voice_memos)
        self._loader_thread.start()
        
        logger.info(f"🔄 Started loading Voice Memos from: {db_path}")
    
    def _on_loading_started(self):
        """Handle loading started"""
        self.refresh_button.setEnabled(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(True)
        self.status_label.setText("Loading Voice Memos...")
    
    def _on_loading_progress(self, message: str):
        """Handle loading progress updates"""
        self.status_label.setText(message)
    
    def _on_loading_finished(self, memos: List[VoiceMemoModel]):
        """Handle loading completion"""
        self.table_model.set_memos(memos)
        
        # Apply default sorting (newest first) - do this after setting data
        QTimer.singleShot(100, lambda: self.table_view.sortByColumn(VoiceMemoTableModel.COL_DATE, Qt.DescendingOrder))
        
        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)
        
        # Check if we got zero memos from a system location due to permission issues
        if len(memos) == 0 and self.current_db_path:
            # Check if this looks like a system database path that might have failed
            db_path_str = str(self.current_db_path)
            if ("Group Containers" in db_path_str and "VoiceMemos" in db_path_str) or "Library" in db_path_str:
                # This is likely a permission issue, try fallback
                fallback_path = "/Users/lopezm52/Documents/VisualCode/Test/CloudRecordings.db"
                if Path(fallback_path).exists() and db_path_str != fallback_path:
                    logger.info(f"🔄 Got 0 memos from system location - trying fallback: {fallback_path}")
                    self.status_label.setText("🔄 Trying test database...")
                    
                    # Clean up current thread first to avoid conflicts
                    if self._loader_thread:
                        self._loader_thread.quit()
                        self._loader_thread.wait()
                        self._loader_thread = None
                        self._loader = None
                    
                    def load_fallback():
                        self.load_voice_memos(fallback_path)
                    
                    QTimer.singleShot(500, load_fallback)
                    return
        
        # Update status based on current search
        search_text = self.search_field.text()
        if search_text:
            visible_count = self.proxy_model.rowCount()
            self.status_label.setText(f"🔍 Showing {visible_count} of {len(memos)} Voice Memos")
        else:
            if len(memos) == 0:
                self.status_label.setText("❌ No Voice Memos found")
            else:
                self.status_label.setText(f"✅ Loaded {len(memos)} Voice Memos")
        
        # Start file monitoring if we have a valid database path and successful load
        if self.current_db_path and Path(self.current_db_path).exists() and len(memos) > 0:
            self.file_watcher.start_watching(self.current_db_path)
        
        # Sort by date column (newest first) after loading data  
        if len(memos) > 0:
            date_column = VoiceMemoTableModel.COL_DATE
            self.table_view.sortByColumn(date_column, Qt.DescendingOrder)
        
        # Clean up thread
        if self._loader_thread:
            self._loader_thread.quit()
            self._loader_thread.wait()
            self._loader_thread = None
            self._loader = None
        
        # Check for existing transcriptions and update statuses
        self._check_existing_transcriptions(memos)
        
        logger.info(f"✅ Successfully loaded {len(memos)} Voice Memos")
    
    def _check_existing_transcriptions(self, memos: List[VoiceMemoModel]):
        """Check for existing transcription files and update memo statuses"""
        transcription_dir = Path.home() / "Library" / "Application Support" / "AudioTransLocal" / "transcriptions"
        
        if not transcription_dir.exists():
            return
        
        transcribed_count = 0
        for memo in memos:
            transcription_file = transcription_dir / f"{memo.uuid}.txt"
            if transcription_file.exists():
                # Update memo status
                memo.transcription_status = "transcribed"
                memo.transcription_file_path = transcription_file
                
                # Update state manager
                from app.services.voice_memo_model import VoiceMemoStatus
                self.state_manager.set_status(memo.uuid, VoiceMemoStatus.TRANSCRIBED)
                transcribed_count += 1
        
        if transcribed_count > 0:
            logger.info(f"📄 Found {transcribed_count} existing transcriptions")
    
    def _on_loading_error(self, error_message: str):
        """Handle loading errors"""
        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)
        
        # Try fallback to test database if system database fails
        if "authorization denied" in error_message.lower():
            fallback_path = "/Users/lopezm52/Documents/VisualCode/Test/CloudRecordings.db"
            if Path(fallback_path).exists() and str(self.current_db_path) != fallback_path:
                logger.info(f"🔄 Authorization denied - attempting fallback to test database: {fallback_path}")
                self.status_label.setText("🔄 Trying test database...")
                
                # Use QTimer to avoid recursive loading issues
                def load_fallback():
                    self.load_voice_memos(fallback_path)
                
                QTimer.singleShot(500, load_fallback)
                return
        
        # If we get here, no fallback is available or fallback also failed
        self.status_label.setText(f"❌ Error: {error_message}")
        
        # Show error dialog
        QMessageBox.critical(
            self,
            "Voice Memos Loading Error",
            f"Failed to load Voice Memos:\n\n{error_message}"
        )
        
        # Clean up thread
        if self._loader_thread:
            self._loader_thread.quit()
            self._loader_thread.wait()
            self._loader_thread = None
            self._loader = None
        
        logger.error(f"❌ Voice Memo loading failed: {error_message}")
    
    def refresh_memos(self):
        """Refresh the Voice Memos list"""
        if self.current_db_path and Path(self.current_db_path).exists():
            self.load_voice_memos(self.current_db_path)
        else:
            # Fallback to test database path
            fallback_path = "/Users/lopezm52/Documents/VisualCode/Test/CloudRecordings.db"
            if Path(fallback_path).exists():
                self.load_voice_memos(fallback_path)
            else:
                self.status_label.setText("❌ Voice Memos database not found")
                QMessageBox.warning(
                    self,
                    "Database Not Found",
                    "Voice Memos database not found.\n\nPlease check your settings or ensure Voice Memos are available."
                )
    
    def get_selected_memo(self) -> Optional[VoiceMemoModel]:
        """Get the currently selected Voice Memo"""
        current = self.table_view.selectionModel().currentIndex()
        if current.isValid():
            # Convert proxy index to source index
            source_index = self.proxy_model.mapToSource(current)
            return self.table_model.get_memo_at_row(source_index.row())
        return None
    
    def set_memo_status(self, memo: VoiceMemoModel, status: VoiceMemoStatus):
        """Set the status of a specific memo"""
        memo_id = self.table_model._get_memo_id(memo)
        self.state_manager.set_status(memo_id, status)
    
    # ============================================================================
    # Epic 3: Transcription Methods
    # ============================================================================
    
    # Transcription workflow methods (Epic 3)
    
    def _on_transcribe_requested(self, memo_id: str):
        """Handle transcription request from Actions column"""
        # Get current model and validate
        current_model = self.model_manager.get_current_model()
        if not current_model:
            QMessageBox.warning(
                self,
                "Whisper Model Error",
                "No Whisper model selected.\n\nPlease select a model in settings."
            )
            return
            
        # Check if model is downloaded
        if not self.model_manager.is_model_downloaded(current_model):
            QMessageBox.warning(
                self,
                "Whisper Model Error", 
                f"Model '{current_model}' is not downloaded.\n\nPlease download the model first."
            )
            return
        
        # Get model info for path
        model_info = self.model_manager.get_model_info(current_model)
        if not model_info:
            QMessageBox.warning(
                self,
                "Whisper Model Error",
                f"Invalid model configuration for '{current_model}'."
            )
            return
            
        model_path = self.model_manager.get_models_directory() / model_info.filename
        logger.info(f"✅ Using Whisper model: {model_path}")
        
        # Find the memo
        memo = self._find_memo_by_id(memo_id)
        if not memo:
            logger.error(f"❌ Memo not found for transcription: {memo_id}")
            return
        
        # Validate audio file exists
        if not memo.file_path or not Path(memo.file_path).exists():
            QMessageBox.warning(
                self,
                "Audio File Not Found",
                f"Audio file not found: {memo.file_path}"
            )
            return
        
        logger.info(f"🎤 Starting transcription for memo: {memo_id}")
        
        # Create and configure transcription worker
        try:
            worker = TranscriptionWorker(memo, model_path)
            
            # Connect worker signals
            worker.signals.started.connect(self._on_transcription_started)
            worker.signals.progress.connect(self._on_transcription_progress)
            worker.signals.finished.connect(self._on_transcription_finished)
            worker.signals.error.connect(self._on_transcription_error)
            
            # Submit to thread pool
            self.thread_pool.start(worker)
            
        except Exception as e:
            error_msg = f"Failed to start transcription: {e}"
            logger.error(f"❌ {error_msg}")
            QMessageBox.critical(self, "Transcription Error", error_msg)
    
    def _on_view_transcription_requested(self, memo_id: str):
        """Handle view transcription request from Actions column"""
        memo = self._find_memo_by_id(memo_id)
        if not memo:
            logger.error(f"❌ Memo not found for viewing: {memo_id}")
            return
        
        if not hasattr(memo, 'transcription_file_path') or not memo.transcription_file_path:
            QMessageBox.warning(
                self,
                "No Transcription",
                "No transcription file found for this memo."
            )
            return
        
        # Open transcription viewer dialog
        self._show_transcription_dialog(memo)
    
    def _on_transcription_started(self, memo_id: str):
        """Handle transcription started signal"""
        memo = self._find_memo_by_id(memo_id)
        if memo:
            memo.transcription_status = "transcribing"
            memo.transcription_progress = "Starting..."
            self._refresh_memo_display(memo)
            logger.info(f"🔄 Transcription started: {memo_id}")
    
    def _on_transcription_progress(self, memo_id: str, message: str):
        """Handle transcription progress signal"""
        memo = self._find_memo_by_id(memo_id)
        if memo:
            memo.transcription_progress = message
            self._refresh_memo_display(memo)
            logger.info(f"📊 Transcription progress {memo_id}: {message}")
    
    def _on_transcription_finished(self, memo_id: str, file_path: str):
        """Handle transcription finished signal"""
        memo = self._find_memo_by_id(memo_id)
        if memo:
            memo.transcription_status = "transcribed"
            memo.transcription_file_path = Path(file_path)
            memo.transcription_progress = None
            memo.transcription_error = None
            self._refresh_memo_display(memo)
            
            # If this memo is currently selected, update the detail panel with transcription
            current = self.table_view.selectionModel().currentIndex()
            if current.isValid():
                source_index = self.proxy_model.mapToSource(current)
                selected_memo = self.table_model.get_memo_at_row(source_index.row())
                if selected_memo and selected_memo.uuid == memo_id:
                    self._load_transcription_in_detail_panel(memo)
            
            logger.info(f"✅ Transcription completed: {memo_id} -> {file_path}")
    
    def _on_transcription_error(self, memo_id: str, error_message: str):
        """Handle transcription error signal with user notification"""
        memo = self._find_memo_by_id(memo_id)
        if memo:
            memo.transcription_status = "error"
            memo.transcription_error = error_message
            memo.transcription_progress = None
            self._refresh_memo_display(memo)
            logger.error(f"❌ Transcription error {memo_id}: {error_message}")
            
            # Show user-friendly error notification
            QMessageBox.warning(
                self,
                "Transcription Failed",
                f"Failed to transcribe '{memo.title}':\n\n{error_message}\n\n"
                f"You can try transcribing again or check the audio file."
            )
    
    def _find_memo_by_id(self, memo_id: str) -> Optional[VoiceMemoModel]:
        """Find a memo by its ID"""
        for memo in self.table_model._memos:
            if memo.uuid == memo_id:
                return memo
        return None
    
    def _refresh_memo_display(self, memo: VoiceMemoModel):
        """Refresh the display for a specific memo"""
        # Find the row index
        for row in range(self.table_model.rowCount()):
            if self.table_model._memos[row].uuid == memo.uuid:
                # Emit data changed for the entire row
                top_left = self.table_model.index(row, 0)
                bottom_right = self.table_model.index(row, self.table_model.columnCount() - 1)
                self.table_model.dataChanged.emit(top_left, bottom_right)
                break
    
    def _show_transcription_dialog(self, memo: VoiceMemoModel):
        """Show the transcription in a dialog window"""
        try:
            with open(memo.transcription_file_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
            
            dialog = TranscriptionViewDialog(memo, transcript_text, self)
            dialog.exec()
            
        except Exception as e:
            error_msg = f"Failed to open transcription file: {e}"
            logger.error(f"❌ {error_msg}")
            QMessageBox.critical(self, "File Error", error_msg)
    
    def _load_transcription_in_detail_panel(self, memo: VoiceMemoModel):
        """Load transcription text into the detail panel results area"""
        try:
            if memo.transcription_file_path and memo.transcription_file_path.exists():
                with open(memo.transcription_file_path, 'r', encoding='utf-8') as f:
                    transcription_text = f.read()
                
                # Update the detail panel's results text area
                self.detail_panel.results_text.setPlainText(transcription_text)
                logger.info(f"📄 Loaded transcription text in detail panel: {len(transcription_text)} characters")
            else:
                logger.warning(f"⚠️ Transcription file not found: {memo.transcription_file_path}")
        except Exception as e:
            error_msg = f"Failed to load transcription text: {e}"
            logger.error(f"❌ {error_msg}")
            self.detail_panel.results_text.setPlainText(f"Error loading transcription: {error_msg}")
    
    def closeEvent(self, event):
        """Clean up resources when the widget is closed"""
        # Stop file watching
        try:
            if self.file_watcher:
                self.file_watcher.stop_watching()
        except Exception as e:
            logger.warning(f"Error stopping file watcher: {e}")
        
        # Stop any running loader thread
        if self._loader_thread and self._loader_thread.isRunning():
            self._loader_thread.quit()
            self._loader_thread.wait()
        
        super().closeEvent(event)
    
    def __del__(self):
        """Destructor - ensure file watcher is stopped"""
        try:
            if hasattr(self, 'file_watcher') and self.file_watcher:
                self.file_watcher.stop_watching()
        except Exception:
            pass  # Ignore errors during cleanup
