#!/bin/bash
# Setup script for ci-deploy user on Ubuntu 24.04 servers
# Creates a locked-down user for CI/CD pipeline deployments
#
# Usage: sudo ./setup-ci-deploy.sh
#
# This script is idempotent - safe to run multiple times.
# Run on each server that needs to accept CI deploy commands.
#
# What it does:
#   1. Creates ci-deploy user (no login shell, no home dir login)
#   2. Generates ed25519 SSH keypair (if not exists)
#   3. Installs ci-dispatcher.sh to /usr/local/sbin/
#   4. Sets up authorized_keys with command= restriction
#   5. Outputs the public key (add to Gitea Actions secrets)

set -euo pipefail

# --- Configuration ---
CI_USER="ci-deploy"
CI_HOME="/home/$CI_USER"
DISPATCHER_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ci-dispatcher.sh"
DISPATCHER_DEST="/usr/local/sbin/ci-dispatcher.sh"
KEY_NAME="ci-deploy-pipeline"

# --- Preflight checks ---

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root (use sudo)" >&2
    exit 1
fi

if [ ! -f "$DISPATCHER_SRC" ]; then
    echo "ERROR: ci-dispatcher.sh not found at $DISPATCHER_SRC" >&2
    echo "This script expects ci-dispatcher.sh in the same directory." >&2
    exit 1
fi

# --- Create user ---

if id "$CI_USER" > /dev/null 2>&1; then
    echo "User $CI_USER already exists"
else
    echo "Creating user $CI_USER..."
    useradd \
        --system \
        --create-home \
        --home-dir "$CI_HOME" \
        --shell /bin/bash \
        --comment "CI/CD deploy user (ForceCommand restricted)" \
        "$CI_USER"
    echo "User $CI_USER created"
fi

# Lock the password (no password login ever)
passwd -l "$CI_USER" > /dev/null 2>&1 || true

# --- Install ci-dispatcher.sh ---

echo "Installing ci-dispatcher.sh to $DISPATCHER_DEST..."
cp "$DISPATCHER_SRC" "$DISPATCHER_DEST"
chmod 755 "$DISPATCHER_DEST"
chown root:root "$DISPATCHER_DEST"
echo "Dispatcher installed"

# --- Generate SSH keypair ---

SSH_DIR="$CI_HOME/.ssh"
mkdir -p "$SSH_DIR"
chown "$CI_USER:$CI_USER" "$SSH_DIR"
chmod 700 "$SSH_DIR"

KEY_PATH="$SSH_DIR/$KEY_NAME"
if [ -f "$KEY_PATH" ]; then
    echo "SSH keypair already exists at $KEY_PATH"
else
    echo "Generating ed25519 SSH keypair..."
    ssh-keygen -t ed25519 -f "$KEY_PATH" -N "" -C "$KEY_NAME@$(hostname)" > /dev/null 2>&1
    chown "$CI_USER:$CI_USER" "$KEY_PATH" "$KEY_PATH.pub"
    chmod 600 "$KEY_PATH"
    chmod 644 "$KEY_PATH.pub"
    echo "Keypair generated"
fi

# --- Setup authorized_keys ---

AUTH_KEYS="$SSH_DIR/authorized_keys"
PUB_KEY=$(cat "$KEY_PATH.pub")

# Build the restricted authorized_keys entry
RESTRICTED_ENTRY="command=\"$DISPATCHER_DEST\",no-port-forwarding,no-agent-forwarding,no-pty,no-user-rc,no-X11-forwarding $PUB_KEY"

# Check if entry already exists (by key fingerprint)
KEY_FP=$(ssh-keygen -lf "$KEY_PATH.pub" | awk '{print $2}')

if [ -f "$AUTH_KEYS" ] && grep -q "$KEY_FP" "$AUTH_KEYS" 2>/dev/null; then
    echo "authorized_keys entry already exists"
else
    echo "$RESTRICTED_ENTRY" >> "$AUTH_KEYS"
    echo "authorized_keys entry added"
fi

chown "$CI_USER:$CI_USER" "$AUTH_KEYS"
chmod 600 "$AUTH_KEYS"

# --- Ensure ci-deploy can run deploy.sh ---
# deploy.sh requires sudo for service reloads and file ownership changes
# Add a sudoers entry that only allows deploy.sh

SUDOERS_FILE="/etc/sudoers.d/ci-deploy"
if [ -f "$SUDOERS_FILE" ]; then
    echo "Sudoers entry already exists"
else
    echo "Creating sudoers entry..."
    cat > "$SUDOERS_FILE" << 'SUDOERS'
# CI/CD deploy user - restricted to deployment scripts only
ci-deploy ALL=(root) NOPASSWD: /opt/config-deploy/scripts/deploy.sh --auto
ci-deploy ALL=(root) NOPASSWD: /opt/config-deploy/scripts/deploy.sh --auto --dry-run
ci-deploy ALL=(root) NOPASSWD: /opt/config-deploy/scripts/plan.sh
ci-deploy ALL=(root) NOPASSWD: /usr/bin/systemctl is-active *
ci-deploy ALL=(root) NOPASSWD: /usr/bin/docker compose ps *
ci-deploy ALL=(root) NOPASSWD: /usr/bin/docker compose up -d *
ci-deploy ALL=(root) NOPASSWD: /usr/bin/docker compose restart *
SUDOERS
    chmod 0440 "$SUDOERS_FILE"
    chown root:root "$SUDOERS_FILE"
    # Validate sudoers syntax
    if visudo -c -f "$SUDOERS_FILE" > /dev/null 2>&1; then
        echo "Sudoers entry created and validated"
    else
        echo "ERROR: Sudoers syntax validation failed!" >&2
        rm -f "$SUDOERS_FILE"
        exit 1
    fi
fi

# --- Git safe directory ---
# ci-deploy needs to read the config-deploy repo owned by another user
if [ -d /opt/config-deploy/repo ]; then
    sudo -u "$CI_USER" git config --global --add safe.directory /opt/config-deploy/repo
    echo "Git safe.directory added for /opt/config-deploy/repo"
fi

# --- Output ---

echo ""
echo "========================================"
echo "ci-deploy user setup complete"
echo "========================================"
echo ""
echo "Server: $(hostname) ($(hostname -I | awk '{print $1}'))"
echo ""
echo "PUBLIC KEY (add to Gitea Actions secrets as CI_DEPLOY_SSH_KEY):"
echo "--- Copy the PRIVATE key below ---"
echo ""
cat "$KEY_PATH"
echo ""
echo "--- End private key ---"
echo ""
echo "KNOWN HOSTS entry (add to Gitea Actions secrets as CI_DEPLOY_KNOWN_HOSTS):"
echo "--- Copy the line below ---"
HOSTIP=$(hostname -I | awk '{print $1}')
ssh-keyscan -t ed25519 "$HOSTIP" 2>/dev/null || echo "# Run: ssh-keyscan -t ed25519 $HOSTIP"
echo "--- End known hosts ---"
echo ""
echo "Test with: ssh -i <private_key> -o StrictHostKeyChecking=no $CI_USER@$HOSTIP plan"
echo ""
