#!/bin/bash
# Setup ACMS CLI alias
# Run with: source setup_alias.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect shell
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    SHELL_RC="$HOME/.profile"
fi

# Add alias if not already present
if ! grep -q "alias acms=" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# ACMS CLI Alias (Added: $(date))" >> "$SHELL_RC"
    echo "alias acms='cd $SCRIPT_DIR && source .env 2>/dev/null && source venv/bin/activate && python3 -m src.scripts.acms_cli'" >> "$SHELL_RC"
    echo "✅ Added 'acms' alias to $SHELL_RC"
    echo "   Run: source $SHELL_RC"
    echo "   Or restart your terminal"
else
    echo "✅ Alias already exists in $SHELL_RC"
fi

echo ""
echo "Test with:"
echo "  acms stats"
echo "  acms search \"your query\""
echo "  acms list --tag milestone"
