#!/bin/bash

# Build script for AudioTransLocal Mac App
echo "🚀 Building AudioTransLocal v1.0 for macOS with PySide6..."

# Get the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found! Please create .venv first."
    exit 1
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/
rm -rf dist/

# Create dist directory
mkdir -p dist

echo "📦 Building application with PyInstaller (PySide6)..."

# Build the application using the virtual environment's Python with PyInstaller module
.venv/bin/python -m PyInstaller AudioTransLocal.spec --clean --noconfirm

# Check if build was successful
if [ -d "dist/AudioTransLocal.app" ]; then
    echo "✅ Build successful!"
    echo "📍 Your app is ready at: dist/AudioTransLocal.app"
    echo ""
    
    # Test if the app can launch
    echo "🧪 Testing app launch..."
    open dist/AudioTransLocal.app
    sleep 3
    
    echo "📦 Creating distribution package..."
    cd dist
    
    # Create a zip file for distribution
    zip -r "AudioTransLocal-v1.0-macOS.zip" AudioTransLocal.app/
    
    echo ""
    echo "✅ Distribution package created!"
    echo "📍 Distribution file: dist/AudioTransLocal-v1.0-macOS.zip"
    echo ""
    echo "App information:"
    echo "  Size: $(du -sh AudioTransLocal.app | cut -f1)"
    echo "  Zip size: $(du -sh AudioTransLocal-v1.0-macOS.zip | cut -f1)"
    echo ""
    echo "🎉 Ready for distribution!"
    echo "Users can:"
    echo "  1. Download AudioTransLocal-v1.0-macOS.zip"
    echo "  2. Unzip it"
    echo "  3. Drag AudioTransLocal.app to Applications folder"
    echo "  4. Run it from Applications or Finder"
    
    cd ..
else
    echo "❌ Build failed!"
    echo "Check the output above for errors."
    exit 1
fi
