#!/bin/bash
# Branch Protection Setup Script
#
# Prerequisites:
# - GitHub CLI (gh) installed and authenticated
# - Repository admin access
#
# Usage:
#   ./scripts/setup_branch_protection.sh

set -e

REPO_OWNER="YuShimoji"
REPO_NAME="NLMandSlideVideoGenerator"
BRANCH="master"

echo "=========================================="
echo "Branch Protection Setup"
echo "=========================================="
echo "Repository: ${REPO_OWNER}/${REPO_NAME}"
echo "Branch: ${BRANCH}"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed."
    echo "Install from: https://cli.github.com/"
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub CLI."
    echo "Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Enable branch protection
echo "🔒 Setting up branch protection for '${BRANCH}'..."

gh api \
  --method PUT \
  "/repos/${REPO_OWNER}/${REPO_NAME}/branches/${BRANCH}/protection" \
  --input - << 'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Tests (Python 3.11)",
      "Type Check (mypy)",
      "Lint"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismissal_restrictions": {},
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": true
}
EOF

if [ $? -eq 0 ]; then
    echo "✅ Branch protection enabled successfully!"
    echo ""
    echo "Protection rules:"
    echo "  - Required status checks: Tests, Type Check, Lint"
    echo "  - PR required for merging"
    echo "  - Dismiss stale reviews"
    echo "  - Require conversation resolution"
    echo "  - Block force pushes and deletions"
    echo ""
    echo "View settings: https://github.com/${REPO_OWNER}/${REPO_NAME}/settings/branches"
else
    echo "❌ Failed to set up branch protection"
    echo "Check repository permissions and try again"
    exit 1
fi
