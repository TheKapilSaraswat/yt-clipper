#!/usr/bin/env bash
set -euo pipefail

echo "=== YouTube Shorts Clipper Setup ==="

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found. Install Python 3.8+ first."
    exit 1
fi

# Check ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "Warning: ffmpeg not found. Install ffmpeg via your package manager."
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  macOS: brew install ffmpeg"
    echo "  Windows: choco install ffmpeg"
fi

# Check yt-dlp
PIP=$(command -v pip3 || command -v pip)
if ! command -v yt-dlp &>/dev/null; then
    echo "Installing yt-dlp..."
    $PIP install yt-dlp
fi

# Install Python deps
$PIP install -r requirements.txt 2>/dev/null || $PIP install yt-dlp google-api-python-client google-auth-oauthlib

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Place client_secret.json in this directory for YouTube upload"
echo "  2. Make sure ffmpeg is installed"
echo "  3. Run: python daily_pipeline.py"
echo ""
