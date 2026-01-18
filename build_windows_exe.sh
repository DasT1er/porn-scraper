#!/bin/bash
# Automatic Windows .exe Builder
# This script builds Windows executables on Linux using Docker

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  Windows .exe Builder for Porn Scraper"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ ERROR: Docker is not installed!"
    echo ""
    echo "Please install Docker first:"
    echo "  Ubuntu/Debian: sudo apt install docker.io"
    echo "  Fedora: sudo dnf install docker"
    echo "  Arch: sudo pacman -S docker"
    echo ""
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ ERROR: Docker daemon is not running!"
    echo ""
    echo "Please start Docker:"
    echo "  sudo systemctl start docker"
    echo ""
    exit 1
fi

echo "✓ Docker is ready"
echo ""

# Create output directory
mkdir -p windows_build

echo "🔨 Building Windows executables..."
echo "   This may take 5-10 minutes on first run (downloading Docker image)"
echo ""

# Build using Docker
docker build -f Dockerfile.windows -t porn-scraper-builder .

# Extract the executables from the container
echo ""
echo "📦 Extracting executables..."
CONTAINER_ID=$(docker create porn-scraper-builder)
docker cp $CONTAINER_ID:/src/dist/scraper.exe ./windows_build/
docker cp $CONTAINER_ID:/src/dist/scraper_ui.exe ./windows_build/
docker cp $CONTAINER_ID:/src/config.yaml ./windows_build/
docker rm $CONTAINER_ID

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ BUILD SUCCESSFUL!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Windows executables are in: ./windows_build/"
ls -lh ./windows_build/
echo ""
echo "📁 Copy these files to Windows:"
echo "   - scraper.exe      (command-line version)"
echo "   - scraper_ui.exe   (interactive UI version)"
echo "   - config.yaml      (configuration file)"
echo ""
echo "⚠️  On Windows, you must install Playwright browsers:"
echo "   pip install playwright"
echo "   playwright install chromium"
echo ""
