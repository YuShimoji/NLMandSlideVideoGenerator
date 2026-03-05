#!/bin/bash
# Branch Protection Setup Script
#
# Sets up master branch protection with the following rules:
# - Direct push prohibited
# - PR required for all changes
# - ci-main workflow (Tests, Type Check, Lint) must pass
# - Enforce for administrators
#
# Prerequisites:
# - GitHub CLI (gh) installed and authenticated
# - Repository admin access
#
# Usage:
#   ./scripts/setup_branch_protection.sh

set -euo pipefail

REPO_OWNER="YuShimoji"
REPO_NAME="NLMandSlideVideoGenerator"
BRANCH="master"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ ${NC}$*"
}

log_success() {
    echo -e "${GREEN}✓ ${NC}$*"
}

log_warning() {
    echo -e "${YELLOW}⚠ ${NC}$*"
}

log_error() {
    echo -e "${RED}✗ ${NC}$*"
}

# Error handler
error_exit() {
    log_error "$1"
    exit 1
}

# Cleanup on exit
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Setup failed with exit code $exit_code"
    fi
    return $exit_code
}
trap cleanup EXIT

echo "=========================================="
echo "Branch Protection Setup for ${BRANCH}"
echo "=========================================="
echo ""

# Prerequisites check
log_info "Checking prerequisites..."

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    error_exit "GitHub CLI (gh) is not installed. Install from: https://cli.github.com/"
fi
log_success "GitHub CLI found"

# Check authentication
if ! gh auth status &> /dev/null; then
    error_exit "Not authenticated with GitHub CLI. Run: gh auth login"
fi
log_success "GitHub CLI authenticated"

# Get repository information
log_info "Verifying repository access..."
if ! REPO_INFO=$(gh api "repos/${REPO_OWNER}/${REPO_NAME}" --jq '.name, .owner.login, .private' 2>&1); then
    error_exit "Repository not accessible. Check owner/name or permissions."
fi
log_success "Repository access verified: ${REPO_OWNER}/${REPO_NAME}"

echo ""
echo "=========================================="
echo "Protection Configuration"
echo "=========================================="
echo "Repository: ${REPO_OWNER}/${REPO_NAME}"
echo "Branch: ${BRANCH}"
echo ""
echo "Rules to be applied:"
echo "  • Direct push prohibited (require PR)"
echo "  • ci-main workflow tests must pass:"
echo "    - Tests (Python 3.11)"
echo "    - Tests (.NET YMM4 Plugin)"
echo "    - Type Check (mypy)"
echo "    - Lint"
echo "  • Enforce rules on administrators (dismiss stale reviews)"
echo "  • Allow force pushes: NO"
echo "  • Allow deletions: NO"
echo ""

# Confirmation prompt
read -p "Continue with these settings? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warning "Setup cancelled by user"
    exit 0
fi

echo ""
log_info "Applying branch protection rules..."
echo ""

# Apply branch protection with all required checks
if gh api \
  --method PUT \
  "/repos/${REPO_OWNER}/${REPO_NAME}/branches/${BRANCH}/protection" \
  --input - << 'PAYLOAD'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Tests (Python 3.11)",
      "Tests (.NET YMM4 Plugin)",
      "Type Check (mypy)",
      "Lint"
    ]
  },
  "enforce_admins": true,
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
PAYLOAD
then
    log_success "Branch protection applied successfully!"
    echo ""
    echo "=========================================="
    echo "Configuration Summary"
    echo "=========================================="
    echo ""
    log_success "Direct push to '${BRANCH}': DISABLED"
    log_success "Pull Request requirement: ENABLED"
    log_success "ci-main workflow: REQUIRED"
    log_success "Admin enforcement: ENABLED"
    echo ""
    log_info "Status check contexts:"
    echo "  • Tests (Python 3.11)"
    echo "  • Tests (.NET YMM4 Plugin)"
    echo "  • Type Check (mypy)"
    echo "  • Lint"
    echo ""
    log_info "Additional rules:"
    echo "  • Stale review dismissal: ENABLED"
    echo "  • Force push: DISABLED"
    echo "  • Branch deletion: DISABLED"
    echo "  • Conversation resolution: REQUIRED"
    echo ""
    log_info "View settings: https://github.com/${REPO_OWNER}/${REPO_NAME}/settings/branches"
    echo ""
    log_success "Branch protection setup completed!"
else
    error_exit "Failed to apply branch protection. Check repository permissions and try again."
fi
