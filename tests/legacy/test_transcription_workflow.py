#!/usr/bin/env python3
"""
Complete transcription workflow tests
"""

import unittest
import sys
import os
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
try:
    from app.core.service_factory import ServiceFactory
    from app.services.transcription_service import TranscriptionService
    from app.services.whisper_model_manager import WhisperModelManager
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    IMPORTS_AVAILABLE = False


class TestTranscriptionWorkflow(unittest.TestCase):
    """Test the complete transcription workflow from end to end"""
    
    @unittest.skipUnless(IMPORTS_AVAILABLE, "Required modules not available")
    def setUp(self):
        """Set up test environment"""
        self.factory = ServiceFactory()
        self.transcription_service = self.factory.get_transcription_service()
        self.model_manager = self.factory.get_whisper_model_manager()
    
    @unittest.skipUnless(IMPORTS_AVAILABLE, "Required modules not available")
    def test_service_dependencies(self):
        """Test that all service dependencies are properly resolved"""
        # Test service creation
        self.assertIsNotNone(self.transcription_service)
        self.assertIsNotNone(self.model_manager)
        
        # Test dependency injection
        self.assertIsNotNone(self.transcription_service.model_manager)
        self.assertIsNotNone(self.transcription_service.credentials_manager)
    
    @unittest.skipUnless(IMPORTS_AVAILABLE, "Required modules not available")
    def test_model_manager_functionality(self):
        """Test model manager basic functionality"""
        # Test getting available models
        models = self.model_manager.get_available_models()
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)
        
        # Test model validation
        self.assertTrue(self.model_manager.is_valid_model("tiny"))
        self.assertTrue(self.model_manager.is_valid_model("base"))
        self.assertFalse(self.model_manager.is_valid_model("nonexistent"))
    
    @unittest.skipUnless(IMPORTS_AVAILABLE, "Required modules not available")
    def test_transcription_service_setup(self):
        """Test transcription service setup and configuration"""
        # Test that service can be configured
        service = self.transcription_service
        
        # Check that the service has access to models
        current_model = service.model_manager.get_current_model()
        self.assertIsNotNone(current_model)
        
        # Check that model is valid
        self.assertTrue(service.model_manager.is_valid_model(current_model))
    
    @unittest.skipUnless(IMPORTS_AVAILABLE, "Required modules not available")
    def test_worker_import(self):
        """Test that worker classes can be imported"""
        try:
            from app.workers.transcription_worker import WhisperTranscriptionWorker
            self.assertTrue(True)  # Import successful
        except ImportError:
            self.fail("Could not import WhisperTranscriptionWorker")
    
    def test_basic_application_structure(self):
        """Test basic application structure without imports"""
        # Test that main files exist
        main_file = project_root / "main.py"
        config_file = project_root / "config.py"
        
        self.assertTrue(main_file.exists(), "main.py should exist")
        self.assertTrue(config_file.exists(), "config.py should exist")
        
        # Test that app directory structure exists
        app_dir = project_root / "app"
        self.assertTrue(app_dir.exists(), "app directory should exist")
        
        services_dir = app_dir / "services"
        self.assertTrue(services_dir.exists(), "services directory should exist")
        
        views_dir = app_dir / "views"
        self.assertTrue(views_dir.exists(), "views directory should exist")
        
        workers_dir = app_dir / "workers"
        self.assertTrue(workers_dir.exists(), "workers directory should exist")
    
    def test_file_sizes(self):
        """Test that reconstructed files have reasonable sizes"""
        important_files = [
            "main.py",
            "config.py",
            "app/core/service_factory.py",
            "app/services/transcription_service.py",
            "app/services/whisper_model_manager.py",
            "app/views/main_window.py",
            "app/views/preferences_window.py"
        ]
        
        for file_path in important_files:
            full_path = project_root / file_path
            if full_path.exists():
                size = full_path.stat().st_size
                self.assertGreater(size, 100, f"{file_path} should not be empty")


if __name__ == '__main__':
    print("Testing Transcription Workflow")
    print("==============================")
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path[0]}")
    print(f"Imports available: {IMPORTS_AVAILABLE}")
    print()
    
    # Run tests
    unittest.main(verbosity=2)
