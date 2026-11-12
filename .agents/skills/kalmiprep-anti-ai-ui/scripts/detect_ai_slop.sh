#!/usr/bin/env bash
# ==========================================================
# KalmiPrep Anti-AI Slop Scanner
#
# Audits templates and styles for generic AI design tropes:
# - Sparkle emojis (✨)
# - Neon rainbow/purple-pink text gradients
# - AI marketing buzzwords (supercharge, unleash your, elevate your)
# - Extreme low-contrast glassmorphism
# ==========================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

echo "=========================================================="
echo " KalmiPrep Anti-AI UI & Slop Scanner"
echo "=========================================================="
echo "Scanning: ${PROJECT_ROOT}/templates and ${PROJECT_ROOT}/static"
echo ""

VIOLATIONS=0

check_pattern() {
    local label="$1"
    local pattern="$2"
    local search_path="$3"

    echo "Checking for ${label}..."
    local matches
    matches=$(grep -rnE "${pattern}" "${search_path}" --exclude-dir={node_modules,.git,.agents} 2>/dev/null || true)

    if [[ -n "${matches}" ]]; then
        echo "  [VIOLATION] Found ${label}:"
        echo "${matches}" | while IFS= read -r line; do
            echo "    → ${line}"
        done
        VIOLATIONS=$((VIOLATIONS + $(echo "${matches}" | wc -l)))
    else
        echo "  ✓ Clean (0 found)"
    fi
    echo ""
}

# 1. Check for Sparkle emojis
check_pattern "Sparkle emojis (✨)" "✨" "${PROJECT_ROOT}/templates"

# 2. Check for neon rainbow text gradients
check_pattern "Neon text gradients" "bg-clip-text.*(from-purple|from-pink|via-purple|to-pink)" "${PROJECT_ROOT}/templates"

# 3. Check for generic AI buzzwords
check_pattern "AI marketing buzzwords" "(supercharge|unleash your potential|elevate your prep|game-changer|AI-powered magic)" "${PROJECT_ROOT}/templates"

# 4. Check for extreme glassmorphism without contrast
check_pattern "Unreadable glassmorphism" "backdrop-blur-(2xl|3xl)[[:space:]]+bg-(white|slate|navy)/[0-9]" "${PROJECT_ROOT}/templates"

echo "=========================================================="
if [[ ${VIOLATIONS} -gt 0 ]]; then
    echo "Scan Complete: ${VIOLATIONS} AI slop violation(s) detected!"
    echo "Refactor templates to adhere to .agents/skills/kalmiprep-anti-ai-ui/"
    echo "=========================================================="
    exit 1
else
    echo "Scan Complete: 0 violations found. UI adheres to Anti-AI standard!"
    echo "=========================================================="
    exit 0
fi
