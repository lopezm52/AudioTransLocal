#!/usr/bin/env python3
"""
Voice Memo Data Source & Parsing Module for AudioTransLocal

This module handles efficient reading and interpretation of Voice Memos data
from the macOS Voice Memos SQLite database using SQLAlchemy 2.0 with async support
and Pydantic V2 for robust data validation.

Epic 2: Voice Memo Browse & Management
US1: Data Source & Parsing
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Union
import logging
from dataclasses import dataclass

# SQLAlchemy 2.0 with async support
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, select, text
from sqlalchemy.exc import SQLAlchemyError

# Pydantic V2 for data validation
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic.types import UUID4

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceMemoModel(BaseModel):
    """
    Pydantic V2 model for Voice Memo data validation and type enforcement.
    
    This model ensures all Voice Memo data is properly validated and typed
    before being used throughout the application.
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        frozen=False
    )
    
    # Core identification
    uuid: str = Field(..., description="Unique identifier for the voice memo")
    title: str = Field(..., min_length=1, description="Display title of the voice memo")
    
    # Timestamps
    creation_date: datetime = Field(..., description="When the memo was created")
    modification_date: Optional[datetime] = Field(None, description="When the memo was last modified")
    
    # File information
    file_path: Optional[Path] = Field(None, description="Path to the .m4a file on disk")
    file_exists: bool = Field(False, description="Whether the audio file exists on disk")
    file_size: Optional[int] = Field(None, ge=0, description="Size of the audio file in bytes")
    
    # Audio metadata
    duration: Optional[float] = Field(None, ge=0.0, description="Duration in seconds")
    sample_rate: Optional[int] = Field(None, ge=0, description="Audio sample rate")
    
    # Database fields (raw data from SQLite)
    db_data: Dict[str, Any] = Field(default_factory=dict, description="Raw database fields")
    
    # Transcription fields (Epic 3)
    transcription_status: str = Field(default="new", description="Current transcription status")
    transcription_file_path: Optional[Path] = Field(None, description="Path to transcript .txt file")
    transcription_error: Optional[str] = Field(None, description="Error message if transcription failed")
    detected_language: Optional[str] = Field(None, description="Detected audio language code")
    transcription_progress: Optional[str] = Field(None, description="Current progress message")
    
    @field_validator('creation_date', 'modification_date', mode='before')
    @classmethod
    def parse_datetime(cls, v):
        """Parse various datetime formats from the database"""
        if v is None:
            return None
        
        if isinstance(v, datetime):
            return v
        
        if isinstance(v, (int, float)):
            # Core Data timestamps: seconds since 2001-01-01 00:00:00 UTC
            # This is the format used by macOS Voice Memos database
            try:
                core_data_epoch = datetime(2001, 1, 1)
                return core_data_epoch + timedelta(seconds=v)
            except (ValueError, OverflowError):
                # Fallback to Unix timestamp if Core Data conversion fails
                try:
                    return datetime.fromtimestamp(v)
                except (ValueError, OverflowError):
                    return datetime.now()
        
        if isinstance(v, str):
            # Try parsing ISO format
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                pass
            
            # Try parsing as timestamp
            try:
                return datetime.fromtimestamp(float(v))
            except (ValueError, TypeError):
                pass
        
        return v
    
    def get_display_title(self) -> str:
        """Get a user-friendly display title"""
        if self.title and self.title.strip():
            return self.title.strip()
        return f"Voice Memo {self.creation_date.strftime('%Y-%m-%d %H:%M')}"
    
    def get_file_info(self) -> str:
        """Get formatted file information"""
        info_parts = []
        
        if self.duration:
            minutes = int(self.duration // 60)
            seconds = int(self.duration % 60)
            info_parts.append(f"{minutes}:{seconds:02d}")
        
        if self.file_size:
            if self.file_size > 1024 * 1024:
                size_mb = self.file_size / (1024 * 1024)
                info_parts.append(f"{size_mb:.1f} MB")
            else:
                size_kb = self.file_size / 1024
                info_parts.append(f"{size_kb:.0f} KB")
        
        return " • ".join(info_parts) if info_parts else "Unknown"


class VoiceMemoDatabase:
    """
    Async database interface for Voice Memos SQLite database.
    
    Uses SQLAlchemy 2.0 with asyncio to ensure database operations
    never block the main UI thread.
    """
    
    def __init__(self, db_path: Path):
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to the Recordings.db SQLite file
        """
        self.db_path = db_path
        self.engine = None
        self.async_session = None
        
    async def connect(self) -> bool:
        """
        Establish async connection to the database.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create async engine for SQLite
            db_url = f"sqlite+aiosqlite:///{self.db_path}"
            self.engine = create_async_engine(
                db_url,
                echo=False,  # Set to True for SQL debugging
                pool_pre_ping=True
            )
            
            # Create session factory
            self.async_session = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test the connection
            async with self.async_session() as session:
                result = await session.execute(text("SELECT 1"))
                result.fetchone()
            
            logger.info(f"✅ Connected to Voice Memos database: {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database {self.db_path}: {e}")
            return False
    
    async def get_table_info(self) -> Dict[str, List[str]]:
        """
        Get information about tables and columns in the database.
        
        Returns:
            Dictionary mapping table names to column lists
        """
        table_info = {}
        
        try:
            async with self.async_session() as session:
                # Get table names
                result = await session.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ))
                tables = result.fetchall()
                
                for (table_name,) in tables:
                    # Get column info for each table
                    result = await session.execute(text(f"PRAGMA table_info({table_name})"))
                    columns = result.fetchall()
                    table_info[table_name] = [col[1] for col in columns]  # col[1] is column name
                
                logger.info(f"📊 Found {len(table_info)} tables in database")
                return table_info
                
        except Exception as e:
            logger.error(f"❌ Failed to get table info: {e}")
            return {}
    
    async def fetch_voice_memos_raw(self) -> List[Dict[str, Any]]:
        """
        Fetch raw voice memo data from the database.
        
        Returns:
            List of dictionaries containing raw database records
        """
        try:
            async with self.async_session() as session:
                # First, let's explore the database structure
                table_info = await self.get_table_info()
                logger.info(f"📋 Available tables: {list(table_info.keys())}")
                
                # Look for the most likely table containing recordings
                recording_tables = [
                    name for name in table_info.keys() 
                    if any(keyword in name.lower() for keyword in ['recording', 'memo', 'voice', 'cloudrecording'])
                ]
                
                if not recording_tables:
                    # Fallback: try known table names from Voice Memos database
                    recording_tables = ['ZCLOUDRECORDING', 'ZRECORDING', 'recordings']
                
                logger.info(f"🎙️  Trying recording tables: {recording_tables}")
                
                # Try each potential table
                for table_name in recording_tables:
                    try:
                        # Get a sample to understand the structure
                        result = await session.execute(text(f"SELECT * FROM {table_name} LIMIT 5"))
                        sample_rows = result.fetchall()
                        
                        if sample_rows:
                            logger.info(f"✅ Found data in table: {table_name}")
                            
                            # Get all columns
                            columns = list(sample_rows[0]._mapping.keys())
                            logger.info(f"📝 Columns: {columns}")
                            
                            # Fetch all records
                            result = await session.execute(text(f"SELECT * FROM {table_name}"))
                            all_rows = result.fetchall()
                            
                            # Convert to dictionaries
                            records = []
                            for row in all_rows:
                                record = dict(row._mapping)
                                records.append(record)
                            
                            logger.info(f"📊 Fetched {len(records)} records from {table_name}")
                            return records
                            
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to query table {table_name}: {e}")
                        continue
                
                logger.warning("❌ No suitable recording table found")
                return []
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch voice memos: {e}")
            return []
    
    async def close(self):
        """Close the database connection"""
        if self.engine:
            await self.engine.dispose()
            logger.info("🔒 Database connection closed")


