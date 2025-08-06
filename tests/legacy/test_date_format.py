#!/usr/bin/env python3
"""
Test the new date format (DD-MMM-YY HH:MM with CEST timezone)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from voice_memo_parser import VoiceMemoParser
import asyncio

async def test_date_format():
    """Test the new date format with timezone adjustment"""
    
    print("🕐 Testing New Date Format (DD-MMM-YY HH:MM CEST)")
    print("=" * 55)
    
    # Test with our database
    db_path = "/Users/lopezm52/Documents/VisualCode/Test"
    
    if not Path(db_path).exists():
        print(f"❌ Test database not found: {db_path}")
        return
    
    # Create parser and load some memos
    parser = VoiceMemoParser(db_path)
    memos = await parser.load_voice_memos()
    
    if not memos:
        print("❌ No memos loaded")
        return
    
    print(f"✅ Loaded {len(memos)} memos")
    print("\n📅 New Date Format Examples (first 10 memos):")
    print("-" * 55)
    
    # Show the first 10 memos with their new date format
    for i, memo in enumerate(memos[:10], 1):
        # Show UTC time and CEST conversion
        utc_time = memo.creation_date
        cest_time = utc_time + timedelta(hours=2)  # Add 2 hours for CEST
        
        # Format as DD-MMM-YY HH:MM
        formatted_date = cest_time.strftime("%d-%b-%y %H:%M")
        
        print(f"{i:2d}. {memo.get_display_title()[:35]:<35} | {formatted_date}")
        print(f"    UTC: {utc_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"    CEST: {cest_time.strftime('%Y-%m-%d %H:%M:%S')} (+2 hours)")
        print()
    
    print(f"✅ Date format test completed!")
    print(f"📋 Format: DD-MMM-YY HH:MM (with CEST timezone adjustment)")

if __name__ == "__main__":
    asyncio.run(test_date_format())
