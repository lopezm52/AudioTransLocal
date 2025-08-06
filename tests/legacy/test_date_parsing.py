#!/usr/bin/env python3
"""
Quick test to verify date display improvements
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from voice_memo_parser import VoiceMemoParser
import asyncio

async def test_date_parsing():
    """Test that dates are now parsing correctly"""
    
    print("🗓️  Testing Date Parsing Improvements")
    print("=" * 45)
    
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
    print("\n📅 Date Display Test (first 10 memos):")
    print("-" * 45)
    
    # Show the first 10 memos with their dates
    for i, memo in enumerate(memos[:10], 1):
        # Show raw date and formatted display
        raw_date = memo.creation_date
        
        # Simulate the display logic from the model
        now = datetime.now()
        today = now.date()
        memo_date = raw_date.date()
        
        if memo_date == today:
            formatted = f"Today {raw_date.strftime('%H:%M')}"
        elif memo_date == today - timedelta(days=1):
            formatted = f"Yesterday {raw_date.strftime('%H:%M')}"
        elif memo_date > today - timedelta(days=7):
            formatted = raw_date.strftime("%A %H:%M")
        else:
            formatted = raw_date.strftime("%m/%d/%y %H:%M")
        
        print(f"{i:2d}. {memo.get_display_title()[:30]:<30} | {formatted}")
        print(f"    Raw: {raw_date}")
    
    print(f"\n✅ Date parsing test completed!")

if __name__ == "__main__":
    asyncio.run(test_date_parsing())
