#!/bin/bash
# Common functions for CI/CD pipeline scripts
# Sourced by all pipeline scripts (infra/, app/, knowledge/)
#
# Provides: logging, JSON output, error handling, exit codes
# Target: Ubuntu 24.04, bash 5.x

set -euo pipefail

# --- Exit codes ---
# Standardized across all scripts for deterministic handling
readonly EXIT_OK=0
readonly EXIT_VALIDATION_FAILED=1
readonly EXIT_DEPLOY_FAILED=2
readonly EXIT_VERIFY_FAILED=3
readonly EXIT_SSH_FAILED=4
readonly EXIT_CONFIG_ERROR=5

# --- Logging ---
# Human-readable stderr logging (for CI job output)
# JSON output goes to stdout (for agent/script parsing)

log_info() {
    local timestamp
    timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    printf '[%s] INFO: %s\n' "$timestamp" "$1" >&2
}

log_warn() {
    local timestamp
    timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    printf '[%s] WARN: %s\n' "$timestamp" "$1" >&2
}

log_error() {
    local timestamp
    timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    printf '[%s] ERROR: %s\n' "$timestamp" "$1" >&2
}

log_step() {
    local timestamp
    timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
    printf '[%s] STEP: %s\n' "$timestamp" "$1" >&2
}

# --- JSON output ---
# All structured output goes to stdout as single-line JSON
# Agents and CI scripts parse stdout; humans read stderr logs

json_ok() {
    local action="$1"
    local extra="${2:-}"
    if [ -n "$extra" ]; then
        printf '{"ok":true,"action":"%s",%s}\n' "$action" "$extra"
    else
        printf '{"ok":true,"action":"%s"}\n' "$action"
    fi
}

json_error() {
    local action="$1"
    local error="$2"
    printf '{"ok":false,"action":"%s","error":"%s"}\n' "$action" "$error"
}

json_result() {
    # Output arbitrary JSON object with ok=true and action field
    # Usage: json_result "validate" '"files":3,"passed":true'
    local action="$1"
    local fields="$2"
    printf '{"ok":true,"action":"%s",%s}\n' "$action" "$fields"
}

# --- Environment validation ---

require_env() {
    # Validate required environment variables are set
    # Usage: require_env TARGET_HOST SSH_KEY_PATH
    local missing=()
    for var in "$@"; do
        if [ -z "${!var:-}" ]; then
            missing+=("$var")
        fi
    done
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required environment variables: ${missing[*]}"
        json_error "config" "missing env vars: ${missing[*]}"
        exit $EXIT_CONFIG_ERROR
    fi
}

# --- Script location ---

# Resolve the ci-scripts root directory relative to any sourcing script
# Usage: source from infra/validate.sh -> CI_SCRIPTS_ROOT points to ci-scripts/
resolve_ci_root() {
    local caller_dir
    caller_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
    # Walk up to find lib/ directory (scripts are one level deep: infra/, app/, etc.)
    CI_SCRIPTS_ROOT="$(cd "$caller_dir/.." && pwd)"
    export CI_SCRIPTS_ROOT
}

# --- Scope / Ring detection ---

# Check if a file path is in Ring 0 (denied/manual-only)
# Uses DENY_PATHS from scope.conf or a hardcoded fallback
is_ring0() {
    local file="$1"
    # Add paths that should NEVER be auto-deployed (Ring 0 = manual only)
    local deny_paths=(
        "opt/gitea/"        # Misconfigured Gitea = no git access = no recovery
        "opt/act_runner/"   # CI runners
        "opt/secrets/"      # Secrets management
        "etc/ssh/"          # SSH config - lockout risk
        "etc/sudoers.d/"    # Privilege escalation risk
        "deploy/"           # Deploy system self-update is too risky for auto-deploy
    )
    for prefix in "${deny_paths[@]}"; do
        if [[ "$file" == "$prefix"* ]]; then
            return 0
        fi
    done
    return 1
}

# Check if a file path is in Ring 1 (auto-deployable)
# Matches infra-config scope.conf ALLOW_PATHS
is_ring1() {
    local file="$1"
    # Add paths that are safe for auto-deployment (Ring 1)
    local allow_paths=(
        "etc/nginx/" "etc/systemd/" "etc/fail2ban/"
        "etc/apt/" "etc/pam.d/" "etc/update-motd.d/"
        "opt/myapp-web/" "opt/myapp-api/" "opt/myapp-worker/" "opt/certbot/"
        "cockpit-plugin/"
    )
    for prefix in "${allow_paths[@]}"; do
        if [[ "$file" == "$prefix"* ]]; then
            return 0
        fi
    done
    return 1
}

# Check changed files and report ring membership
# FAIL-CLOSED: files not matching Ring 0 or Ring 1 are treated as Ring 0
# (unknown files block auto-deploy for safety)
# Reads file list from stdin, outputs JSON summary
classify_changes() {
    local ring0_files=()
    local ring1_files=()

    while IFS= read -r file; do
        [ -z "$file" ] && continue
        if is_ring0 "$file"; then
            ring0_files+=("$file")
        elif is_ring1 "$file"; then
            ring1_files+=("$file")
        else
            # FAIL CLOSED: unknown files treated as Ring 0 (block deploy)
            log_warn "Unknown path '$file' treated as Ring 0 (fail-closed)"
            ring0_files+=("$file")
        fi
    done

    local ring0_count=${#ring0_files[@]}
    local ring1_count=${#ring1_files[@]}
    local has_ring0="false"
    [ "$ring0_count" -gt 0 ] && has_ring0="true"

    # Build JSON arrays
    local ring0_json="[]"
    local ring1_json="[]"
    if [ "$ring0_count" -gt 0 ]; then
        ring0_json=$(printf '%s\n' "${ring0_files[@]}" | jq -R . | jq -sc .)
    fi
    if [ "$ring1_count" -gt 0 ]; then
        ring1_json=$(printf '%s\n' "${ring1_files[@]}" | jq -R . | jq -sc .)
    fi

    printf '{"has_ring0":%s,"ring0_count":%d,"ring1_count":%d,"ring0_files":%s,"ring1_files":%s}\n' \
        "$has_ring0" "$ring0_count" "$ring1_count" "$ring0_json" "$ring1_json"
}

# Detect affected services from a list of changed file paths (stdin)
# Extracts service names from opt/<service>/ and etc/<service>/ patterns
# Returns space-separated unique service names
detect_affected_services() {
    local services=()
    local seen=""
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        local svc=""
        # opt/<service>/... -> service name
        if [[ "$file" == opt/*/docker-compose.yml ]] || [[ "$file" == opt/*/* ]]; then
            svc=$(echo "$file" | cut -d/ -f2)
        # etc/nginx/... -> nginx
        elif [[ "$file" == etc/*/* ]]; then
            svc=$(echo "$file" | cut -d/ -f2)
        fi
        if [ -n "$svc" ] && [[ ! " $seen " == *" $svc "* ]]; then
            services+=("$svc")
            seen="$seen $svc"
        fi
    done
    echo "${services[*]}"
}

# --- Utility ---

# Run a command and capture exit code without triggering set -e
run_check() {
    local ec=0
    "$@" || ec=$?
    return $ec
}

# Elapsed time helper for step timing
timer_start() {
    _TIMER_START=$(date +%s)
}

timer_elapsed() {
    local now
    now=$(date +%s)
    echo $(( now - _TIMER_START ))
}
