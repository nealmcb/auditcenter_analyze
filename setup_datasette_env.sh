#!/bin/bash
# Create isolated environment for datasette to avoid numpy conflicts

set -e

echo "Creating virtual environment for datasette..."
python3 -m venv datasette-env

echo "Activating environment..."
source datasette-env/bin/activate

echo "Installing datasette with compatible numpy..."
pip install --upgrade pip
pip install 'numpy<2'  # NumPy 1.x for compatibility
pip install datasette datasette-vega

echo ""
echo "✓ Setup complete!"
echo ""
echo "To use datasette:"
echo "  source datasette-env/bin/activate"
echo "  datasette colorado_rla.db --metadata datasette-metadata.json"
echo ""
echo "To exit:"
echo "  deactivate"

