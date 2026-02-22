#!/bin/bash
# Verify deployment on target server
# Runs health checks against services affected by the changeset
#
# Usage: verify.sh
# Required env vars:
#   TARGET_HOST  - Server IP to verify (e.g., <passive-server-ip>)
#   SSH_KEY_PATH - Path to ci-deploy SSH private key
#
# Optional env vars:
#   VERIFY_SERVICES  - Space-separated list of services to check (auto-detected if not set)
#   VERIFY_URLS      - Space-separated list of URLs to health check
#
# Exit: 0 if all checks pass, EXIT_VERIFY_FAILED if any fail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
source "$SCRIPT_DIR/../lib/ssh.sh"
source "$SCRIPT_DIR/../lib/health.sh"
source "$SCRIPT_DIR/../lib/report.sh"
resolve_ci_root

detect_gitea_env

log_step "Verifying deployment on $TARGET_HOST"
require_env TARGET_HOST SSH_KEY_PATH

if [ -n "${GITEA_TOKEN:-}" ]; then
    report_pending "ci/verify" "Running health checks"
fi

timer_start
ERRORS=0
CHECKS=0

# --- Determine services to verify ---

if [ -n "${VERIFY_SERVICES:-}" ]; then
    SERVICES="$VERIFY_SERVICES"
    log_info "Using explicit service list: $SERVICES"
else
    # Auto-detect from git diff
    CURRENT_SHA="${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo '')}"
    PREVIOUS_SHA="${GITHUB_EVENT_BEFORE:-$(git rev-parse HEAD~1 2>/dev/null || echo '')}"

    if [ -n "$PREVIOUS_SHA" ] && [ "$PREVIOUS_SHA" != "0000000000000000000000000000000000000000" ]; then
        SERVICES=$(git diff --name-only "$PREVIOUS_SHA".."$CURRENT_SHA" 2>/dev/null | detect_affected_services)
    else
        SERVICES=$(git ls-files 2>/dev/null | detect_affected_services)
    fi
    log_info "Auto-detected services: ${SERVICES:-none}"
fi

# --- Check each service ---

if [ -n "$SERVICES" ]; then
    for service in $SERVICES; do
        CHECKS=$((CHECKS + 1))
        log_info "Checking service: $service"

        EC=0
        ssh_status "$service" > /dev/null 2>&1 || EC=$?

        if [ $EC -eq 0 ]; then
            log_info "  $service: healthy"
        else
            log_error "  $service: FAILED"
            ERRORS=$((ERRORS + 1))
        fi
    done
fi

# --- Check URLs ---

if [ -n "${VERIFY_URLS:-}" ]; then
    for url in $VERIFY_URLS; do
        CHECKS=$((CHECKS + 1))
        log_info "Health check: $url"

        EC=0
        check_http "$url" > /dev/null 2>&1 || EC=$?

        if [ $EC -eq 0 ]; then
            log_info "  $url: healthy"
        else
            log_error "  $url: FAILED"
            ERRORS=$((ERRORS + 1))
        fi
    done
fi

# --- Always check nginx (it's the reverse proxy for everything) ---

if [ -n "$SERVICES" ]; then
    CHECKS=$((CHECKS + 1))
    log_info "Checking nginx status..."

    EC=0
    ssh_status "nginx" > /dev/null 2>&1 || EC=$?

    if [ $EC -eq 0 ]; then
        log_info "  nginx: active"
    else
        log_error "  nginx: FAILED"
        ERRORS=$((ERRORS + 1))
    fi
fi

# --- Summary ---

ELAPSED=$(timer_elapsed)

if [ "$CHECKS" -eq 0 ]; then
    log_info "No services to verify (no affected services detected)"
    json_result "verify" "\"host\":\"$TARGET_HOST\",\"checks\":0,\"errors\":0,\"elapsed_s\":$ELAPSED"
    if [ -n "${GITEA_TOKEN:-}" ]; then
        report_success "ci/verify" "No services to verify"
    fi
    exit $EXIT_OK
fi

if [ "$ERRORS" -gt 0 ]; then
    log_error "VERIFICATION FAILED: $ERRORS/$CHECKS checks failed (${ELAPSED}s)"
    json_error "verify" "$ERRORS/$CHECKS checks failed on $TARGET_HOST"
    if [ -n "${GITEA_TOKEN:-}" ]; then
        report_failure "ci/verify" "$ERRORS/$CHECKS checks failed (${ELAPSED}s)"
    fi
    exit $EXIT_VERIFY_FAILED
fi

log_info "VERIFICATION PASSED: $CHECKS/$CHECKS checks OK (${ELAPSED}s)"
json_result "verify" "\"host\":\"$TARGET_HOST\",\"checks\":$CHECKS,\"errors\":0,\"elapsed_s\":$ELAPSED"
if [ -n "${GITEA_TOKEN:-}" ]; then
    report_success "ci/verify" "All $CHECKS checks passed (${ELAPSED}s)"
fi
exit $EXIT_OK
