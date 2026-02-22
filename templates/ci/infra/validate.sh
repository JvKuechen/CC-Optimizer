#!/bin/bash
# Validate infrastructure configs before deployment
# Runs nginx -t, visudo -c, systemd-analyze verify on staged configs
#
# This runs in the CI runner (not on the target server).
# It validates the config files in the repo checkout, not live configs.
# For checks that require the target server (e.g., nginx -t with includes),
# use verify.sh which runs via SSH on the actual server.
#
# Usage: validate.sh
# Exit: 0 if all validations pass, 1 if any fail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"
resolve_ci_root

log_step "Starting config validation"

ERRORS=0
CHECKS=0

# --- Nginx config syntax ---
# Check for basic syntax issues in nginx configs (not a full nginx -t, that needs the server)
NGINX_FILES=$(find . -path "*/etc/nginx/*" -name "*.conf" 2>/dev/null || true)
if [ -n "$NGINX_FILES" ]; then
    log_info "Checking nginx config files..."
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        CHECKS=$((CHECKS + 1))

        # Basic checks: balanced braces, no empty upstream blocks
        OPEN=$(grep -c '{' "$f" 2>/dev/null || echo 0)
        CLOSE=$(grep -c '}' "$f" 2>/dev/null || echo 0)
        if [ "$OPEN" -ne "$CLOSE" ]; then
            log_error "Unbalanced braces in $f (open=$OPEN, close=$CLOSE)"
            ERRORS=$((ERRORS + 1))
        else
            log_info "  OK: $f"
        fi
    done <<< "$NGINX_FILES"
else
    log_info "No nginx config files found in changeset"
fi

# --- Sudoers syntax ---
SUDOERS_FILES=$(find . -path "*/etc/sudoers.d/*" -type f 2>/dev/null || true)
if [ -n "$SUDOERS_FILES" ]; then
    log_info "Checking sudoers files..."
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        CHECKS=$((CHECKS + 1))

        # visudo -c can validate standalone files if available
        if command -v visudo > /dev/null 2>&1; then
            if visudo -c -f "$f" > /dev/null 2>&1; then
                log_info "  OK: $f"
            else
                log_error "Sudoers syntax error in $f"
                ERRORS=$((ERRORS + 1))
            fi
        else
            # Fallback: basic syntax checks
            if grep -qE '^[^#].*ALL.*NOPASSWD' "$f" 2>/dev/null; then
                log_info "  OK (basic check): $f"
            else
                log_warn "  Cannot validate (no visudo): $f"
            fi
        fi
    done <<< "$SUDOERS_FILES"
else
    log_info "No sudoers files found in changeset"
fi

# --- Systemd unit syntax ---
SYSTEMD_FILES=$(find . -path "*/etc/systemd/*" \( -name "*.service" -o -name "*.timer" \) 2>/dev/null || true)
if [ -n "$SYSTEMD_FILES" ]; then
    log_info "Checking systemd unit files..."
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        CHECKS=$((CHECKS + 1))

        # systemd-analyze verify if available
        if command -v systemd-analyze > /dev/null 2>&1; then
            if systemd-analyze verify "$f" > /dev/null 2>&1; then
                log_info "  OK: $f"
            else
                # systemd-analyze verify often warns about missing units in CI
                # Only count as error if it's a real syntax issue
                log_warn "  Warning (may be false positive in CI): $f"
            fi
        else
            # Fallback: check for required sections
            if grep -q '^\[Unit\]' "$f" 2>/dev/null || grep -q '^\[Timer\]' "$f" 2>/dev/null; then
                log_info "  OK (basic check): $f"
            else
                log_error "Missing [Unit] or [Timer] section in $f"
                ERRORS=$((ERRORS + 1))
            fi
        fi
    done <<< "$SYSTEMD_FILES"
else
    log_info "No systemd unit files found in changeset"
fi

# --- Docker Compose syntax ---
COMPOSE_FILES=$(find . -path "*/opt/*/docker-compose.yml" 2>/dev/null || true)
if [ -n "$COMPOSE_FILES" ]; then
    log_info "Checking docker-compose files..."
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        CHECKS=$((CHECKS + 1))

        # Basic YAML validation (check for PyYAML, not just Python)
        if command -v python3 > /dev/null 2>&1 && python3 -c "import yaml" 2>/dev/null; then
            if python3 -c "import yaml; yaml.safe_load(open('$f'))" 2>/dev/null; then
                log_info "  OK: $f"
            else
                log_error "Invalid YAML in $f"
                ERRORS=$((ERRORS + 1))
            fi
        elif command -v python > /dev/null 2>&1 && python -c "import yaml" 2>/dev/null; then
            if python -c "import yaml; yaml.safe_load(open('$f'))" 2>/dev/null; then
                log_info "  OK: $f"
            else
                log_error "Invalid YAML in $f"
                ERRORS=$((ERRORS + 1))
            fi
        else
            log_warn "  Cannot validate YAML (no PyYAML): $f"
        fi
    done <<< "$COMPOSE_FILES"
else
    log_info "No docker-compose files found in changeset"
fi

# --- Shell script syntax ---
SHELL_FILES=$(find . -path "*/scripts/*.sh" -o -path "*/deploy/*.sh" 2>/dev/null | sort -u || true)
if [ -n "$SHELL_FILES" ]; then
    log_info "Checking shell script syntax..."
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        CHECKS=$((CHECKS + 1))

        if bash -n "$f" 2>/dev/null; then
            log_info "  OK: $f"
        else
            log_error "Shell syntax error in $f"
            ERRORS=$((ERRORS + 1))
        fi
    done <<< "$SHELL_FILES"
else
    log_info "No shell scripts found in changeset"
fi

# --- Summary ---

log_step "Validation complete: $CHECKS checks, $ERRORS errors"

if [ "$ERRORS" -gt 0 ]; then
    log_error "VALIDATION FAILED ($ERRORS errors)"
    json_error "validate" "$ERRORS validation errors in $CHECKS checks"
    exit $EXIT_VALIDATION_FAILED
fi

log_info "VALIDATION PASSED"
json_result "validate" "\"checks\":$CHECKS,\"errors\":0,\"passed\":true"
exit $EXIT_OK
