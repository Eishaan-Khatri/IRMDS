# gstack Notes

This project uses gstack-style AI workflows for investigation, review,
documentation sync, QA, and shipping.

Recommended local install:

```bash
git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
cd ~/.claude/skills/gstack
./setup --team
```

Useful workflows for IRMDS:

| Workflow | When to use it |
|:--|:--|
| `/investigate` | root-cause debugging before applying fixes |
| `/review` | pre-merge branch review |
| `/qa` | dashboard and browser-flow testing |
| `/document-release` | README/docs sync after code changes |
| `/ship` | final verification, commit, push, and PR/release preparation |

Project-specific expectations:

- Use `/investigate` before guessing at failures.
- Use `/document-release` whenever modules, routes, or setup steps change.
- Use `/ship` only after `ruff`, `mypy`, `pytest`, `compileall`, and
  `git diff --check` pass.
- Use `/browse` for browser-based UI checks when the dashboard/API are running.
