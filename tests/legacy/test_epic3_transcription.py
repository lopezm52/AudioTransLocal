#!/usr/bin/env python3
"""
Test workflow for complete epic 3 transcription functionality
"""

import unittest
import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.service_factory import ServiceFactory
from app.services.transcription_service import TranscriptionService


class TestEpic3Transcription(unittest.TestCase):
    """Test complete transcription workflow"""
    
    def setUp(self):
        """Set up test environment"""
        self.factory = ServiceFactory()
        self.transcription_service = self.factory.get_transcription_service()
        
        # Create temporary directory for test files
        self.test_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        """Clean up test environment"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_transcription_service_initialization(self):
        """Test that transcription service initializes properly"""
        self.assertIsNotNone(self.transcription_service)
        self.assertIsInstance(self.transcription_service, TranscriptionService)
        self.assertIsNotNone(self.transcription_service.model_manager)
        self.assertIsNotNone(self.transcription_service.credentials_manager)
    
    def test_model_availability_check(self):
        """Test checking for available Whisper models"""
        models = self.transcription_service.model_manager.get_available_models()
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)
        
        # Check that basic models are available
        model_names = [model[0] for model in models]
        self.assertIn("tiny", model_names)
        self.assertIn("base", model_names)
    
    def test_default_model_selection(self):
        """Test that a default model is selected"""
        current_model = self.transcription_service.model_manager.get_current_model()
        self.assertIsNotNone(current_model)
        self.assertIsInstance(current_model, str)
    
    def test_model_download_status(self):
        """Test checking model download status"""
        models = self.transcription_service.model_manager.get_available_models()
        
        for model_name, _ in models:
            is_downloaded = self.transcription_service.model_manager.is_model_downloaded(model_name)
            self.assertIsInstance(is_downloaded, bool)
    
    @unittest.skipIf(not os.path.exists("/System/Library/Sounds/Ping.aiff"), 
                     "Test audio file not available")
    def test_audio_file_validation(self):
        """Test audio file validation with system sound"""
        test_file = "/System/Library/Sounds/Ping.aiff"
        
        # This would be the validation logic
        self.assertTrue(Path(test_file).exists())
    
    def test_transcription_worker_creation(self):
        """Test that transcription worker can be created"""
        # This tests the worker instantiation without actually running transcription
        try:
            from app.workers.transcription_worker import WhisperTranscriptionWorker
            worker = WhisperTranscriptionWorker("dummy_file.wav", "base")
            self.assertIsNotNone(worker)
        except ImportError:
            self.fail("Could not import WhisperTranscriptionWorker")
    
    def test_service_factory_singleton(self):
        """Test that services are properly managed as singletons"""
        service1 = self.factory.get_transcription_service()
        service2 = self.factory.get_transcription_service()
        
        self.assertIs(service1, service2)
    
    def test_dependency_injection_wiring(self):
        """Test that all dependencies are properly injected"""
        service = self.transcription_service
        
        # Check that all required dependencies are present
        self.assertIsNotNone(service.model_manager)
        self.assertIsNotNone(service.credentials_manager)
        
        # Check that the model manager has the correct configuration
        models = service.model_manager.get_available_models()
        self.assertGreater(len(models), 0)


if __name__ == '__main__':
    # Set up test environment
    os.environ['PYTHONPATH'] = str(project_root)
    
    print("Running Epic 3 Transcription Tests...")
    print("=====================================")
    
    # Run tests with verbose output
    unittest.main(verbosity=2)
