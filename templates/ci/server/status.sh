#!/bin/bash
# Server deployment status - single command health check
#
# Reports: deployed SHA, nginx health, docker services, config drift
#
# Usage:
#   status.sh           - Full status report
#   status.sh --brief   - One-line summary (for scripts)
#
# Exit codes:
#   0 = Everything healthy
#   1 = Issues detected (drift, unhealthy services, etc.)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

BRIEF=false
[[ "${1:-}" == "--brief" ]] && BRIEF=true

ISSUES=0

# --- Helpers ---

ok()   { echo "  [OK]   $1"; }
warn() { echo "  [WARN] $1"; ISSUES=$((ISSUES + 1)); }
fail() { echo "  [FAIL] $1"; ISSUES=$((ISSUES + 1)); }

# --- Gather state ---

HOSTNAME=$(hostname -s)
DEPLOYED_SHA=$(get_deployed_sha)
DEPLOYED_SHORT="${DEPLOYED_SHA:0:8}"

# Get latest from repo (without resetting working tree)
cd "$REPO_DIR" 2>/dev/null || { fail "Repo not found at $REPO_DIR"; exit 1; }
git fetch origin "$BRANCH" --quiet 2>/dev/null || true
LATEST_SHA=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "unknown")
LATEST_SHORT="${LATEST_SHA:0:8}"

BEHIND=0
if [[ -n "$DEPLOYED_SHA" && "$LATEST_SHA" != "unknown" ]]; then
    BEHIND=$(git rev-list --count "$DEPLOYED_SHA".."origin/$BRANCH" 2>/dev/null || echo "?")
fi

# --- Brief mode ---

if [[ "$BRIEF" == true ]]; then
    if [[ "$BEHIND" == "0" ]]; then
        echo "$HOSTNAME: deployed=$DEPLOYED_SHORT latest=$LATEST_SHORT (up to date)"
    else
        echo "$HOSTNAME: deployed=$DEPLOYED_SHORT latest=$LATEST_SHORT ($BEHIND behind)"
    fi
    exit 0
fi

# --- Full report ---

echo "=== Deployment Status: $HOSTNAME ==="
echo ""

# 1. SHA comparison
echo "Commits:"
if [[ -z "$DEPLOYED_SHA" ]]; then
    warn "No deployed SHA recorded"
elif [[ "$DEPLOYED_SHA" == "$LATEST_SHA" ]]; then
    ok "Up to date ($DEPLOYED_SHORT)"
else
    warn "Behind by $BEHIND commit(s): deployed=$DEPLOYED_SHORT latest=$LATEST_SHORT"
    git log --oneline "$DEPLOYED_SHA".."origin/$BRANCH" 2>/dev/null | while read -r line; do
        echo "         $line"
    done
fi
echo ""

# 2. Nginx
echo "Nginx:"
if systemctl is-active --quiet nginx 2>/dev/null; then
    ok "nginx is running"
else
    fail "nginx is NOT running"
fi
if nginx -t 2>/dev/null; then
    ok "config syntax valid"
else
    fail "config syntax errors"
fi
echo ""

# 3. Docker services
echo "Docker services:"
# Add your Docker Compose service directory names here
DOCKER_APPS=(myapp-web myapp-api myapp-worker)
for app in "${DOCKER_APPS[@]}"; do
    APP_DIR="/opt/$app"
    if [[ ! -f "$APP_DIR/docker-compose.yml" ]]; then
        continue
    fi
    # Get container status
    STATUS=$(cd "$APP_DIR" && docker compose ps --format '{{.Name}}: {{.Status}}' 2>/dev/null || echo "error")
    if [[ "$STATUS" == "error" || -z "$STATUS" ]]; then
        warn "$app: cannot check status"
    else
        ALL_HEALTHY=true
        while IFS= read -r line; do
            if echo "$line" | grep -qiE "unhealthy|exit|dead|restarting"; then
                fail "$line"
                ALL_HEALTHY=false
            fi
        done <<< "$STATUS"
        if [[ "$ALL_HEALTHY" == true ]]; then
            # Collapse to single line showing container count
            COUNT=$(echo "$STATUS" | wc -l | tr -d ' ')
            ok "$app: $COUNT container(s) healthy"
        fi
    fi
done

# act_runner (separate since it's Ring 0)
if [[ -f "/opt/act_runner/docker-compose.yml" ]]; then
    RUNNER_STATUS=$(cd /opt/act_runner && docker compose ps --format '{{.Name}}: {{.Status}}' 2>/dev/null || echo "error")
    if [[ "$RUNNER_STATUS" == "error" || -z "$RUNNER_STATUS" ]]; then
        warn "act_runner: cannot check status"
    else
        ALL_HEALTHY=true
        while IFS= read -r line; do
            if echo "$line" | grep -qiE "unhealthy|exit|dead|restarting"; then
                fail "$line"
                ALL_HEALTHY=false
            fi
        done <<< "$RUNNER_STATUS"
        if [[ "$ALL_HEALTHY" == true ]]; then
            ok "act_runner: running"
        fi
    fi
fi
echo ""

# 4. Config drift (deployed files vs repo)
echo "Config drift:"
if [[ -n "$DEPLOYED_SHA" ]]; then
    DRIFT_COUNT=0
    # Check nginx sites
    for site in /etc/nginx/sites-available/*; do
        [[ ! -f "$site" ]] && continue
        BASENAME=$(basename "$site")
        REPO_FILE="$REPO_DIR/etc/nginx/sites-available/$BASENAME"
        if [[ -f "$REPO_FILE" ]]; then
            if ! diff -q "$site" "$REPO_FILE" > /dev/null 2>&1; then
                warn "drift: etc/nginx/sites-available/$BASENAME"
                DRIFT_COUNT=$((DRIFT_COUNT + 1))
            fi
        fi
    done
    if [[ $DRIFT_COUNT -eq 0 ]]; then
        ok "No config drift detected (nginx checked)"
    fi
else
    warn "Cannot check drift without deployed SHA"
fi
echo ""

# 5. Optional: additional system services
# Uncomment and customize for your environment:
# echo "System services:"
# if systemctl is-active --quiet <service-name> 2>/dev/null; then
#     ok "<service-name> is running"
# else
#     warn "<service-name> is NOT running"
# fi
# echo ""

# --- Summary ---

echo "=== Summary: $HOSTNAME ==="
if [[ $ISSUES -eq 0 ]]; then
    echo "All checks passed."
    exit 0
else
    echo "$ISSUES issue(s) found."
    exit 1
fi
