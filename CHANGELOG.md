## v0.3.0 (2026-03-30)

### Features

- Added shell command filtering with two execution modes: `restricted` (allowlist-only) and `unrestricted` (denylist-based), configured via `ADB_EXECUTION_MODE`
- Added `ADB_ALLOW_SHELL=false` support to disable all `adb shell` commands entirely
- Added `tools.denied` config block to hide specific MCP tools from the agent at server startup, keeping context lean and preventing accidental misuse
- Added extra tool packs scaffold — optional feature modules can now be loaded at startup via the `extra_tool_packs` config block, laying the groundwork for modular capability expansion
- Shell denylist supports basename matching, so `/system/bin/rm` is caught by a simple `rm` entry
- New `security`, `tools`, and `extra_tool_packs` blocks added to `adb_config.yaml` with inline examples
- Comprehensive unit tests covering all filtering paths

## v0.2.0 (2026-03-29)

### Features

- Added `get_screen_elements` tool — parses the UI hierarchy and returns structured, coordinate-annotated elements with interaction properties. Supports four modes: `tappable`, `interactive`, `input`, and `all`
- Added `get_screen_text` tool — extracts all visible screen text sorted top-to-bottom as plain text, optimised for LLM context efficiency
- Added automated release tooling via commitizen: single-command version bumps, changelog generation, and tag pushing via `scripts/release.sh`
- Added CI guard job to enforce that the publish workflow only runs on tags pushed to `main`
- Added GitHub Release creation step that pulls release notes directly from `CHANGELOG.md`

### Improvements

- Pinned `fastmcp` and `pydantic` dependency ranges in `pyproject.toml` and `requirements.txt`
- Added `Issues` and `Documentation` project URLs to `pyproject.toml`
- README badges and Glama card restored and layout cleaned up

## v0.1.3 (2026-03-28)

### Features

- Added MCP Registry publishing step to the CI/CD workflow
- Added `CONTRIBUTING.md` and `SECURITY.md`

### Fixes

- Corrected YAML syntax issues in the `publish-mcp-registry` CI job

## v0.1.2 (2026-03-24)

### Fixes

- Reduced PyPI badge cache TTL to force version refresh after release

## v0.1.1 (2026-03-23)

### Features

- Initial public release
- 11 MCP tools covering screen capture, UI hierarchy inspection, touch and swipe input, text entry, keycode events, app launching, arbitrary ADB commands, device listing, and UI change detection
