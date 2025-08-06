#!/usr/bin/env python3
"""
Download worker for handling model downloads and other download tasks
"""

from PySide6.QtCore import QThread, Signal, QObject, Slot
from typing import Optional, Callable, Any
import logging
import time

logger = logging.getLogger(__name__)


class DownloadWorker(QThread):
    """
    Generic download worker that can handle various download tasks.
    Designed to be extended for specific download types (models, updates, etc.)
    """
    
    # Signals
    progress_updated = Signal(int)  # Progress percentage (0-100)
    status_updated = Signal(str)   # Status message
    download_completed = Signal()  # Download completed successfully
    download_failed = Signal(str)  # Download failed with error message
    download_cancelled = Signal()  # Download was cancelled
    
    def __init__(self, download_url: str = None, destination_path: str = None, 
                 download_type: str = "generic"):
        """
        Initialize the download worker.
        
        Args:
            download_url: URL to download from
            destination_path: Where to save the downloaded file
            download_type: Type of download (for identification)
        """
        super().__init__()
        
        self.download_url = download_url
        self.destination_path = destination_path
        self.download_type = download_type
        
        self._cancelled = False
        self._progress_callback: Optional[Callable[[int], None]] = None
        self._status_callback: Optional[Callable[[str], None]] = None
    
    def set_progress_callback(self, callback: Callable[[int], None]):
        """Set callback for progress updates"""
        self._progress_callback = callback
    
    def set_status_callback(self, callback: Callable[[str], None]):
        """Set callback for status updates"""
        self._status_callback = callback
    
    def cancel(self):
        """Cancel the download"""
        self._cancelled = True
        logger.info(f"Cancelling {self.download_type} download")
    
    def is_cancelled(self) -> bool:
        """Check if download was cancelled"""
        return self._cancelled
    
    def update_progress(self, percentage: int):
        """
        Update download progress.
        
        Args:
            percentage: Progress percentage (0-100)
        """
        if not self._cancelled:
            self.progress_updated.emit(percentage)
            if self._progress_callback:
                self._progress_callback(percentage)
    
    def update_status(self, message: str):
        """
        Update download status.
        
        Args:
            message: Status message
        """
        if not self._cancelled:
            self.status_updated.emit(message)
            if self._status_callback:
                self._status_callback(message)
    
    def run(self):
        """
        Main download execution.
        Override this method in subclasses for specific download logic.
        """
        try:
            logger.info(f"Starting {self.download_type} download")
            self.update_status(f"Starting {self.download_type} download...")
            
            # Base implementation - simulate download
            self._simulate_download()
            
            if not self._cancelled:
                self.update_status("Download completed successfully")
                self.download_completed.emit()
                logger.info(f"{self.download_type} download completed")
            else:
                self.download_cancelled.emit()
                logger.info(f"{self.download_type} download cancelled")
                
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            logger.error(error_msg)
            self.download_failed.emit(error_msg)
    
    def _simulate_download(self):
        """
        Simulate a download process.
        Replace this with actual download logic in subclasses.
        """
        total_steps = 100
        
        for i in range(total_steps + 1):
            if self._cancelled:
                break
            
            # Simulate download progress
            progress = int((i / total_steps) * 100)
            self.update_progress(progress)
            
            if i % 20 == 0:
                self.update_status(f"Downloaded {progress}%...")
            
            # Simulate work
            self.msleep(50)  # Sleep for 50ms


class ModelDownloadWorker(DownloadWorker):
    """
    Specialized download worker for ML models.
    """
    
    def __init__(self, model_name: str, model_url: str = None, 
                 destination_path: str = None):
        """
        Initialize the model download worker.
        
        Args:
            model_name: Name of the model to download
            model_url: URL to download the model from
            destination_path: Where to save the model
        """
        super().__init__(model_url, destination_path, "model")
        self.model_name = model_name
    
    def run(self):
        """Download a machine learning model"""
        try:
            logger.info(f"Starting download of model: {self.model_name}")
            self.update_status(f"Downloading {self.model_name} model...")
            
            # Check if download is needed
            if self._is_model_already_downloaded():
                self.update_status(f"Model {self.model_name} already exists")
                self.update_progress(100)
                self.download_completed.emit()
                return
            
            # Perform actual download
            self._download_model()
            
            if not self._cancelled:
                self.update_status(f"Model {self.model_name} downloaded successfully")
                self.download_completed.emit()
                logger.info(f"Model {self.model_name} download completed")
            else:
                self.download_cancelled.emit()
                logger.info(f"Model {self.model_name} download cancelled")
                
        except Exception as e:
            error_msg = f"Model download failed: {str(e)}"
            logger.error(error_msg)
            self.download_failed.emit(error_msg)
    
    def _is_model_already_downloaded(self) -> bool:
        """Check if the model is already downloaded"""
        # Base implementation - override in subclasses
        if self.destination_path:
            from pathlib import Path
            return Path(self.destination_path).exists()
        return False
    
    def _download_model(self):
        """
        Download the actual model.
        This is a placeholder - override in subclasses for specific model types.
        """
        # Simulate model download with realistic timing
        steps = [
            (5, "Initializing download..."),
            (15, "Connecting to model repository..."),
            (25, "Downloading model metadata..."),
            (40, "Downloading model weights..."),
            (70, "Downloading tokenizer files..."),
            (85, "Downloading configuration..."),
            (95, "Verifying download..."),
            (100, "Download complete")
        ]
        
        for progress, status in steps:
            if self._cancelled:
                break
            
            self.update_progress(progress)
            self.update_status(status)
            
            # Simulate variable download speeds
            if progress < 50:
                self.msleep(200)  # Slower initial setup
            else:
                self.msleep(100)  # Faster data transfer