class VoiceMemoParser:
    """
    Main parser class that orchestrates database reading, validation,
    and file system cross-referencing.
    """
    
    def __init__(self, voice_memos_folder: Path):
        """
        Initialize the parser.
        
        Args:
            voice_memos_folder: Path to the Voice Memos folder containing CloudRecordings.db
        """
        self.voice_memos_folder = Path(voice_memos_folder)
        self.db_path = self.voice_memos_folder / "CloudRecordings.db"  # Correct database name
        self.database = VoiceMemoDatabase(self.db_path)
        
    async def load_voice_memos(self) -> List[VoiceMemoModel]:
        """
        Load and parse all Voice Memos with validation and file cross-referencing.
        
        This is the main entry point that performs the complete data loading process:
        1. Connect to database
        2. Query for Voice Memo records
        3. Validate data with Pydantic
        4. Cross-reference with .m4a files on disk
        
        Returns:
            List of validated VoiceMemoModel instances
        """
        voice_memos = []
        
        try:
            # Step 1: Connect to database
            logger.info(f"🔌 Connecting to Voice Memos database...")
            if not await self.database.connect():
                logger.error("❌ Failed to connect to database")
                return []
            
            # Step 2: Fetch raw data
            logger.info("📊 Fetching Voice Memo records...")
            raw_records = await self.database.fetch_voice_memos_raw()
            
            if not raw_records:
                logger.warning("⚠️  No Voice Memo records found")
                return []
            
            # Step 3: Process and validate each record
            logger.info(f"🔍 Processing {len(raw_records)} records...")
            
            for i, raw_record in enumerate(raw_records):
                try:
                    # Parse the raw database record into our Pydantic model
                    voice_memo = await self._parse_raw_record(raw_record)
                    
                    if voice_memo:
                        voice_memos.append(voice_memo)
                        logger.debug(f"✅ Parsed record {i+1}: {voice_memo.get_display_title()}")
                    
                except Exception as e:
                    logger.warning(f"⚠️  Failed to parse record {i+1}: {e}")
                    continue
            
            logger.info(f"🎙️  Successfully loaded {len(voice_memos)} Voice Memos")
            
        except Exception as e:
            logger.error(f"❌ Failed to load Voice Memos: {e}")
        
        finally:
            # Always close the database connection
            await self.database.close()
        
        return voice_memos
    
    async def _parse_raw_record(self, raw_record: Dict[str, Any]) -> Optional[VoiceMemoModel]:
        """
        Parse a raw database record into a validated VoiceMemoModel.
        
        Args:
            raw_record: Raw dictionary from database query
            
        Returns:
            VoiceMemoModel instance or None if parsing failed
        """
        try:
            # Extract key fields using the correct Voice Memos database schema
            # Based on CloudRecordings.db structure
            
            # Primary fields from ZCLOUDRECORDING table
            path_field = self._find_field(raw_record, ['zpath', 'ZPATH', 'path'])
            title_field = self._find_field(raw_record, ['zcustomlabel', 'ZCUSTOMLABEL', 'customlabel'])
            encrypted_title_field = self._find_field(raw_record, ['zencryptedtitle', 'ZENCRYPTEDTITLE', 'encryptedtitle'])
            date_field = self._find_field(raw_record, ['zdate', 'ZDATE', 'date', 'creationdate'])
            duration_field = self._find_field(raw_record, ['zduration', 'ZDURATION', 'duration'])
            
            # Generate a UUID from path or other unique identifier if available
            uuid_field = self._find_field(raw_record, ['zuuid', 'ZUUID', 'uuid', 'id'])
            if not uuid_field and path_field:
                # Generate UUID from path for consistency
                import hashlib
                uuid_field = hashlib.md5(str(path_field).encode()).hexdigest()
            elif not uuid_field:
                # Last resort: generate from record hash
                uuid_field = f"generated_{hash(str(raw_record))}"
            
            # Handle title - ZENCRYPTEDTITLE contains the actual user-visible title
            display_title = None
            
            # Priority 1: ZENCRYPTEDTITLE (contains the actual user-visible title)
            if encrypted_title_field and str(encrypted_title_field).strip():
                display_title = str(encrypted_title_field).strip()
            
            # Priority 2: ZCUSTOMLABEL (fallback, usually timestamp-based)
            elif title_field and str(title_field).strip():
                display_title = str(title_field).strip()
            
            # Fallback: Generate a title from creation date
            if not display_title:
                if date_field:
                    try:
                        if isinstance(date_field, (int, float)):
                            # Core Data timestamp - convert to readable date
                            readable_date = datetime(2001, 1, 1) + timedelta(seconds=date_field)
                            display_title = f"Voice Memo {readable_date.strftime('%Y-%m-%d %H:%M')}"
                        else:
                            display_title = f"Voice Memo {date_field}"
                    except:
                        display_title = "Untitled Voice Memo"
                else:
                    display_title = "Untitled Voice Memo"
            
            # Build the Voice Memo model data
            memo_data = {
                'uuid': str(uuid_field),
                'title': str(display_title),
                'creation_date': date_field or datetime.now(),
                'modification_date': None,  # Not typically stored in Voice Memos DB
                'duration': float(duration_field) if duration_field and duration_field != 0 else None,
                'db_data': raw_record
            }
            
            # Create the model (this will trigger Pydantic validation)
            voice_memo = VoiceMemoModel(**memo_data)
            
            # Cross-reference with file system using ZPATH
            if path_field:
                voice_memo.db_data['zpath'] = path_field  # Store for file lookup
            
            await self._cross_reference_file(voice_memo)
            
            return voice_memo
            
        except Exception as e:
            logger.warning(f"Failed to parse record: {e}")
            logger.debug(f"Raw record: {raw_record}")
            return None
    
    def _find_field(self, record: Dict[str, Any], field_names: List[str]) -> Any:
        """
        Find a field value by trying multiple possible field names.
        
        Args:
            record: Database record dictionary
            field_names: List of possible field names to try
            
        Returns:
            Field value or None if not found
        """
        for field_name in field_names:
            # Try exact match
            if field_name in record:
                return record[field_name]
            
            # Try case-insensitive match
            for key, value in record.items():
                if key.lower() == field_name.lower():
                    return value
        
        return None
    
    async def _cross_reference_file(self, voice_memo: VoiceMemoModel) -> None:
        """
        Cross-reference the Voice Memo with its corresponding .m4a file on disk.
        
        Uses ZPATH from the database to locate the actual file.
        
        Args:
            voice_memo: VoiceMemoModel to update with file information
        """
        try:
            # Get the ZPATH from database data
            zpath = voice_memo.db_data.get('zpath')
            
            if zpath:
                # ZPATH is relative to the Voice Memos folder
                file_path = self.voice_memos_folder / zpath
                
                if file_path.exists() and file_path.suffix.lower() == '.m4a':
                    voice_memo.file_path = file_path
                    voice_memo.file_exists = True
                    voice_memo.file_size = file_path.stat().st_size
                    logger.debug(f"📁 Found file for {voice_memo.get_display_title()}: {file_path.name}")
                    return
            
            # Fallback: search for .m4a files that might match
            # Look for .m4a files with UUID in name or any .m4a files
            possible_patterns = [
                f"*{voice_memo.uuid}*.m4a",
                "*.m4a"
            ]
            
            for pattern in possible_patterns:
                m4a_files = list(self.voice_memos_folder.rglob(pattern))
                if m4a_files:
                    # Use the first match
                    file_path = m4a_files[0]
                    voice_memo.file_path = file_path
                    voice_memo.file_exists = True
                    voice_memo.file_size = file_path.stat().st_size
                    logger.debug(f"📁 Found file (fallback) for {voice_memo.get_display_title()}: {file_path.name}")
                    break
            
            if not voice_memo.file_exists:
                logger.debug(f"❌ No file found for {voice_memo.get_display_title()} (ZPATH: {zpath})")
                
        except Exception as e:
            logger.warning(f"Failed to cross-reference file for {voice_memo.uuid}: {e}")


