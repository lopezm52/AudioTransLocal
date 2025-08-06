#!/usr/bin/env python3
"""
Whisper Model Management Widget

A self-contained widget for managing Whisper model selection and downloads
according to the technical specification.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QComboBox, QPushButton, QProgressBar, QMessageBox,
                              QGroupBox)
from PySide6.QtCore import QThreadPool, QRunnable, Signal, QObject, Slot
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ModelDownloadTask(QRunnable):
    """QRunnable task for downloading models in QThreadPool"""
    
    def __init__(self, download_object):
        super().__init__()
        self.download_object = download_object
        self.setAutoDelete(True)
    
    def run(self):
        """Execute the download"""
        self.download_object.download()


class WhisperModelWidget(QWidget):
    """
    Self-contained widget for Whisper model management.
    
    Implements the complete state management logic as specified:
    - Model selection via QComboBox
    - Status display showing download state
    - Stateful download button
    - Progress bar with cancel functionality
    - Integration with ModelDownloadWorker
    """
    
    def __init__(self, whisper_model_manager, parent=None):
        """
        Initialize the Whisper Model Management widget.
        
        Args:
            whisper_model_manager: WhisperModelManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.whisper_model_manager = whisper_model_manager
        self.current_download_task = None
        self.thread_pool = QThreadPool.globalInstance()
        
        self._setup_ui()
        self._setup_connections()
        self._refresh_ui_state()
    
    def _setup_ui(self):
        """Set up the UI components according to specification"""
        layout = QVBoxLayout(self)
        
        # Create group box for better organization
        group_box = QGroupBox("Whisper Model Management")
        group_layout = QVBoxLayout(group_box)
        
        # Model selection row
        selection_layout = QHBoxLayout()
        selection_layout.addWidget(QLabel("Model:"))
        
        # QComboBox for model selection
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        selection_layout.addWidget(self.model_combo)
        
        selection_layout.addStretch()
        group_layout.addLayout(selection_layout)
        
        # Status label
        self.model_status_label = QLabel("Loading models...")
        group_layout.addWidget(self.model_status_label)
        
        # Button and progress row
        button_layout = QHBoxLayout()
        
        # Download button (stateful)
        self.download_button = QPushButton("Download")
        self.download_button.setMinimumWidth(100)
        button_layout.addWidget(self.download_button)
        
        # Cancel button (hidden by default)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.hide()
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        group_layout.addLayout(button_layout)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.hide()
        group_layout.addWidget(self.progress_bar)
        
        layout.addWidget(group_box)
        layout.addStretch()
    
    def _setup_connections(self):
        """Set up signal connections"""
        # UI connections
        self.model_combo.currentTextChanged.connect(self._on_model_selection_changed)
        self.download_button.clicked.connect(self._on_download_clicked)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        
        # Populate model combo box
        self._populate_models()
    
    def _populate_models(self):
        """Populate the model combo box"""
        try:
            models = self.whisper_model_manager.get_available_models()
            self.model_combo.clear()
            
            for model_id, display_name in models:
                self.model_combo.addItem(display_name, model_id)
            
            # Set current model if any
            current_model = self.whisper_model_manager.get_current_model()
            for i in range(self.model_combo.count()):
                if self.model_combo.itemData(i) == current_model:
                    self.model_combo.setCurrentIndex(i)
                    break
                    
        except Exception as e:
            logger.error(f"Failed to populate models: {e}")
            self.model_status_label.setText("Failed to load models")
    
    def _get_selected_model_id(self) -> Optional[str]:
        """Get the currently selected model ID"""
        current_index = self.model_combo.currentIndex()
        if current_index >= 0:
            return self.model_combo.itemData(current_index)
        return None
    
    def _refresh_ui_state(self):
        """Refresh UI state based on current model selection"""
        model_id = self._get_selected_model_id()
        if not model_id:
            self.model_status_label.setText("No model selected")
            self.download_button.setEnabled(False)
            return
        
        # Update status label using whisper_manager.get_model_status_text()
        status_text = self.whisper_model_manager.get_model_status_text(model_id)
        self.model_status_label.setText(status_text)
        
        # Update button state based on download status
        is_downloaded = self.whisper_model_manager.is_model_downloaded(model_id)
        
        if is_downloaded:
            # Model is downloaded: disable button, show "Downloaded"
            self.download_button.setText("Downloaded")
            self.download_button.setEnabled(False)
            self._hide_progress_controls()
        else:
            # Model is not downloaded: enable button, show "Download"
            self.download_button.setText("Download")
            self.download_button.setEnabled(True)
            self._hide_progress_controls()
    
    def _hide_progress_controls(self):
        """Hide progress bar and cancel button"""
        self.progress_bar.hide()
        self.cancel_button.hide()
    
    def _show_progress_controls(self):
        """Show progress bar and cancel button, hide download button"""
        self.download_button.hide()
        self.progress_bar.show()
        self.cancel_button.show()
        self.progress_bar.setValue(0)
    
    def _reset_to_idle_state(self):
        """Reset UI to idle state after download completion"""
        self.download_button.show()
        self._hide_progress_controls()
        self.model_combo.setEnabled(True)
        self.current_download_task = None
        self._refresh_ui_state()
    
    def _on_model_selection_changed(self):
        """Handle model selection change"""
        # Update the selected model in the manager
        model_id = self._get_selected_model_id()
        if model_id:
            self.whisper_model_manager.set_current_model(model_id)
        
        # Refresh UI state
        self._refresh_ui_state()
    
    def _on_download_clicked(self):
        """Handle download button click"""
        model_id = self._get_selected_model_id()
        if not model_id:
            return
        
        # Get download information from manager
        download_info = self.whisper_model_manager.get_model_download_info(model_id)
        if not download_info:
            QMessageBox.warning(
                self,
                "Download Error",
                f"Cannot get download information for {model_id}"
            )
            return
        
        download_url = download_info.get("download_url")
        if not download_url:
            QMessageBox.warning(
                self,
                "Download Error", 
                f"Download URL not available for {model_id}"
            )
            return
        
        # Confirm download for large models
        size_mb = download_info.get("size_mb", 0)
        if size_mb > 500:
            reply = QMessageBox.question(
                self,
                "Download Large Model",
                f"You are about to download {download_info['display_name']} ({size_mb} MB).\n\n"
                f"This may take several minutes depending on your internet connection.\n\n"
                f"Do you want to continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
        
        # Transition to downloading state
        self._show_progress_controls()
        self.model_combo.setEnabled(False)  # Disable combo box during download
        
        # Create download task using the corrected architecture
        from app.workers.download_worker import WhisperModelDownloadTask
        
        self.current_download_task = WhisperModelDownloadTask(
            model_id, 
            self.whisper_model_manager
        )
        
        # Connect signals
        self.current_download_task.progress_updated.connect(self._on_progress_updated)
        self.current_download_task.status_updated.connect(self._on_status_updated)
        self.current_download_task.download_completed.connect(self._on_download_completed)
        
        # Submit to thread pool (the task will handle this internally)
        task_runner = ModelDownloadTask(self.current_download_task)
        self.thread_pool.start(task_runner)
        
        logger.info(f"Started download for model: {model_id}")
    
    def _on_cancel_clicked(self):
        """Handle cancel button click"""
        if self.current_download_task:
            self.current_download_task.cancel()
            logger.info("Download cancelled by user")
        
        # Reset to idle state
        self._reset_to_idle_state()
        self.model_status_label.setText("Download cancelled")
    
    @Slot(str, int)
    def _on_progress_updated(self, model_id: str, percentage: int):
        """Handle progress updates from download worker"""
        self.progress_bar.setValue(percentage)
    
    @Slot(str, str)
    def _on_status_updated(self, model_id: str, status: str):
        """Handle status updates from download worker"""
        self.model_status_label.setText(status)
    
    @Slot(str, bool, str)
    def _on_download_completed(self, model_id: str, success: bool, message: str):
        """Handle download completion"""
        # Reset UI to idle state
        self._reset_to_idle_state()
        
        # Show completion message
        if success:
            QMessageBox.information(
                self,
                "Download Complete",
                f"Successfully downloaded {model_id} model.\n\n{message}"
            )
            logger.info(f"Download completed successfully: {model_id}")
        else:
            QMessageBox.warning(
                self,
                "Download Failed", 
                f"Failed to download {model_id} model.\n\n{message}"
            )
            logger.error(f"Download failed: {model_id} - {message}")
        
        # Refresh the model status display
        self._refresh_ui_state()
    
    def refresh(self):
        """Public method to refresh the widget state"""
        self._populate_models()
        self._refresh_ui_state()
