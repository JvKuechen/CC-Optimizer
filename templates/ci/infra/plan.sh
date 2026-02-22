#!/bin/bash
# Generate deployment plan: what changed, which ring, what will deploy
#
# Reads git diff to determine changed files, classifies them by ring,
# and outputs a human-readable plan + JSON summary.
#
# Usage: plan.sh
# Env vars:
#   GITHUB_SHA         - Current commit SHA (set by Gitea Actions)
#   GITHUB_EVENT_BEFORE - Previous commit SHA (set by Gitea Actions on push)
#
# Exit: 0 always (plan is informational, never fails)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
resolve_ci_root

log_step "Generating deployment plan"

# --- Determine changed files ---

CURRENT_SHA="${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo 'unknown')}"
PREVIOUS_SHA="${GITHUB_EVENT_BEFORE:-$(git rev-parse HEAD~1 2>/dev/null || echo '')}"

if [ -z "$PREVIOUS_SHA" ] || [ "$PREVIOUS_SHA" = "0000000000000000000000000000000000000000" ]; then
    # First push or force push - list all files
    log_info "No previous SHA available, listing all tracked files"
    CHANGED_FILES=$(git ls-files 2>/dev/null || echo "")
else
    log_info "Comparing ${PREVIOUS_SHA:0:8}..${CURRENT_SHA:0:8}"
    CHANGED_FILES=$(git diff --name-only "$PREVIOUS_SHA".."$CURRENT_SHA" 2>/dev/null || git ls-files)
fi

TOTAL_FILES=$(echo "$CHANGED_FILES" | grep -c . 2>/dev/null || echo 0)

if [ "$TOTAL_FILES" -eq 0 ]; then
    log_info "No files changed"
    json_result "plan" '"total":0,"has_ring0":false,"ring0_count":0,"ring1_count":0,"deploy":false'
    exit 0
fi

# --- Classify by ring ---

CLASSIFICATION=$(echo "$CHANGED_FILES" | classify_changes)
HAS_RING0=$(echo "$CLASSIFICATION" | jq -r '.has_ring0')
RING0_COUNT=$(echo "$CLASSIFICATION" | jq -r '.ring0_count')
RING1_COUNT=$(echo "$CLASSIFICATION" | jq -r '.ring1_count')

# --- Human-readable output (stderr) ---

log_info "========================================"
log_info "DEPLOYMENT PLAN"
log_info "========================================"
log_info "Commit: ${CURRENT_SHA:0:8}"
log_info "Files changed: $TOTAL_FILES"
log_info "Ring 0 (manual): $RING0_COUNT"
log_info "Ring 1 (auto):   $RING1_COUNT"
log_info "----------------------------------------"

if [ "$HAS_RING0" = "true" ]; then
    log_warn "Ring 0 files detected - deploy will be VALIDATE-ONLY"
    log_warn "Ring 0 changes require manual deployment:"
    echo "$CLASSIFICATION" | jq -r '.ring0_files[]' 2>/dev/null | while IFS= read -r f; do
        log_warn "  [Ring 0] $f"
    done
fi

if [ "$RING1_COUNT" -gt 0 ]; then
    log_info "Ring 1 files (will auto-deploy to passive):"
    echo "$CLASSIFICATION" | jq -r '.ring1_files[]' 2>/dev/null | while IFS= read -r f; do
        log_info "  [Ring 1] $f"
    done
fi

# Detect affected services
AFFECTED_SERVICES=$(echo "$CHANGED_FILES" | detect_affected_services)
if [ -n "$AFFECTED_SERVICES" ]; then
    log_info "----------------------------------------"
    log_info "Affected services: $AFFECTED_SERVICES"
fi

SHOULD_DEPLOY="true"
if [ "$RING1_COUNT" -eq 0 ]; then
    SHOULD_DEPLOY="false"
    log_info "No Ring 1 changes - nothing to auto-deploy"
fi

log_info "========================================"

# --- JSON output (stdout) ---

# Build services JSON array
SERVICES_JSON="[]"
if [ -n "$AFFECTED_SERVICES" ]; then
    SERVICES_JSON=$(echo "$AFFECTED_SERVICES" | tr ' ' '\n' | jq -R . | jq -sc .)
fi

json_result "plan" "\"commit\":\"${CURRENT_SHA:0:8}\",\"total\":$TOTAL_FILES,\"has_ring0\":$HAS_RING0,\"ring0_count\":$RING0_COUNT,\"ring1_count\":$RING1_COUNT,\"deploy\":$SHOULD_DEPLOY,\"affected_services\":$SERVICES_JSON"

exit 0
