#!/usr/bin/env python3
"""
Whisper Model Manager for AudioTransLocal

This module centralizes all Whisper model management including:
- Model selection and validation using Pydantic models
- Settings persistence
- Model file verification
- Path management

Epic 3: Core Transcription Workflow - Model Management
"""

import logging
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

from PySide6.QtCore import QSettings, QObject, Signal
from pydantic import ValidationError

from app.models.whisper_model import WhisperModelConfig, WhisperModel

# Configure logging
logger = logging.getLogger(__name__)


class WhisperModelManager(QObject):
    """
    Centralized manager for Whisper model selection and validation.
    
    This class handles all aspects of Whisper model management using
    type-safe Pydantic models for configuration data.
    """
    
    # Signal emitted when the selected model changes
    model_changed = Signal(str)  # model_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings()
        self._models_config: Optional[WhisperModelConfig] = None
        self._models_dir = Path.home() / "Library" / "Application Support" / "AudioTransLocal" / "models"
        self._models_dir.mkdir(parents=True, exist_ok=True)
        self._load_models_config()
        
    def get_models_directory(self) -> Path:
        """Get the directory where models are stored"""
        return self._models_dir
    
    def _load_models_config(self):
        """Load models configuration using Pydantic validation"""
        try:
            # Try resources directory first
            models_file = Path(__file__).parent.parent.parent / "resources" / "whisper_models.json"
            
            if models_file.exists():
                self._models_config = WhisperModelConfig.load_from_json(models_file)
                logger.info(f"✅ Loaded {len(self._models_config.whisper_models)} model configurations with validation")
            else:
                logger.warning(f"⚠️ Models config not found: {models_file}")
                self._create_fallback_config()
                
        except ValidationError as e:
            logger.error(f"❌ Model configuration validation failed: {e}")
            self._create_fallback_config()
        except Exception as e:
            logger.error(f"❌ Failed to load models config: {e}")
            self._create_fallback_config()
    
    def _create_fallback_config(self):
        """Create a minimal fallback configuration"""
        fallback_data = {
            "whisper_models": {
                "tiny": {
                    "display_name": "Tiny",
                    "filename": "ggml-tiny.bin",
                    "download_url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
                    "size_mb": 75,
                    "sha256": "be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21",
                    "description": "Fastest model, multilingual support"
                },
                "base": {
                    "display_name": "Base",
                    "filename": "ggml-base.bin", 
                    "download_url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
                    "size_mb": 142,
                    "sha256": "465707469ff3a37a2b9b8d8f89f2f99de7299dac7e3e8fe0aa3b15a1a9df7f39",
                    "description": "Good balance of speed and accuracy"
                }
            }
        }
        
        try:
            self._models_config = WhisperModelConfig(**fallback_data)
            logger.info("✅ Created fallback model configuration")
        except ValidationError as e:
            logger.error(f"❌ Failed to create fallback config: {e}")
            # Create minimal empty config as last resort
            self._models_config = WhisperModelConfig(whisper_models={})
    
    def get_available_models(self) -> List[Tuple[str, str]]:
        """
        Get list of available Whisper models for UI display.
        
        Returns:
            List of (model_id, display_name) tuples
        """
        if not self._models_config:
            return []
        
        model_list = []
        
        for model_id, model in self._models_config.whisper_models.items():
            display_name = f"{model.display_name} ({model.size_mb} MB)"
            model_list.append((model_id, display_name))
        
        return model_list
    
    def get_model_info(self, model_id: str) -> Optional[WhisperModel]:
        """
        Get detailed information about a specific model.
        
        Args:
            model_id: The model identifier
            
        Returns:
            WhisperModel instance with validated data, or None if not found
        """
        if not self._models_config:
            return None
        
        return self._models_config.get_model(model_id)
    
    
    def is_model_downloaded(self, model_id: str) -> bool:
        """
        Check if a model is already downloaded locally.
        
        Args:
            model_id: The model identifier (e.g., 'tiny', 'base', etc.)
            
        Returns:
            True if model is downloaded, False otherwise
        """
        model = self.get_model_info(model_id)
        if not model:
            return False
            
        # Check for ggml model file in our application's models directory
        model_file = self._models_dir / model.filename
        
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
        model = self.get_model_info(model_id)
        if not model:
            return "Unknown model"
        
        if self.is_model_downloaded(model_id):
            return "Downloaded"
        else:
            return f"Not downloaded ({model.size_mb} MB)"

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
        available_model_ids = [mid for mid, _ in self.get_available_models()]
        if model_id not in available_model_ids:
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
        model = self.get_model_info(model_id)
        if not model:
            return None
        
        destination_path = self._models_dir / model.filename
        
        return {
            "model_id": model_id,
            "download_url": str(model.download_url),
            "destination_path": str(destination_path),
            "filename": model.filename,
            "size_mb": model.size_mb,
            "sha256": model.sha256,
            "display_name": model.display_name
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

    def get_models_by_size_range(self, max_size_mb: Optional[int] = None) -> List[Tuple[str, str]]:
        """
        Get models filtered by maximum size.
        
        Args:
            max_size_mb: Maximum size in MB, or None for no limit
            
        Returns:
            List of (model_id, display_name) tuples for models within size limit
        """
        if not self._models_config:
            return []
        
        filtered_models = self._models_config.get_models_by_size(max_size_mb)
        
        result = []
        for model_id, model in filtered_models.items():
            display_name = f"{model.display_name} ({model.size_mb} MB)"
            result.append((model_id, display_name))
        
        return result