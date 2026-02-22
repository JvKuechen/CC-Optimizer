#!/bin/bash
# Promote deployment to the active server
# Same as deploy-passive but targets the active/primary server
#
# This is triggered by a separate workflow_dispatch (manual gate).
# Never called automatically from the push pipeline.
#
# Usage: promote.sh
# Required env vars:
#   TARGET_HOST  - Active server IP (e.g., <active-server-ip>)
#   SSH_KEY_PATH - Path to ci-deploy SSH private key
#
# Exit: 0 on success, non-zero on failure

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
source "$SCRIPT_DIR/../lib/ssh.sh"
source "$SCRIPT_DIR/../lib/report.sh"
resolve_ci_root

detect_gitea_env

log_step "Promoting to active server ($TARGET_HOST)"
require_env TARGET_HOST SSH_KEY_PATH

if [ -n "${GITEA_TOKEN:-}" ]; then
    report_pending "ci/promote" "Promoting to active server"
fi

# --- Pre-check: plan ---

log_info "Running plan on active server..."
PLAN_OUTPUT=""
PLAN_EC=0
PLAN_OUTPUT=$(ssh_plan) || PLAN_EC=$?

if [ $PLAN_EC -ne 0 ]; then
    log_error "Plan failed on active server"
    echo "$PLAN_OUTPUT"
    if [ -n "${GITEA_TOKEN:-}" ]; then
        report_failure "ci/promote" "Plan failed on active"
    fi
    json_error "promote" "plan failed on $TARGET_HOST"
    exit $EXIT_DEPLOY_FAILED
fi

log_info "Plan output:"
echo "$PLAN_OUTPUT" >&2

# --- Deploy ---

timer_start

log_info "Deploying to active server..."
DEPLOY_OUTPUT=""
DEPLOY_EC=0
DEPLOY_OUTPUT=$(ssh_deploy "false") || DEPLOY_EC=$?
ELAPSED=$(timer_elapsed)

if [ $DEPLOY_EC -ne 0 ]; then
    log_error "Promote to active FAILED (${ELAPSED}s)"
    echo "$DEPLOY_OUTPUT"
    if [ -n "${GITEA_TOKEN:-}" ]; then
        report_failure "ci/promote" "Promote failed on active (${ELAPSED}s)"
    fi
    json_error "promote" "deploy failed on $TARGET_HOST (exit $DEPLOY_EC)"
    exit $EXIT_DEPLOY_FAILED
fi

log_info "Promote to active SUCCEEDED (${ELAPSED}s)"
echo "$DEPLOY_OUTPUT"

if [ -n "${GITEA_TOKEN:-}" ]; then
    report_success "ci/promote" "Promoted to active (${ELAPSED}s)"
fi

json_result "promote" "\"host\":\"$TARGET_HOST\",\"elapsed_s\":$ELAPSED"
exit $EXIT_OK
