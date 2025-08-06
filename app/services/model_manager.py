#!/usr/bin/env python3
"""
Model manager service for handling different model backends
"""

from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Generic model manager that can be extended for specific model types.
    Currently focused on Whisper models but designed to be extensible.
    """
    
    def __init__(self):
        """Initialize the model manager"""
        self._models: Dict[str, Dict[str, Any]] = {}
        self._current_model: Optional[str] = None
        self._model_cache_dir = Path.home() / ".cache" / "audiotranslocal" / "models"
        self._model_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize available models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize the available models catalog"""
        # This is a base implementation that can be overridden
        self._models = {
            "default": {
                "name": "default",
                "description": "Default model",
                "size": "unknown",
                "capabilities": ["transcription"],
                "downloaded": False,
                "path": None
            }
        }
        self._current_model = "default"
    
    def get_available_models(self) -> List[Tuple[str, str]]:
        """
        Get list of available models.
        
        Returns:
            List of (model_name, description) tuples
        """
        return [(name, info["description"]) for name, info in self._models.items()]
    
    def get_current_model(self) -> Optional[str]:
        """Get the currently selected model"""
        return self._current_model
    
    def set_current_model(self, model_name: str) -> bool:
        """
        Set the current model.
        
        Args:
            model_name: Name of the model to set as current
            
        Returns:
            True if model was set successfully, False otherwise
        """
        if model_name in self._models:
            self._current_model = model_name
            logger.info(f"Set current model to: {model_name}")
            return True
        else:
            logger.warning(f"Model not found: {model_name}")
            return False
    
    def is_valid_model(self, model_name: str) -> bool:
        """
        Check if a model name is valid.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if model is valid, False otherwise
        """
        return model_name in self._models
    
    def is_model_downloaded(self, model_name: str) -> bool:
        """
        Check if a model is downloaded and available locally.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if model is downloaded, False otherwise
        """
        if model_name not in self._models:
            return False
        
        model_info = self._models[model_name]
        return model_info.get("downloaded", False)
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Dictionary with model information, or None if model not found
        """
        return self._models.get(model_name)
    
    def get_model_path(self, model_name: str) -> Optional[Path]:
        """
        Get the local path to a downloaded model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Path to the model file, or None if not available
        """
        if model_name not in self._models:
            return None
        
        model_info = self._models[model_name]
        path = model_info.get("path")
        
        if path:
            return Path(path)
        return None
    
    def download_model(self, model_name: str, progress_callback=None) -> bool:
        """
        Download a model to local storage.
        
        Args:
            model_name: Name of the model to download
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if download was successful, False otherwise
        """
        if model_name not in self._models:
            logger.error(f"Unknown model: {model_name}")
            return False
        
        if self.is_model_downloaded(model_name):
            logger.info(f"Model already downloaded: {model_name}")
            return True
        
        # Base implementation - subclasses should override this
        logger.warning("Base ModelManager download_model called - should be overridden")
        return False
    
    def remove_model(self, model_name: str) -> bool:
        """
        Remove a downloaded model from local storage.
        
        Args:
            model_name: Name of the model to remove
            
        Returns:
            True if removal was successful, False otherwise
        """
        if model_name not in self._models:
            logger.error(f"Unknown model: {model_name}")
            return False
        
        model_info = self._models[model_name]
        model_path = model_info.get("path")
        
        if model_path and Path(model_path).exists():
            try:
                Path(model_path).unlink()
                model_info["downloaded"] = False
                model_info["path"] = None
                logger.info(f"Removed model: {model_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to remove model {model_name}: {e}")
                return False
        else:
            logger.warning(f"Model not found on disk: {model_name}")
            return False
    
    def get_download_status(self) -> Dict[str, bool]:
        """
        Get download status for all models.
        
        Returns:
            Dictionary mapping model names to download status
        """
        return {name: info["downloaded"] for name, info in self._models.items()}
    
    def get_cache_directory(self) -> Path:
        """Get the directory where models are cached"""
        return self._model_cache_dir
    
    def clear_cache(self) -> bool:
        """
        Clear all cached models.
        
        Returns:
            True if cache was cleared successfully, False otherwise
        """
        try:
            import shutil
            if self._model_cache_dir.exists():
                shutil.rmtree(self._model_cache_dir)
                self._model_cache_dir.mkdir(parents=True, exist_ok=True)
                
                # Update model states
                for model_info in self._models.values():
                    model_info["downloaded"] = False
                    model_info["path"] = None
                
                logger.info("Cleared model cache")
                return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    def get_total_cache_size(self) -> int:
        """
        Get total size of cached models in bytes.
        
        Returns:
            Total size in bytes
        """
        total_size = 0
        
        try:
            for file_path in self._model_cache_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.error(f"Failed to calculate cache size: {e}")
        
        return total_size
