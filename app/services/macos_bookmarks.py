#!/usr/bin/env python3
"""
macOS Security-Scoped Bookmarks handler for AudioTransLocal

This module provides functionality to create and resolve security-scoped bookmarks
on macOS, which are required to maintain access to user-selected folders across
app restarts in sandboxed applications.
"""

import sys
import base64
from typing import Optional, Tuple
from pathlib import Path

try:
    from Foundation import NSURL, NSData
    from Cocoa import NSURLBookmarkCreationWithSecurityScope, NSURLBookmarkResolutionWithSecurityScope
    MACOS_AVAILABLE = True
except ImportError:
    MACOS_AVAILABLE = False
    print("Warning: PyObjC not available. Security-scoped bookmarks will not work.")


class SecurityScopedBookmarkManager:
    """
    Manages security-scoped bookmarks for macOS folder access.
    
    Security-scoped bookmarks allow sandboxed applications to retain access
    to user-selected folders across app restarts, which is required by modern
    macOS privacy and sandboxing controls.
    """
    
    @staticmethod
    def is_available() -> bool:
        """Check if security-scoped bookmarks are available on this system."""
        return MACOS_AVAILABLE and sys.platform == 'darwin'
    
    @staticmethod
    def create_bookmark(folder_path: str) -> Optional[str]:
        """
        Create a security-scoped bookmark for the given folder path.
        
        Args:
            folder_path: The absolute path to the folder
            
        Returns:
            Base64-encoded bookmark data, or None if creation failed
        """
        if not SecurityScopedBookmarkManager.is_available():
            print("Security-scoped bookmarks not available on this platform")
            return None
        
        try:
            # Convert path to NSURL
            folder_url = NSURL.fileURLWithPath_(folder_path)
            
            # Create security-scoped bookmark
            bookmark_data, error = folder_url.bookmarkDataWithOptions_includingResourceValuesForKeys_relativeToURL_error_(
                NSURLBookmarkCreationWithSecurityScope,
                None,
                None,
                None
            )
            
            if error:
                print(f"Error creating bookmark: {error}")
                return None
            
            if bookmark_data:
                # Convert NSData to base64 string for storage
                bookmark_bytes = bookmark_data.bytes().tobytes()
                bookmark_b64 = base64.b64encode(bookmark_bytes).decode('utf-8')
                print(f"✅ Created security-scoped bookmark for: {folder_path}")
                return bookmark_b64
            else:
                print("Failed to create bookmark data")
                return None
                
        except Exception as e:
            print(f"Exception creating bookmark: {e}")
            return None
    
    @staticmethod
    def resolve_bookmark(bookmark_data: str) -> Optional[Tuple[str, object]]:
        """
        Resolve a security-scoped bookmark back to a folder path and URL.
        
        Args:
            bookmark_data: Base64-encoded bookmark data
            
        Returns:
            Tuple of (folder_path, security_scoped_url) or None if resolution failed
            The security_scoped_url should be used to start accessing the folder.
        """
        if not SecurityScopedBookmarkManager.is_available():
            print("Security-scoped bookmarks not available on this platform")
            return None
        
        try:
            # Decode base64 bookmark data
            bookmark_bytes = base64.b64decode(bookmark_data.encode('utf-8'))
            bookmark_nsdata = NSData.dataWithBytes_length_(bookmark_bytes, len(bookmark_bytes))
            
            # Resolve bookmark to URL
            resolved_url, is_stale, error = NSURL.URLByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error_(
                bookmark_nsdata,
                NSURLBookmarkResolutionWithSecurityScope,
                None,
                None,
                None
            )
            
            if error:
                print(f"Error resolving bookmark: {error}")
                return None
            
            if resolved_url:
                folder_path = resolved_url.path()
                if is_stale:
                    print(f"⚠️  Bookmark is stale for: {folder_path}")
                else:
                    print(f"✅ Resolved security-scoped bookmark to: {folder_path}")
                
                return folder_path, resolved_url
            else:
                print("Failed to resolve bookmark")
                return None
                
        except Exception as e:
            print(f"Exception resolving bookmark: {e}")
            return None
    
    @staticmethod
    def start_accessing_url(security_scoped_url) -> bool:
        """
        Start accessing a security-scoped URL.
        
        Must be called before accessing files in the folder.
        Should be paired with stop_accessing_url when done.
        
        Args:
            security_scoped_url: The NSURL returned from resolve_bookmark
            
        Returns:
            True if access was successfully started
        """
        if not SecurityScopedBookmarkManager.is_available():
            return False
        
        try:
            success = security_scoped_url.startAccessingSecurityScopedResource()
            if success:
                print("✅ Started accessing security-scoped resource")
            else:
                print("❌ Failed to start accessing security-scoped resource")
            return success
        except Exception as e:
            print(f"Exception starting access: {e}")
            return False
    
    @staticmethod
    def stop_accessing_url(security_scoped_url) -> None:
        """
        Stop accessing a security-scoped URL.
        
        Should be called when done accessing files in the folder.
        Must be paired with start_accessing_url.
        
        Args:
            security_scoped_url: The NSURL returned from resolve_bookmark
        """
        if not SecurityScopedBookmarkManager.is_available():
            return
        
        try:
            security_scoped_url.stopAccessingSecurityScopedResource()
            print("✅ Stopped accessing security-scoped resource")
        except Exception as e:
            print(f"Exception stopping access: {e}")


