#!/usr/bin/env python3
"""
Whisper Model Manager for AudioTransLocal

This module centralizes all Whisper model management including:
- Model selection and validation
- Settings persistence
- Model file verification
- Path management
- Model downloading with progress tracking

Epic 3: Core Transcription Workflow - Model Management
"""

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from PySide6.QtCore import QSettings, QObject, Signal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WhisperModelManager(QObject):
    """
    Centralized manager for Whisper model selection and validation.
    
    This class handles all aspects of Whisper model management:
    - Loading available models from whisper_models.json
    - Persisting user's selected model in QSettings
    - Validating model file existence and integrity
    - Providing model information to UI components
    - Downloading models to proper storage location
    """
    
    # Signal emitted when the selected model changes
    model_changed = Signal(str)  # model_path
    # Signal emitted when download progress updates
    download_progress = Signal(str, int)  # model_name, percentage
    # Signal emitted when download completes
    download_completed = Signal(str, bool)  # model_name, success
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings()
        self._models_config = None
        self._models_dir = Path.home() / "Library" / "Application Support" / "AudioTransLocal" / "models"
        self._models_dir.mkdir(parents=True, exist_ok=True)
        self._load_models_config()
        
    def get_models_directory(self) -> Path:
        """Get the directory where models are stored"""
        return self._models_dir
    
    def _load_models_config(self):
        """Load models configuration from whisper_models.json"""
        try:
            # Try resources directory first
            models_file = Path(__file__).parent.parent.parent / "resources" / "whisper_models.json"
            if models_file.exists():
                with open(models_file, 'r') as f:
                    self._models_config = json.load(f)
                logger.info(f"✅ Loaded {len(self._models_config.get('whisper_models', {}))} model configurations")
            else:
                # Fallback to basic configuration
                logger.warning(f"⚠️ Models config not found: {models_file}")
                self._models_config = {
                    "whisper_models": {
                        "tiny": {
                            "display_name": "Tiny",
                            "description": "Fastest, least accurate",
                            "size": "39 MB",
                            "size_mb": 39,
                            "filename": "tiny.pt"
                        },
                        "base": {
                            "display_name": "Base", 
                            "description": "Good balance of speed and accuracy",
                            "size": "142 MB",
                            "size_mb": 142,
                            "filename": "base.pt"
                        },
                        "small": {
                            "display_name": "Small",
                            "description": "Better accuracy, slower", 
                            "size": "466 MB",
                            "size_mb": 466,
                            "filename": "small.pt"
                        },
                        "medium": {
                            "display_name": "Medium",
                            "description": "High accuracy",
                            "size": "1.42 GB", 
                            "size_mb": 1420,
                            "filename": "medium.pt"
                        },
                        "large": {
                            "display_name": "Large",
                            "description": "Best accuracy, slowest",
                            "size": "2.87 GB",
                            "size_mb": 2870, 
                            "filename": "large.pt"
                        }
                    }
                }
        except Exception as e:
            logger.error(f"❌ Failed to load models config: {e}")
            self._models_config = {
                "whisper_models": {
                    "tiny": {"display_name": "Tiny", "size": "39 MB", "size_mb": 39},
                    "base": {"display_name": "Base", "size": "142 MB", "size_mb": 142}
                }
            }
    
    def get_available_models(self) -> List[Tuple[str, str]]:
        """
        Get list of available Whisper models for UI display.
        
        Returns:
            List of (model_id, display_name) tuples
        """
        models = self._models_config.get("whisper_models", {})
        model_list = []
        
        for model_id, model_info in models.items():
            display_name = model_info.get("display_name", model_id)
            size_info = model_info.get("size", "")
            if size_info:
                display_name += f" ({size_info})"
            model_list.append((model_id, display_name))
        
        return model_list
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model"""
        models = self._models_config.get("whisper_models", {})
        return models.get(model_id)
    
    def is_model_downloaded(self, model_id: str) -> bool:
        """
        Check if a model is already downloaded locally.
        
        Args:
            model_id: The model identifier (e.g., 'tiny', 'base', etc.)
            
        Returns:
            True if model is downloaded, False otherwise
        """
        model_info = self.get_model_info(model_id)
        if not model_info:
            return False
            
        # Check for ggml model file in our application's models directory
        filename = model_info.get("filename", f"ggml-{model_id}.bin")
        model_file = self._models_dir / filename
        
        # Verify file exists and has reasonable size (> 1MB to avoid empty files)
        if model_file.exists():
            try:
                file_size = model_file.stat().st_size
                return file_size > 1024 * 1024  # At least 1MB
            except OSError:
                return False
        
        return False
    
    def get_model_status_text(self, model_id: str) -> str:
        """
        Get status text for a model for UI display.
        
        Args:
            model_id: The model identifier
            
        Returns:
            Status text describing the model's download state
        """
        model_info = self.get_model_info(model_id)
        if not model_info:
            return "Unknown model"
        
        if self.is_model_downloaded(model_id):
            return "Downloaded"
        else:
            # Try size_mb first, then size, then fallback
            size_mb = model_info.get("size_mb")
            if size_mb:
                size = f"{size_mb} MB"
            else:
                size = model_info.get("size", "Unknown size")
            return f"Not downloaded ({size})"
    
    def get_current_model(self) -> str:
        """Get the currently selected model ID"""
        return self.settings.value("transcription/selected_model", "tiny")
    
    def set_current_model(self, model_id: str) -> bool:
        """
        Set the current Whisper model.
        
        Args:
            model_id: ID of the model to select
            
        Returns:
            True if model was set successfully, False otherwise
        """
        models = dict(self.get_available_models())
        if model_id not in [mid for mid, _ in self.get_available_models()]:
            logger.error(f"❌ Model not available: {model_id}")
            return False
        
        # Save to settings
        self.settings.setValue("transcription/selected_model", model_id)
        self.settings.sync()
        
        logger.info(f"✅ Selected model: {model_id}")
        self.model_changed.emit(model_id)
        return True
    
    def get_model_download_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get download information for a specific model.
        
        Args:
            model_id: The model identifier
            
        Returns:
            Dictionary with download info including URL and destination path
        """
        model_info = self.get_model_info(model_id)
        if not model_info:
            return None
        
        # Get download URL and destination path
        download_url = model_info.get("download_url")
        filename = model_info.get("filename", f"ggml-{model_id}.bin")
        destination_path = self._models_dir / filename
        
        return {
            "model_id": model_id,
            "download_url": download_url,
            "destination_path": str(destination_path),
            "filename": filename,
            "size_mb": model_info.get("size_mb", 0),
            "sha256": model_info.get("sha256"),
            "display_name": model_info.get("display_name", model_id)
        }
    
    def verify_model_integrity(self, model_id: str) -> bool:
        """
        Verify the integrity of a downloaded model using SHA256 checksum.
        
        Args:
            model_id: The model identifier
            
        Returns:
            True if model file is valid, False otherwise
        """
        download_info = self.get_model_download_info(model_id)
        if not download_info:
            return False
        
        expected_sha256 = download_info.get("sha256")
        if not expected_sha256:
            # If no checksum is provided, just check file existence
            return self.is_model_downloaded(model_id)
        
        model_file = Path(download_info["destination_path"])
        if not model_file.exists():
            return False
        
        try:
            import hashlib
            sha256_hash = hashlib.sha256()
            with open(model_file, "rb") as f:
                # Read file in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            calculated_sha256 = sha256_hash.hexdigest()
            return calculated_sha256.lower() == expected_sha256.lower()
            
        except Exception as e:
            logger.error(f"❌ Failed to verify model integrity: {e}")
            return False
