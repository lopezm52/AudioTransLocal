#!/usr/bin/env python3
"""
Test script for AudioTransLocal validation system
"""

import os
from pathlib import Path
from validation import SettingsValidator

def test_validation_system():
    """Test the validation system with various inputs"""
    
    print("🧪 AudioTransLocal Validation System Tests")
    print("=" * 50)
    
    # Test 1: Valid folder (Downloads)
    print("\n1. Testing valid folder (Downloads):")
    downloads_path = os.path.expanduser("~/Downloads")
    result = SettingsValidator.validate_audio_folder(downloads_path)
    print(f"   Valid: {result.is_valid}")
    if result.has_warnings():
        print(f"   Warnings: {result.get_warning_message()}")
    
    # Test 2: Invalid folder (non-existent)
    print("\n2. Testing invalid folder (non-existent):")
    result = SettingsValidator.validate_audio_folder("/nonexistent/folder")
    print(f"   Valid: {result.is_valid}")
    if result.has_errors():
        print(f"   Errors: {result.get_error_message()}")
    
    # Test 3: Voice Memos folder (if exists)
    print("\n3. Testing Voice Memos folder:")
    voice_memos_path = os.path.expanduser("~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings")
    if os.path.exists(voice_memos_path):
        result = SettingsValidator.validate_audio_folder(voice_memos_path)
        print(f"   Valid: {result.is_valid}")
        if result.has_warnings():
            print(f"   Warnings: {result.get_warning_message()}")
        else:
            print("   ✅ Voice Memos database found!")
    else:
        print("   Voice Memos folder not found on this system")
    
    # Test 4: Valid API key
    print("\n4. Testing valid API key:")
    result = SettingsValidator.validate_api_settings(api_key="test_api_key_1234567890")
    print(f"   Valid: {result.is_valid}")
    if result.has_warnings():
        print(f"   Warnings: {result.get_warning_message()}")
    
    # Test 5: Invalid API key (too short)
    print("\n5. Testing invalid API key (too short):")
    result = SettingsValidator.validate_api_settings(api_key="short")
    print(f"   Valid: {result.is_valid}")
    if result.has_errors():
        print(f"   Errors: {result.get_error_message()}")
    
    # Test 6: Invalid API key (whitespace)
    print("\n6. Testing invalid API key (contains whitespace):")
    result = SettingsValidator.validate_api_settings(api_key="api key with spaces")
    print(f"   Valid: {result.is_valid}")
    if result.has_errors():
        print(f"   Errors: {result.get_error_message()}")
    
    # Test 7: Valid model ID
    print("\n7. Testing valid model ID:")
    result = SettingsValidator.validate_whisper_model("tiny.en")
    print(f"   Valid: {result.is_valid}")
    
    # Test 8: Invalid model ID
    print("\n8. Testing invalid model ID:")
    result = SettingsValidator.validate_whisper_model("invalid model id!")
    print(f"   Valid: {result.is_valid}")
    if result.has_errors():
        print(f"   Errors: {result.get_error_message()}")
    
    # Test 9: Complete settings validation
    print("\n9. Testing complete settings validation:")
    result = SettingsValidator.validate_all_settings(
        folder_path=downloads_path,
        api_key="test_api_key_1234567890",
        model_id="tiny.en"
    )
    print(f"   Valid: {result.is_valid}")
    if result.has_warnings():
        print(f"   Warnings: {result.get_warning_message()}")
    if result.has_errors():
        print(f"   Errors: {result.get_error_message()}")
    
    print("\n✅ Validation system tests completed!")


def test_real_voice_memos_validation():
    """Test validation with real Voice Memos data"""
    
    print("\n🎙️  Testing Validation with Real Voice Memos Data")
    print("=" * 50)
    
    # Test with real Voice Memos data
    real_test_path = "/Users/lopezm52/Documents/VisualCode/Test"
    
    if os.path.exists(real_test_path):
        print(f"\n📂 Testing real Voice Memos folder: {real_test_path}")
        result = SettingsValidator.validate_audio_folder(real_test_path)
        print(f"   Valid: {result.is_valid}")
        
        if result.has_warnings():
            print(f"   Warnings: {result.get_warning_message()}")
        
        if result.has_errors():
            print(f"   Errors: {result.get_error_message()}")
        
        if result.is_valid and not result.has_warnings():
            print("   ✅ Real Voice Memos database validation passed!")
            
            # Also test if we can list the files
            test_path = Path(real_test_path)
            m4a_files = list(test_path.glob("*.m4a"))
            db_file = test_path / "CloudRecordings.db"
            
            print(f"   📊 Found {len(m4a_files)} .m4a files")
            print(f"   🗄️  Database size: {db_file.stat().st_size / 1024:.1f} KB")
    else:
        print(f"   ❌ Real test data not found at: {real_test_path}")


if __name__ == "__main__":
    test_validation_system()
    test_real_voice_memos_validation()
