<!--
Thanks for the PR. Keep this short — one summary, one test plan, one issue link.
Full guidelines: CONTRIBUTING.md and AGENTS.md (for AI-agent contributors).
-->

## Summary

<!-- One or two sentences. What changed, why. -->

## Linked issue

Closes #<!-- issue number -->

## Test plan

- [ ] `uv run pytest` passes (all unit tests green)
- [ ] New behavior is covered by a new unit test
- [ ] Tested manually against the live USPTO API (if applicable) — describe how below

<!-- Notes on manual / integration testing: -->

## Checklist

- [ ] Docstrings updated (especially `USE THIS TOOL WHEN:` and `Args:` for tool definitions)
- [ ] Version bumped in `pyproject.toml` AND `src/patent_mcp_server/config.py` (`USER_AGENT`) if user-visible
- [ ] If touching a decommissioned API: followed the 7-step pattern in [CLAUDE.md](../CLAUDE.md)
- [ ] No new dependencies (or, if added, justified in the description)
