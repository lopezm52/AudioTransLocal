#!/usr/bin/env python3
"""
A standalone script to calculate the SHA256 hash and size of a local file.
"""
import sys
import os
import hashlib

def verify_local_file(file_path):
    """Calculates and prints the SHA256 hash and size of the given file."""
    
    # 1. Check if the file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found at '{file_path}'")
        return

    try:
        # 2. Calculate the SHA256 hash
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read the file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        calculated_hash = sha256_hash.hexdigest()
        
        # 3. Get the file size
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1000 * 1000) # Megabytes (10^6)

        # 4. Print the results
        print("\n--- File Verification Report ---")
        print(f"File Path:    {file_path}")
        print(f"File Size:    {file_size_bytes} bytes (~{file_size_mb:.2f} MB)")
        print(f"SHA256 Hash:  {calculated_hash}")
        print("------------------------------\n")

    except Exception as e:
        print(f"An error occurred while processing the file: {e}")

if __name__ == "__main__":
    # Ensure a file path is provided as a command-line argument
    if len(sys.argv) < 2:
        print("Usage: python3 check_file.py /path/to/your/file")
    else:
        file_to_check = sys.argv[1]
        verify_local_file(file_to_check)