# Convenience functions for easy integration

async def load_voice_memos_async(voice_memos_folder: Union[str, Path]) -> List[VoiceMemoModel]:
    """
    Convenience function to load Voice Memos asynchronously.
    
    Args:
        voice_memos_folder: Path to the Voice Memos folder
        
    Returns:
        List of VoiceMemoModel instances
    """
    parser = VoiceMemoParser(Path(voice_memos_folder))
    return await parser.load_voice_memos()


def load_voice_memos_sync(voice_memos_folder: Union[str, Path]) -> List[VoiceMemoModel]:
    """
    Convenience function to load Voice Memos synchronously (runs async in event loop).
    
    Args:
        voice_memos_folder: Path to the Voice Memos folder
        
    Returns:
        List of VoiceMemoModel instances
    """
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we need to create a task
            # This is typically used when called from async context
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, load_voice_memos_async(voice_memos_folder))
                return future.result()
        else:
            # Loop exists but not running, can use it directly
            return loop.run_until_complete(load_voice_memos_async(voice_memos_folder))
    except RuntimeError:
        # No event loop, create a new one
        return asyncio.run(load_voice_memos_async(voice_memos_folder))


# Test function
async def test_voice_memo_parsing():
    """Test the Voice Memo parsing functionality."""
    print("🎙️  Testing Voice Memo Data Source & Parsing")
    print("=" * 50)
    
    # Test with Voice Memos folder - CORRECTED PATH
    voice_memos_path = Path.home() / "Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"
    
    if not voice_memos_path.exists():
        print("❌ Voice Memos folder not found on this system")
        print(f"   Expected path: {voice_memos_path}")
        return
    
    print(f"📂 Testing with Voice Memos folder: {voice_memos_path}")
    
    try:
        # Test database connection
        db_path = voice_memos_path / "CloudRecordings.db"
        if not db_path.exists():
            print(f"❌ Voice Memos database not found: {db_path}")
            return
        
        print(f"🗄️  Found database: {db_path}")
        
        # Load Voice Memos
        print("🔄 Loading Voice Memos...")
        voice_memos = await load_voice_memos_async(voice_memos_path)
        
        print(f"📊 Results:")
        print(f"   Total Voice Memos found: {len(voice_memos)}")
        
        if voice_memos:
            print(f"\n📝 Sample Voice Memos:")
            for i, memo in enumerate(voice_memos[:5]):  # Show first 5
                print(f"   {i+1}. {memo.get_display_title()}")
                print(f"      Created: {memo.creation_date.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"      File: {'✅ Found' if memo.file_exists else '❌ Missing'}")
                print(f"      Info: {memo.get_file_info()}")
                print()
        
        print("✅ Voice Memo parsing test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_voice_memo_parsing())
