#!/usr/bin/env python3
"""
Whisper Model Manager for AudioTransLocal

This module centralizes all Whisper model management including:
- Model selection and validation
- Settings persistence
- Model file verification
- Path management

Epic 3: Core Transcription Workflow - Model Management
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

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
    """
    
    # Signal emitted when the selected model changes
    model_changed = Signal(str)  # model_path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings()
        self._models_config = None
        self._load_models_config()
    
    def _load_models_config(self):
        """Load models configuration from whisper_models.json"""
        try:
            models_file = Path(__file__).parent / "whisper_models.json"
            if models_file.exists():
                with open(models_file, 'r') as f:
                    self._models_config = json.load(f)
                logger.info(f"✅ Loaded {len(self._models_config.get('whisper_models', {}))} model configurations")
            else:
                logger.warning(f"⚠️ Models config not found: {models_file}")
                self._models_config = {"whisper_models": {}}
        except Exception as e:
            logger.error(f"❌ Failed to load models config: {e}")
            self._models_config = {"whisper_models": {}}
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """
        Get dictionary of available Whisper models.
        
        Returns:
            Dictionary mapping model keys to model info
        """
        return self._models_config.get("whisper_models", {})
    
    def get_current_model_path(self) -> Optional[str]:
        """
        Get the path to the currently selected Whisper model.
        
        Returns:
            Absolute path to model file, or None if no valid model selected
        """
        # Get selected model from settings
        selected_model = self.settings.value("transcription/selected_model", "tiny")
        
        # Get model info
        models = self.get_available_models()
        if selected_model not in models:
            logger.warning(f"⚠️ Selected model '{selected_model}' not in available models")
            # Try to use first available model
            if models:
                selected_model = list(models.keys())[0]
                logger.info(f"🔄 Falling back to first available model: {selected_model}")
            else:
                return None
        
        model_info = models[selected_model]
        filename = model_info.get("filename")
        if not filename:
            logger.error(f"❌ No filename specified for model: {selected_model}")
            return None
        
        # Check in project directory first
        project_path = Path(__file__).parent / filename
        if project_path.exists():
            logger.info(f"✅ Found model in project directory: {project_path}")
            return str(project_path)
        
        # Check in user's Application Support directory
        app_support = Path.home() / "Library" / "Application Support" / "AudioTransLocal" / "models"
        app_support_path = app_support / filename
        if app_support_path.exists():
            logger.info(f"✅ Found model in Application Support: {app_support_path}")
            return str(app_support_path)
        
        # Model file not found
        logger.warning(f"⚠️ Model file not found: {filename}")
        return None
    
    def set_current_model(self, model_key: str) -> bool:
        """
        Set the current Whisper model.
        
        Args:
            model_key: Key of the model to select
            
        Returns:
            True if model was set successfully, False otherwise
        """
        models = self.get_available_models()
        if model_key not in models:
            logger.error(f"❌ Model not available: {model_key}")
            return False
        
        # Save to settings
        self.settings.setValue("transcription/selected_model", model_key)
        
        # Get the actual path
        model_path = self.get_current_model_path()
        if model_path:
            logger.info(f"✅ Selected model: {model_key} -> {model_path}")
            self.model_changed.emit(model_path)
            return True
        else:
            logger.error(f"❌ Model file not found for: {model_key}")
            return False
    
    def validate_current_model(self) -> Dict[str, Any]:
        """
        Validate the currently selected model.
        
        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'path': str or None,
                'model_key': str,
                'model_info': dict,
                'file_size': int or None,
                'error': str or None
            }
        """
        result = {
            'valid': False,
            'path': None,
            'model_key': None,
            'model_info': {},
            'file_size': None,
            'error': None
        }
        
        try:
            # Get current model
            selected_model = self.settings.value("transcription/selected_model", "tiny")
            result['model_key'] = selected_model
            
            models = self.get_available_models()
            if selected_model not in models:
                result['error'] = f"Model '{selected_model}' not in configuration"
                return result
            
            result['model_info'] = models[selected_model]
            
            # Check if file exists
            model_path = self.get_current_model_path()
            if not model_path:
                result['error'] = f"Model file not found: {result['model_info'].get('filename', 'unknown')}"
                return result
            
            result['path'] = model_path
            
            # Get file size
            try:
                file_path = Path(model_path)
                result['file_size'] = file_path.stat().st_size
            except Exception as e:
                result['error'] = f"Cannot access model file: {e}"
                return result
            
            # Validation successful
            result['valid'] = True
            logger.info(f"✅ Model validation successful: {selected_model}")
            
        except Exception as e:
            result['error'] = f"Validation error: {e}"
            logger.error(f"❌ Model validation failed: {e}")
        
        return result
    
    def get_model_download_info(self, model_key: str) -> Optional[Dict[str, Any]]:
        """
        Get download information for a specific model.
        
        Args:
            model_key: Key of the model
            
        Returns:
            Dictionary with download info or None if model not found
        """
        models = self.get_available_models()
        if model_key not in models:
            return None
        
        model_info = models[model_key].copy()
        model_info['key'] = model_key
        return model_info
