# IRMDS MVP Hardening Plan

IRMDS is currently a working v0 developer demo, not a finished end-user
product. This plan defines the minimum hardening path required before calling
it an MVP.

## MVP Definition

An IRMDS MVP is ready when a new technical user can:

1. Clone the repo.
2. Install dependencies or run Docker.
3. Start a deterministic demo.
4. See useful system state in the dashboard.
5. Understand the API contract.
6. Add a minimal module using the documented lifecycle.
7. Run tests and know what a clean repo looks like.
8. Report bugs or contribute without private instructions.

The MVP does not include real physical actuation, production authentication,
fleet management, distributed event backends, or real deployment operations.

## Current Product Readiness

| Area | Current State | MVP Gap |
|:--|:--|:--|
| Kernel | Working sync/threaded module runtime | Contract docs and contract tests need to become stricter |
| Modules | Four domains exist | Demo-focused; not production data sources |
| API | FastAPI routes exist | Error contract and auth story need hardening |
| Dashboard | Functional v0 command center | Needs better operator workflow and failure-state tests |
| CLI | `version` and `demo` exist | Needs tests and read-only status/config commands |
| Docker | API + dashboard boot | Does not auto-start modules by default |
| Docs | README, verification, starter guide exist | Needs troubleshooting, contribution, API contract docs |
| GitHub | CI exists | Needs issue templates, PR template, release process |
| Safety | Dry-run commands only | Must keep this boundary explicit |

## Hardening Slices

### Slice 1 - Open-Source Hygiene

Goal: make the repo usable by someone who is not the original author.

- Add `CONTRIBUTING.md`.
- Add GitHub issue templates.
- Add GitHub pull request template.
- Add `SECURITY.md`.
- Add `docs/troubleshooting.md`.
- Add `docs/api_contract.md`.
- Harden the GitHub backlog script so it can create missing labels and avoid
  duplicate milestones/issues.
- Add CLI tests.
- Add dashboard API-helper tests.

Exit criteria:

- CI passes.
- Local `pytest tests -q` passes.
- `scripts/create_github_backlog.py --dry-run` works.
- A contributor can understand setup, verification, and contribution workflow.

### Slice 2 - Product Visibility

Goal: make the dashboard feel like a product, not only a technical proof.

- Add explicit demo boot state.
- Add module start/stop controls in dashboard.
- Add latest alert detail view.
- Add command lifecycle timeline.
- Add dashboard screenshots to README.
- Add one short recorded demo.

Exit criteria:

- Running `python scripts/demo.py` gives a visible, useful dashboard.
- A user can explain what the system is doing after 60 seconds.

### Slice 3 - Runtime Resilience

Goal: reduce ways the runtime can silently fail.

- Add module lifecycle contract tests.
- Add timeout and retry behavior around module start/stop routes.
- Add cheap versus deep health checks.
- Add structured API error responses.
- Add API tests for failure cases.
- Add optional API key auth, disabled by default for demo.

Exit criteria:

- Common bad inputs return predictable API errors.
- Module failures are visible in API and dashboard.
- Demo mode remains frictionless.

### Slice 4 - MVP Release

Goal: tag a coherent MVP release.

- Run fresh-clone verification.
- Run Docker verification.
- Update changelog.
- Tag release.
- Create GitHub release.
- Attach demo video link.

Exit criteria:

- `v0.3.0` or `v0.5.0` can be described as a public technical MVP.

## Deferred Beyond MVP

These are important but should not block the MVP:

- Real hardware actuation.
- Kubernetes deployment.
- Kafka/Redis event backend.
- Multi-node fleet management.
- JWT/RBAC.
- Model registry and MLOps.
- Real packet capture.
- Real market data feeds.
- Production visual model packaging.

## Non-Negotiable Gates

Before any release:

```bash
python -m compileall -q api core modules dashboard cli notifications tests scripts examples
ruff check .
mypy core api modules
pytest tests -q
git diff --check
python scripts/demo.py --smoke --no-dashboard
python -m cli.main demo --smoke --no-dashboard
docker compose config
```
