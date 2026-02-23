# CI/CD Strategy for Gitea-Backed Workspaces

Last updated: 2026-02-13
Status: Phase C complete, Phase D started

---

## Architecture Decision Record

**Decision:** Gitea Actions with DinD runners on host network, two-label architecture (container mode for infra, host mode for Docker builds), Ring 0/Ring 1 safety model, scripts-as-bricks pipeline templates, dedicated ci-deploy user with SSH access, Python CLI + MCP for Gitea API integration (planned).

**Rationale:** Synthesized from Claude Code docs analysis, AI architectural review, existing deployment patterns, and field-tested corrections from initial pipeline deployment. Optimized for AI-agent-driven development (Claude Code as primary developer) and self-hosted infrastructure requirements.

---

## Ring Model

Formalizes what infra-config already does with scope.conf:

**Ring 0 (Manual only, human gate required):**
- Gitea itself (opt/gitea/)
- act_runner infrastructure (compose, registration, config)
- secrets manager (secrets store)
- Core SSH/auth/sudoers configs
- CI/CD pipeline definitions (workflow YAML, ci-scripts repo)

**Ring 1 (Automated: push -> validate -> deploy passive -> verify -> promote):**
- Everything in scope.conf ALLOW_PATHS
- nginx configs, systemd units, Docker app stacks
- Application code deployments

**Pipeline behavior by ring:**
- Ring 0 changes: validate + plan output only. Ring 0 warning fires correctly. Promotion requires manual workflow_dispatch trigger.
- Ring 1 changes: full automated pipeline (validate -> deploy passive -> health check -> report status). Promotion to active via separate manual workflow_dispatch.

**Ring detection in pipeline:** Check changed files against scope.conf DENY_PATHS. If any match, skip deploy jobs and output plan only. No separate classify script needed -- scope.conf is the source of truth.

---

## Implementation Phases

### Phase A: Foundation -- COMPLETE

**A1. ci-scripts repo** -- COMPLETE
- Repo: https://gitea.example.com/ExampleOrg/ci-scripts
- Current version: v0.1.3, 11 commits
- Versioned with semver tags (v0.1.0, v0.1.1, v0.1.2, v0.1.3)
- Tags are immutable (no retagging, no force-push on tags)
- This repo generates/updates content, publishes tags
- ci-scripts is a protected repo on Gitea (admin-only push, no tag deletion)

```
ci-scripts/
  infra/
    validate.sh          # nginx -t, visudo -c, systemd-analyze verify
    plan.sh              # Compute diff summary, output what will change
    deploy-passive.sh    # SSH to passive server, run deploy.sh --auto
    verify.sh            # curl endpoints, docker health, log assertions
    promote.sh           # SSH to active server, trigger deploy
  app/
    lint.sh              # Language-specific linting
    test.sh              # Run test suite
    build.sh             # Build container image
    deploy-passive.sh    # Deploy to passive
    smoke.sh             # Smoke test endpoints
  knowledge/
    validate.sh          # Check export format
    reindex-trigger.sh   # Trigger RAG reindexing
  lib/
    common.sh            # Logging, error handling, JSON output helpers, detect_affected_services
    ssh.sh               # SSH wrapper (file-based key, known_hosts, structured output)
    health.sh            # HTTP health checks (--max-time, --retry), Docker health, log scanning
    report.sh            # Format results for Gitea commit status API
  runner/
    docker-compose.yml   # act_runner with sidecar DinD
    config.yaml          # Runner config (container.network: host)
    register.sh          # Runner registration script
    .env.example         # Runner config template
  server/
    setup-ci-deploy.sh   # Create ci-deploy user, install dispatcher
    ci-dispatcher.sh     # SSH ForceCommand allowlist
    status.sh            # Server health check (deployed SHA, services, drift)
```

