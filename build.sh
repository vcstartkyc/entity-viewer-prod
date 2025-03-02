#!/bin/bash

# Create output directories
mkdir -p .output
mkdir -p .output/functions

# Copy application files
cp -r app.py data static templates translations messages.pot babel.cfg requirements.txt .output/

# Copy functions
cp -r functions/* .output/functions/

# Create _routes.json for static asset handling
cat > .output/_routes.json << 'EOL'
{
  "version": 1,
  "include": ["/*"],
  "exclude": []
}
EOL
