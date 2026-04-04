# Contributing

Agent Droid Bridge is an MCP server that connects AI agents to Android devices via ADB. Contributions that improve mobile device automation and control are welcome.

## Getting started

For prerequisites (Python 3.11+, ADB, uv), see [docs/setup.md](docs/setup.md).

**Dev setup**

```bash
git clone https://github.com/Neverlow512/agent-droid-bridge.git
cd agent-droid-bridge
python3.11 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
```

**Running tests**

```bash
pytest
```

Tests live in `tests/unit/` and `tests/integration/`. `asyncio_mode` is set to `auto` — no extra boilerplate needed for async tests.

## Making changes

**Branches**

Use the appropriate prefix: `feat/`, `fix/`, `chore/`, `docs/`.

**Commits**

Follow conventional commit format: `type(scope): description`

| Type | Purpose | Version Bump |
|------|---------|--------------|
| `feat` | New user-facing capability | MINOR (0.x.0) |
| `fix` | Bug fix | PATCH (0.0.x) |
| `chore` | Tooling, dependencies, config | No changelog entry |
| `docs` | Documentation only | No changelog entry |
| `feat!` or `BREAKING CHANGE:` | Breaking change | MAJOR (x.0.0) |

A `feat!` or `BREAKING CHANGE:` footer triggers a MAJOR version bump. MAJOR means breaking change, not "big release".

**Code standards**

- All code must use `async`/`await`. Synchronous code is only acceptable where async is technically impossible.
- Use Pydantic models for all data structures and config validation.
- All imports at the top of the file, never inside functions.
- No hardcoded values. Configuration belongs in environment variables or config files.
- Comments only for non-obvious intent or constraints, not to narrate what the code does.
- Keep files under 300 lines. Split by responsibility when a file grows beyond that.
- Linter: `ruff` with `line-length = 100`. Run `ruff check .` and `ruff format .` before committing.

## Submitting a PR

- Open a PR from your branch to `main`.
- The maintainer will squash merge the PR.
- The squash commit message is what appears in the changelog. Include a clear conventional commit message in your PR description as the suggested merge message — subject line as `type(scope): description`, and body bullet points as user-facing changelog entries. The body bullets are written verbatim into `CHANGELOG.md` by CI.
- One PR per feature or fix.
- New functionality requires tests.
- All existing tests must pass and `ruff` must report no errors.

Install the pre-commit hook to validate commit messages:

```bash
pip install pre-commit && pre-commit install
```

## Reporting bugs

Open an issue on [GitHub Issues](https://github.com/Neverlow512/agent-droid-bridge/issues) and include:

- Package version
- Steps to reproduce
- Expected vs actual behaviour
- OS, ADB version, and device/emulator details

## Requesting features

Open an issue and describe the use case, not just the feature. What are you trying to accomplish and why does the current toolset fall short?

## Scope

Contributions focused on mobile device automation and control are in scope. The project is Android-first. iOS or other platform support is not categorically ruled out but would require prior discussion before implementation. Contributions that add functionality unrelated to mobile device control are out of scope.

## Maintainer note

This is a solo-maintained personal project. I aim to respond to issues and PRs within a few days, but there is no guaranteed timeline.
