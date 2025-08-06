#!/usr/bin/env python3
"""
Extract and display the actual user-given titles from Voice Memos database
"""

import sqlite3
import sys
from pathlib import Path

def show_voice_memo_titles():
    """Extract actual user-given titles from Voice Memos database"""
    
    # Path to the test database
    db_path = "/Users/lopezm52/Documents/VisualCode/Test/CloudRecordings.db"
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🎙️  Voice Memos - Actual User-Given Titles")
        print("=" * 60)
        
        # First, let's examine the ZCLOUDRECORDING table structure
        cursor.execute("PRAGMA table_info(ZCLOUDRECORDING)")
        columns = cursor.fetchall()
        
        print(f"\n📋 ZCLOUDRECORDING table has {len(columns)} columns:")
        for col in columns[:10]:  # Show first 10 columns
            print(f"   - {col[1]} ({col[2]})")
        
        if len(columns) > 10:
            print(f"   ... and {len(columns) - 10} more columns")
        
        # Now let's look for title-related fields
        title_fields = []
        for col in columns:
            col_name = col[1].lower()
            if any(keyword in col_name for keyword in ['title', 'name', 'label', 'text', 'custom']):
                title_fields.append(col[1])
        
        print(f"\n🏷️  Potential title fields: {title_fields}")
        
        # Query for records with different potential title fields
        query = """
        SELECT 
            Z_PK,
            ZDATE,
            ZPATH,
            ZCUSTOMLABEL,
            ZCUSTOMLABELFORSORTING,
            ZENCRYPTEDTITLE,
            ZDURATION
        FROM ZCLOUDRECORDING 
        ORDER BY ZDATE DESC
        LIMIT 20
        """
        
        cursor.execute(query)
        records = cursor.fetchall()
        
        print(f"\n📊 Found {len(records)} recent Voice Memos:")
        print("-" * 60)
        
        for i, record in enumerate(records, 1):
            pk, creation_date, path, custom_label, custom_sorting, encrypted_title, duration = record
            
            # Convert Core Data timestamp to readable date
            if creation_date:
                # Core Data uses 2001-01-01 as epoch
                import datetime
                readable_date = datetime.datetime(2001, 1, 1) + datetime.timedelta(seconds=creation_date)
                date_str = readable_date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_str = "Unknown"
            
            print(f"\n{i:2d}. Recording #{pk} from {date_str}")
            
            # Show all potential title sources
            if custom_label:
                print(f"    📝 ZCUSTOMLABEL: '{custom_label}'")
            else:
                print(f"    📝 ZCUSTOMLABEL: (empty)")
                
            if custom_sorting:
                print(f"    🔤 ZCUSTOMLABELFORSORTING: '{custom_sorting}'")
            else:
                print(f"    🔤 ZCUSTOMLABELFORSORTING: (empty)")
                
            if encrypted_title:
                print(f"    🔐 ZENCRYPTEDTITLE: '{encrypted_title}'")
            else:
                print(f"    🔐 ZENCRYPTEDTITLE: (empty)")
            
            if path:
                print(f"    📁 File path: {path}")
            
            if duration:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                print(f"    ⏱️  Duration: {minutes}:{seconds:02d}")
        
        # Let's also check if there are any other tables that might contain titles
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"\n🗄️  All tables in database:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   - {table_name}: {count} records")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return

if __name__ == "__main__":
    show_voice_memo_titles()
