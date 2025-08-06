#!/usr/bin/env python3
"""
AudioTransLocal - Settings Validation Module
Provides robust validation for application settings using Pydantic models.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, validator, ValidationError
from urllib.parse import urlparse


class AudioFolderSettings(BaseModel):
    """Validation model for audio folder settings"""
    folder_path: str = Field(..., min_length=1, description="Path to the audio files folder")
    
    @validator('folder_path')
    def validate_folder_path(cls, v):
        """Validate that the folder path exists and is accessible"""
        if not v or not v.strip():
            raise ValueError("Folder path cannot be empty")
        
        path = Path(v).expanduser()
        if not path.exists():
            raise ValueError(f"Folder does not exist: {v}")
        
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {v}")
        
        # Check if folder is readable
        if not os.access(path, os.R_OK):
            raise ValueError(f"Folder is not readable: {v}")
        
        return str(path)  # Return resolved path
    
    def has_voice_memos_db(self) -> bool:
        """Check if the folder contains a Voice Memos database"""
        recordings_db_path = Path(self.folder_path) / "CloudRecordings.db"  # Correct database name
        return recordings_db_path.exists() and recordings_db_path.is_file()


class APISettings(BaseModel):
    """Validation model for API settings"""
    n8n_api_key: Optional[str] = Field(None, description="n8n API key for workflow integration")
    n8n_base_url: Optional[str] = Field(None, description="Base URL for n8n instance")
    
    @validator('n8n_api_key')
    def validate_api_key(cls, v):
        """Validate API key format"""
        if v is not None:
            v = v.strip()
            if v == "":
                return None  # Empty string becomes None
            
            # Basic format validation - API keys should be reasonable length
            if len(v) < 10:
                raise ValueError("API key appears to be too short (minimum 10 characters)")
            
            if len(v) > 200:
                raise ValueError("API key appears to be too long (maximum 200 characters)")
            
            # Check for obviously invalid characters
            if any(char in v for char in [' ', '\n', '\r', '\t']):
                raise ValueError("API key contains invalid whitespace characters")
        
        return v
    
    @validator('n8n_base_url')
    def validate_base_url(cls, v):
        """Validate base URL format"""
        if v is not None:
            v = v.strip()
            if v == "":
                return None  # Empty string becomes None
            
            # Parse URL to validate format
            try:
                parsed = urlparse(v)
                if not parsed.scheme:
                    raise ValueError("URL must include a scheme (http:// or https://)")
                
                if parsed.scheme not in ['http', 'https']:
                    raise ValueError("URL scheme must be http or https")
                
                if not parsed.netloc:
                    raise ValueError("URL must include a hostname")
                
            except Exception as e:
                raise ValueError(f"Invalid URL format: {str(e)}")
        
        return v


class WhisperModelSettings(BaseModel):
    """Validation model for Whisper model settings"""
    selected_model: str = Field(default="tiny.en", description="Selected Whisper model ID")
    models_directory: Optional[str] = Field(None, description="Directory for storing downloaded models")
    
    @validator('selected_model')
    def validate_model_id(cls, v):
        """Validate model ID format"""
        if not v or not v.strip():
            raise ValueError("Model ID cannot be empty")
        
        # Basic format validation - model IDs should be alphanumeric with dots/dashes
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError("Model ID contains invalid characters")
        
        return v.strip()
    
    @validator('models_directory')
    def validate_models_directory(cls, v):
        """Validate models directory"""
        if v is not None:
            v = v.strip()
            if v == "":
                return None
            
            path = Path(v).expanduser()
            # Create directory if it doesn't exist
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Cannot create models directory: {str(e)}")
            
            # Check if directory is writable
            if not os.access(path, os.W_OK):
                raise ValueError(f"Models directory is not writable: {v}")
            
            return str(path)
        
        return v


class ApplicationSettings(BaseModel):
    """Main application settings model that combines all validation"""
    audio_folder: AudioFolderSettings
    api_settings: APISettings = Field(default_factory=APISettings)
    whisper_model: WhisperModelSettings = Field(default_factory=WhisperModelSettings)
    
    class Config:
        # Allow extra fields for future extensibility
        extra = "allow"


class ValidationResult:
    """Result of a validation operation"""
    
    def __init__(self, is_valid: bool, errors: list = None, warnings: list = None, data: dict = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.data = data or {}
    
    def has_errors(self) -> bool:
        """Check if there are any validation errors"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any validation warnings"""
        return len(self.warnings) > 0
    
    def get_error_message(self) -> str:
        """Get formatted error message"""
        if not self.has_errors():
            return ""
        
        if len(self.errors) == 1:
            return self.errors[0]
        
        return f"Multiple validation errors:\n• " + "\n• ".join(self.errors)
    
    def get_warning_message(self) -> str:
        """Get formatted warning message"""
        if not self.has_warnings():
            return ""
        
        if len(self.warnings) == 1:
            return self.warnings[0]
        
        return f"Multiple warnings:\n• " + "\n• ".join(self.warnings)


