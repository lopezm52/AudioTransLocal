#!/usr/bin/env python3
"""
Custom Item Delegates for Voice Memo Table

This module provides custom QStyledItemDelegate implementations for
enhanced UI elements in the Voice Memo table, including transcription
action buttons and status indicators.

Epic 3: Core Transcription Workflow
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QRect, QSize, Signal, QEvent, QPoint
from PySide6.QtGui import QPainter, QFont, QColor, QPen
from PySide6.QtWidgets import (
    QStyledItemDelegate, QStyleOptionViewItem, QWidget, QStyle,
    QPushButton, QHBoxLayout, QApplication, QToolTip
)


class TranscriptionActionsDelegate(QStyledItemDelegate):
    """
    Custom delegate for the Actions column that shows Transcribe/View buttons.
    
    This delegate displays different buttons based on the transcription status:
    - "Transcribe" button for new/untranscribed memos
    - "View Transcription" button for completed transcriptions
    - Disabled state during processing
    """
    
    # Signals emitted when buttons are clicked
    transcribe_requested = Signal(str)  # memo_id
    view_transcription_requested = Signal(str)  # memo_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.button_height = 24
        self.button_width = 120
        self.margin = 4
    
    def createEditor(self, parent, option, index):
        """Create the button widget for the Actions column"""
        memo = index.data(Qt.ItemDataRole.UserRole)
        if not memo:
            return None
        
        # Create container widget
        widget = QWidget(parent)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(self.margin, 2, self.margin, 2)
        layout.setSpacing(4)
        
        # Determine button type based on transcription status
        status = getattr(memo, 'transcription_status', 'new')
        
        if status == 'transcribed' and hasattr(memo, 'transcription_file_path') and memo.transcription_file_path:
            # Show "View Transcription" button
            button = QPushButton("View Transcription")
            button.setFixedSize(self.button_width, self.button_height)
            button.clicked.connect(lambda: self.view_transcription_requested.emit(memo.uuid))
            button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        elif status in ['new', 'error']:
            # Show "Transcribe" button
            button = QPushButton("Transcribe")
            button.setFixedSize(self.button_width, self.button_height)
            button.clicked.connect(lambda: self.transcribe_requested.emit(memo.uuid))
            button.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
        else:
            # Show disabled button during processing
            button = QPushButton("Processing...")
            button.setFixedSize(self.button_width, self.button_height)
            button.setEnabled(False)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #9E9E9E;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 10px;
                }
            """)
        
        layout.addWidget(button)
        layout.addStretch()
        
        return widget
    
    def paint(self, painter, option, index):
        """Paint the delegate - use default implementation as we use createEditor"""
        super().paint(painter, option, index)
    
    def sizeHint(self, option, index):
        """Return the size hint for the Actions column"""
        return QSize(self.button_width + 2 * self.margin, self.button_height + 4)
    
    def updateEditorGeometry(self, editor, option, index):
        """Update the geometry of the editor widget"""
        editor.setGeometry(option.rect)


class TranscriptionStatusDelegate(QStyledItemDelegate):
    """
    Custom delegate for the Status column that shows transcription progress
    with visual indicators and progress information.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def paint(self, painter, option, index):
        """Custom paint method for status column with visual indicators"""
        painter.save()
        
        # Get memo and status information
        memo = index.data(Qt.ItemDataRole.UserRole)
        if not memo:
            super().paint(painter, option, index)
            painter.restore()
            return
        
        status = getattr(memo, 'transcription_status', 'new')
        progress_text = getattr(memo, 'transcription_progress', '')
        
        # Set up painting
        rect = option.rect
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background for selected/hovered items
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, option.palette.highlight())
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(rect, option.palette.alternateBase())
        
        # Draw status indicator and text
        text_rect = rect.adjusted(25, 0, -5, 0)  # Leave space for indicator
        indicator_rect = QRect(rect.x() + 5, rect.y() + rect.height()//2 - 6, 12, 12)
        
        if status == 'new':
            # Gray circle for new/ready
            painter.setBrush(QColor("#9E9E9E"))
            painter.setPen(QPen(QColor("#757575"), 1))
            painter.drawEllipse(indicator_rect)
            text = "Ready"
            
        elif status == 'transcribing':
            # Blue animated circle for processing
            painter.setBrush(QColor("#2196F3"))
            painter.setPen(QPen(QColor("#1976D2"), 1))
            painter.drawEllipse(indicator_rect)
            text = progress_text if progress_text else "Transcribing..."
            
        elif status == 'transcribed':
            # Green checkmark for completed
            painter.setBrush(QColor("#4CAF50"))
            painter.setPen(QPen(QColor("#2E7D32"), 2))
            painter.drawEllipse(indicator_rect)
            # Draw checkmark
            painter.setPen(QPen(QColor("white"), 2))
            check_points = [
                (indicator_rect.x() + 3, indicator_rect.y() + 6),
                (indicator_rect.x() + 5, indicator_rect.y() + 8),
                (indicator_rect.x() + 9, indicator_rect.y() + 4)
            ]
            for i in range(len(check_points) - 1):
                painter.drawLine(check_points[i][0], check_points[i][1], 
                               check_points[i+1][0], check_points[i+1][1])
            text = "Transcribed"
            
        elif status == 'error':
            # Red X for error
            painter.setBrush(QColor("#F44336"))
            painter.setPen(QPen(QColor("#C62828"), 1))
            painter.drawEllipse(indicator_rect)
            # Draw X
            painter.setPen(QPen(QColor("white"), 2))
            painter.drawLine(indicator_rect.x() + 3, indicator_rect.y() + 3,
                           indicator_rect.x() + 9, indicator_rect.y() + 9)
            painter.drawLine(indicator_rect.x() + 9, indicator_rect.y() + 3,
                           indicator_rect.x() + 3, indicator_rect.y() + 9)
            text = "Error"
            
        else:
            # Default gray for unknown status
            painter.setBrush(QColor("#9E9E9E"))
            painter.setPen(QPen(QColor("#757575"), 1))
            painter.drawEllipse(indicator_rect)
            text = status.title()
        
        # Draw text
        painter.setPen(option.palette.text().color())
        font = QFont(option.font)
        if status == 'transcribing':
            font.setItalic(True)
        painter.setFont(font)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        
        painter.restore()
    
    def sizeHint(self, option, index):
        """Return appropriate size hint for status column"""
        return QSize(150, 30)
    
    def helpEvent(self, event, view, option, index):
        """Handle tooltip events to show error messages"""
        if event.type() == QEvent.Type.ToolTip:
            memo = index.data(Qt.ItemDataRole.UserRole)
            if memo and hasattr(memo, 'transcription_error') and memo.transcription_error:
                # Show error message in tooltip
                QToolTip.showText(event.globalPos(), f"Error: {memo.transcription_error}")
                return True
            elif memo and hasattr(memo, 'transcription_status'):
                status = memo.transcription_status
                if status == 'transcribed':
                    tooltip = "Transcription completed successfully"
                elif status == 'transcribing':
                    progress = getattr(memo, 'transcription_progress', 'In progress...')
                    tooltip = f"Status: {progress}"
                elif status == 'new':
                    tooltip = "Ready for transcription"
                else:
                    tooltip = f"Status: {status}"
                
                QToolTip.showText(event.globalPos(), tooltip)
                return True
        
        return super().helpEvent(event, view, option, index)
