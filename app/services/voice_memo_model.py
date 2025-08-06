#!/usr/bin/env python3
"""
Voice Memo Table Model & State Management for AudioTransLocal

This module implements the QAbstractTableModel for efficient display of Voice Memos
using Qt's Model/View architecture with centralized state management.

Epic 2: Voice Memo Browse & Management
US2: UI View & State Management
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from enum import Enum
import logging

from PySide6.QtCore import (
    QAbstractTableModel, QModelIndex, Qt, Signal, QTimer, QObject
)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QFont
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QWidget, QStyle

from app.services.voice_memo_parser import VoiceMemoModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceMemoStatus(Enum):
    """Enumeration of possible Voice Memo processing states"""
    NEW = "new"
    TRANSCRIBING = "transcribing"
    TRANSCRIBED = "transcribed"
    ERROR = "error"
    PROCESSING = "processing"


class VoiceMemoStateManager(QObject):
    """
    Centralized state management for Voice Memo processing status.
    
    This class maintains a dictionary mapping memo UUIDs to their current
    processing state and emits signals when states change.
    """
    
    # Signal emitted when a memo's status changes
    status_changed = Signal(str, VoiceMemoStatus)  # memo_id, new_status
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_map: Dict[str, VoiceMemoStatus] = {}
        logger.info("✅ Voice Memo State Manager initialized")
    
    def get_status(self, memo_id: str) -> VoiceMemoStatus:
        """Get the current status of a memo"""
        return self._status_map.get(memo_id, VoiceMemoStatus.NEW)
    
    def set_status(self, memo_id: str, status: VoiceMemoStatus) -> None:
        """Set the status of a memo and emit change signal"""
        old_status = self._status_map.get(memo_id, VoiceMemoStatus.NEW)
        
        if old_status != status:
            self._status_map[memo_id] = status
            logger.debug(f"📊 Status changed for {memo_id}: {old_status.value} → {status.value}")
            self.status_changed.emit(memo_id, status)
    
    def get_all_statuses(self) -> Dict[str, VoiceMemoStatus]:
        """Get a copy of all current statuses"""
        return self._status_map.copy()
    
    def clear_all_statuses(self) -> None:
        """Clear all status information"""
        self._status_map.clear()
        logger.info("🗑️  All memo statuses cleared")


class VoiceMemoTableModel(QAbstractTableModel):
    """
    QAbstractTableModel for efficient display of Voice Memos.
    
    This model implements Qt's Model/View architecture for memory-efficient
    display of potentially large Voice Memo datasets.
    """
    
    # Column indices
    COL_TITLE = 0
    COL_DATE = 1
    COL_DURATION = 2
    COL_SIZE = 3
    COL_STATUS = 4
    COL_ACTIONS = 5
    
    # Column headers
    HEADERS = [
        "Title",
        "Date Created", 
        "Duration",
        "File Size",
        "Status",
        "Actions"
    ]
    
    def __init__(self, state_manager: VoiceMemoStateManager, parent=None):
        super().__init__(parent)
        self._memos: List[VoiceMemoModel] = []
        self._state_manager = state_manager
        
        # Connect to state changes
        self._state_manager.status_changed.connect(self._on_status_changed)
        
        logger.info("✅ Voice Memo Table Model initialized")
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """Return the number of Voice Memos"""
        return len(self._memos)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        """Return the number of columns"""
        return len(self.HEADERS)
    
    def headerData(self, section: int, orientation: Qt.Orientation, role: int) -> Any:
        """Return header data for the table"""
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            if 0 <= section < len(self.HEADERS):
                return self.HEADERS[section]
        return None
    
    def data(self, index: QModelIndex, role: int) -> Any:
        """Return data for the given index and role"""
        if not index.isValid() or not (0 <= index.row() < len(self._memos)):
            return None
        
        memo = self._memos[index.row()]
        column = index.column()
        
        if role == Qt.ItemDataRole.DisplayRole:
            return self._get_display_data(memo, column)
        elif role == Qt.ItemDataRole.ToolTipRole:
            return self._get_tooltip_data(memo, column)
        elif role == Qt.ItemDataRole.UserRole:
            # Return the memo object itself for custom delegates
            return memo
        elif role == Qt.ItemDataRole.UserRole + 1:
            # Return the status for this memo
            memo_id = self._get_memo_id(memo)
            return self._state_manager.get_status(memo_id)
        
        return None
    
    def _get_display_data(self, memo: VoiceMemoModel, column: int) -> str:
        """Get display text for a memo and column"""
        if column == self.COL_TITLE:
            # Use the actual user-visible title (from ZENCRYPTEDTITLE)
            return memo.get_display_title()
        
        elif column == self.COL_DATE:
            # Convert UTC time to CET/CEST (Central European Time)
            # CET is UTC+1, CEST (summer time) is UTC+2
            # Since it's August 2025, we're in summer time (CEST = UTC+2)
            utc_time = memo.creation_date
            local_time = utc_time + timedelta(hours=2)  # Add 2 hours for CEST
            
            # Format as DD-MMM-YY HH:MM
            return local_time.strftime("%d-%b-%y %H:%M")
        
        elif column == self.COL_DURATION:
            if memo.duration:
                minutes = int(memo.duration // 60)
                seconds = int(memo.duration % 60)
                return f"{minutes}:{seconds:02d}"
            return "Unknown"
        
        elif column == self.COL_SIZE:
            if memo.file_size:
                if memo.file_size > 1024 * 1024:
                    size_mb = memo.file_size / (1024 * 1024)
                    return f"{size_mb:.1f} MB"
                elif memo.file_size > 1024:
                    size_kb = memo.file_size / 1024
                    return f"{size_kb:.1f} KB"
                else:
                    return f"{memo.file_size} B"
            return "Unknown"
        
        elif column == self.COL_STATUS:
            # Show transcription status and progress
            if hasattr(memo, 'transcription_status'):
                status = memo.transcription_status
                if status == "new":
                    return "Ready"
                elif status == "transcribing":
                    if hasattr(memo, 'transcription_progress') and memo.transcription_progress:
                        return memo.transcription_progress
                    return "Transcribing..."
                elif status == "transcribed":
                    return "✅ Transcribed"
                elif status == "error":
                    return "❌ Error"
                else:
                    return status.title()
            else:
                # Fallback to state manager
                memo_id = self._get_memo_id(memo)
                status = self._state_manager.get_status(memo_id)
                return status.value.replace('_', ' ').title()
        
        elif column == self.COL_ACTIONS:
            # Actions column shows buttons - handled by custom delegate
            return ""
        
        return ""
    
    def _get_tooltip_data(self, memo: VoiceMemoModel, column: int) -> str:
        """Get tooltip text for a memo and column"""
        if column == self.COL_TITLE:
            tooltip_parts = [f"Title: {memo.get_display_title()}"]
            if memo.file_path:
                tooltip_parts.append(f"File: {memo.file_path}")
            if not memo.file_exists:
                tooltip_parts.append("⚠️ Audio file not found on disk")
            return "\n".join(tooltip_parts)
        
        elif column == self.COL_DATE:
            # Convert UTC to CEST and show detailed date for tooltip
            utc_time = memo.creation_date
            local_time = utc_time + timedelta(hours=2)  # Add 2 hours for CEST
            return f"Created: {local_time.strftime('%A, %d %B %Y at %H:%M:%S')} CEST"
        
        elif column == self.COL_DURATION:
            if memo.duration:
                return f"Duration: {memo.duration:.1f} seconds"
            return "Duration unknown"
        
        elif column == self.COL_SIZE:
            if memo.file_size:
                return f"File size: {memo.file_size:,} bytes"
            return "File size unknown"
        
        elif column == self.COL_STATUS:
            memo_id = self._get_memo_id(memo)
            status = self._state_manager.get_status(memo_id)
            status_descriptions = {
                VoiceMemoStatus.NEW: "Ready for transcription",
                VoiceMemoStatus.TRANSCRIBING: "Currently being transcribed",
                VoiceMemoStatus.TRANSCRIBED: "Transcription completed",
                VoiceMemoStatus.ERROR: "An error occurred during processing",
                VoiceMemoStatus.PROCESSING: "Processing in progress"
            }
            return status_descriptions.get(status, "Unknown status")
        
        return ""
    
    def _get_memo_id(self, memo: VoiceMemoModel) -> str:
        """Get a unique ID for a memo (using UUID or fallback)"""
        # Use the UUID from the database, or create one from creation date + title
        if hasattr(memo, 'uuid') and memo.uuid:
            return memo.uuid
        
        # Fallback: create ID from creation date and title
        date_str = memo.creation_date.isoformat()
        title_hash = hash(memo.get_display_title())
        return f"{date_str}_{title_hash}"
    
    def _on_status_changed(self, memo_id: str, new_status: VoiceMemoStatus) -> None:
        """Handle status change signals by updating the appropriate table row"""
        # Find the row for this memo
        for row, memo in enumerate(self._memos):
            if self._get_memo_id(memo) == memo_id:
                # Emit dataChanged signal for the status column only
                status_index = self.index(row, self.COL_STATUS)
                self.dataChanged.emit(status_index, status_index, [Qt.ItemDataRole.DisplayRole])
                logger.debug(f"🔄 Updated status display for row {row}")
                break
    
    def set_memos(self, memos: List[VoiceMemoModel]) -> None:
        """Set the list of memos to display"""
        self.beginResetModel()
        
        # Sort memos by creation date (newest first)
        self._memos = sorted(memos, key=lambda memo: memo.creation_date, reverse=True)
        
        # Initialize all memos as "NEW" status
        for memo in self._memos:
            memo_id = self._get_memo_id(memo)
            if self._state_manager.get_status(memo_id) == VoiceMemoStatus.NEW:
                # Only set if not already set (preserve existing statuses)
                self._state_manager.set_status(memo_id, VoiceMemoStatus.NEW)
        
        self.endResetModel()
        logger.info(f"📊 Model updated with {len(self._memos)} Voice Memos (sorted by date)")
    
    def get_memo_at_row(self, row: int) -> Optional[VoiceMemoModel]:
        """Get the memo at the specified row"""
        if 0 <= row < len(self._memos):
            return self._memos[row]
        return None
    
    def refresh_memo_statuses(self) -> None:
        """Refresh the display of all memo statuses"""
        if self._memos:
            top_left = self.index(0, self.COL_STATUS)
            bottom_right = self.index(len(self._memos) - 1, self.COL_STATUS)
            self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.DisplayRole])
            logger.debug("🔄 Refreshed all memo status displays")


class VoiceMemoStatusDelegate(QStyledItemDelegate):
    """
    Custom delegate for rendering Voice Memo status with icons.
    
    This delegate renders status as icons instead of text for better
    visual representation and native macOS aesthetics.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_icons = self._create_status_icons()
        logger.info("✅ Voice Memo Status Delegate initialized")
    
    def _create_status_icons(self) -> Dict[VoiceMemoStatus, QIcon]:
        """Create status icons (placeholder implementation)"""
        # TODO: Replace with actual SF Symbols or high-quality icons
        icons = {}
        
        # For now, create simple colored circles as placeholders
        for status in VoiceMemoStatus:
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Choose color based on status
            if status == VoiceMemoStatus.NEW:
                painter.setBrush(Qt.GlobalColor.lightGray)
            elif status == VoiceMemoStatus.TRANSCRIBING:
                painter.setBrush(Qt.GlobalColor.blue)
            elif status == VoiceMemoStatus.TRANSCRIBED:
                painter.setBrush(Qt.GlobalColor.green)
            elif status == VoiceMemoStatus.ERROR:
                painter.setBrush(Qt.GlobalColor.red)
            elif status == VoiceMemoStatus.PROCESSING:
                painter.setBrush(Qt.GlobalColor.yellow)
            
            painter.drawEllipse(2, 2, 12, 12)
            painter.end()
            
            icons[status] = QIcon(pixmap)
        
        return icons
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Custom paint method for status column"""
        if index.column() == VoiceMemoTableModel.COL_STATUS:
            # Get the status from the model
            status = index.data(Qt.ItemDataRole.UserRole + 1)
            
            if isinstance(status, VoiceMemoStatus) and status in self._status_icons:
                # Draw the icon
                icon = self._status_icons[status]
                icon_rect = option.rect
                icon_rect.setWidth(16)
                icon_rect.setHeight(16)
                icon_rect.moveCenter(option.rect.center())
                
                icon.paint(painter, icon_rect)
                
                # Draw status text next to icon
                text_rect = option.rect
                text_rect.setLeft(icon_rect.right() + 8)
                
                status_text = status.value.replace('_', ' ').title()
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, status_text)
                
                return
        
        # Fall back to default painting for other columns
        super().paint(painter, option, index)
    
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Return size hint for status column"""
        size = super().sizeHint(option, index) 
        
        if index.column() == VoiceMemoTableModel.COL_STATUS:
            # Make status column a bit wider to accommodate icon + text
            size.setWidth(max(size.width(), 120))
        
        return size
