#!/usr/bin/env python3
"""
Model Download Worker for AudioTransLocal

This module provides a non-blocking, progress-tracking download worker for
Whisper model files. It follows the proper Qt threading pattern with QRunnable
and provides real-time progress updates.
"""

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Optional

import httpx
from PySide6.QtCore import QObject, QRunnable, Signal

logger = logging.getLogger(__name__)


class ModelDownloadSignals(QObject):
    """Signals for model download worker with structured data"""
    
    # Emitted when download progress changes - passes structured progress dict
    progress_updated = Signal(dict)  # {'model_id': str, 'percentage': int, 'downloaded_bytes': int, 'total_bytes': int, 'speed_bps': float}
    
    # Emitted when download status changes
    status_updated = Signal(str, str)  # model_id, status_message
    
    # Emitted when download completes
    download_completed = Signal(str, bool, str)  # model_id, success, message
    
    # Emitted when download is cancelled
    download_cancelled = Signal(str)  # model_id


class ModelDownloadWorker(QRunnable):
    """
    Worker class for downloading Whisper model files with progress tracking.
    
    This worker downloads a file from a URL to a destination path, providing
    real-time progress updates and SHA256 verification.
    """
    
    def __init__(self, model_id: str, download_url: str, destination_path: str, 
                 expected_sha256: Optional[str] = None):
        """
        Initialize the download worker.
        
        Args:
            model_id: The model identifier
            download_url: URL to download the model from
            destination_path: Local path where the model should be saved
            expected_sha256: Expected SHA256 checksum for verification (optional)
        """
        super().__init__()
        self.model_id = model_id
        self.download_url = download_url
        self.destination_path = Path(destination_path)
        self.expected_sha256 = expected_sha256
        self.signals = ModelDownloadSignals()
        self._cancelled = False
        
        # Ensure destination directory exists
        self.destination_path.parent.mkdir(parents=True, exist_ok=True)
    
    def cancel(self):
        """Cancel the download operation"""
        self._cancelled = True
        logger.info(f"Download cancelled for model: {self.model_id}")
    
    def run(self):
        """Execute the download operation"""
        try:
            self._download_file()
        except Exception as e:
            logger.error(f"❌ Download failed for {self.model_id}: {e}")
            self.signals.download_completed.emit(
                self.model_id, False, f"Download failed: {str(e)}"
            )
    
    def _download_file(self):
        """Download the file with progress tracking"""
        try:
            self.signals.status_updated.emit(self.model_id, "Connecting...")
            
            download_start_time = time.time()
            last_progress_time = download_start_time
            
            # Use httpx for streaming download with progress tracking
            with httpx.stream("GET", self.download_url, follow_redirects=True) as response:
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.reason_phrase}")
                
                # Get total file size from headers
                total_size = int(response.headers.get("content-length", 0))
                
                if total_size == 0:
                    logger.warning(f"⚠️ Content-Length header missing for {self.model_id}")
                
                downloaded_size = 0
                
                # Open destination file for writing
                with open(self.destination_path, "wb") as f:
                    self.signals.status_updated.emit(self.model_id, "Downloading...")
                    
                    # Download in chunks
                    for chunk in response.iter_bytes(chunk_size=64 * 1024):  # 64KB chunks
                        if self._cancelled:
                            # Clean up partial file
                            f.close()
                            if self.destination_path.exists():
                                self.destination_path.unlink()
                            self.signals.download_cancelled.emit(self.model_id)
                            return
                        
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Calculate progress and speed
                        current_time = time.time()
                        if current_time - last_progress_time >= 0.1:  # Update every 100ms
                            elapsed_time = current_time - download_start_time
                            speed_bps = downloaded_size / elapsed_time if elapsed_time > 0 else 0
                            
                            if total_size > 0:
                                percentage = int((downloaded_size / total_size) * 100)
                            else:
                                percentage = 0
                            
                            # Emit structured progress data
                            progress_data = {
                                'model_id': self.model_id,
                                'percentage': percentage,
                                'downloaded_bytes': downloaded_size,
                                'total_bytes': total_size,
                                'speed_bps': speed_bps,
                                'elapsed_seconds': elapsed_time
                            }
                            self.signals.progress_updated.emit(progress_data)
                            last_progress_time = current_time
                
                self.signals.status_updated.emit(self.model_id, "Download complete, verifying...")
                
                # Verify file integrity if SHA256 is provided
                if self.expected_sha256:
                    if self._verify_sha256():
                        self.signals.status_updated.emit(self.model_id, "Verification successful")
                        self.signals.download_completed.emit(
                            self.model_id, True, 
                            f"Successfully downloaded and verified {self.destination_path.name}"
                        )
                    else:
                        # Remove corrupted file
                        if self.destination_path.exists():
                            self.destination_path.unlink()
                        self.signals.download_completed.emit(
                            self.model_id, False, 
                            "Download failed: File integrity check failed"
                        )
                else:
                    # No verification, just confirm download
                    self.signals.download_completed.emit(
                        self.model_id, True, 
                        f"Successfully downloaded {self.destination_path.name}"
                    )
                
        except Exception as e:
            # Clean up partial file on error
            if self.destination_path.exists():
                try:
                    self.destination_path.unlink()
                except:
                    pass
            
            error_msg = f"Download failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.signals.download_completed.emit(self.model_id, False, error_msg)
    
    def _verify_sha256(self) -> bool:
        """Verify the downloaded file's SHA256 checksum"""
        if not self.expected_sha256:
            return True
        
        try:
            self.signals.status_updated.emit(self.model_id, "Verifying file integrity...")
            
            sha256_hash = hashlib.sha256()
            
            with open(self.destination_path, "rb") as f:
                # Read file in chunks to handle large files efficiently
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            calculated_sha256 = sha256_hash.hexdigest()
            
            if calculated_sha256.lower() == self.expected_sha256.lower():
                logger.info(f"✅ SHA256 verification successful for {self.model_id}")
                return True
            else:
                logger.error(f"❌ SHA256 mismatch for {self.model_id}")
                logger.error(f"   Expected: {self.expected_sha256}")
                logger.error(f"   Got:      {calculated_sha256}")
                return False
                
        except Exception as e:
            logger.error(f"❌ SHA256 verification failed for {self.model_id}: {e}")
            return False