class SettingsValidator:
    """Main validator class for application settings"""
    
    @classmethod
    def validate_audio_folder(cls, folder_path: str) -> ValidationResult:
        """Validate audio folder settings"""
        errors = []
        warnings = []
        
        try:
            # Create and validate the model
            folder_settings = AudioFolderSettings(folder_path=folder_path)
            
            # Check for Voice Memos database
            if not folder_settings.has_voice_memos_db():
                warnings.append(
                    "The selected folder does not appear to contain a Voice Memos database (CloudRecordings.db). "
                    "Please ensure you have selected the correct folder."
                )
            
            return ValidationResult(
                is_valid=True,
                warnings=warnings,
                data={"folder_path": folder_settings.folder_path}
            )
            
        except ValidationError as e:
            for error in e.errors():
                field = error.get('loc', [''])[0] if error.get('loc') else ''
                message = error.get('msg', 'Unknown error')
                errors.append(f"{field}: {message}" if field else message)
            
            return ValidationResult(is_valid=False, errors=errors)
        
        except Exception as e:
            return ValidationResult(is_valid=False, errors=[f"Unexpected validation error: {str(e)}"])
    
    @classmethod
    def validate_api_settings(cls, api_key: str = None, base_url: str = None) -> ValidationResult:
        """Validate API settings"""
        errors = []
        warnings = []
        
        try:
            # Create and validate the model
            api_settings = APISettings(n8n_api_key=api_key, n8n_base_url=base_url)
            
            # Add warnings for missing but optional settings
            if not api_settings.n8n_api_key:
                warnings.append("No API key configured. Some features may not be available.")
            
            if not api_settings.n8n_base_url:
                warnings.append("No base URL configured. API calls will use default settings.")
            
            return ValidationResult(
                is_valid=True,
                warnings=warnings,
                data={
                    "api_key": api_settings.n8n_api_key,
                    "base_url": api_settings.n8n_base_url
                }
            )
            
        except ValidationError as e:
            for error in e.errors():
                field = error.get('loc', [''])[0] if error.get('loc') else ''
                message = error.get('msg', 'Unknown error')
                errors.append(f"{field}: {message}" if field else message)
            
            return ValidationResult(is_valid=False, errors=errors)
        
        except Exception as e:
            return ValidationResult(is_valid=False, errors=[f"Unexpected validation error: {str(e)}"])
    
    @classmethod
    def validate_whisper_model(cls, model_id: str, models_dir: str = None) -> ValidationResult:
        """Validate Whisper model settings"""
        errors = []
        warnings = []
        
        try:
            # Create and validate the model
            model_settings = WhisperModelSettings(
                selected_model=model_id,
                models_directory=models_dir
            )
            
            return ValidationResult(
                is_valid=True,
                warnings=warnings,
                data={
                    "selected_model": model_settings.selected_model,
                    "models_directory": model_settings.models_directory
                }
            )
            
        except ValidationError as e:
            for error in e.errors():
                field = error.get('loc', [''])[0] if error.get('loc') else ''
                message = error.get('msg', 'Unknown error')
                errors.append(f"{field}: {message}" if field else message)
            
            return ValidationResult(is_valid=False, errors=errors)
        
        except Exception as e:
            return ValidationResult(is_valid=False, errors=[f"Unexpected validation error: {str(e)}"])
    
    @classmethod
    def validate_all_settings(cls, folder_path: str, api_key: str = None, base_url: str = None, 
                             model_id: str = "tiny.en", models_dir: str = None) -> ValidationResult:
        """Validate all application settings together"""
        all_errors = []
        all_warnings = []
        all_data = {}
        
        # Validate each component
        folder_result = cls.validate_audio_folder(folder_path)
        api_result = cls.validate_api_settings(api_key, base_url)
        model_result = cls.validate_whisper_model(model_id, models_dir)
        
        # Collect results
        if folder_result.has_errors():
            all_errors.extend([f"Audio Folder: {err}" for err in folder_result.errors])
        else:
            all_data.update(folder_result.data)
        
        if folder_result.has_warnings():
            all_warnings.extend([f"Audio Folder: {warn}" for warn in folder_result.warnings])
        
        if api_result.has_errors():
            all_errors.extend([f"API Settings: {err}" for err in api_result.errors])
        else:
            all_data.update(api_result.data)
        
        if api_result.has_warnings():
            all_warnings.extend([f"API Settings: {warn}" for warn in api_result.warnings])
        
        if model_result.has_errors():
            all_errors.extend([f"Whisper Model: {err}" for err in model_result.errors])
        else:
            all_data.update(model_result.data)
        
        if model_result.has_warnings():
            all_warnings.extend([f"Whisper Model: {warn}" for warn in model_result.warnings])
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            data=all_data
        )