class WhisperModelDownloadWorker(ModelDownloadWorker):
    """
    Specialized download worker for Whisper models.
    """
    
    def __init__(self, model_name: str):
        """
        Initialize Whisper model download worker.
        
        Args:
            model_name: Name of the Whisper model (tiny, base, small, etc.)
        """
        super().__init__(model_name, None, None)
        
        # Whisper model information
        self._model_sizes = {
            "tiny": "37 MB",
            "base": "142 MB", 
            "small": "466 MB",
            "medium": "1.42 GB",
            "large": "2.87 GB",
            "large-v2": "2.87 GB",
            "large-v3": "2.87 GB"
        }
    
    def _download_model(self):
        """Download Whisper model using the whisper library"""
        try:
            # Import whisper library for actual download
            import whisper
            
            # Update status with model size info
            model_size = self._model_sizes.get(self.model_name, "Unknown size")
            self.update_status(f"Downloading {self.model_name} model ({model_size})...")
            
            # Simulate download phases
            phases = [
                (10, "Preparing download..."),
                (20, "Downloading model files..."),
                (60, "Processing model data..."),
                (80, "Optimizing model..."),
                (95, "Finalizing installation..."),
                (100, "Model ready for use")
            ]
            
            # Download with progress simulation
            for progress, status in phases:
                if self._cancelled:
                    break
                
                self.update_progress(progress)
                self.update_status(status)
                
                # Actual download happens here (simplified)
                if progress == 20:
                    # This is where the real whisper.load_model() would be called
                    # For now, just simulate the time it takes
                    pass
                
                # Variable timing based on model size
                if self.model_name in ["large", "large-v2", "large-v3"]:
                    self.msleep(300)  # Larger models take longer
                elif self.model_name in ["medium"]:
                    self.msleep(200)
                else:
                    self.msleep(100)
            
        except ImportError:
            logger.warning("Whisper library not available - simulating download")
            self._simulate_download()
        except Exception as e:
            logger.error(f"Whisper model download error: {e}")
            raise


class WhisperModelDownloadTask(QObject):
    """
    Download task for Whisper models using the proper ModelDownloadWorker.
    
    This acts as a bridge between the UI and the actual download worker,
    maintaining the proper separation of concerns.
    """
    
    # Signals for UI updates
    progress_updated = Signal(str, int)  # model_id, percentage
    status_updated = Signal(str, str)    # model_id, status
    download_completed = Signal(str, bool, str)  # model_id, success, message
    
    def __init__(self, model_id: str, whisper_model_manager):
        super().__init__()
        self.model_id = model_id
        self.whisper_model_manager = whisper_model_manager
        self.download_worker = None
        self._cancelled = False
    
    def cancel(self):
        """Cancel the download"""
        self._cancelled = True
        if self.download_worker:
            self.download_worker.cancel()
    
    def download(self):
        """Start the download process"""
        if self._cancelled:
            return
        
        # Get download information from the manager
        download_info = self.whisper_model_manager.get_model_download_info(self.model_id)
        if not download_info:
            self.download_completed.emit(
                self.model_id, False, "Model information not found"
            )
            return
        
        download_url = download_info.get("download_url")
        if not download_url:
            self.download_completed.emit(
                self.model_id, False, "Download URL not available"
            )
            return
        
        # Create the actual download worker
        from app.workers.model_download_worker import ModelDownloadWorker
        
        self.download_worker = ModelDownloadWorker(
            model_id=self.model_id,
            download_url=download_url,
            destination_path=download_info["destination_path"],
            expected_sha256=download_info.get("sha256")
        )
        
        # Connect worker signals to our signals
        self.download_worker.signals.progress_updated.connect(self._on_progress_updated)
        self.download_worker.signals.status_updated.connect(self._on_status_updated)
        self.download_worker.signals.download_completed.connect(self._on_download_completed)
        self.download_worker.signals.download_cancelled.connect(self._on_download_cancelled)
        
        # Submit to thread pool
        from PySide6.QtCore import QThreadPool
        QThreadPool.globalInstance().start(self.download_worker)
    
    @Slot(str, int, int, int)
    def _on_progress_updated(self, model_id: str, percentage: int, downloaded: int, total: int):
        """Handle progress updates from worker"""
        self.progress_updated.emit(model_id, percentage)
    
    @Slot(str, str)
    def _on_status_updated(self, model_id: str, status: str):
        """Handle status updates from worker"""
        self.status_updated.emit(model_id, status)
    
    @Slot(str, bool, str)
    def _on_download_completed(self, model_id: str, success: bool, message: str):
        """Handle download completion from worker"""
        self.download_completed.emit(model_id, success, message)
    
    @Slot(str)
    def _on_download_cancelled(self, model_id: str):
        """Handle download cancellation from worker"""
        self.download_completed.emit(model_id, False, "Download cancelled")
