#!/bin/bash
# SSH ForceCommand for ci-deploy user
# Only allows pre-approved deploy operations
# All outputs are JSON for deterministic parsing by CI and agents
#
# Installed to: /usr/local/sbin/ci-dispatcher.sh
# Referenced by: ci-deploy user's authorized_keys command= directive
#
# The SSH client sends a command string which becomes SSH_ORIGINAL_COMMAND.
# This script validates it against a strict allowlist and executes the
# corresponding operation. Anything not explicitly allowed is rejected.

set -euo pipefail

# --- JSON output helpers ---
json_ok()    { printf '{"ok":true,"action":"%s"%s}\n' "$1" "${2:+,$2}"; }
json_error() { printf '{"ok":false,"action":"%s","error":"%s"}\n' "$1" "$2"; }

# --- Allowed services ---
# Add your Docker Compose service directory names here
ALLOWED_SERVICES="nginx myapp-web myapp-api myapp-worker certbot"

is_allowed_service() {
    local service="$1"
    local s
    for s in $ALLOWED_SERVICES; do
        if [ "$s" = "$service" ]; then
            return 0
        fi
    done
    return 1
}

# --- Main dispatch ---

CMD="${SSH_ORIGINAL_COMMAND:-}"

if [ -z "$CMD" ]; then
    json_error "dispatch" "no command provided"
    exit 1
fi

case "$CMD" in

    # --- Deploy operations ---

    "deploy ring1")
        # deploy.sh logs go to stderr (visible in CI), only JSON on stdout
        sudo /opt/config-deploy/scripts/deploy.sh --auto >&2
        EC=$?
        if [ $EC -eq 0 ]; then
            json_ok "deploy"
        else
            json_error "deploy" "exit code $EC"
        fi
        exit $EC
        ;;

    "deploy ring1 --dry-run")
        sudo /opt/config-deploy/scripts/deploy.sh --auto --dry-run >&2
        EC=$?
        if [ $EC -eq 0 ]; then
            json_ok "deploy-dry-run"
        else
            json_error "deploy-dry-run" "exit code $EC"
        fi
        exit $EC
        ;;

    # --- Plan ---

    "plan")
        sudo /opt/config-deploy/scripts/plan.sh >&2
        EC=$?
        if [ $EC -eq 0 ]; then
            json_ok "plan"
        else
            json_error "plan" "exit code $EC"
        fi
        exit $EC
        ;;

    # --- Health checks ---

    "health "*)
        URL="${CMD#health }"
        # Allow only *.internal URLs (with optional path)
        if [[ "$URL" =~ ^https://[a-z0-9-]+\.example\.com(/[a-zA-Z0-9_./-]*)?$ ]]; then
            RESULT=$(curl -sf --max-time 10 --retry 2 --retry-delay 3 \
                -o /dev/null \
                -w '{"ok":true,"action":"health","url":"%{url}","status":%{http_code},"time_s":%{time_total}}' \
                "$URL" 2>/dev/null)
            EC=$?
            if [ $EC -eq 0 ]; then
                echo "$RESULT"
            else
                json_error "health" "curl failed for $URL (exit $EC)"
                exit 1
            fi
        else
            json_error "health" "URL not in allowed domain (must be https://*.internal)" >&2
            exit 1
        fi
        ;;

    # --- Service status ---

    "status "*)
        SERVICE="${CMD#status }"
        case "$SERVICE" in
            nginx)
                STATE=$(sudo systemctl is-active nginx 2>/dev/null || echo "unknown")
                json_ok "status" "\"service\":\"nginx\",\"state\":\"$STATE\""
                ;;
            *)
                if is_allowed_service "$SERVICE"; then
                    PS_JSON=$(cd "/opt/$SERVICE" && sudo docker compose ps --format json 2>/dev/null || echo "[]")
                    json_ok "status" "\"service\":\"$SERVICE\",\"containers\":$PS_JSON"
                else
                    json_error "status" "unknown service: $SERVICE" >&2
                    exit 1
                fi
                ;;
        esac
        ;;

    # --- Catch-all: reject unknown commands ---

    *)
        json_error "dispatch" "command not allowed: $CMD" >&2
        echo "Allowed commands:" >&2
        echo "  deploy ring1 [--dry-run]" >&2
        echo "  plan" >&2
        echo "  health <url>" >&2
        echo "  status <service>" >&2
        echo "Services: $ALLOWED_SERVICES" >&2
        exit 1
        ;;
esac
