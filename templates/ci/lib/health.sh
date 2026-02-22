#!/bin/bash
# Health check functions for CI/CD pipeline verification
# HTTP endpoint checks, Docker service status, log scanning
#
# Required env vars:
#   TARGET_HOST  - IP or hostname of server to check
#   SSH_KEY_PATH - Path to SSH private key (for remote checks)

# Source common and ssh if not already loaded
if [ -z "${EXIT_OK:-}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    source "$SCRIPT_DIR/common.sh"
    source "$SCRIPT_DIR/ssh.sh"
fi

# --- HTTP health checks ---

# Check an HTTP endpoint directly (from the runner, not via SSH)
# Usage: check_http "https://home.example.com" 200
check_http() {
    local url="$1"
    local expected_status="${2:-200}"
    local max_time="${3:-10}"

    log_info "HTTP check: $url (expect $expected_status)"

    local http_code
    local time_total
    local ec=0

    http_code=$(curl -sf --max-time "$max_time" --retry 2 --retry-delay 3 \
        -o /dev/null -w '%{http_code}' "$url" 2>/dev/null) || ec=$?

    if [ $ec -ne 0 ]; then
        log_error "HTTP check failed: $url (curl exit $ec)"
        json_error "health_http" "curl failed for $url (exit $ec)"
        return $EXIT_VERIFY_FAILED
    fi

    if [ "$http_code" -eq "$expected_status" ]; then
        log_info "HTTP check passed: $url -> $http_code"
        json_ok "health_http" "\"url\":\"$url\",\"status\":$http_code"
        return $EXIT_OK
    else
        log_error "HTTP check failed: $url -> $http_code (expected $expected_status)"
        json_error "health_http" "status $http_code (expected $expected_status) for $url"
        return $EXIT_VERIFY_FAILED
    fi
}

# Check an HTTP endpoint via the remote server's ci-dispatcher
# This tests the endpoint from the server's perspective (useful for localhost-bound services)
check_http_remote() {
    local url="$1"
    ssh_health "$url"
}

# --- Docker service checks ---

# Check Docker service status via remote ci-dispatcher
# Usage: check_docker_service "dashboard"
check_docker_service() {
    local service="$1"

    log_info "Docker check: $service on $TARGET_HOST"

    local output
    local ec=0
    output=$(ssh_status "$service") || ec=$?

    if [ $ec -ne 0 ]; then
        log_error "Docker check failed for $service"
        return $EXIT_VERIFY_FAILED
    fi

    # Parse JSON output to check if containers are running
    local ok
    ok=$(echo "$output" | jq -r '.ok // false' 2>/dev/null)
    if [ "$ok" = "true" ]; then
        log_info "Docker check passed: $service"
        echo "$output"
        return $EXIT_OK
    else
        log_error "Docker check failed: $service"
        echo "$output"
        return $EXIT_VERIFY_FAILED
    fi
}

# --- Service verification ---

# Verify a service using ci-dispatcher's verify command
# Runs the service-specific check script on the remote host
check_service_verify() {
    local service="$1"

    log_info "Service verify: $service on $TARGET_HOST"

    local output
    local ec=0
    output=$(ssh_verify "$service") || ec=$?

    if [ $ec -ne 0 ]; then
        log_error "Service verify failed: $service"
        echo "$output"
        return $EXIT_VERIFY_FAILED
    fi

    log_info "Service verify passed: $service"
    echo "$output"
    return $EXIT_OK
}

# --- Composite checks ---

# Run all health checks for a list of services
# Usage: check_services nginx myapp-web myapp-api
# Returns: 0 if all pass, EXIT_VERIFY_FAILED if any fail
check_services() {
    local services=("$@")
    local failed=()
    local passed=()

    for service in "${services[@]}"; do
        local ec=0
        check_docker_service "$service" > /dev/null || ec=$?
        if [ $ec -eq 0 ]; then
            passed+=("$service")
        else
            failed+=("$service")
        fi
    done

    local pass_count=${#passed[@]}
    local fail_count=${#failed[@]}
    local total=$(( pass_count + fail_count ))

    if [ $fail_count -eq 0 ]; then
        log_info "All $total services healthy"
        json_ok "health_all" "\"passed\":$pass_count,\"failed\":0"
        return $EXIT_OK
    else
        log_error "$fail_count/$total services failed: ${failed[*]}"
        json_error "health_all" "$fail_count services failed: ${failed[*]}"
        return $EXIT_VERIFY_FAILED
    fi
}

# Determine which services were affected by changed files
# Reads file list from stdin, outputs space-separated service names
detect_affected_services() {
    local services=()
    local seen=()

    while IFS= read -r file; do
        [ -z "$file" ] && continue
        local service=""

        case "$file" in
            etc/nginx/*)
                service="nginx"
                ;;
            opt/*/*)
                # Extract service name from opt/<service>/...
                service=$(echo "$file" | cut -d'/' -f2)
                ;;
            etc/systemd/*)
                # Systemd units might affect any service, check nginx at minimum
                service="nginx"
                ;;
        esac

        if [ -n "$service" ]; then
            # Deduplicate
            local already_seen=false
            for s in "${seen[@]+"${seen[@]}"}"; do
                if [ "$s" = "$service" ]; then
                    already_seen=true
                    break
                fi
            done
            if [ "$already_seen" = "false" ]; then
                services+=("$service")
                seen+=("$service")
            fi
        fi
    done

    echo "${services[*]}"
}
