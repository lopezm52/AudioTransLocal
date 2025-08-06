"""
Configuration settings for AudioTransLocal
"""

import os
from pathlib import Path

# Application settings
APP_NAME = "AudioTransLocal"
VERSION = "1.0.0"

# File paths
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"

# Audio settings
DEFAULT_SAMPLE_RATE = 16000
CHUNK_SIZE = 1024

# Transcription settings
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"]

# Create directories if they don't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
