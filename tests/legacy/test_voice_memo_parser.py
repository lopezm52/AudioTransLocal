#!/usr/bin/env python3
"""
Test script for Voice Memo parser functionality
"""

import asyncio
import sqlite3
from pathlib import Path
from datetime import datetime
import tempfile
import os

from voice_memo_parser import VoiceMemoParser, VoiceMemoModel, load_voice_memos_async


def create_test_voice_memos_db(db_path: Path):
    """Create a test Voice Memos database with sample data matching real CloudRecordings.db structure"""
    
    # Create the database file
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create a table that matches the real Voice Memos CloudRecordings.db structure
    cursor.execute('''
        CREATE TABLE ZCLOUDRECORDING (
            Z_PK INTEGER PRIMARY KEY,
            Z_ENT INTEGER,
            Z_OPT INTEGER,
            ZDATE REAL,
            ZDURATION REAL,
            ZCUSTOMLABEL TEXT,
            ZENCRYPTEDTITLE BLOB,
            ZPATH TEXT
        )
    ''')
    
    # Insert sample Voice Memo records using the correct schema
    # ZDATE uses Core Data timestamp (seconds since 2001-01-01 00:00:00 UTC)
    base_timestamp = 736000000  # Some time after 2001
    
    sample_records = [
        (1, 1, 1, base_timestamp, 45.5, "Meeting with Dr. Smith", None, "Recording1.m4a"),
        (2, 1, 1, base_timestamp + 1000, 120.0, "Grocery List", None, "Recording2.m4a"),
        (3, 1, 1, base_timestamp + 2000, 30.2, None, b"encrypted_title_blob", "Recording3.m4a"),  # Encrypted title case
        (4, 1, 1, base_timestamp + 3000, 15.8, "Quick Note", None, "Recording4.m4a"),
    ]
    
    cursor.executemany('''
        INSERT INTO ZCLOUDRECORDING 
        (Z_PK, Z_ENT, Z_OPT, ZDATE, ZDURATION, ZCUSTOMLABEL, ZENCRYPTEDTITLE, ZPATH)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_records)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Created test CloudRecordings.db with {len(sample_records)} records: {db_path}")


async def test_voice_memo_parser():
    """Test the Voice Memo parser with a mock database"""
    
    print("🧪 Testing Voice Memo Parser")
    print("=" * 50)
    
    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test database with correct name
        db_path = temp_path / "CloudRecordings.db"
        create_test_voice_memos_db(db_path)
        
        # Create some dummy .m4a files matching ZPATH entries
        for filename in ["Recording1.m4a", "Recording2.m4a", "Recording3.m4a", "Recording4.m4a"]:
            dummy_file = temp_path / filename
            dummy_file.write_bytes(b"dummy audio data for testing")
        
        print(f"\n📂 Test folder: {temp_path}")
        print(f"🗄️  Test database: {db_path}")
        
        # Test the parser
        try:
            print("\n🔄 Loading Voice Memos...")
            voice_memos = await load_voice_memos_async(temp_path)
            
            print(f"\n📊 Results:")
            print(f"   Total Voice Memos found: {len(voice_memos)}")
            
            if voice_memos:
                print(f"\n📝 Voice Memos Details:")
                for i, memo in enumerate(voice_memos):
                    print(f"   {i+1}. {memo.get_display_title()}")
                    print(f"      UUID: {memo.uuid}")
                    print(f"      Created: {memo.creation_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"      Duration: {memo.duration}s" if memo.duration else "      Duration: Unknown")
                    print(f"      File: {'✅ Found' if memo.file_exists else '❌ Missing'}")
                    if memo.file_exists:
                        print(f"      Size: {memo.file_size} bytes")
                    print(f"      Info: {memo.get_file_info()}")
                    print()
                
                # Test Pydantic validation
                print("🔍 Testing Pydantic Validation:")
                sample_memo = voice_memos[0]
                print(f"   Model validation: ✅ Passed")
                print(f"   Display title: '{sample_memo.get_display_title()}'")
                print(f"   File info: '{sample_memo.get_file_info()}'")
                
            else:
                print("   ❌ No Voice Memos were parsed successfully")
            
            print("\n✅ Voice Memo parser test completed!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


async def test_database_exploration():
    """Test database exploration capabilities"""
    
    print("\n🔍 Testing Database Exploration")
    print("=" * 30)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "CloudRecordings.db"
        create_test_voice_memos_db(db_path)
        
        from voice_memo_parser import VoiceMemoDatabase
        
        db = VoiceMemoDatabase(db_path)
        
        try:
            if await db.connect():
                print("✅ Database connection successful")
                
                # Test table exploration
                table_info = await db.get_table_info()
                print(f"📋 Found tables: {list(table_info.keys())}")
                
                for table_name, columns in table_info.items():
                    print(f"   {table_name}: {columns}")
                
                # Test raw data fetching
                raw_records = await db.fetch_voice_memos_raw()
                print(f"📊 Fetched {len(raw_records)} raw records")
                
                if raw_records:
                    print("📝 Sample record:")
                    sample = raw_records[0]
                    for key, value in sample.items():
                        print(f"   {key}: {value}")
                
            else:
                print("❌ Database connection failed")
                
        finally:
            await db.close()


async def test_real_voice_memos_data():
    """Test with real Voice Memos data copied for testing"""
    
    print("\n🎙️  Testing with Real Voice Memos Data")
    print("=" * 50)
    
    # Path to the real test data
    real_test_path = Path("/Users/lopezm52/Documents/VisualCode/Test")
    
    if not real_test_path.exists():
        print("❌ Real test data not found. Skipping real data test.")
        return
    
    db_path = real_test_path / "CloudRecordings.db"
    if not db_path.exists():
        print("❌ Real CloudRecordings.db not found. Skipping real data test.")
        return
    
    print(f"📂 Real test folder: {real_test_path}")
    print(f"🗄️  Real database: {db_path}")
    
    try:
        print("\n🔄 Loading Real Voice Memos...")
        voice_memos = await load_voice_memos_async(real_test_path)
        
        print(f"\n📊 Real Data Results:")
        print(f"   Total Voice Memos found: {len(voice_memos)}")
        
        if voice_memos:
            print(f"\n📝 Real Voice Memos (first 10):")
            for i, memo in enumerate(voice_memos[:10]):  # Show first 10
                print(f"   {i+1}. {memo.get_display_title()}")
                print(f"      UUID: {memo.uuid[:8]}...")
                print(f"      Created: {memo.creation_date.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"      Duration: {memo.duration}s" if memo.duration else "      Duration: Unknown")
                print(f"      File: {'✅ Found' if memo.file_exists else '❌ Missing'}")
                if memo.file_exists and memo.file_size:
                    size_mb = memo.file_size / (1024 * 1024)
                    print(f"      Size: {size_mb:.1f} MB")
                print(f"      Info: {memo.get_file_info()}")
                
                # Show database raw data for first entry
                if i == 0:
                    print(f"      Raw DB fields: {list(memo.db_data.keys())}")
                print()
            
            if len(voice_memos) > 10:
                print(f"   ... and {len(voice_memos) - 10} more Voice Memos")
            
            # Check for encrypted titles
            encrypted_count = sum(1 for memo in voice_memos if "Encrypted" in memo.title)
            print(f"\n🔐 Encryption Info:")
            print(f"   Encrypted titles found: {encrypted_count}")
            print(f"   Readable titles: {len(voice_memos) - encrypted_count}")
            
        else:
            print("   ❌ No Voice Memos were parsed from real data")
        
        print("\n✅ Real Voice Memo data test completed!")
        
    except Exception as e:
        print(f"❌ Real data test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🎙️  Voice Memo Parser Test Suite")
    print("=" * 50)
    
    # Run the tests
    asyncio.run(test_voice_memo_parser())
    asyncio.run(test_database_exploration())
    asyncio.run(test_real_voice_memos_data())
