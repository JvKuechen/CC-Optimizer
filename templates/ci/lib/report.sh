#!/bin/bash
# Gitea commit status reporting for CI/CD pipelines
# Posts build status back to Gitea so commits show green/red checks
#
# Required env vars:
#   GITEA_API_URL  - Base URL of Gitea API (e.g., https://gitea.example.com/api/v1)
#   GITEA_TOKEN    - API token with repo status write permission
#   REPO_OWNER     - Repository owner/org (e.g., ExampleOrg)
#   REPO_NAME      - Repository name (e.g., my-project)
#   COMMIT_SHA     - Full commit SHA to set status on

# Source common if not already loaded
if [ -z "${EXIT_OK:-}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    source "$SCRIPT_DIR/common.sh"
fi

# --- Status reporting ---

# Set commit status on Gitea
# Usage: report_status "success" "All checks passed" "ci/validate"
# States: pending, success, error, failure, warning
report_status() {
    local state="$1"
    local description="$2"
    local context="${3:-ci/pipeline}"
    local target_url="${4:-}"

    # Validate required env vars
    require_env GITEA_API_URL GITEA_TOKEN REPO_OWNER REPO_NAME COMMIT_SHA

    local url="${GITEA_API_URL}/repos/${REPO_OWNER}/${REPO_NAME}/statuses/${COMMIT_SHA}"

    local payload
    payload=$(printf '{"state":"%s","description":"%s","context":"%s"' \
        "$state" "$description" "$context")

    if [ -n "$target_url" ]; then
        payload="${payload},\"target_url\":\"${target_url}\""
    fi
    payload="${payload}}"

    log_info "Reporting status: $state ($context) for ${COMMIT_SHA:0:8}"

    local http_code
    local ec=0

    http_code=$(curl -sf --max-time 10 \
        -X POST \
        -H "Authorization: token ${GITEA_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        -o /dev/null -w '%{http_code}' \
        "$url" 2>/dev/null) || ec=$?

    if [ $ec -ne 0 ] || [ "$http_code" -lt 200 ] || [ "$http_code" -ge 300 ]; then
        log_error "Failed to report status (HTTP $http_code, curl exit $ec)"
        json_error "report_status" "HTTP $http_code posting to $url"
        return 1
    fi

    log_info "Status reported: $state"
    json_ok "report_status" "\"state\":\"$state\",\"context\":\"$context\",\"sha\":\"${COMMIT_SHA:0:8}\""
    return 0
}

# --- Convenience wrappers ---

report_pending() {
    local context="${1:-ci/pipeline}"
    local description="${2:-Build in progress}"
    report_status "pending" "$description" "$context"
}

report_success() {
    local context="${1:-ci/pipeline}"
    local description="${2:-All checks passed}"
    report_status "success" "$description" "$context"
}

report_failure() {
    local context="${1:-ci/pipeline}"
    local description="${2:-Build failed}"
    report_status "failure" "$description" "$context"
}

report_error() {
    local context="${1:-ci/pipeline}"
    local description="${2:-Build error}"
    report_status "error" "$description" "$context"
}

# --- Comment on commit ---
# Posts a comment on the commit (useful for plan output or failure details)

comment_commit() {
    local body="$1"

    require_env GITEA_API_URL GITEA_TOKEN REPO_OWNER REPO_NAME COMMIT_SHA

    local url="${GITEA_API_URL}/repos/${REPO_OWNER}/${REPO_NAME}/git/commits/${COMMIT_SHA}/comments"

    # Escape body for JSON (basic: newlines and quotes)
    local escaped_body
    escaped_body=$(printf '%s' "$body" | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/g' | tr -d '\n')
    escaped_body="${escaped_body%\\n}"

    local payload
    payload=$(printf '{"body":"%s"}' "$escaped_body")

    local http_code
    local ec=0

    http_code=$(curl -sf --max-time 10 \
        -X POST \
        -H "Authorization: token ${GITEA_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        -o /dev/null -w '%{http_code}' \
        "$url" 2>/dev/null) || ec=$?

    if [ $ec -ne 0 ] || [ "$http_code" -lt 200 ] || [ "$http_code" -ge 300 ]; then
        log_warn "Failed to post commit comment (HTTP $http_code)"
        return 1
    fi

    log_info "Comment posted on ${COMMIT_SHA:0:8}"
    return 0
}

# --- Auto-detect env from Gitea Actions ---
# Sets REPO_OWNER, REPO_NAME, COMMIT_SHA from Gitea Actions env vars if available

detect_gitea_env() {
    # Gitea Actions sets these automatically
    if [ -n "${GITHUB_REPOSITORY:-}" ] && [ -z "${REPO_OWNER:-}" ]; then
        REPO_OWNER="${GITHUB_REPOSITORY%%/*}"
        REPO_NAME="${GITHUB_REPOSITORY##*/}"
        export REPO_OWNER REPO_NAME
    fi

    if [ -n "${GITHUB_SHA:-}" ] && [ -z "${COMMIT_SHA:-}" ]; then
        COMMIT_SHA="$GITHUB_SHA"
        export COMMIT_SHA
    fi

    if [ -n "${GITHUB_SERVER_URL:-}" ] && [ -z "${GITEA_API_URL:-}" ]; then
        GITEA_API_URL="${GITHUB_SERVER_URL}/api/v1"
        export GITEA_API_URL
    fi

    # GITEA_TOKEN must be set explicitly (from secrets)
}
