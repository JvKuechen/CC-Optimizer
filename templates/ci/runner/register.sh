#!/bin/bash
# register.sh - Register a new Gitea Actions runner and configure .env file

set -e

# Check required environment variables
if [ -z "$GITEA_URL" ]; then
    echo "Error: GITEA_URL environment variable is required"
    echo "Example: export GITEA_URL=https://git.example.com"
    exit 1
fi

if [ -z "$GITEA_ADMIN_TOKEN" ]; then
    echo "Error: GITEA_ADMIN_TOKEN environment variable is required"
    echo "Generate a token from Gitea Settings -> Applications -> Manage Access Tokens"
    exit 1
fi

# Trim trailing slash from URL if present
GITEA_URL=${GITEA_URL%/}

echo "Requesting registration token from $GITEA_URL..."

# Call Gitea API to generate a registration token
RESPONSE=$(curl -s -X POST \
    -H "Authorization: token $GITEA_ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    "$GITEA_URL/api/v1/user/actions/runners/registration-token")

# Extract token from JSON response
TOKEN=$(echo "$RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "Error: Failed to retrieve registration token"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "Registration token obtained successfully"

# Check if .env file exists
if [ -f .env ]; then
    echo "Warning: .env file already exists. Backing up to .env.backup"
    cp .env .env.backup
fi

# Create .env file from template
if [ -f .env.example ]; then
    cp .env.example .env
else
    echo "Error: .env.example not found"
    exit 1
fi

# Update RUNNER_TOKEN in .env file
if command -v sed > /dev/null 2>&1; then
    # Use sed if available
    sed -i "s/RUNNER_TOKEN=.*/RUNNER_TOKEN=$TOKEN/" .env
else
    # Fallback to manual update
    echo "Warning: sed not available, please manually update RUNNER_TOKEN in .env"
    echo "RUNNER_TOKEN=$TOKEN"
    exit 0
fi

# Update GITEA_INSTANCE_URL in .env file
sed -i "s|GITEA_INSTANCE_URL=.*|GITEA_INSTANCE_URL=$GITEA_URL|" .env

echo ""
echo "Configuration complete!"
echo "The .env file has been created with the registration token."
echo ""
echo "Next steps:"
echo "1. Edit .env and set RUNNER_LABELS for this server"
echo "   - primary-server: RUNNER_LABELS=self-hosted,primary-server,active-capable"
echo "   - secondary-server: RUNNER_LABELS=self-hosted,secondary-server,passive-capable"
echo "2. Start the runner: docker compose up -d"
echo "3. Check logs: docker compose logs -f runner"
echo ""
