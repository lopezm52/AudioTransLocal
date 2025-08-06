"""
Service Factory for Dependency Injection
"""

from app.services.credentials_manager import CredentialsManager
from app.services.whisper_model_manager import WhisperModelManager
from app.services.transcription_service import TranscriptionService


class ServiceFactory:
    """Central service factory for dependency injection"""
    
    def __init__(self):
        self._credentials_manager = None
        self._whisper_model_manager = None
        self._transcription_service = None
    
    def get_credentials_manager(self):
        """Get singleton instance of CredentialsManager"""
        if self._credentials_manager is None:
            self._credentials_manager = CredentialsManager()
        return self._credentials_manager
    
    def get_whisper_model_manager(self):
        """Get singleton instance of WhisperModelManager"""
        if self._whisper_model_manager is None:
            self._whisper_model_manager = WhisperModelManager()
        return self._whisper_model_manager
    
    def get_transcription_service(self):
        """Get singleton instance of TranscriptionService"""
        if self._transcription_service is None:
            # Create the transcription service with the whisper model manager dependency
            whisper_model_manager = self.get_whisper_model_manager()
            self._transcription_service = TranscriptionService(whisper_model_manager)
        return self._transcription_service
