#!/usr/bin/env python3
"""
Quick script to show the actual recording names/titles from the real Voice Memos data
"""

import asyncio
from pathlib import Path
from voice_memo_parser import load_voice_memos_async

async def show_recording_names():
    """Show the actual recording names from the real data"""
    
    print("🎙️  Recording Names from Real Voice Memos Data")
    print("=" * 60)
    
    test_path = Path("/Users/lopezm52/Documents/VisualCode/Test")
    
    if not test_path.exists():
        print("❌ Test data not found")
        return
    
    try:
        voice_memos = await load_voice_memos_async(test_path)
        print(f"Found {len(voice_memos)} recordings\n")
        
        print("📝 Recording Titles/Names:")
        print("-" * 40)
        
        for i, memo in enumerate(voice_memos[:20]):  # Show first 20
            print(f"{i+1:2d}. {memo.title}")
            
            # Also show some database info for the first few
            if i < 3:
                print(f"    📅 Created: {memo.creation_date}")
                if memo.db_data.get('ZCUSTOMLABEL'):
                    print(f"    🏷️  Custom Label: {memo.db_data['ZCUSTOMLABEL']}")
                if memo.db_data.get('ZPATH'):
                    print(f"    📁 File Path: {memo.db_data['ZPATH']}")
                print()
        
        if len(voice_memos) > 20:
            print(f"\n... and {len(voice_memos) - 20} more recordings")
        
        # Also show the actual file names on disk
        print(f"\n📁 Actual .m4a File Names on Disk:")
        print("-" * 40)
        m4a_files = sorted(list(test_path.glob("*.m4a")))
        for i, file_path in enumerate(m4a_files[:10]):
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"{i+1:2d}. {file_path.name} ({size_mb:.1f} MB)")
            
        if len(m4a_files) > 10:
            print(f"\n... and {len(m4a_files) - 10} more files")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(show_recording_names())
