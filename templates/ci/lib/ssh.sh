#!/bin/bash
# SSH wrapper for CI/CD pipeline scripts
# Provides file-based key handling, strict host verification, structured output
#
# Required env vars:
#   TARGET_HOST  - IP or hostname to connect to
#   SSH_KEY_PATH - Path to private key file (written by workflow, cleaned up after)
#
# Optional env vars:
#   SSH_USER     - Remote user (default: ci-deploy)
#   SSH_PORT     - Remote port (default: 22)
#   SSH_TIMEOUT  - Connection timeout in seconds (default: 10)

# Source common if not already loaded
if [ -z "${EXIT_OK:-}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    source "$SCRIPT_DIR/common.sh"
fi

# --- SSH configuration ---

SSH_USER="${SSH_USER:-ci-deploy}"
SSH_PORT="${SSH_PORT:-22}"
SSH_TIMEOUT="${SSH_TIMEOUT:-10}"

# Build SSH options array (reused by all ssh calls)
_ssh_opts() {
    local opts=(
        -i "$SSH_KEY_PATH"
        -o "IdentitiesOnly=yes"
        -o "StrictHostKeyChecking=yes"
        -o "UserKnownHostsFile=${SSH_KNOWN_HOSTS:-$HOME/.ssh/known_hosts}"
        -o "ConnectTimeout=$SSH_TIMEOUT"
        -o "ServerAliveInterval=5"
        -o "ServerAliveCountMax=3"
        -o "BatchMode=yes"
        -o "LogLevel=ERROR"
        -p "$SSH_PORT"
    )
    printf '%s\n' "${opts[@]}"
}

# --- Core SSH execution ---

# Execute a command on the remote host via ci-deploy user
# The command is passed as SSH_ORIGINAL_COMMAND to ci-dispatcher.sh
# Returns: exit code from remote command
# Stdout: remote command output (JSON from ci-dispatcher)
# Stderr: connection errors and logging
ssh_exec() {
    local cmd="$1"

    # Validate required env vars
    if [ -z "${TARGET_HOST:-}" ]; then
        log_error "TARGET_HOST not set"
        json_error "ssh" "TARGET_HOST not set"
        return $EXIT_SSH_FAILED
    fi
    if [ -z "${SSH_KEY_PATH:-}" ]; then
        log_error "SSH_KEY_PATH not set"
        json_error "ssh" "SSH_KEY_PATH not set"
        return $EXIT_SSH_FAILED
    fi
    if [ ! -f "$SSH_KEY_PATH" ]; then
        log_error "SSH key file not found: $SSH_KEY_PATH"
        json_error "ssh" "SSH key file not found"
        return $EXIT_SSH_FAILED
    fi

    log_info "SSH to ${SSH_USER}@${TARGET_HOST}: ${cmd}"

    local output
    local ec=0

    # Read ssh opts into array
    local opts=()
    while IFS= read -r opt; do
        opts+=("$opt")
    done < <(_ssh_opts)

    output=$(ssh "${opts[@]}" "${SSH_USER}@${TARGET_HOST}" "$cmd" 2>/dev/null) || ec=$?

    if [ $ec -ne 0 ] && [ -z "$output" ]; then
        # SSH connection failed (no output from remote)
        log_error "SSH connection failed (exit code $ec)"
        json_error "ssh" "connection failed to ${TARGET_HOST} (exit $ec)"
        return $EXIT_SSH_FAILED
    fi

    # Pass through remote output (should be JSON from ci-dispatcher)
    if [ -n "$output" ]; then
        echo "$output"
    fi

    return $ec
}

# --- Convenience wrappers ---
# These call ci-dispatcher commands via ssh_exec

# Run deploy on remote (Ring 1 only)
ssh_deploy() {
    local dry_run="${1:-false}"
    if [ "$dry_run" = "true" ]; then
        ssh_exec "deploy ring1 --dry-run"
    else
        ssh_exec "deploy ring1"
    fi
}

# Get deployment plan from remote
ssh_plan() {
    ssh_exec "plan"
}

# Verify a service on remote
ssh_verify() {
    local service="$1"
    ssh_exec "verify $service"
}

# Health check a URL from remote
ssh_health() {
    local url="$1"
    ssh_exec "health $url"
}

# Get service status from remote
ssh_status() {
    local service="$1"
    ssh_exec "status $service"
}

# --- SSH key setup helper ---
# Used in workflow steps to write key from secret to file

setup_ssh_key() {
    local key_content="$1"
    local key_path="${2:-$HOME/.ssh/ci_deploy}"
    local known_hosts_content="${3:-}"

    mkdir -p "$(dirname "$key_path")"
    printf '%s\n' "$key_content" > "$key_path"
    chmod 600 "$key_path"

    if [ -n "$known_hosts_content" ]; then
        printf '%s\n' "$known_hosts_content" > "$(dirname "$key_path")/known_hosts"
        export SSH_KNOWN_HOSTS="$(dirname "$key_path")/known_hosts"
    fi

    export SSH_KEY_PATH="$key_path"
    log_info "SSH key written to $key_path"
}

# Clean up SSH key (call in if:always() step)
cleanup_ssh_key() {
    local key_path="${1:-$HOME/.ssh/ci_deploy}"
    if [ -f "$key_path" ]; then
        rm -f "$key_path"
        log_info "SSH key cleaned up"
    fi
    local known_hosts="$(dirname "$key_path")/known_hosts"
    if [ -f "$known_hosts" ]; then
        rm -f "$known_hosts"
    fi
}
