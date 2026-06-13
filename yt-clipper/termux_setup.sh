#!/data/data/com.termux/files/usr/bin/bash
echo "=== YouTube Clipper - Android Setup ==="
echo ""

# Update packages
echo "[1/5] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# Install Python and required system packages
echo "[2/5] Installing Python and dependencies..."
pkg install -y python ffmpeg

# Install Python packages
echo "[3/5] Installing Python libraries..."
pip install yt-dlp google-api-python-client google-auth-oauthlib flask

# Create project directory
echo "[4/5] Setting up project..."
mkdir -p ~/youtube_clipper
cd ~/youtube_clipper

# Download the app files from your computer
# (You'll need to transfer android_app.py to your phone)

echo ""
echo "=== Setup Complete ==="
echo ""
echo "NEXT STEPS:"
echo "1. Copy android_app.py to: ~/youtube_clipper/"
echo "   Use: scp or termux-setup-storage then copy from internal storage"
echo ""
echo "2. Place client_secret.json in: ~/youtube_clipper/"
echo ""
echo "3. Run the app:"
echo "   cd ~/youtube_clipper && python android_app.py"
echo ""
echo "4. Open in your browser at: http://localhost:5000"
echo ""
echo "   Or from another device: http://$(ip -4 addr show wlan0 2>/dev/null | grep -oP 'inet \K[\d.]+' | head -1):5000"
echo ""
