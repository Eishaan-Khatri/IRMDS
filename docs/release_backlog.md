# IRMDS Release Backlog

This file mirrors the GitHub milestones and issues that should exist for the
next public releases. It is kept in-repo because authenticated GitHub issue
creation is not always available from local agent sessions.

To create this backlog on GitHub:

```bash
python scripts/create_github_backlog.py --dry-run
GITHUB_TOKEN=<token-with-issues-write> python scripts/create_github_backlog.py
```

On Windows PowerShell:

```powershell
$env:GITHUB_TOKEN = "<token-with-issues-write>"
python scripts/create_github_backlog.py
```

## Milestone: v0.2.0 - Reproducible Demo Polish

Goal: make the current runtime easy to verify, demo, and understand.

Issues:

1. Verify GitHub Actions and document the checked commit.
2. Add `docs/verification.md` with local, fresh-clone, demo, and Docker checks.
3. Split README setup into quick local demo, installed CLI demo, Docker demo,
   full visual YOLO setup, and dry-run command safety boundary.
4. Improve dashboard v0 visibility: module status, latest alerts/events,
   current metrics, and command ledger.
5. Add a demo-mode indicator to the dashboard and demo script.
6. Strengthen module starter docs with lifecycle, event, and metric contracts.
7. Add a minimal example module and discovery-style test.

Done when:

- CI is green on the release commit.
- `python scripts/demo.py --smoke --no-dashboard` passes.
- `irmds demo --smoke --no-dashboard` passes after editable install.
- Docker Compose serves API docs and dashboard.
- README can guide a new user without private explanation.

## Milestone: v0.3.0 - Developer Experience Hardening

Goal: make IRMDS credible as an open-source developer project.

Issues:

1. Add `CONTRIBUTING.md`.
2. Add issue templates and PR template.
3. Add API error response documentation.
4. Add contract tests for module lifecycle behavior.
5. Add CLI tests for `irmds demo`, `irmds status`, and future read-only commands.
6. Add dashboard API connection failure states.
7. Add troubleshooting docs for Windows, Docker, and optional visual inference.

Done when:

- A contributor can add a module using only the docs.
- A failing setup has a clear troubleshooting path.
- API behavior is documented enough for external callers.

## Milestone: v0.5.0 - Public Alpha Candidate

Goal: make the architecture durable enough for serious public attention.

Issues:

1. Add `docs/architecture.md` with kernel, event, module, and command diagrams.
2. Add schema versioning for events and commands.
3. Attach session IDs consistently to alerts/events/commands where applicable.
4. Add `/metrics/prometheus` or a documented metrics exporter plan.
5. Add config profiles for `demo`, `dev`, `test`, `docker`, and `full-visual`.
6. Add screenshots and a short demo video link to README.
7. Add release checklist automation or script.

Done when:

- The repo communicates architecture and execution quality without a live pitch.
- New modules can be built against stable contracts.
- Demo artifacts exist for users who do not run the project locally.

## Milestone: v1.0-alpha - Stable Monitoring Runtime

Goal: establish a stable monitoring runtime API and extension surface.

Issues:

1. Freeze v1 contracts for `BaseModule`, `Event`, `Command`, `Metrics`, and `Health`.
2. Add a module starter kit or scaffold command.
3. Add API authentication baseline for non-demo deployments.
4. Add notification adapters: console, Slack, Discord, email.
5. Add persistent event/alert/session migration strategy.
6. Add stronger observability: structured logs, Prometheus metrics, health modes.
7. Add security policy and safety policy docs.

Done when:

- v1 APIs are stable enough for external modules.
- Monitoring is production-shaped, even if real actuation remains out of scope.
- The public story is accurate, defensible, and useful.
