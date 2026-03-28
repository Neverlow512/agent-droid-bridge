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

Follow conventional commit prefixes: `feat:`, `fix:`, `chore:`, `docs:`.

**Code standards**

- All code must use `async`/`await`. Synchronous code is only acceptable where async is technically impossible.
- Use Pydantic models for all data structures and config validation.
- All imports at the top of the file, never inside functions.
- No hardcoded values. Configuration belongs in environment variables or config files.
- Comments only for non-obvious intent or constraints, not to narrate what the code does.
- Keep files under 300 lines. Split by responsibility when a file grows beyond that.
- Linter: `ruff` with `line-length = 100`. Run `ruff check .` and `ruff format .` before committing.

## Submitting a PR

- One change per PR.
- New functionality requires tests.
- The PR description should cover what changed and why.
- All existing tests must pass and `ruff` must report no errors.

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
