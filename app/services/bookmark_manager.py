#!/usr/bin/env python3
"""
Bookmark manager for handling voice memo bookmarks and annotations
"""

from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Bookmark:
    """Represents a bookmark within an audio file"""
    
    def __init__(self, timestamp: float, title: str, description: str = "", tags: List[str] = None):
        """
        Initialize a bookmark.
        
        Args:
            timestamp: Time position in seconds
            title: Bookmark title
            description: Optional description
            tags: Optional list of tags
        """
        self.timestamp = timestamp
        self.title = title
        self.description = description
        self.tags = tags or []
        self.created_at = datetime.now()
        self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate a unique ID for this bookmark"""
        import hashlib
        content = f"{self.timestamp}_{self.title}_{self.created_at.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert bookmark to dictionary"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bookmark':
        """Create bookmark from dictionary"""
        bookmark = cls(
            timestamp=data["timestamp"],
            title=data["title"],
            description=data.get("description", ""),
            tags=data.get("tags", [])
        )
        bookmark.id = data.get("id", bookmark.id)
        if "created_at" in data:
            bookmark.created_at = datetime.fromisoformat(data["created_at"])
        return bookmark


class BookmarkManager:
    """Manages bookmarks for voice memo files"""
    
    def __init__(self):
        """Initialize the bookmark manager"""
        self._bookmarks: Dict[str, List[Bookmark]] = {}  # file_path -> bookmarks
        self._config_dir = Path.home() / ".config" / "audiotranslocal"
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._bookmarks_file = self._config_dir / "bookmarks.json"
        
        # Load existing bookmarks
        self._load_bookmarks()
    
    def _load_bookmarks(self):
        """Load bookmarks from persistent storage"""
        try:
            if self._bookmarks_file.exists():
                with open(self._bookmarks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for file_path, bookmark_list in data.items():
                    self._bookmarks[file_path] = [
                        Bookmark.from_dict(bookmark_data) 
                        for bookmark_data in bookmark_list
                    ]
                
                logger.info(f"Loaded bookmarks for {len(self._bookmarks)} files")
        except Exception as e:
            logger.error(f"Failed to load bookmarks: {e}")
    
    def _save_bookmarks(self):
        """Save bookmarks to persistent storage"""
        try:
            data = {}
            for file_path, bookmark_list in self._bookmarks.items():
                data[file_path] = [bookmark.to_dict() for bookmark in bookmark_list]
            
            with open(self._bookmarks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug("Saved bookmarks to disk")
        except Exception as e:
            logger.error(f"Failed to save bookmarks: {e}")
    
    def add_bookmark(self, file_path: str, timestamp: float, title: str, 
                    description: str = "", tags: List[str] = None) -> str:
        """
        Add a bookmark to a file.
        
        Args:
            file_path: Path to the audio file
            timestamp: Time position in seconds
            title: Bookmark title
            description: Optional description
            tags: Optional list of tags
            
        Returns:
            The ID of the created bookmark
        """
        bookmark = Bookmark(timestamp, title, description, tags)
        
        if file_path not in self._bookmarks:
            self._bookmarks[file_path] = []
        
        self._bookmarks[file_path].append(bookmark)
        
        # Keep bookmarks sorted by timestamp
        self._bookmarks[file_path].sort(key=lambda b: b.timestamp)
        
        self._save_bookmarks()
        logger.info(f"Added bookmark '{title}' at {timestamp:.2f}s for {Path(file_path).name}")
        
        return bookmark.id
    
    def remove_bookmark(self, file_path: str, bookmark_id: str) -> bool:
        """
        Remove a bookmark.
        
        Args:
            file_path: Path to the audio file
            bookmark_id: ID of the bookmark to remove
            
        Returns:
            True if bookmark was removed, False otherwise
        """
        if file_path not in self._bookmarks:
            return False
        
        bookmark_list = self._bookmarks[file_path]
        for i, bookmark in enumerate(bookmark_list):
            if bookmark.id == bookmark_id:
                removed_bookmark = bookmark_list.pop(i)
                self._save_bookmarks()
                logger.info(f"Removed bookmark '{removed_bookmark.title}'")
                return True
        
        return False
    
    def get_bookmarks(self, file_path: str) -> List[Bookmark]:
        """
        Get all bookmarks for a file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            List of bookmarks sorted by timestamp
        """
        return self._bookmarks.get(file_path, [])
    
    def get_bookmark(self, file_path: str, bookmark_id: str) -> Optional[Bookmark]:
        """
        Get a specific bookmark.
        
        Args:
            file_path: Path to the audio file
            bookmark_id: ID of the bookmark
            
        Returns:
            The bookmark if found, None otherwise
        """
        bookmarks = self.get_bookmarks(file_path)
        for bookmark in bookmarks:
            if bookmark.id == bookmark_id:
                return bookmark
        return None
    
    def update_bookmark(self, file_path: str, bookmark_id: str, 
                       title: str = None, description: str = None, 
                       tags: List[str] = None) -> bool:
        """
        Update an existing bookmark.
        
        Args:
            file_path: Path to the audio file
            bookmark_id: ID of the bookmark to update
            title: New title (optional)
            description: New description (optional)
            tags: New tags (optional)
            
        Returns:
            True if bookmark was updated, False otherwise
        """
        bookmark = self.get_bookmark(file_path, bookmark_id)
        if not bookmark:
            return False
        
        if title is not None:
            bookmark.title = title
        if description is not None:
            bookmark.description = description
        if tags is not None:
            bookmark.tags = tags
        
        self._save_bookmarks()
        logger.info(f"Updated bookmark '{bookmark.title}'")
        return True
    
    def search_bookmarks(self, query: str) -> List[Tuple[str, Bookmark]]:
        """
        Search for bookmarks by title, description, or tags.
        
        Args:
            query: Search query
            
        Returns:
            List of (file_path, bookmark) tuples matching the query
        """
        results = []
        query_lower = query.lower()
        
        for file_path, bookmark_list in self._bookmarks.items():
            for bookmark in bookmark_list:
                # Search in title, description, and tags
                if (query_lower in bookmark.title.lower() or 
                    query_lower in bookmark.description.lower() or
                    any(query_lower in tag.lower() for tag in bookmark.tags)):
                    results.append((file_path, bookmark))
        
        return results
    
    def get_bookmarks_by_tag(self, tag: str) -> List[Tuple[str, Bookmark]]:
        """
        Get all bookmarks with a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of (file_path, bookmark) tuples with the tag
        """
        results = []
        tag_lower = tag.lower()
        
        for file_path, bookmark_list in self._bookmarks.items():
            for bookmark in bookmark_list:
                if any(tag_lower == existing_tag.lower() for existing_tag in bookmark.tags):
                    results.append((file_path, bookmark))
        
        return results
    
    def get_all_tags(self) -> List[str]:
        """
        Get all unique tags across all bookmarks.
        
        Returns:
            List of unique tags
        """
        all_tags = set()
        
        for bookmark_list in self._bookmarks.values():
            for bookmark in bookmark_list:
                all_tags.update(bookmark.tags)
        
        return sorted(list(all_tags))
    
    def export_bookmarks(self, file_path: str = None) -> Dict[str, Any]:
        """
        Export bookmarks to a dictionary.
        
        Args:
            file_path: Optional file path to export bookmarks for specific file
            
        Returns:
            Dictionary containing bookmark data
        """
        if file_path:
            bookmarks = self.get_bookmarks(file_path)
            return {
                "file_path": file_path,
                "bookmarks": [bookmark.to_dict() for bookmark in bookmarks],
                "exported_at": datetime.now().isoformat()
            }
        else:
            data = {}
            for fp, bookmark_list in self._bookmarks.items():
                data[fp] = [bookmark.to_dict() for bookmark in bookmark_list]
            
            return {
                "all_bookmarks": data,
                "exported_at": datetime.now().isoformat()
            }
    
    def import_bookmarks(self, data: Dict[str, Any], merge: bool = True) -> bool:
        """
        Import bookmarks from a dictionary.
        
        Args:
            data: Dictionary containing bookmark data
            merge: If True, merge with existing bookmarks; if False, replace
            
        Returns:
            True if import was successful, False otherwise
        """
        try:
            if "file_path" in data and "bookmarks" in data:
                # Single file import
                file_path = data["file_path"]
                if not merge:
                    self._bookmarks[file_path] = []
                
                for bookmark_data in data["bookmarks"]:
                    bookmark = Bookmark.from_dict(bookmark_data)
                    if file_path not in self._bookmarks:
                        self._bookmarks[file_path] = []
                    self._bookmarks[file_path].append(bookmark)
                
                # Sort bookmarks
                self._bookmarks[file_path].sort(key=lambda b: b.timestamp)
                
            elif "all_bookmarks" in data:
                # Multiple files import
                if not merge:
                    self._bookmarks.clear()
                
                for file_path, bookmark_list in data["all_bookmarks"].items():
                    if file_path not in self._bookmarks:
                        self._bookmarks[file_path] = []
                    
                    for bookmark_data in bookmark_list:
                        bookmark = Bookmark.from_dict(bookmark_data)
                        self._bookmarks[file_path].append(bookmark)
                    
                    # Sort bookmarks
                    self._bookmarks[file_path].sort(key=lambda b: b.timestamp)
            
            self._save_bookmarks()
            logger.info("Successfully imported bookmarks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import bookmarks: {e}")
            return False
    
    def clear_bookmarks(self, file_path: str = None) -> bool:
        """
        Clear bookmarks for a file or all files.
        
        Args:
            file_path: Optional file path to clear bookmarks for specific file
            
        Returns:
            True if clearing was successful, False otherwise
        """
        try:
            if file_path:
                if file_path in self._bookmarks:
                    del self._bookmarks[file_path]
                    logger.info(f"Cleared bookmarks for {Path(file_path).name}")
            else:
                self._bookmarks.clear()
                logger.info("Cleared all bookmarks")
            
            self._save_bookmarks()
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear bookmarks: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about bookmarks.
        
        Returns:
            Dictionary with bookmark statistics
        """
        total_bookmarks = sum(len(bookmarks) for bookmarks in self._bookmarks.values())
        total_files = len(self._bookmarks)
        all_tags = self.get_all_tags()
        
        return {
            "total_bookmarks": total_bookmarks,
            "total_files": total_files,
            "total_tags": len(all_tags),
            "tags": all_tags,
            "files_with_bookmarks": list(self._bookmarks.keys()),
            "average_bookmarks_per_file": total_bookmarks / max(total_files, 1)
        }
