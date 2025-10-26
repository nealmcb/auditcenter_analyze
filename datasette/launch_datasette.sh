#!/bin/bash
# Launch datasette in isolated environment

if [ ! -d "datasette-env" ]; then
    echo "Virtual environment not found. Run setup first:"
    echo "  bash setup_datasette_env.sh"
    exit 1
fi

source datasette-env/bin/activate
datasette ../output/colorado_rla.db --metadata metadata.json

