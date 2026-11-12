#!/usr/bin/env bash
set -euo pipefail

# KalmiPrep CSS Build & Template Validation Script
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "${PROJECT_ROOT}"

echo "=========================================================="
echo " KalmiPrep UI & CSS Compilation Verification"
echo "=========================================================="

echo "1. Checking Tailwind CSS input file..."
if [ ! -f "static/css/input.css" ]; then
    echo "ERROR: static/css/input.css not found!"
    exit 1
fi

echo "2. Compiling Tailwind CSS..."
if command -v npx &>/dev/null; then
    npx tailwindcss -i ./static/css/input.css -o ./static/css/styles.css --minify
else
    echo "  (Using node:20-alpine container runner...)"
    docker run --rm -v "${PROJECT_ROOT}:/app" -w /app node:20-alpine npx tailwindcss -i ./static/css/input.css -o ./static/css/styles.css --minify
fi

OUTPUT_SIZE=$(wc -c < static/css/styles.css)
echo "✓ Tailwind compiled successfully (${OUTPUT_SIZE} bytes)"

echo "3. Verifying dark mode color tokens in output..."
if grep -q "navy-950" static/css/styles.css && grep -q "brand-500" static/css/styles.css; then
    echo "✓ Color tokens (navy-950, brand-500) detected in compiled CSS."
else
    echo "WARNING: Key color tokens might be missing from compiled output."
fi

echo "=========================================================="
echo " CSS Verification Complete!"
echo "=========================================================="
