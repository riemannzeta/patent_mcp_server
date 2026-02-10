---
title: Fix Dependabot Security Vulnerabilities
type: fix
date: 2026-02-10
priority: high
---

# Fix Dependabot Security Vulnerabilities

## Overview

Address 5 security vulnerabilities across 3 packages identified by GitHub Dependabot and pip-audit. These include one runtime dependency vulnerability (python-multipart) and four dev-only dependency vulnerabilities (urllib3, jaraco-context).

## Problem Statement

The project has known security vulnerabilities in its dependency chain:

| Package | Current | Fix Version | CVE | CVSS | Type |
|---------|---------|-------------|-----|------|------|
| python-multipart | 0.0.20 | 0.0.22 | [CVE-2026-24486](https://nvd.nist.gov/vuln/detail/CVE-2026-24486) | 8.2-8.8 | **Runtime** |
| urllib3 | 2.5.0 | 2.6.3 | [CVE-2026-21441](https://nvd.nist.gov/vuln/detail/CVE-2026-21441) | 8.9 | Dev only |
| urllib3 | 2.5.0 | 2.6.0 | [CVE-2025-66418](https://nvd.nist.gov/vuln/detail/CVE-2025-66418) | - | Dev only |
| urllib3 | 2.5.0 | 2.6.0 | [CVE-2025-66471](https://nvd.nist.gov/vuln/detail/CVE-2025-66471) | - | Dev only |
| jaraco-context | 6.0.1 | 6.1.0 | [CVE-2026-23949](https://nvd.nist.gov/vuln/detail/CVE-2026-23949) | 8.6 | Dev only |

### Vulnerability Details

**CVE-2026-24486 (python-multipart)** - Path Traversal allowing attackers to write uploaded files to arbitrary filesystem locations via malicious filenames. Only affects non-default configuration with `UPLOAD_DIR` and `UPLOAD_KEEP_FILENAME=True`. This is a transitive dependency of `mcp[cli]`.

**CVE-2026-21441 (urllib3)** - Decompression bomb safeguard bypass when following HTTP redirects with streaming API, enabling DoS attacks. Transitive via `twine→id→requests`.

**CVE-2026-23949 (jaraco-context)** - Zip Slip path traversal in `tarball()` function allowing extraction of files outside intended directory. Transitive via `twine→keyring`.

### Dependency Chain

```
patent-mcp-server
├── mcp[cli] v1.23.1
│   └── python-multipart v0.0.20  ← CVE-2026-24486 (RUNTIME)
└── [dev] twine v6.2.0
    ├── id v1.5.0
    │   └── requests v2.32.5
    │       └── urllib3 v2.5.0    ← CVE-2026-21441, CVE-2025-66418, CVE-2025-66471
    └── keyring v25.7.0
        └── jaraco-context v6.0.1 ← CVE-2026-23949
```

## Proposed Solution

Add explicit dependency constraints to `pyproject.toml` to force minimum safe versions of vulnerable packages.

### Approach

1. **Runtime fix**: Add `python-multipart>=0.0.22` to `[project.dependencies]`
2. **Dev-only fixes**: Add `urllib3>=2.6.3` and `jaraco-context>=6.1.0` to `[dependency-groups].dev`
3. Regenerate lock file with `uv sync`
4. Run full test suite to verify no breaking changes
5. Verify vulnerability remediation with `pip-audit`

### Why This Approach

- **Explicit constraints** ensure minimum safe versions regardless of transitive dependency resolution
- Adding to `[project.dependencies]` for python-multipart affects all users (runtime protection)
- Adding to `[dependency-groups].dev` for dev dependencies only affects developers
- Minimal invasive change - no need to update MCP version or refactor code

## Technical Considerations

### Breaking Change Risk

| Package | Version Jump | Risk Assessment |
|---------|-------------|-----------------|
| python-multipart | 0.0.20 → 0.0.22 | Low - patch release, API compatible |
| urllib3 | 2.5.0 → 2.6.3 | Medium - minor version bump, check changelog |
| jaraco-context | 6.0.1 → 6.1.0 | Low - patch release, only affects tarball() |

### Compatibility

- All fix versions are available on PyPI
- Python version support unchanged (3.10-3.13)
- No direct code changes required - these are transitive dependencies

### Lock File

The `uv.lock` file (1332 lines) will be regenerated. This is already tracked in git and should be committed alongside `pyproject.toml` changes for reproducible builds.

## Acceptance Criteria

### Functional Requirements

- [x] `pip-audit` reports 0 known vulnerabilities after update
- [x] `uv tree` shows python-multipart >= 0.0.22
- [x] `uv tree` shows urllib3 >= 2.6.3
- [x] `uv tree` shows jaraco-context >= 6.1.0

### Non-Functional Requirements

- [x] All unit tests pass (`uv run pytest` - expect ~179 passed, ~44 skipped)
- [x] MCP server starts without errors (`uv run patent-mcp-server`)
- [x] No new deprecation warnings introduced

### Quality Gates

- [x] No test regressions
- [x] Lock file regenerated and committed
- [x] Commit message references CVE numbers

## Implementation Plan

### Phase 1: Update Dependencies

**File: `pyproject.toml`**

```toml
# Add to [project.dependencies] section:
dependencies = [
    "h2>=4.2.0",
    "httpx>=0.28.1",
    "mcp[cli]>=1.3.0",
    "python-dotenv>=1.0.1",
    "pydantic>=2.0.0",
    "python-multipart>=0.0.22",  # CVE-2026-24486 fix
    "tenacity>=8.0.0",
]

# Add to [dependency-groups].dev section:
[dependency-groups]
dev = [
    "build>=1.3.0",
    "jaraco-context>=6.1.0",  # CVE-2026-23949 fix
    "pytest>=8.4.2",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=7.0.0",
    "twine>=6.2.0",
    "urllib3>=2.6.3",  # CVE-2026-21441, CVE-2025-66418, CVE-2025-66471 fix
]
```

### Phase 2: Regenerate Lock File

```bash
uv sync
```

### Phase 3: Verify Versions

```bash
uv tree | grep -E "python-multipart|urllib3|jaraco-context"
```

Expected output:
```
│   └── python-multipart v0.0.22
│       └── urllib3 v2.6.3
        └── jaraco-context v6.1.0
```

### Phase 4: Run Tests

```bash
# Unit tests (default)
uv run pytest

# Verify server starts
uv run patent-mcp-server --help
```

### Phase 5: Verify Remediation

```bash
uv run pip-audit
```

Expected: `No known vulnerabilities found`

### Phase 6: Commit

```bash
git add pyproject.toml uv.lock
git commit -m "fix: Update dependencies to address security vulnerabilities

- python-multipart 0.0.20 → 0.0.22 (CVE-2026-24486)
- urllib3 2.5.0 → 2.6.3 (CVE-2026-21441, CVE-2025-66418, CVE-2025-66471)
- jaraco-context 6.0.1 → 6.1.0 (CVE-2026-23949)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

## Dependencies & Prerequisites

- uv package manager installed
- Network access for package downloads
- Write access to repository

## Risk Analysis & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| urllib3 breaking change | Low | Medium | Run full test suite; rollback if fails |
| Dependency resolution conflict | Low | High | uv handles conflicts; manual resolution if needed |
| Test failures unrelated to update | Low | Low | Investigate before attributing to dependency update |

### Rollback Plan

If issues are discovered post-update:

```bash
git checkout HEAD~1 -- pyproject.toml uv.lock
uv sync
```

## Success Metrics

1. Zero vulnerabilities reported by `pip-audit`
2. All 179 unit tests passing
3. Server starts and responds to basic requests
4. No new deprecation warnings in test output

## Future Considerations

### Recommended Follow-Up Work

1. **Add GitHub Actions CI** - Automate test runs on PR/push
2. **Add Dependabot configuration** - Automate dependency update PRs
3. **Add pip-audit to pre-commit hooks** - Catch vulnerabilities early
4. **Consider updating MCP** - Current 1.23.1, latest is 1.26.0

### Proposed Dependabot Config

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      security:
        applies-to: security-updates
```

## References

### Internal References

- Dependency configuration: `pyproject.toml`
- Lock file: `uv.lock`
- Test configuration: `pytest.ini`
- Development guidelines: `CLAUDE.md`

### External References

- [CVE-2026-24486 - NVD](https://nvd.nist.gov/vuln/detail/CVE-2026-24486)
- [CVE-2026-21441 - NVD](https://nvd.nist.gov/vuln/detail/CVE-2026-21441)
- [CVE-2026-23949 - NVD](https://nvd.nist.gov/vuln/detail/CVE-2026-23949)
- [python-multipart GitHub Advisory](https://github.com/advisories/GHSA-wp53-j4wj-2cfg)
- [urllib3 GitHub Advisory](https://github.com/advisories/GHSA-38jv-5279-wg99)
- [jaraco-context GitHub Advisory](https://github.com/advisories/GHSA-58pv-8j8x-9vj2)

### Related Work

- GitHub Dependabot alerts: https://github.com/riemannzeta/patent_mcp_server/security/dependabot
