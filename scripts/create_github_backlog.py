"""
Create the IRMDS release milestones and issues on GitHub.

Usage:
    python scripts/create_github_backlog.py --dry-run
    set GITHUB_TOKEN=ghp_...
    python scripts/create_github_backlog.py

The script uses only the Python standard library so it can run before optional
developer tools such as `gh` are installed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_REPO = "Eishaan-Khatri/IRMDS"
API_ROOT = "https://api.github.com"


@dataclass(frozen=True)
class IssueSpec:
    title: str
    body: str
    labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class MilestoneSpec:
    title: str
    description: str
    issues: tuple[IssueSpec, ...]


MILESTONES: tuple[MilestoneSpec, ...] = (
    MilestoneSpec(
        title="v0.2.0 - Reproducible Demo Polish",
        description="Make the current runtime easy to verify, demo, and understand.",
        issues=(
            IssueSpec(
                "Verify CI and document the checked commit",
                "Confirm GitHub Actions is green for the release commit and record the run URL.",
                ("release", "verification"),
            ),
            IssueSpec(
                "Add verification guide",
                "Document local, fresh-clone, demo, and Docker verification commands with expected output.",
                ("docs", "verification"),
            ),
            IssueSpec(
                "Split README setup paths",
                "Separate quick local demo, installed CLI demo, Docker demo, full visual YOLO setup, and dry-run safety boundary.",
                ("docs", "dx"),
            ),
            IssueSpec(
                "Improve dashboard v0 visibility",
                "Show module status, latest events, current metrics, and command ledger with clear empty states.",
                ("dashboard", "v0.2"),
            ),
            IssueSpec(
                "Add demo-mode indicator",
                "Make demo/sample mode visible in the dashboard and demo runtime environment.",
                ("dashboard", "demo"),
            ),
            IssueSpec(
                "Strengthen module starter docs",
                "Document BaseModule lifecycle, event schema, metric schema, and starter test expectations.",
                ("docs", "sdk"),
            ),
            IssueSpec(
                "Add minimal example module and discovery test",
                "Provide a tiny example module and a test proving starter-style plugin discovery works.",
                ("tests", "sdk"),
            ),
        ),
    ),
    MilestoneSpec(
        title="v0.3.0 - Developer Experience Hardening",
        description="Make IRMDS credible as an open-source developer project.",
        issues=(
            IssueSpec("Add CONTRIBUTING.md", "Document setup, branching, tests, and module contribution rules."),
            IssueSpec("Add issue and PR templates", "Create GitHub templates for bugs, module proposals, docs, security concerns, and pull requests."),
            IssueSpec("Document API error responses", "Define standard error shape and common failure cases."),
            IssueSpec("Add module lifecycle contract tests", "Expand tests around start, stop, restart, health, and metrics contracts."),
            IssueSpec("Add CLI tests", "Cover demo and future read-only CLI commands."),
            IssueSpec("Improve dashboard failure states", "Make API connection failures and missing data states actionable."),
            IssueSpec("Add troubleshooting docs", "Cover Windows, Docker, optional visual inference, and SQLite/runtime DB issues."),
        ),
    ),
    MilestoneSpec(
        title="v0.5.0 - Public Alpha Candidate",
        description="Make the architecture durable enough for serious public attention.",
        issues=(
            IssueSpec("Add architecture documentation", "Document kernel, event, module, and command flows with diagrams."),
            IssueSpec("Add schema versioning", "Version Event and Command payload contracts."),
            IssueSpec("Attach session IDs consistently", "Attach session identifiers to alerts, events, and commands where applicable."),
            IssueSpec("Add Prometheus metrics plan or endpoint", "Expose or document Prometheus-compatible metrics."),
            IssueSpec("Add config profiles", "Support demo, dev, test, docker, and full-visual profiles."),
            IssueSpec("Add screenshots and demo video", "Include stable README screenshots and a short demo video link."),
            IssueSpec("Add release checklist automation", "Create a release checklist script or documented release gate."),
        ),
    ),
    MilestoneSpec(
        title="v1.0-alpha - Stable Monitoring Runtime",
        description="Establish a stable monitoring runtime API and extension surface.",
        issues=(
            IssueSpec("Freeze v1 runtime contracts", "Define stable BaseModule, Event, Command, Metrics, and Health contracts."),
            IssueSpec("Add module starter kit or scaffold command", "Make new modules easy to generate and test."),
            IssueSpec("Add API authentication baseline", "Protect non-demo deployments with a minimal auth layer."),
            IssueSpec("Add notification adapters", "Implement console, Slack, Discord, and email notification routes."),
            IssueSpec("Add persistence migration strategy", "Document or implement schema migration for persistent records."),
            IssueSpec("Add observability baseline", "Provide structured logs, metrics, and health modes."),
            IssueSpec("Add security and safety policies", "Document safe-use boundaries, security reporting, and actuation limits."),
        ),
    ),
)


def _request(method: str, path: str, token: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "IRMDS-release-backlog",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def create_backlog(repo: str, token: str, dry_run: bool) -> None:
    """Create milestones and issues for the release backlog."""
    for milestone in MILESTONES:
        print(f"[milestone] {milestone.title}")
        milestone_number = None

        if not dry_run:
            created = _request(
                "POST",
                f"/repos/{repo}/milestones",
                token,
                {"title": milestone.title, "description": milestone.description},
            )
            milestone_number = created["number"]

        for issue in milestone.issues:
            print(f"  [issue] {issue.title}")
            if dry_run:
                continue

            _request(
                "POST",
                f"/repos/{repo}/issues",
                token,
                {
                    "title": issue.title,
                    "body": issue.body,
                    "labels": list(issue.labels),
                    "milestone": milestone_number,
                },
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create IRMDS GitHub release backlog.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub owner/repo target.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned backlog only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

    if not token and not args.dry_run:
        print("Missing GITHUB_TOKEN or GH_TOKEN. Re-run with --dry-run or provide a token.", file=sys.stderr)
        return 2

    try:
        create_backlog(args.repo, token or "", args.dry_run)
    except urllib.error.HTTPError as exc:
        print(f"GitHub API error: HTTP {exc.code} {exc.read().decode('utf-8')}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
