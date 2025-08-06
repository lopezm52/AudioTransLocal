#!/usr/bin/env python3
"""
Test script to verify search functionality and project integrity
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_project_structure():
    """Test that the project structure is intact"""
    print("Testing Project Structure")
    print("=" * 25)
    
    # Check main files
    main_files = [
        "main.py",
        "config.py",
        "audio_utils.py"
    ]
    
    for file_name in main_files:
        file_path = project_root / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"✅ {file_name}: {size} bytes")
        else:
            print(f"❌ {file_name}: Missing")
    
    # Check app structure
    app_dir = project_root / "app"
    if app_dir.exists():
        print(f"✅ app/ directory exists")
        
        subdirs = ["core", "services", "views", "workers"]
        for subdir in subdirs:
            subdir_path = app_dir / subdir
            if subdir_path.exists():
                init_file = subdir_path / "__init__.py"
                init_status = "✅" if init_file.exists() else "❌"
                print(f"  {init_status} app/{subdir}/ (__init__.py)")
            else:
                print(f"  ❌ app/{subdir}/ missing")
    else:
        print("❌ app/ directory missing")


def test_service_imports():
    """Test that services can be imported"""
    print("\nTesting Service Imports")
    print("=" * 23)
    
    services = [
        ("app.core.service_factory", "ServiceFactory"),
        ("app.services.transcription_service", "TranscriptionService"),
        ("app.services.whisper_model_manager", "WhisperModelManager"),
        ("app.services.credentials_manager", "CredentialsManager"),
        ("app.services.voice_memo_parser", "VoiceMemoParser")
    ]
    
    for module_name, class_name in services:
        try:
            module = __import__(module_name, fromlist=[class_name])
            service_class = getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}")
        except ImportError as e:
            print(f"❌ {module_name}.{class_name}: {e}")
        except AttributeError as e:
            print(f"❌ {module_name}.{class_name}: {e}")


def test_dependency_injection():
    """Test the dependency injection system"""
    print("\nTesting Dependency Injection")
    print("=" * 28)
    
    try:
        from app.core.service_factory import ServiceFactory
        
        factory = ServiceFactory()
        print("✅ ServiceFactory created")
        
        # Test service creation
        services = [
            ("TranscriptionService", factory.get_transcription_service),
            ("WhisperModelManager", factory.get_whisper_model_manager),
            ("CredentialsManager", factory.get_credentials_manager),
            ("VoiceMemoParser", factory.get_voice_memo_parser)
        ]
        
        for service_name, getter in services:
            try:
                service = getter()
                print(f"✅ {service_name} created")
            except Exception as e:
                print(f"❌ {service_name}: {e}")
        
        # Test singleton behavior
        try:
            service1 = factory.get_transcription_service()
            service2 = factory.get_transcription_service()
            if service1 is service2:
                print("✅ Singleton behavior verified")
            else:
                print("❌ Singleton behavior failed")
        except Exception as e:
            print(f"❌ Singleton test failed: {e}")
            
    except ImportError as e:
        print(f"❌ Could not import ServiceFactory: {e}")


def test_view_imports():
    """Test that views can be imported"""
    print("\nTesting View Imports")
    print("=" * 20)
    
    views = [
        ("app.views.main_window", "MainWindow"),
        ("app.views.preferences_window", "PreferencesWindow"),
        ("app.views.voice_memo_view", "VoiceMemoView"),
        ("app.views.welcome_dialog", "WelcomeDialog")
    ]
    
    for module_name, class_name in views:
        try:
            module = __import__(module_name, fromlist=[class_name])
            view_class = getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}")
        except ImportError as e:
            print(f"❌ {module_name}.{class_name}: {e}")
        except AttributeError as e:
            print(f"❌ {module_name}.{class_name}: {e}")


def test_worker_imports():
    """Test that workers can be imported"""
    print("\nTesting Worker Imports")
    print("=" * 22)
    
    workers = [
        ("app.workers.transcription_worker", "WhisperTranscriptionWorker"),
        ("app.workers.download_worker", "DownloadWorker")
    ]
    
    for module_name, class_name in workers:
        try:
            module = __import__(module_name, fromlist=[class_name])
            worker_class = getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}")
        except ImportError as e:
            print(f"❌ {module_name}.{class_name}: {e}")
        except AttributeError as e:
            print(f"❌ {module_name}.{class_name}: {e}")


def test_main_application():
    """Test that the main application can be imported"""
    print("\nTesting Main Application")
    print("=" * 24)
    
    try:
        import main
        if hasattr(main, 'AudioTransLocalApp'):
            print("✅ main.AudioTransLocalApp found")
        else:
            print("❌ main.AudioTransLocalApp not found")
            
        if hasattr(main, 'main'):
            print("✅ main.main() function found")
        else:
            print("❌ main.main() function not found")
            
    except ImportError as e:
        print(f"❌ Could not import main: {e}")


def count_files():
    """Count and report on project files"""
    print("\nFile Statistics")
    print("=" * 15)
    
    # Count Python files
    py_files = list(project_root.rglob("*.py"))
    py_files = [f for f in py_files if ".venv" not in str(f)]
    py_files = [f for f in py_files if "__pycache__" not in str(f)]
    
    print(f"Total Python files: {len(py_files)}")
    
    # Check for empty files
    empty_files = []
    for file_path in py_files:
        try:
            size = file_path.stat().st_size
            if size == 0:
                empty_files.append(str(file_path))
        except Exception:
            pass
    
    if empty_files:
        print(f"Empty files: {len(empty_files)}")
        for empty_file in empty_files:
            rel_path = Path(empty_file).relative_to(project_root)
            print(f"  - {rel_path}")
    else:
        print("✅ No empty Python files found")


def main():
    """Run all verification tests"""
    print("AudioTransLocal - Project Verification")
    print("=" * 37)
    print(f"Project root: {project_root}")
    print()
    
    test_project_structure()
    test_service_imports()
    test_dependency_injection()
    test_view_imports()
    test_worker_imports()
    test_main_application()
    count_files()
    
    print("\nVerification Complete")
    print("=" * 21)


if __name__ == "__main__":
    main()
