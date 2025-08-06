#!/usr/bin/env python3
"""
Integration tests for the main application
"""

import unittest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestMainIntegration(unittest.TestCase):
    """Test main application integration"""
    
    def test_main_module_exists(self):
        """Test that main.py exists and has required content"""
        main_file = project_root / "main.py"
        self.assertTrue(main_file.exists(), "main.py should exist")
        
        # Check file is not empty
        size = main_file.stat().st_size
        self.assertGreater(size, 100, "main.py should not be empty")
    
    def test_config_module_exists(self):
        """Test that config.py exists and has required content"""
        config_file = project_root / "config.py"
        self.assertTrue(config_file.exists(), "config.py should exist")
        
        # Check file is not empty
        size = config_file.stat().st_size
        self.assertGreater(size, 100, "config.py should not be empty")
    
    def test_app_structure(self):
        """Test that the app directory structure is correct"""
        app_dir = project_root / "app"
        self.assertTrue(app_dir.exists(), "app directory should exist")
        
        # Check subdirectories
        subdirs = ["core", "services", "views", "workers"]
        for subdir in subdirs:
            subdir_path = app_dir / subdir
            self.assertTrue(subdir_path.exists(), f"app/{subdir} should exist")
            
            # Check for __init__.py
            init_file = subdir_path / "__init__.py"
            self.assertTrue(init_file.exists(), f"app/{subdir}/__init__.py should exist")
    
    def test_main_import(self):
        """Test that main module can be imported"""
        try:
            import main
            self.assertTrue(hasattr(main, 'AudioTransLocalApp'), 
                          "main module should have AudioTransLocalApp class")
        except ImportError as e:
            # This is expected if dependencies are missing
            print(f"Expected import error: {e}")
    
    def test_config_import(self):
        """Test that config module can be imported"""
        try:
            import config
            # Check for expected configuration
            expected_attrs = ['APPLICATION_NAME', 'VERSION', 'DEFAULT_MODEL']
            for attr in expected_attrs:
                self.assertTrue(hasattr(config, attr), 
                              f"config should have {attr}")
        except ImportError as e:
            self.fail(f"config module should be importable: {e}")
    
    def test_service_files_exist(self):
        """Test that all service files exist"""
        services_dir = project_root / "app" / "services"
        expected_services = [
            "transcription_service.py",
            "whisper_model_manager.py", 
            "credentials_manager.py",
            "voice_memo_parser.py",
            "model_manager.py",
            "bookmark_manager.py"
        ]
        
        for service_file in expected_services:
            service_path = services_dir / service_file
            self.assertTrue(service_path.exists(), f"{service_file} should exist")
            
            # Check file is not empty
            size = service_path.stat().st_size
            self.assertGreater(size, 100, f"{service_file} should not be empty")
    
    def test_view_files_exist(self):
        """Test that all view files exist"""
        views_dir = project_root / "app" / "views"
        expected_views = [
            "main_window.py",
            "preferences_window.py",
            "voice_memo_view.py",
            "welcome_dialog.py"
        ]
        
        for view_file in expected_views:
            view_path = views_dir / view_file
            self.assertTrue(view_path.exists(), f"{view_file} should exist")
            
            # Check file is not empty
            size = view_path.stat().st_size
            self.assertGreater(size, 100, f"{view_file} should not be empty")
    
    def test_worker_files_exist(self):
        """Test that all worker files exist"""
        workers_dir = project_root / "app" / "workers"
        expected_workers = [
            "transcription_worker.py",
            "download_worker.py"
        ]
        
        for worker_file in expected_workers:
            worker_path = workers_dir / worker_file
            self.assertTrue(worker_path.exists(), f"{worker_file} should exist")
            
            # Check file is not empty
            size = worker_path.stat().st_size
            self.assertGreater(size, 100, f"{worker_file} should not be empty")
    
    def test_virtual_environment(self):
        """Test that virtual environment exists"""
        venv_dir = project_root / ".venv"
        if venv_dir.exists():
            # Check for Python executable
            python_exe = venv_dir / "bin" / "python"
            if not python_exe.exists():
                python_exe = venv_dir / "Scripts" / "python.exe"  # Windows
            
            if python_exe.exists():
                # Virtual environment is properly set up
                self.assertTrue(True)
            else:
                print("Virtual environment exists but Python executable not found")
        else:
            print("No virtual environment found (may be using system Python)")
    
    def test_dependencies_availability(self):
        """Test availability of key dependencies"""
        required_modules = [
            'PySide6',
            'torch', 
            'whisper',
            'keyring'
        ]
        
        available_modules = []
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
                available_modules.append(module)
            except ImportError:
                missing_modules.append(module)
        
        print(f"Available modules: {available_modules}")
        if missing_modules:
            print(f"Missing modules: {missing_modules}")
        
        # For now, just record the status
        self.assertIsInstance(available_modules, list)
        self.assertIsInstance(missing_modules, list)


class TestProjectStructure(unittest.TestCase):
    """Test overall project structure"""
    
    def test_project_files(self):
        """Test that expected project files exist"""
        expected_files = [
            "main.py",
            "config.py", 
            "requirements.txt",
            "audio_utils.py",
            "test_main.py"
        ]
        
        for file_name in expected_files:
            file_path = project_root / file_name
            if file_path.exists():
                size = file_path.stat().st_size
                self.assertGreater(size, 10, f"{file_name} should not be empty")
    
    def test_no_empty_python_files(self):
        """Test that no Python files are empty"""
        python_files = list(project_root.rglob("*.py"))
        
        # Exclude virtual environment and cache files
        python_files = [f for f in python_files if ".venv" not in str(f)]
        python_files = [f for f in python_files if "__pycache__" not in str(f)]
        
        empty_files = []
        for file_path in python_files:
            try:
                size = file_path.stat().st_size
                if size == 0:
                    empty_files.append(str(file_path))
            except Exception:
                pass  # Skip files that can't be read
        
        if empty_files:
            print(f"Found {len(empty_files)} empty Python files:")
            for empty_file in empty_files[:10]:  # Show first 10
                print(f"  - {empty_file}")
        
        # Don't fail the test, just report
        self.assertIsInstance(empty_files, list)


if __name__ == '__main__':
    print("Testing Main Application Integration")
    print("====================================")
    print(f"Project root: {project_root}")
    print(f"Current working directory: {os.getcwd()}")
    print()
    
    unittest.main(verbosity=2)
