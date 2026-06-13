#!/bin/bash
# ============================================================
# SENTINEL-7 UAP Live Map — push to GitHub
# ============================================================
# 1. Extract: tar -xzf uap-live-map-with-git.tar.gz && cd uap-live-map
# 2. Make sure ~/.github_token contains your GitHub Personal Access Token
#    (Settings -> Developer settings -> Fine-grained tokens, repo:write scope)
# 3. Run: bash push-to-github.sh
# ============================================================

set -e

USERNAME="qshaiya"
REPO="UAP-Global-Map2"
TOKEN_FILE="$HOME/.github_token"

if [ ! -f "$TOKEN_FILE" ]; then
  echo "❌ Token file not found at $TOKEN_FILE"
  echo "   Create it with: echo 'github_pat_XXXX...' > ~/.github_token"
  exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")

echo "⬆️  Pushing code to https://github.com/$USERNAME/$REPO ..."
git remote remove origin 2>/dev/null || true
git remote add origin "https://$USERNAME:$TOKEN@github.com/$USERNAME/$REPO.git"
git push -u origin main --force

echo ""
echo "✅ Done! Visit: https://github.com/$USERNAME/$REPO"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "  1. Go to https://github.com/$USERNAME/$REPO/settings/secrets/actions"
echo "     and add a secret named OPENROUTER_API_KEY with your OpenRouter key"
echo "     (get one free at https://openrouter.ai/keys, add ~\$1-2 credit for the"
echo "     web search plugin)."
echo "  2. (Optional) Enable GitHub Pages: Settings -> Pages -> Source: main branch, / (root)"
echo "     Your live map will then be at: https://$USERNAME.github.io/$REPO/"
echo "  3. The daily scan runs automatically at 09:00 UTC, or trigger manually:"
echo "     Actions tab -> Daily UAP Scan -> Run workflow"
