#!/bin/bash
# Publishing House Workspace Startup Script
# Runs when DevSpaces workspace starts

set -e

echo "🚀 Publishing House workspace starting..."

# Install Publishing House skills (if not already)
SKILLS_DIR="$HOME/.claude/skills/rhdp-publishing-house-skills"
if [ ! -d "$SKILLS_DIR" ]; then
    echo "📥 Installing Publishing House skills..."
    git clone https://github.com/rhpds/rhdp-publishing-house-skills.git "$SKILLS_DIR"
else
    echo "✅ Publishing House skills already installed"
fi

# Configure Claude Code CLI settings
mkdir -p "$HOME/.config/claude"
cat > "$HOME/.config/claude/config.json" <<EOF
{
  "apiKey": "$MAAS_API_KEY",
  "model": "claude-sonnet-4-5"
}
EOF

echo "✅ Workspace ready!"
echo ""
echo "🎯 Quick Start:"
echo "   1. Open terminal"
echo "   2. Run: claude --help"
echo "   3. Start building with /rhdp-publishing-house"
echo ""
