#!/usr/bin/env python3
"""
Tests for the Dependency Injection architecture
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test imports
try:
    from app.core.service_factory import ServiceFactory
    from app.services.transcription_service import TranscriptionService
    from app.services.whisper_model_manager import WhisperModelManager
    from app.services.credentials_manager import CredentialsManager
    from app.services.voice_memo_parser import VoiceMemoParser
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    IMPORTS_AVAILABLE = False


class TestDependencyInjection(unittest.TestCase):
    """Test the Dependency Injection implementation"""
    
    @unittest.skipUnless(IMPORTS_AVAILABLE, "Required modules not available")
    def setUp(self):
        """Set up test environment"""
        self.factory = ServiceFactory()
    
    @unittest.skipUnless(IMPORTS_AVAILABLE, "Required modules not available")
    def test_service_factory_creation(self):
        """Test that ServiceFactory can be created"""
        self.assertIsNotNone(self.factory)
        self.assertIsInstance(self.factory, ServiceFactory)
    
    @unittest.skipUnless(IMPORTS_AVAILABLE, "Required modules not available")
    def test_service_singleton_behavior(self):
        """Test that services are properly managed as singletons"""
        # Get the same service multiple times
        service1 = self.factory.get_transcription_service()
        service2 = self.factory.get_transcription_service()
        
        # Should be the same instance
        self.assertIs(service1, service2)
        
        # Test with other services
        model_manager1 = self.factory.get_whisper_model_manager()
        model_manager2 = self.factory.get_whisper_model_manager()
        self.assertIs(model_manager1, model_manager2)
    
    @unittest.skipUnless(IMPORTS_AVAILABLE, "Required modules not available")
    def test_service_types(self):
        """Test that services are of the correct types"""
        transcription_service = self.factory.get_transcription_service()
        model_manager = self.factory.get_whisper_model_manager()
        credentials_manager = self.factory.get_credentials_manager()
        parser = self.factory.get_voice_memo_parser()
        
        self.assertIsInstance(transcription_service, TranscriptionService)
        self.assertIsInstance(model_manager, WhisperModelManager)
        self.assertIsInstance(credentials_manager, CredentialsManager)
        self.assertIsInstance(parser, VoiceMemoParser)
    
    @unittest.skipUnless(IMPORTS_AVAILABLE, "Required modules not available")
    def test_dependency_injection(self):
        """Test that dependencies are properly injected"""
        transcription_service = self.factory.get_transcription_service()
        
        # Check that dependencies are injected
        self.assertIsNotNone(transcription_service.model_manager)
        self.assertIsNotNone(transcription_service.credentials_manager)
        
        # Check that injected dependencies are the same as factory-created ones
        self.assertIs(transcription_service.model_manager, self.factory.get_whisper_model_manager())
        self.assertIs(transcription_service.credentials_manager, self.factory.get_credentials_manager())
    
    @unittest.skipUnless(IMPORTS_AVAILABLE, "Required modules not available")
    def test_service_initialization(self):
        """Test that services are properly initialized"""
        services = [
            self.factory.get_transcription_service(),
            self.factory.get_whisper_model_manager(), 
            self.factory.get_credentials_manager(),
            self.factory.get_voice_memo_parser()
        ]
        
        # All services should be created without errors
        for service in services:
            self.assertIsNotNone(service)
    
    def test_architecture_without_imports(self):
        """Test basic architecture without requiring imports"""
        # Test that the expected file structure exists
        expected_files = [
            "app/core/service_factory.py",
            "app/services/transcription_service.py",
            "app/services/whisper_model_manager.py",
            "app/services/credentials_manager.py",
            "app/services/voice_memo_parser.py"
        ]
        
        for file_path in expected_files:
            full_path = project_root / file_path
            self.assertTrue(full_path.exists(), f"Expected file {file_path} should exist")
            
            # Check that files are not empty
            size = full_path.stat().st_size
            self.assertGreater(size, 100, f"File {file_path} should not be empty")


class TestServiceFactoryInterface(unittest.TestCase):
    """Test the ServiceFactory interface"""
    
    @unittest.skipUnless(IMPORTS_AVAILABLE, "Required modules not available")
    def test_factory_methods_exist(self):
        """Test that all expected factory methods exist"""
        factory = ServiceFactory()
        
        expected_methods = [
            'get_transcription_service',
            'get_whisper_model_manager',
            'get_credentials_manager',
            'get_voice_memo_parser'
        ]
        
        for method_name in expected_methods:
            self.assertTrue(hasattr(factory, method_name), 
                          f"ServiceFactory should have method {method_name}")
            
            method = getattr(factory, method_name)
            self.assertTrue(callable(method), 
                          f"{method_name} should be callable")


if __name__ == '__main__':
    print("Testing Dependency Injection Architecture")
    print("=========================================")
    print(f"Project root: {project_root}")
    print(f"Imports available: {IMPORTS_AVAILABLE}")
    print()
    
    unittest.main(verbosity=2)
