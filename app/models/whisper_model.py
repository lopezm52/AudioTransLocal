"""
Pydantic models for Whisper model configuration

This module provides type-safe models for handling Whisper model
configuration data, replacing raw dictionary usage with validated
data structures.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Union
from pydantic import BaseModel, HttpUrl, Field


class WhisperModel(BaseModel):
    """
    Pydantic model for individual Whisper model configuration.
    
    Provides validation and type safety for model metadata.
    """
    display_name: str = Field(..., description="Human-readable model name")
    filename: str = Field(..., description="Local filename for the model")
    download_url: HttpUrl = Field(..., description="URL for downloading the model")
    size_mb: int = Field(..., gt=0, description="Model size in megabytes")
    sha256: str = Field(..., min_length=64, max_length=64, description="SHA256 checksum")
    description: str = Field(..., description="Detailed model description")

    class Config:
        """Pydantic configuration"""
        # Allow extra fields for future extensibility
        extra = "allow"
        # Use enum values for serialization
        use_enum_values = True


class WhisperModelConfig(BaseModel):
    """
    Container for all Whisper model configurations.
    
    Provides validation and convenient access to model data.
    """
    whisper_models: Dict[str, WhisperModel] = Field(
        ..., 
        description="Dictionary of model_id -> WhisperModel"
    )

    @classmethod
    def load_from_json(cls, file_path: Union[str, Path]) -> 'WhisperModelConfig':
        """
        Load and validate model configuration from JSON file.
        
        Args:
            file_path: Path to the whisper_models.json file (str or Path)
            
        Returns:
            Validated WhisperModelConfig instance
            
        Raises:
            FileNotFoundError: If the JSON file doesn't exist
            ValidationError: If the JSON data doesn't match the schema
        """
        # Convert to Path object for consistent handling
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Model configuration file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls(**data)

    def get_model(self, model_id: str) -> Optional[WhisperModel]:
        """
        Get a specific model by ID.
        
        Args:
            model_id: The model identifier
            
        Returns:
            WhisperModel instance or None if not found
        """
        return self.whisper_models.get(model_id)

    def get_model_ids(self) -> list[str]:
        """Get list of all available model IDs."""
        return list(self.whisper_models.keys())

    def get_models_by_size(self, max_size_mb: Optional[int] = None) -> Dict[str, WhisperModel]:
        """
        Get models filtered by maximum size.
        
        Args:
            max_size_mb: Maximum size in MB, or None for no limit
            
        Returns:
            Dictionary of filtered models
        """
        if max_size_mb is None:
            return self.whisper_models
        
        return {
            model_id: model 
            for model_id, model in self.whisper_models.items() 
            if model.size_mb <= max_size_mb
        }

    class Config:
        """Pydantic configuration"""
        extra = "allow"
        use_enum_values = True
