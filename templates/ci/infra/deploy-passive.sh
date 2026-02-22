#!/bin/bash
# Deploy Ring 1 changes to the passive server
# Connects via SSH to ci-deploy user, runs deploy.sh --auto
#
# Usage: deploy-passive.sh
# Required env vars:
#   TARGET_HOST  - Passive server IP (e.g., <passive-server-ip>)
#   SSH_KEY_PATH - Path to ci-deploy SSH private key
#
# Exit: 0 on success, non-zero on failure

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
source "$SCRIPT_DIR/../lib/ssh.sh"
source "$SCRIPT_DIR/../lib/report.sh"
resolve_ci_root

# Auto-detect Gitea env vars for status reporting
detect_gitea_env

log_step "Deploying Ring 1 to passive server ($TARGET_HOST)"
require_env TARGET_HOST SSH_KEY_PATH

# Report pending status
if [ -n "${GITEA_TOKEN:-}" ]; then
    report_pending "ci/deploy-passive" "Deploying to passive server"
fi

# --- Dry run first ---

log_info "Running dry-run deploy..."
DRY_OUTPUT=""
DRY_EC=0
DRY_OUTPUT=$(ssh_deploy "true") || DRY_EC=$?

if [ $DRY_EC -ne 0 ]; then
    log_error "Dry-run deploy failed"
    echo "$DRY_OUTPUT"
    if [ -n "${GITEA_TOKEN:-}" ]; then
        report_failure "ci/deploy-passive" "Dry-run deploy failed"
    fi
    json_error "deploy-passive" "dry-run failed on $TARGET_HOST"
    exit $EXIT_DEPLOY_FAILED
fi

log_info "Dry-run passed, proceeding with real deploy"

# --- Real deploy ---

timer_start
DEPLOY_OUTPUT=""
DEPLOY_EC=0
DEPLOY_OUTPUT=$(ssh_deploy "false") || DEPLOY_EC=$?
ELAPSED=$(timer_elapsed)

if [ $DEPLOY_EC -ne 0 ]; then
    log_error "Deploy to passive FAILED (${ELAPSED}s)"
    echo "$DEPLOY_OUTPUT"
    if [ -n "${GITEA_TOKEN:-}" ]; then
        report_failure "ci/deploy-passive" "Deploy failed on passive (${ELAPSED}s)"
    fi
    json_error "deploy-passive" "deploy failed on $TARGET_HOST (exit $DEPLOY_EC)"
    exit $EXIT_DEPLOY_FAILED
fi

log_info "Deploy to passive SUCCEEDED (${ELAPSED}s)"
echo "$DEPLOY_OUTPUT"

if [ -n "${GITEA_TOKEN:-}" ]; then
    report_success "ci/deploy-passive" "Deployed to passive (${ELAPSED}s)"
fi

json_result "deploy-passive" "\"host\":\"$TARGET_HOST\",\"elapsed_s\":$ELAPSED"
exit $EXIT_OK
