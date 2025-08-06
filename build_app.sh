#!/bin/bash

# Build script for AudioTransLocal Mac App
echo "🚀 Building AudioTransLocal for macOS with PySide6..."

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/
rm -rf dist/

# Build the application
echo "📦 Building application with PyInstaller (PySide6 + Centralized Styling)..."
/Users/lopezm52/Documents/VisualCode/AudioTransLocal/.venv/bin/pyinstaller AudioTransLocal.spec --clean

# Check if build was successful
if [ -d "dist/AudioTransLocal.app" ]; then
    echo "✅ Build successful!"
    echo "📍 Your app is ready at: dist/AudioTransLocal.app"
    echo ""
    echo "To test the app:"
    echo "  open dist/AudioTransLocal.app"
    echo ""
    echo "To distribute:"
    echo "  1. Zip the .app file: cd dist && zip -r AudioTransLocal.zip AudioTransLocal.app"
    echo "  2. Share the zip file with other Mac users"
    echo ""
    echo "App size:"
    du -sh dist/AudioTransLocal.app
else
    echo "❌ Build failed!"
    exit 1
fi
