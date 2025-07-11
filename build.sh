#!/bin/bash
SCRIPT_DIR=$(dirname "$(realpath "$0")")

# Build CLI tool (console)
pyinstaller --noconfirm --onefile --console "$SCRIPT_DIR/streamledge.py"

# Build server (windowed + static/templates)
pyinstaller --noconfirm --onefile --windowed \
  --add-data "$SCRIPT_DIR/static:static/" \
  --add-data "$SCRIPT_DIR/templates:templates/" \
  "$SCRIPT_DIR/streamledge_server.py"

echo "Build complete! Check the 'dist' folder."
