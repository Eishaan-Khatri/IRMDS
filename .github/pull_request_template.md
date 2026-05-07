## Summary

Describe what changed and why.

## Verification

- [ ] `python -m compileall -q api core modules dashboard cli notifications tests scripts examples`
- [ ] `ruff check .`
- [ ] `mypy core api modules`
- [ ] `pytest tests -q`
- [ ] `git diff --check`

## Demo Impact

- [ ] Not demo-related
- [ ] `python scripts/demo.py --smoke --no-dashboard`
- [ ] `python -m cli.main demo --smoke --no-dashboard`
- [ ] Docker checked if Docker behavior changed

## Safety

- [ ] No real hardware actuation added
- [ ] Dry-run command boundary preserved
- [ ] No secrets committed
- [ ] Docs updated for behavior changes

## Notes

Add any reviewer context, known limitations, or follow-up work.