class BookmarkAwareSettings:
    """
    A wrapper around QSettings that handles security-scoped bookmarks for folder paths.
    
    This class automatically creates bookmarks when storing folder paths and
    resolves them when retrieving folder paths.
    """
    
    def __init__(self, settings):
        """
        Initialize with a QSettings instance.
        
        Args:
            settings: QSettings instance to wrap
        """
        self.settings = settings
        self._active_urls = {}  # Track active security-scoped URLs
    
    def store_folder_path(self, key: str, folder_path: str) -> bool:
        """
        Store a folder path with security-scoped bookmark.
        
        Args:
            key: Settings key to store under
            folder_path: Absolute path to the folder
            
        Returns:
            True if stored successfully
        """
        if SecurityScopedBookmarkManager.is_available():
            # Create security-scoped bookmark
            bookmark_data = SecurityScopedBookmarkManager.create_bookmark(folder_path)
            if bookmark_data:
                # Store bookmark data instead of path
                self.settings.setValue(f"{key}_bookmark", bookmark_data)
                self.settings.setValue(f"{key}_path", folder_path)  # Also store path for fallback
                return True
            else:
                print(f"Failed to create bookmark for {folder_path}, storing path only")
                self.settings.setValue(f"{key}_path", folder_path)
                return False
        else:
            # Fallback: just store the path
            self.settings.setValue(f"{key}_path", folder_path)
            return True
    
    def get_folder_path(self, key: str) -> Optional[str]:
        """
        Retrieve a folder path, resolving security-scoped bookmark if needed.
        
        Args:
            key: Settings key to retrieve
            
        Returns:
            Folder path if available and accessible, None otherwise
        """
        if SecurityScopedBookmarkManager.is_available():
            # Try to resolve bookmark first
            bookmark_data = self.settings.value(f"{key}_bookmark")
            if bookmark_data:
                result = SecurityScopedBookmarkManager.resolve_bookmark(bookmark_data)
                if result:
                    folder_path, security_scoped_url = result
                    
                    # Start accessing the security-scoped resource
                    if SecurityScopedBookmarkManager.start_accessing_url(security_scoped_url):
                        # Store the active URL for later cleanup
                        self._active_urls[key] = security_scoped_url
                        return folder_path
                    else:
                        print(f"Failed to start accessing security-scoped resource for {key}")
                
                print(f"Failed to resolve bookmark for {key}, falling back to stored path")
        
        # Fallback: return stored path
        return self.settings.value(f"{key}_path")
    
    def cleanup_security_scoped_access(self, key: str = None) -> None:
        """
        Clean up security-scoped access for a specific key or all keys.
        
        Args:
            key: Specific key to cleanup, or None to cleanup all
        """
        if key:
            if key in self._active_urls:
                SecurityScopedBookmarkManager.stop_accessing_url(self._active_urls[key])
                del self._active_urls[key]
        else:
            # Clean up all active URLs
            for active_key, url in self._active_urls.items():
                SecurityScopedBookmarkManager.stop_accessing_url(url)
            self._active_urls.clear()
    
    def __del__(self):
        """Cleanup all security-scoped access when the object is destroyed."""
        self.cleanup_security_scoped_access()


# Test function
def test_security_scoped_bookmarks():
    """Test the security-scoped bookmark functionality."""
    print("🔐 Testing Security-Scoped Bookmarks")
    print("=" * 50)
    
    if not SecurityScopedBookmarkManager.is_available():
        print("❌ Security-scoped bookmarks not available on this platform")
        return
    
    # Test with Downloads folder
    test_folder = "/Users/lopezm52/Downloads"
    
    print(f"\n1. Testing bookmark creation for: {test_folder}")
    bookmark_data = SecurityScopedBookmarkManager.create_bookmark(test_folder)
    
    if bookmark_data:
        print(f"   ✅ Bookmark created (length: {len(bookmark_data)} chars)")
        
        print(f"\n2. Testing bookmark resolution:")
        result = SecurityScopedBookmarkManager.resolve_bookmark(bookmark_data)
        
        if result:
            resolved_path, security_scoped_url = result
            print(f"   ✅ Bookmark resolved to: {resolved_path}")
            
            print(f"\n3. Testing security-scoped access:")
            if SecurityScopedBookmarkManager.start_accessing_url(security_scoped_url):
                print("   ✅ Successfully started accessing security-scoped resource")
                
                # Test accessing a file in the folder
                try:
                    import os
                    files = os.listdir(resolved_path)
                    print(f"   ✅ Successfully listed {len(files)} items in folder")
                except Exception as e:
                    print(f"   ❌ Failed to access folder contents: {e}")
                
                SecurityScopedBookmarkManager.stop_accessing_url(security_scoped_url)
                print("   ✅ Successfully stopped accessing security-scoped resource")
            else:
                print("   ❌ Failed to start accessing security-scoped resource")
        else:
            print("   ❌ Failed to resolve bookmark")
    else:
        print("   ❌ Failed to create bookmark")
    
    print("\n✅ Security-scoped bookmark tests completed!")


if __name__ == "__main__":
    test_security_scoped_bookmarks()
