#!/bin/bash
set -euo pipefail

# SessionStart hook for Chicago Clay Coop
# Installs beads CLI and validates environment

echo '{"async": false}'

# Ensure Go is installed
if ! command -v go &> /dev/null; then
  echo "Error: Go is required to install beads CLI" >&2
  exit 1
fi

# Install beads CLI via Go
echo "Installing beads CLI..."
go install github.com/steveyegge/beads/cmd/bd@latest 2>&1 | grep -v "downloading" || true

# Add go/bin to PATH for this session
export PATH="$HOME/go/bin:$PATH"
echo "export PATH=\"\$HOME/go/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"

# Verify beads is available
if ! command -v bd &> /dev/null; then
  echo "Error: Failed to install beads CLI" >&2
  exit 1
fi

# Verify Python 3.7+ is available
echo "Checking Python environment..."
if ! command -v python3 &> /dev/null; then
  echo "Error: Python 3 is required" >&2
  exit 1
fi

python3 --version

# Validate Python can import required modules
echo "Validating Python modules..."
python3 -c "import json, os, re, datetime, pathlib, urllib.parse; print('✓ All required modules available')"

echo "✓ Session setup complete!"
