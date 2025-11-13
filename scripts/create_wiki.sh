#!/bin/bash
# Script to create Wiki pages after Wiki is initialized via web interface
# Usage: After creating first page at https://github.com/KikuAI-Lab/reliapi/wiki
#        run: ./scripts/create_wiki.sh

set -e

REPO="KikuAI-Lab/reliapi"
WIKI_DIR="docs/wiki"

echo "Creating Wiki pages for $REPO..."

# Check if gh is authenticated
if ! gh auth status &>/dev/null; then
    echo "Error: GitHub CLI not authenticated. Run 'gh auth login' first."
    exit 1
fi

# Create pages
for file in "$WIKI_DIR"/*.md; do
    if [ -f "$file" ]; then
        title=$(basename "$file" .md)
        echo "Creating: $title"
        
        gh api repos/$REPO/wiki \
            -X POST \
            -f title="$title" \
            -f body="$(cat "$file")" \
            || echo "  ⚠️  Failed (Wiki may not be initialized yet)"
        
        sleep 1
    fi
done

echo ""
echo "✅ Wiki pages creation attempted."
echo "   If Wiki is not initialized, create first page at:"
echo "   https://github.com/$REPO/wiki"
echo ""
echo "   Then run this script again."