Per-repo monitoring scripts (live in each workspace's deploy/scripts/):
```
  deploy/scripts/
    watch-run.sh         # Client-side: polls Gitea API until run completes
                         # Supports --sha <sha> for race-free post-push watching
                         # Designed for Claude Code run_in_background pattern
```

**A2. gitea-mcp Python CLI** -- PLANNED (not yet started)
- Core operations: repo create, pr create/list/merge, pipeline status, comment, secrets set
- Token stored in Windows Credential Manager (or env var fallback)
- Structured JSON output for agent parsing
- Works standalone (scripts, CI jobs) and via MCP wrapper

```
gitea-mcp/
  gitea_mcp/
    __init__.py
    cli.py               # Click-based CLI
    client.py            # Gitea API client (requests)
    models.py            # Response types
  mcp_server.py          # MCP wrapper (thin, calls CLI functions)
  pyproject.toml
```

**A3. MCP configuration template** -- PLANNED (depends on A2)
- .mcp.json template for workspaces that need Gitea integration
- Exposes gitea-mcp as native Claude Code tools

```json
{
  "mcpServers": {
    "gitea": {
      "command": "python",
      "args": ["-m", "gitea_mcp.mcp_server"],
      "env": {
        "GITEA_URL": "https://gitea.example.com",
        "GITEA_TOKEN_SOURCE": "credential_manager"
      }
    }
  }
}
```

**A4. Workflow templates** -- COMPLETE (infra working in infra-config, app working in example-app)
- Gitea Actions YAML for infra and app repos
- Infra: Call ci-scripts at pinned tag, pass repo-specific env vars
- App: Docker build + push with host-mode execution (no ci-scripts dependency)
- NOT reusable workflows (Gitea support is unreliable), just copy-and-customize YAML
- SSH keys written to files with printf (not echo, avoids trailing newlines)
- Internal CA cert: infra uses `INTERNAL_CA_PEM` secret, app uses compose volume mounts
- Concurrency group prevents overlapping deploys (infra only)

```yaml
# .gitea/workflows/infra.yml (ACTUAL working config from infra-config)
name: Infrastructure Deploy
on:
  push:
    branches: [main]

concurrency:
  group: infra-deploy
  cancel-in-progress: false

env:
  CI_SCRIPTS_REF: v0.1.3

jobs:
  validate:
    runs-on: [self-hosted, docker://node:20-bookworm, secondary-server]
    steps:
      - name: Install tools and internal CA
        run: |
          apt-get update && apt-get install -y jq curl ca-certificates openssh-client
          printf '%s\n' "$INTERNAL_CA_PEM" > /usr/local/share/ca-certificates/internal-ca.crt
          update-ca-certificates
        env:
          INTERNAL_CA_PEM: ${{ secrets.INTERNAL_CA_PEM }}
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2
      - uses: actions/checkout@v4
        with:
          repository: ExampleOrg/ci-scripts
          ref: ${{ env.CI_SCRIPTS_REF }}
          path: ci-scripts
      - name: Validate configs
        run: ci-scripts/infra/validate.sh
      - name: Generate plan
        run: ci-scripts/infra/plan.sh

  deploy-passive:
    needs: validate
    runs-on: [self-hosted, docker://node:20-bookworm, secondary-server, passive-capable]
    steps:
      - name: Install tools and internal CA
        run: |
          apt-get update && apt-get install -y jq curl ca-certificates openssh-client
          printf '%s\n' "$INTERNAL_CA_PEM" > /usr/local/share/ca-certificates/internal-ca.crt
          update-ca-certificates
        env:
          INTERNAL_CA_PEM: ${{ secrets.INTERNAL_CA_PEM }}
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2
      - uses: actions/checkout@v4
        with:
          repository: ExampleOrg/ci-scripts
          ref: ${{ env.CI_SCRIPTS_REF }}
          path: ci-scripts
      - name: Setup SSH key
        run: |
          mkdir -p /root/.ssh
          printf '%s\n' "$CI_DEPLOY_SSH_KEY" > /root/.ssh/ci_deploy
          chmod 600 /root/.ssh/ci_deploy
          printf '%s\n' "$CI_DEPLOY_KNOWN_HOSTS" > /root/.ssh/known_hosts
        env:
          CI_DEPLOY_SSH_KEY: ${{ secrets.CI_DEPLOY_SSH_KEY }}
          CI_DEPLOY_KNOWN_HOSTS: ${{ secrets.CI_DEPLOY_KNOWN_HOSTS }}
      - name: Deploy to passive
        run: ci-scripts/infra/deploy-passive.sh
        env:
          TARGET_HOST: <passive-server-ip>
          SSH_KEY_PATH: /root/.ssh/ci_deploy
          GITEA_TOKEN: ${{ secrets.GITEA_TOKEN }}
      - name: Verify deployment
        run: ci-scripts/infra/verify.sh
        env:
          TARGET_HOST: <passive-server-ip>
          GITEA_TOKEN: ${{ secrets.GITEA_TOKEN }}
      - name: Cleanup SSH key
        if: always()
        run: rm -f /root/.ssh/ci_deploy /root/.ssh/known_hosts
```

```yaml
# .gitea/workflows/promote.yml (separate manual trigger)
name: Promote to Active
on:
  workflow_dispatch:
    inputs:
      commit_sha:
        description: 'Commit SHA to promote (must have passed deploy-passive)'
        required: true
      ci_scripts_ref:
        description: 'ci-scripts version'
        required: true
        default: 'v0.1.3'

jobs:
  promote:
    runs-on: [self-hosted, docker://node:20-bookworm, primary-server, active-capable]
    steps:
      - name: Install tools and internal CA
        run: |
          apt-get update && apt-get install -y jq curl ca-certificates openssh-client
          printf '%s\n' "$INTERNAL_CA_PEM" > /usr/local/share/ca-certificates/internal-ca.crt
          update-ca-certificates
        env:
          INTERNAL_CA_PEM: ${{ secrets.INTERNAL_CA_PEM }}
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.commit_sha }}
      - uses: actions/checkout@v4
        with:
          repository: ExampleOrg/ci-scripts
          ref: ${{ inputs.ci_scripts_ref }}
          path: ci-scripts
      - name: Setup SSH key
        run: |
          mkdir -p /root/.ssh
          printf '%s\n' "$CI_DEPLOY_SSH_KEY" > /root/.ssh/ci_deploy
          chmod 600 /root/.ssh/ci_deploy
          printf '%s\n' "$CI_DEPLOY_KNOWN_HOSTS" > /root/.ssh/known_hosts
        env:
          CI_DEPLOY_SSH_KEY: ${{ secrets.CI_DEPLOY_SSH_KEY }}
          CI_DEPLOY_KNOWN_HOSTS: ${{ secrets.CI_DEPLOY_KNOWN_HOSTS }}
      - name: Promote to active
        run: ci-scripts/infra/promote.sh
        env:
          TARGET_HOST: <active-server-ip>
          SSH_KEY_PATH: /root/.ssh/ci_deploy
          GITEA_TOKEN: ${{ secrets.GITEA_TOKEN }}
      - name: Verify active
        run: ci-scripts/infra/verify.sh
        env:
          TARGET_HOST: <active-server-ip>
          GITEA_TOKEN: ${{ secrets.GITEA_TOKEN }}
      - name: Cleanup SSH key
        if: always()
        run: rm -f /root/.ssh/ci_deploy /root/.ssh/known_hosts
```

```yaml
# .gitea/workflows/build.yml (ACTUAL working config from example-app, 2026-02-13)
# For repos that build Docker images and push to Gitea registry.
# Uses host-mode execution (linux_amd64 label).
name: Build & Push Image

on:
  push:
    branches: [main]

jobs:
  build:
    name: Build Docker Image
    runs-on: linux_amd64
    env:
      DOCKER_HOST: unix:///var/run/dind/docker.sock
    steps:
      - name: Install Docker CLI
        run: |
          wget -qO- https://download.docker.com/linux/static/stable/x86_64/docker-27.5.1.tgz \
            | tar xz --strip-components=1 -C /usr/local/bin docker/docker
          docker version

      - name: Checkout
        run: |
          git clone https://gitea.example.com/${{ github.repository }}.git workspace
          cd workspace
          git checkout ${{ github.sha }}

      - name: Set image tags
        id: tags
        run: |
          SHORT_SHA=$(echo "${{ github.sha }}" | cut -c1-7)
          echo "short_sha=$SHORT_SHA" >> "$GITHUB_OUTPUT"
          REPO_LC=$(echo "${{ github.repository }}" | tr '[:upper:]' '[:lower:]')
          echo "image=gitea.example.com/$REPO_LC" >> "$GITHUB_OUTPUT"

      - name: Login to Gitea registry
        run: |
          echo "${{ secrets.REGISTRY_TOKEN }}" | \
            docker login gitea.example.com -u "${{ secrets.REGISTRY_USER }}" --password-stdin

      - name: Build and push
        run: |
          IMAGE="${{ steps.tags.outputs.image }}"
          SHA_TAG="${{ steps.tags.outputs.short_sha }}"
          cd workspace
          docker build -t "$IMAGE:$SHA_TAG" -t "$IMAGE:latest" .
          docker push "$IMAGE:$SHA_TAG"
          docker push "$IMAGE:latest"
          echo "Pushed $IMAGE:$SHA_TAG and $IMAGE:latest"

      - name: Cleanup
        if: always()
        run: docker logout gitea.example.com 2>/dev/null || true
```

---

### Phase B: Runner + Deploy Channel -- COMPLETE (B1), PLANNED (B2)

**B1. act_runner setup on both servers** -- COMPLETE (updated 2026-02-13 with field-tested corrections)
- DinD on host network, runner on host network, shared DinD socket volume
- Runner connects to DinD via Unix socket (not TCP): `DOCKER_HOST: unix:///var/run/dind/docker.sock`
- DinD listens on both Unix socket and TCP (socket preferred, TCP as fallback)
- `CONFIG_FILE: /data/config.yaml` MUST be set or config is silently ignored
- Two-label architecture: `self-hosted` (container mode) + `linux_amd64` (host mode)
- Pinned image versions (no :latest)
- Labeled by server: `primary-server` on <active-ip>, `secondary-server` on <passive-ip>
- Both registered against gitea.example.com (DNS failover handles which Gitea instance)
- DinD mounts internal CA cert for Gitea registry trust (docker login/push)
- act_runner version: 0.2.11 confirmed working

**CRITICAL: act_runner 0.2.11 container.* bug:** ALL `container.*` config settings are silently ignored (`container.network`, `container.options`, `container.docker_host`, `container.privileged`). Job containers always get isolated per-job bridge networks regardless of config. This was discovered during example-app pipeline debugging -- see `findings/cicd-runner-corrections.md` for full analysis. The infra pipeline was never affected because SSH works from bridge networks (outbound). App pipelines that need Docker daemon access MUST use host-mode labels.

```yaml
# runner/docker-compose.yml (ACTUAL working config, field-tested 2026-02-13)
# Pre-deploy: echo '{}' > daemon.json (must exist before compose up)
services:
  dind:
    image: docker:27.5-dind
    privileged: true
    network_mode: host
    environment:
      DOCKER_TLS_CERTDIR: ""
    volumes:
      - dind-data:/var/lib/docker
      - dind-socket:/var/run/dind
      - ./daemon.json:/etc/docker/daemon.json:ro
      - /usr/local/share/ca-certificates/custom-ca.crt:/etc/docker/certs.d/gitea.example.com/ca.crt:ro
    command:
      - dockerd
      - -H
      - unix:///var/run/dind/docker.sock
      - -H
      - tcp://127.0.0.1:2375
    restart: unless-stopped

  runner:
    image: gitea/act_runner:0.2.11
    network_mode: host
    environment:
      GITEA_INSTANCE_URL: ${GITEA_INSTANCE_URL}
      GITEA_RUNNER_REGISTRATION_TOKEN: ${RUNNER_TOKEN}
      DOCKER_HOST: unix:///var/run/dind/docker.sock
      CONFIG_FILE: /data/config.yaml
      GITEA_RUNNER_LABELS: ${RUNNER_LABELS}
    volumes:
      - runner-data:/data
      - dind-socket:/var/run/dind
      - /usr/local/share/ca-certificates:/usr/local/share/ca-certificates:ro
      - /etc/ssl/certs:/etc/ssl/certs:ro
    restart: unless-stopped

volumes:
  dind-data:
  dind-socket:
  runner-data:
```

Per-server .env:
```bash
# primary-server
RUNNER_TOKEN=<from gitea>
RUNNER_LABELS=self-hosted:docker://node:20-bookworm,primary-server:docker://node:20-bookworm,active-capable:docker://node:20-bookworm,linux_amd64:host

# secondary-server
RUNNER_TOKEN=<from gitea>
RUNNER_LABELS=self-hosted:docker://node:20-bookworm,secondary-server:docker://node:20-bookworm,passive-capable:docker://node:20-bookworm,linux_amd64:host
```

Note: Labels use format `label:execution-mode` where mode is `docker://<image>` (container) or `host` (runner native). Labels in .env are only read during first registration. After that, labels come from config.yaml `runner.labels` section. To change labels: edit config.yaml, delete `/data/.runner`, restart runner.

Note: config.yaml MUST include `runner.labels` with both modes:
```yaml
runner:
  labels:
    - "self-hosted:docker://node:20-bookworm"
    - "linux_amd64:host"

container:
  # WARNING: ALL container.* settings are IGNORED by act_runner 0.2.11.
  # Kept for documentation only.
  network: ""
```

**B2. ci-deploy user on both servers** -- PLANNED (not yet verified)

The ci-deploy user exists and SSH key-based access works (the pipeline SSHes as ci-deploy successfully). However, the ForceCommand dispatcher (`ci-dispatcher.sh`) is NOT verified as deployed. Currently deploy-passive.sh and verify.sh SSH directly and run commands.

The planned ForceCommand setup:
- Dedicated unprivileged user, no login shell
- SSH key restricted via authorized_keys command= directive
- ForceCommand points to ci-dispatcher.sh
- All outputs are JSON for deterministic parsing

```bash
# /usr/local/sbin/ci-dispatcher.sh (PLANNED, not yet deployed)
#!/bin/bash
# SSH ForceCommand for ci-deploy user
# Only allows pre-approved deploy operations
# All outputs are JSON for deterministic parsing by CI and agents
set -euo pipefail

json_ok()    { printf '{"ok":true,"action":"%s"%s}\n' "$1" "${2:+,$2}"; }
json_error() { printf '{"ok":false,"action":"%s","error":"%s"}\n' "$1" "$2"; }

CMD="$SSH_ORIGINAL_COMMAND"

case "$CMD" in
    "deploy ring1")
        /opt/config-deploy/scripts/deploy.sh --auto 2>&1
        EC=$?
        if [ $EC -eq 0 ]; then json_ok "deploy"; else json_error "deploy" "exit code $EC"; fi
        exit $EC
        ;;
    "deploy ring1 --dry-run")
        /opt/config-deploy/scripts/deploy.sh --auto --dry-run 2>&1
        EC=$?
        if [ $EC -eq 0 ]; then json_ok "deploy-dry-run"; else json_error "deploy-dry-run" "exit code $EC"; fi
        exit $EC
        ;;
    "plan")
        /opt/config-deploy/scripts/plan.sh 2>&1
        EC=$?
        if [ $EC -eq 0 ]; then json_ok "plan"; else json_error "plan" "exit code $EC"; fi
        exit $EC
        ;;
    "verify "*)
        SERVICE="${CMD#verify }"
        case "$SERVICE" in
            nginx|dashboard|webapp-one|webapp-two|example-app|webapp-three|webapp-four|certbot)
                /opt/config-deploy/scripts/check.sh "$SERVICE" 2>&1
                EC=$?
                if [ $EC -eq 0 ]; then
                    json_ok "verify" "\"service\":\"$SERVICE\""
                else
                    json_error "verify" "service $SERVICE check failed"
                fi
                exit $EC
                ;;
            *)
                json_error "verify" "unknown service: $SERVICE" >&2
                exit 1
                ;;
        esac
        ;;
    "health "*)
        URL="${CMD#health }"
        if [[ "$URL" =~ ^https://[a-z0-9-]+\.example\.com(/.*)?$ ]]; then
            RESULT=$(curl -sf --max-time 10 --retry 2 -o /dev/null \
                -w '{"ok":true,"action":"health","url":"%{url}","status":%{http_code},"time_s":%{time_total}}' \
                "$URL" 2>/dev/null)
            if [ $? -eq 0 ]; then
                echo "$RESULT"
            else
                json_error "health" "curl failed for $URL"
                exit 1
            fi
        else
            json_error "health" "URL not in allowed domain" >&2
            exit 1
        fi
        ;;
    "status "*)
        SERVICE="${CMD#status }"
        case "$SERVICE" in
            nginx)
                STATE=$(systemctl is-active nginx 2>/dev/null || echo "unknown")
                json_ok "status" "\"service\":\"nginx\",\"state\":\"$STATE\""
                ;;
            dashboard|webapp-one|webapp-two|example-app|webapp-three|webapp-four|certbot)
                PS_JSON=$(cd "/opt/$SERVICE" && docker compose ps --format json 2>/dev/null || echo "[]")
                json_ok "status" "\"service\":\"$SERVICE\",\"containers\":$PS_JSON"
                ;;
            *)
                json_error "status" "unknown service: $SERVICE" >&2
                exit 1
                ;;
        esac
        ;;
    *)
        json_error "dispatch" "command not allowed: $CMD" >&2
        echo "Allowed: deploy ring1, plan, verify <service>, health <url>, status <service>" >&2
        exit 1
        ;;
esac
```

authorized_keys entry (planned):
```
command="/usr/local/sbin/ci-dispatcher.sh",no-port-forwarding,no-agent-forwarding,no-pty,no-user-rc,no-X11-forwarding ssh-ed25519 AAAA... ci-deploy@pipeline
```

**B3. Secrets management** -- COMPLETE (per-repo Gitea secrets)
- Infra pipeline secrets: CI_DEPLOY_SSH_KEY, CI_DEPLOY_KNOWN_HOSTS, GITEA_TOKEN, INTERNAL_CA_PEM
- App pipeline secrets: REGISTRY_USER, REGISTRY_TOKEN
- Using Gitea Actions secrets (per-repo scope, considering org-level for shared secrets)
- SSH key written to file with printf (not echo), cleaned up in `if: always()` step
- Infra: Internal CA cert installed via update-ca-certificates in "Install tools" step
- App: Internal CA cert handled by DinD compose volume mount (no secret needed in workflow)
- Migrate to secrets manager AppRole auth later if needed

---

### Phase C: First Pipeline (infra-config) -- COMPLETE

**C1. Pipeline working** -- COMPLETE
- `.gitea/workflows/infra.yml` -- triggered on push to main
- Ring 0 changes: validate + plan only, Ring 0 warning fires correctly
- Ring 1 changes: full automated pipeline (validate -> deploy-passive -> verify)
- 12 pipeline runs to get it fully working (see Lessons Learned below)
- All four stages working: Validate, Plan, Deploy-passive, Verify
- Ring 1 auto-deploys to passive server (<secondary-ip>) on push to main

**C2. Collapse the 20-command workflow** -- COMPLETE

Before (interactive Claude Code session):
```
git status -> git diff -> git add -> git commit -> git push
ssh <passive-ip> plan -> ssh <passive-ip> deploy -> ssh <passive-ip> check logs -> ssh <passive-ip> check service -> curl test
ssh <active-ip> plan -> ssh <active-ip> deploy -> ssh <active-ip> check logs -> ssh <active-ip> check service -> curl test
```

After (interactive Claude Code session):
```
git add -> git commit -> git push
# Launch watcher as background task:
bash deploy/scripts/watch-run.sh --sha $(git rev-parse HEAD)
# Continue working, read output when notified
# Confirm with: ssh <admin-user>@<passive-server-ip> "sudo /opt/config-deploy/scripts/status.sh"
```

After (with promote):
```
# workflow_dispatch in Gitea UI
# Or: gitea-mcp pipeline promote <run-id> (when CLI is built)
```

**C3. Update infra-config workspace** -- COMPLETE
- CLAUDE.md: pipeline-first deploy workflow, new service added to services table
- deploy-to-server.md skill: pipeline-first, manual SSH as fallback
- check-deploy.md skill: /check-deploy with watch mode (background task)
- nginx-configs.md rule: correct internal CA wildcard cert paths
- settings.json: GIT_SSL_NO_VERIFY removed from allow list
- .gitignore: fixed blanket .claude/ ignore, skills/rules now tracked

**C4. Server monitoring scripts** -- COMPLETE
- `deploy/scripts/status.sh` -- single-command health report (deployed SHA, nginx, docker services, config drift, sssd). Supports `--brief` for one-line summary. Deployed to both servers.
- `deploy/scripts/watch-run.sh` -- polls Gitea API until pipeline run completes. Supports `--sha <sha>` to match by commit (no race condition). Designed for Claude Code `run_in_background: true` pattern.

---

### Phase D: Expand to Other Repos -- IN PROGRESS

**D1. App repo template (example-app as pilot)** -- COMPLETE (2026-02-13)
- example-app (search.example.com) is the first app pipeline
- Uses host-mode execution (`linux_amd64` label) for Docker build + push
- Builds Docker image, pushes to Gitea container registry (gitea.example.com)
- Required discovering the two-label architecture (see findings/cicd-runner-corrections.md)
- Workflow: `.gitea/workflows/build.yml` -- wget, manual git clone, docker build/push
- Required secrets: `REGISTRY_USER`, `REGISTRY_TOKEN` (per-repo or org-level)
- Image pushed as both `<sha-tag>` and `latest`

**D2. Helpdesk bot (second app pipeline)**
- Next candidate after example-app template is proven
- Same workflow template, different Dockerfile/build context

**D3. Knowledge repo template (knowledge-base as pilot)**
- validate export format -> trigger reindex
- Minimal pipeline, mostly just status reporting

**D4. New repo bootstrapping**
- `gitea-mcp repo init --type infra|app|knowledge`
- Creates repo, sets branch protections, copies workflow template, configures secrets
- One command to go from "new project" to "fully CI/CD enabled"

**D5. Enhancements (future)**
- yamllint for workflow YAML validation
- CI integrity job (validate ci-scripts tag is in approved allowlist)
- Headless Claude in pipeline for AI-powered PR review

---

## Lessons Learned (Phase C debugging)

Twelve bugs discovered and fixed across Phase C (infra-config, 12 runs) and Phase D (example-app, ~10 runs):

1. **TLS cert verification** -- Job containers (node:20-bookworm) lack the internal CA cert for gitea.example.com. All HTTPS operations (git clone, curl, Gitea API) fail with certificate errors. Fix: Store CA cert as INTERNAL_CA_PEM Gitea secret, install it via update-ca-certificates in an "Install tools" step before checkout.

2. **PyYAML false positives** -- node:20-bookworm has python3 but not PyYAML. validate.sh checked for `python3` binary presence and tried `import yaml`, causing false failures. Fix: Check `import yaml` success, not just python3 binary existence.

3. **Missing detect_affected_services** -- Function called in pipeline scripts but never defined anywhere. Fix: Added detect_affected_services to lib/common.sh.

4. **Multi-line jq output** -- `jq -s` produces pretty-printed JSON, which breaks `tail -1` parsing in downstream scripts. Fix: Use `jq -sc` (compact output) for all JSON piped through tail.

5. **SSH tilde expansion** -- `~` is not expanded in YAML env vars, so `SSH_KEY_PATH: ~/.ssh/ci_deploy` resolves to a literal `~/.ssh/ci_deploy` path. Fix: Use absolute paths `/root/.ssh/ci_deploy` everywhere.

6. **DinD network isolation** -- Docker bridge networks cannot reach the host LAN. Job containers on a bridge network cannot SSH to <passive-server-ip> for deployment. Fix: DinD runs with `network_mode: host` and binds dockerd to `tcp://127.0.0.1:2375`.

7. **UFW blocks Docker bridge SSH** -- Even with DinD on host networking, job containers on Docker bridge subnets are blocked by UFW rules. Original "fix" was `container.network: host` in config.yaml, but this setting is **silently ignored** by act_runner 0.2.11. The infra pipeline worked anyway because SSH is outbound from bridge networks and isn't blocked by UFW (UFW blocks inbound only by default). The actual fix for app pipelines that need Docker daemon access: use host-mode labels (`linux_amd64:host`) so the job runs inside the runner container itself, which has the DinD socket volume mounted.

8. **`CONFIG_FILE` env var required** -- The act_runner startup script (`/opt/act/run.sh`) only loads config.yaml if `CONFIG_FILE` is set in the environment. Without it, all config (log level, labels, container settings) is silently ignored. Fix: Add `CONFIG_FILE: /data/config.yaml` to runner environment in docker-compose.yml.

9. **`GITEA_RUNNER_LABELS` env var ignored after registration** -- Once registered, labels are stored in `.runner` file and on the Gitea server. The env var is only read during initial registration. Even then, config.yaml `runner.labels` takes precedence (runner emits a warning). Fix: Define labels in config.yaml under `runner.labels`. To change: edit config.yaml, delete `/data/.runner`, restart runner.

10. **DinD CA trust for internal registries** -- `docker login` and `docker push` go through the DinD daemon, which has its own TLS trust store. Internal CA certs must be mounted at `/etc/docker/certs.d/<registry>/ca.crt` inside the DinD container. Fix: Volume mount in docker-compose.yml.

11. **`actions/checkout@v4` requires Node.js** -- The checkout action is JavaScript and requires Node.js. The act_runner container (Alpine 3.20) has git and wget but no Node.js or curl. Host-mode workflows must use manual `git clone`. Container-mode workflows (node:20-bookworm) have Node.js and `actions/checkout@v4` works fine.

12. **DinD `daemon.json` mount must be a file** -- If `daemon.json` doesn't exist when compose starts, Docker creates a directory at the mount point, causing DinD to fail. Fix: Pre-create with `echo '{}' > daemon.json` before first `docker compose up`.

---

## Claude Code Integration Points

### For Interactive Development (Windows dev machine)

| Tool | Purpose | How | Status |
|------|---------|-----|--------|
| GITEA_TOKEN | Gitea API access | Windows user env var, admin scopes | Working |
| watch-run.sh | Background pipeline monitor | `run_in_background`, polls until complete | Working |
| status.sh | Server health check | Single SSH command, full or brief report | Working |
| /check-deploy skill | Combined pipeline + server check | Skill in infra-config workspace | Working |
| gitea-mcp CLI | Gitea API operations | Bash commands, pre-allowed in settings.json | PLANNED |
| MCP server | Native tool access | .mcp.json in workspace, no permission prompts | PLANNED |
| Hooks | Auto-format, lint | Existing PostToolUse hooks continue working | Working |

### For CI/CD Pipeline (server runners)

| Tool | Purpose | How | Status |
|------|---------|-----|--------|
| ci-scripts | Deterministic deploy steps | Shell scripts, pinned version | Working (v0.1.3) |
| ci-dispatcher.sh | Least-privilege SSH | ForceCommand allowlist, JSON output | PLANNED |
| claude -p (future) | AI-powered PR review | Headless Claude in pipeline job | PLANNED |
| claude-code-action (future) | PR/issue automation | If Gitea Actions compatibility works | PLANNED |

---

## Security Model

**CI has LESS power than interactive sessions:**

| Capability | Interactive (<admin-user>) | CI (ci-deploy) |
|------------|---------------------|-----------------|
| Ring 0 deploy | Manual SSH | Blocked (pipeline skips deploy) |
| Ring 1 deploy | Full access | deploy.sh --auto only |
| Docker exec | Allowed (read) | status only (JSON) |
| Arbitrary commands | Yes (with permissions) | No (allowlist planned) |
| Gitea admin | Via <admin-user> | API token (scoped) |
| Promote to active | Manual decision | workflow_dispatch (gate) |
| SSH key handling | Agent-forwarded | File-based, per-job, cleaned up |

**Job container networking:** Two modes. Container-mode jobs (`self-hosted` label, node:20-bookworm) run on per-job bridge networks -- they CAN reach the LAN for SSH deploys (outbound from bridge is allowed) but CANNOT reach the DinD daemon. Host-mode jobs (`linux_amd64` label) run inside the runner container on the host network -- they have full LAN access and Docker daemon access via shared socket. The original plan to use `container.network: host` for all jobs was invalidated by the act_runner 0.2.11 container.* config bug.

**Branch protection on Gitea (setup during Phase B):**
- main: no force push, no delete
- ci-scripts: admin-only push, no tag deletion/force-update
- Require CI pass before merge (after pipeline is stable)

**Runner isolation:**
- Sidecar DinD on host network, shared socket volume between DinD and runner
- Container-mode jobs (bridge network): SSH deploys work, no Docker access
- Host-mode jobs (runner container): full Docker access via socket, full LAN access
- Jobs that need host deploy use SSH to ci-deploy user
- Runner labels ensure deploy jobs run on the correct server

---

## Two-Label Architecture

The runner has two execution modes, selected by workflow `runs-on`:

| Label | Mode | Use Case | Environment | Docker Access |
|-------|------|----------|-------------|---------------|
| `self-hosted` | `docker://node:20-bookworm` | Infra deploys (SSH, curl, git) | node:20 container, bridge network | No |
| `linux_amd64` | `host` | Docker builds (build, push, login) | Alpine runner container, host network | Yes (socket) |

**Why two modes?** act_runner 0.2.11 ignores all `container.*` config settings. Job containers always get isolated bridge networks where the DinD daemon is unreachable at `127.0.0.1:2375` (that points to the container's own loopback). Host-mode jobs run inside the runner container itself, which has the DinD socket volume mounted.

**Infra pipelines** (`runs-on: self-hosted`): Get node:20-bookworm containers with Node.js, curl, apt. `actions/checkout@v4` works. SSH to servers works (outbound from bridge). Cannot call Docker daemon.

**App pipelines** (`runs-on: linux_amd64`): Run in the Alpine runner container. Have wget and git but no Node.js or curl. Must use manual `git clone` and `wget`. Can call Docker daemon via shared socket.

## Runner Targeting

| Job | Runs on | Why |
|-----|---------|-----|
| validate, plan | `self-hosted, secondary-server` | Infra: container mode, passive runner |
| deploy-passive | `self-hosted, secondary-server, passive-capable` | Deploys to passive server |
| verify-passive | `self-hosted, secondary-server, passive-capable` | Tests passive endpoints |
| promote (active) | `self-hosted, primary-server, active-capable` | Deploys to active server |
| verify-active | `self-hosted, primary-server, active-capable` | Tests active endpoints |
| docker build/push | `linux_amd64` | App: host mode, any runner with Docker access |

If active server is broken, push a fix -> passive runner picks up validate + deploy-passive. Fix verified on passive. Then active runner picks up promote when it comes back (or manually trigger from passive with SSH to active).

---

## Repo Map

```
Gitea (gitea.example.com)
  ExampleOrg/
    ci-scripts          # Shared pipeline scripts (protected, semver tagged, v0.1.3)
    infra-config        # Infrastructure config (Phase C, pipeline working)
    example-app      # App repo (Phase D1, first app pipeline working)
    notify-bot        # App repo (Phase D2, planned)
    knowledge-base               # Knowledge repo (Phase D3, planned)
    ...                 # All Work/ repos eventually

CC-Optimizer (this workspace, GitHub-synced)
  templates/ci/         # Source for ci-scripts content before publishing
  playbook/cicd-strategy.md  # This document
  findings/cicd-runner-corrections.md  # Field-tested corrections (2026-02-13)
```

---

## Resolved Decisions

1. **DinD TLS:** Resolved -- plaintext. DinD listens on both Unix socket (`/var/run/dind/docker.sock` via named volume) and TCP (`127.0.0.1:2375`). Socket preferred. Safe because DinD is already privileged.
2. **Runner isolation:** DinD on host network. Container-mode jobs get per-job bridge networks (can SSH out, can't reach Docker). Host-mode jobs run in runner container (full Docker + LAN access). `container.network: host` does NOT work in act_runner 0.2.11.
3. **Runner labels:** Labeled by server (primary-server, secondary-server) with role (active-capable, passive-capable). Deploy jobs target specific runners.
4. **Promote gate:** Manual workflow_dispatch (separate workflow). No auto-promote initially.
5. **ci-scripts versioning:** Semver tags, immutable. CC-Optimizer generates, admin pushes tags. Current: v0.1.3.
6. **Deploy user:** ci-deploy user exists, SSH key auth works. ForceCommand dispatcher planned but not yet deployed.
7. **SSH key handling:** Written to file per-job with printf (not echo), cleaned up in `if: always()` step. Never env var.
8. **SSH key paths:** Use /root/.ssh/ absolute paths (~ not expanded in YAML env vars).
9. **Dispatcher output:** JSON for all responses (ok/error envelope) -- planned.
10. **CI scripts location:** Dedicated Gitea repo. CC-Optimizer is source, ci-scripts is consumption point.
11. **Start point:** CC-Optimizer first (Phase A), infra-config is first customer (Phase C).
12. **act_runner version:** 0.2.11 confirmed working. Has critical bug: ALL `container.*` config settings are silently ignored. Job containers always get per-job bridge networks.
13. **Job container image:** node:20-bookworm for container-mode jobs (has git, bash, jq, Node.js prerequisites). Alpine runner native for host-mode jobs (has git, wget only).
14. **CA cert handling:** Two mechanisms. Infra pipelines (container mode): `INTERNAL_CA_PEM` Gitea secret installed via `update-ca-certificates`. App pipelines (host mode): Runner container mounts host CA certs directly, DinD gets per-registry CA cert via compose volume.
15. **ci-scripts compact jq:** Use `jq -sc` (compact) for all JSON piped through tail. Pretty-printed output breaks tail -1 parsing.
16. **Two-label architecture:** `self-hosted:docker://node:20-bookworm` for infra (SSH deploys), `linux_amd64:host` for app (Docker build/push). Workflows select mode via `runs-on`.
17. **CONFIG_FILE env var:** Must be set to `/data/config.yaml` in runner environment or config.yaml is silently ignored by startup script.
18. **DinD socket sharing:** Named `dind-socket` volume shared between DinD and runner. DinD listens on `unix:///var/run/dind/docker.sock` (custom path, not default `/var/run/docker.sock`).
19. **Host-mode checkout:** `actions/checkout@v4` fails in host mode (no Node.js). Use manual `git clone` + `git checkout`. Runner container has host CA certs mounted so HTTPS works.
20. **DinD internal CA trust:** Mount CA cert at `/etc/docker/certs.d/<registry>/ca.crt` inside DinD container. Docker Engine checks this per-request, no daemon restart needed.

## Phase B Sequencing (safe bring-up order) -- COMPLETE

1. Push ci-scripts repo to Gitea, tag v0.1.0 -- DONE
2. Set up ONE server first (secondary-server / passive) -- DONE
3. Create workflow, test through 12 iterations -- DONE
4. Runner registered and working on secondary-server -- DONE
5. primary-server runner setup -- PLANNED (for promote workflow)
6. ForceCommand dispatcher deployment -- PLANNED

## Gitea API Token Setup

**User-wide token (Windows dev machine):**
- Stored as `GITEA_TOKEN` Windows user environment variable
- Admin scopes (all Claude Code instances share it for full Gitea admin)
- Access in bash: `GITEA_TOKEN=$(powershell -Command "[Environment]::GetEnvironmentVariable('GITEA_TOKEN', 'User')")`
- Set via: Settings > System > Environment Variables > User variables, or:
  `[Environment]::SetEnvironmentVariable("GITEA_TOKEN", "token-here", "User")`

**CI pipeline token (Gitea Actions secrets):**
- Stored as per-repo Gitea secret `CI_GITEA_STATUS_TOKEN`
- Minimum scopes: `repo`, `write:issue`, `write:misc`, `read:user`
- Do NOT grant `admin` scope unless specifically needed for repo creation/bootstrapping
- Store the token name and scope in secrets manager metadata for auditability

## Open Questions (resolve during implementation)

1. **Monitoring:** How to alert when a pipeline fails? Gitea webhook to Teams? Email? The webapp-one bot itself?
2. **Gitea Actions secrets scope:** Currently per-repo. Org-level would reduce duplication but is TBD.

---

## Dependencies

- Phase A: COMPLETE. ci-scripts repo created, workflow templates working (infra + app). gitea-mcp CLI still planned.
- Phase B: B1 COMPLETE (runner working on secondary-server, updated with two-label architecture). B2 PLANNED (ForceCommand dispatcher).
- Phase C: COMPLETE. Config-repo infra pipeline working end-to-end.
- Phase D: IN PROGRESS. D1 COMPLETE (example-app app pipeline working). D2-D5 planned.

---

## Success Criteria

The 20-command workflow becomes 4:
1. `git commit` (with whatever files are staged)
2. `git push`
3. `watch-run.sh --sha $(git rev-parse HEAD)` (background task, auto-reports when done)
4. `status.sh --brief` on target server (confirm deployment landed)

Promotion to active is a conscious decision, not part of the push flow.
