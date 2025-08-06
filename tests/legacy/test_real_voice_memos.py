#!/usr/bin/env python3
"""
Real Voice Memos Data Test Script

This script specifically tests with the real Voice Memos data 
copied to /Users/lopezm52/Documents/VisualCode/Test/ for development purposes.
"""

import asyncio
from pathlib import Path
from voice_memo_parser import load_voice_memos_async
from validation import SettingsValidator

async def test_real_voice_memos():
    """Comprehensive test with real Voice Memos data"""
    
    print("🎙️  Real Voice Memos Data Analysis")
    print("=" * 60)
    
    # Real test data path
    test_path = Path("/Users/lopezm52/Documents/VisualCode/Test")
    
    if not test_path.exists():
        print("❌ Test data folder not found")
        return
    
    # 1. Validation Test
    print("\n1️⃣  VALIDATION TEST")
    print("-" * 30)
    result = SettingsValidator.validate_audio_folder(str(test_path))
    print(f"Folder valid: {result.is_valid}")
    if result.has_warnings():
        print(f"Warnings: {result.get_warning_message()}")
    
    # 2. File System Analysis
    print("\n2️⃣  FILE SYSTEM ANALYSIS")
    print("-" * 30)
    m4a_files = list(test_path.glob("*.m4a"))
    waveform_files = list(test_path.glob("*.waveform"))
    db_file = test_path / "CloudRecordings.db"
    
    print(f"📁 Audio files (.m4a): {len(m4a_files)}")
    print(f"🌊 Waveform files: {len(waveform_files)}")
    print(f"🗄️  Database size: {db_file.stat().st_size / 1024:.1f} KB")
    
    # 3. Voice Memo Parsing Test
    print("\n3️⃣  VOICE MEMO PARSING")
    print("-" * 30)
    
    try:
        voice_memos = await load_voice_memos_async(test_path)
        print(f"✅ Successfully parsed {len(voice_memos)} Voice Memos")
        
        if voice_memos:
            # Analysis
            with_files = sum(1 for memo in voice_memos if memo.file_exists)
            with_duration = sum(1 for memo in voice_memos if memo.duration)
            encrypted_titles = sum(1 for memo in voice_memos if "Encrypted" in memo.title or memo.title.endswith("Z"))
            
            print(f"📊 Statistics:")
            print(f"   Files found: {with_files}/{len(voice_memos)}")
            print(f"   With duration: {with_duration}/{len(voice_memos)}")
            print(f"   Encrypted/timestamp titles: {encrypted_titles}/{len(voice_memos)}")
            
            # Duration analysis
            durations = [memo.duration for memo in voice_memos if memo.duration]
            if durations:
                total_duration = sum(durations)
                avg_duration = total_duration / len(durations)
                max_duration = max(durations)
                min_duration = min(durations)
                
                print(f"⏱️  Duration Analysis:")
                print(f"   Total: {total_duration/60:.1f} minutes")
                print(f"   Average: {avg_duration:.1f} seconds")
                print(f"   Range: {min_duration:.1f}s - {max_duration:.1f}s")
            
            # Sample entries
            print(f"\n📝 Sample Voice Memos:")
            for i, memo in enumerate(voice_memos[:5]):
                print(f"   {i+1}. {memo.get_display_title()[:50]}")
                print(f"      Created: {memo.creation_date.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"      Duration: {memo.duration:.1f}s" if memo.duration else "      Duration: Unknown")
                print(f"      File: {'✅' if memo.file_exists else '❌'} | Size: {memo.file_size/1024/1024:.1f} MB" if memo.file_size else "      File: ❌")
    
    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point"""
    asyncio.run(test_real_voice_memos())


if __name__ == "__main__":
    main()
