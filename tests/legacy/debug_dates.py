#!/usr/bin/env python3
"""
Debug date values in Voice Memos database
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta

def debug_voice_memo_dates():
    """Debug date values from Voice Memos database"""
    
    # Path to the test database
    db_path = "/Users/lopezm52/Documents/VisualCode/Test/CloudRecordings.db"
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🗓️  Voice Memos Date Debug")
        print("=" * 50)
        
        # Query for recent records with date analysis
        query = """
        SELECT 
            Z_PK,
            ZDATE,
            ZENCRYPTEDTITLE,
            ZPATH
        FROM ZCLOUDRECORDING 
        ORDER BY ZDATE DESC
        LIMIT 10
        """
        
        cursor.execute(query)
        records = cursor.fetchall()
        
        print(f"📊 Analyzing {len(records)} recent Voice Memos:\n")
        
        for i, record in enumerate(records, 1):
            pk, raw_date, title, path = record
            
            print(f"{i:2d}. Recording #{pk}")
            print(f"    📝 Title: '{title}'")
            print(f"    📁 File: {path}")
            print(f"    🕐 Raw ZDATE: {raw_date} (type: {type(raw_date)})")
            
            if raw_date:
                try:
                    # Core Data uses 2001-01-01 00:00:00 UTC as epoch (978307200 Unix timestamp)
                    # ZDATE appears to be seconds since 2001-01-01 00:00:00 UTC
                    core_data_epoch = datetime(2001, 1, 1)
                    converted_date = core_data_epoch + timedelta(seconds=raw_date)
                    
                    print(f"    ✅ Converted: {converted_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                    
                    # Also try Unix timestamp interpretation
                    if raw_date > 1000000000:  # Reasonable Unix timestamp range
                        unix_date = datetime.fromtimestamp(raw_date)
                        print(f"    🔄 Unix interp: {unix_date.strftime('%Y-%m-%d %H:%M:%S')} local")
                    
                except Exception as e:
                    print(f"    ❌ Conversion error: {e}")
            
            print()
        
        # Check what the current date conversion is producing
        print("🔍 Current Parser Logic Test:")
        test_date = records[0][1] if records else None
        if test_date:
            print(f"   Raw value: {test_date}")
            
            # Test current parser logic
            if isinstance(test_date, (int, float)):
                if test_date > 978307200:  # Core Data epoch
                    unix_timestamp = test_date + 978307200
                    result_date = datetime.fromtimestamp(unix_timestamp)
                    print(f"   Current logic result: {result_date}")
                else:
                    result_date = datetime.fromtimestamp(test_date)
                    print(f"   Direct Unix result: {result_date}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return

if __name__ == "__main__":
    debug_voice_memo_dates()
