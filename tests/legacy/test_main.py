#!/usr/bin/env python3
"""
Basic tests for AudioTransLocal application
"""

import unittest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.service_factory import ServiceFactory
from app.services.credentials_manager import CredentialsManager
from app.services.whisper_model_manager import WhisperModelManager
from app.services.voice_memo_parser import VoiceMemoParser
from app.services.transcription_service import TranscriptionService


class TestServiceFactory(unittest.TestCase):
    """Test the ServiceFactory dependency injection"""
    
    def setUp(self):
        self.factory = ServiceFactory()
    
    def test_singleton_behavior(self):
        """Test that services are singletons"""
        service1 = self.factory.get_credentials_manager()
        service2 = self.factory.get_credentials_manager()
        self.assertIs(service1, service2)
    
    def test_all_services_available(self):
        """Test that all expected services are available"""
        # Should not raise exceptions
        credentials = self.factory.get_credentials_manager()
        model_manager = self.factory.get_whisper_model_manager()
        parser = self.factory.get_voice_memo_parser()
        transcription = self.factory.get_transcription_service()
        
        self.assertIsInstance(credentials, CredentialsManager)
        self.assertIsInstance(model_manager, WhisperModelManager)
        self.assertIsInstance(parser, VoiceMemoParser)
        self.assertIsInstance(transcription, TranscriptionService)


class TestCredentialsManager(unittest.TestCase):
    """Test credentials management"""
    
    def setUp(self):
        self.manager = CredentialsManager()
    
    def test_openai_key_methods(self):
        """Test OpenAI API key management"""
        # These should not raise exceptions
        key = self.manager.get_openai_api_key()
        self.assertIsInstance(key, (str, type(None)))
        
        # Test setting (but don't actually set to avoid keyring pollution)
        # self.manager.set_openai_api_key("test_key")


class TestWhisperModelManager(unittest.TestCase):
    """Test Whisper model management"""
    
    def setUp(self):
        self.manager = WhisperModelManager()
    
    def test_available_models(self):
        """Test getting available models"""
        models = self.manager.get_available_models()
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)
        
        # Check model structure
        for model in models:
            self.assertIsInstance(model, tuple)
            self.assertEqual(len(model), 2)  # (name, description)
    
    def test_model_validation(self):
        """Test model name validation"""
        # Valid models
        self.assertTrue(self.manager.is_valid_model("tiny"))
        self.assertTrue(self.manager.is_valid_model("base"))
        
        # Invalid model
        self.assertFalse(self.manager.is_valid_model("nonexistent"))


class TestVoiceMemoParser(unittest.TestCase):
    """Test voice memo parsing"""
    
    def setUp(self):
        self.parser = VoiceMemoParser()
    
    def test_file_filtering(self):
        """Test audio file filtering"""
        # Mock file list
        files = [
            "audio.m4a",
            "document.txt", 
            "recording.wav",
            "video.mp4",
            "image.jpg"
        ]
        
        audio_files = [f for f in files if self.parser._is_audio_file(f)]
        expected = ["audio.m4a", "recording.wav", "video.mp4"]
        
        self.assertEqual(sorted(audio_files), sorted(expected))


class TestTranscriptionService(unittest.TestCase):
    """Test transcription service"""
    
    def setUp(self):
        factory = ServiceFactory()
        self.service = factory.get_transcription_service()
    
    def test_service_initialization(self):
        """Test that service initializes properly"""
        self.assertIsNotNone(self.service)
        self.assertIsNotNone(self.service.model_manager)
        self.assertIsNotNone(self.service.credentials_manager)


class TestApplicationIntegration(unittest.TestCase):
    """Test application integration"""
    
    def test_import_main_module(self):
        """Test that main module can be imported"""
        try:
            import main
            self.assertTrue(hasattr(main, 'AudioTransLocalApp'))
        except ImportError as e:
            self.fail(f"Could not import main module: {e}")
    
    def test_config_available(self):
        """Test that config is available"""
        try:
            import config
            self.assertTrue(hasattr(config, 'APPLICATION_NAME'))
        except ImportError as e:
            self.fail(f"Could not import config: {e}")


if __name__ == '__main__':
    # Set up test environment
    os.environ['PYTHONPATH'] = str(project_root)
    
    # Run tests
    unittest.main(verbosity=2)
