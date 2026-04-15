## v0.6.0 (2026-04-15)

### Features

- env-first configuration and documentation overhaul
- Replace YAML-only configuration with env-first loading; all settings now
  configurable from the MCP client env block with no file editing required
- Add ADB_CONFIG_SOURCE to switch between env mode (default) and legacy
  YAML mode, preserving full backward compatibility for existing users
- Add 30 unit tests covering env loading, comma-split lists, and config
  source dispatch
- Add docs/troubleshooting.md covering the most common setup issues with
  per-client restart instructions
- Add docs/workflows.md with three advanced multi-tool workflow examples:
  app crash triage, UI state-aware automation, and exported component probing
- Rewrite README for clarity and promotional appeal; remove redundant prose
  and AI-style em-dashes
- Fix server.json version drift (0.1.3 -> 0.5.1) and add it to commitizen
  version_files so it stays in sync on future releases
- Fix logging.md example showing MCP_LOG_ENABLED=false in the enabling section

## v0.5.1 (2026-04-13)

### Bug Fixes

- bump fastmcp and pytest to address known vulnerabilities
- fastmcp >=3.2.0 resolves CVE-2026-32871, CVE-2026-27124, CVE-2025-64340
- pytest >=9.0.3 resolves CVE-2025-71176
- pip-audit added to dev dependencies
- OpenSSF Scorecard workflow added, runs on every push to main

## v0.5.0 (2026-04-12)

### Features

- add extra tool pack system and app_manager pack (0.5.0, beta)
- Introduce extra tool pack system — optional domain-specific tool modules loaded at startup via adb_config.yaml
- Add app_manager as the first pack, providing 9 new tools: list_packages, get_app_info, install_app, uninstall_app, pull_apk, manage_permission, launch_app_extra, manage_app, inject_intent
- Implement full service layer for pm, am, and shell-based ADB commands with structured Pydantic responses
- Add dumpsys package parser with API 30+ compatibility — metadata, permissions, and component extraction
- Normalize component names to package/class format for direct use with inject_intent
- Auto-resolve launcher activity via pm resolve-activity --brief in launch_app_extra
- Populate requires_root field dynamically based on root availability for manage_app clear_cache
- Add docs/extra-tool-packs.md — pack contract, enabling packs, and authoring guide
- Update docs/tools.md with full app_manager tool reference
- Update README, configuration.md, and CONTRIBUTING.md for the pack system
- Bump development status to Beta

## v0.4.2 (2026-04-05)

### Bug Fixes

- expose dynamic tool catalog via server instructions at startup
- Server generates instructions at startup via FastMCP lifespan hook, reflecting the active tool set after deny-list filtering
- Tools are grouped by section (Core vs extra packs) with concise first-sentence descriptions extracted from each tool's docstring
- Core tools expose a module-level description; extra packs can provide a PACK_META dict to contribute a section description
- _pack_meta module-level dict collects descriptions from loaded packs at startup for use in instruction generation
- Unit tests added for build_server_instructions, pack metadata collection via load_extra_packs, and lifespan wiring
- README and docs updated to document the feature, PACK_META convention for pack authors, and logging env vars in quick start config blocks

## v0.4.1 (2026-04-05)

### Bug Fixes

- fix debug levels, config path, and add check_device_capabilities
- Add check_device_capabilities tool for structured device introspection with identity, security, and hardware modes
- Fix ADB session logger not passing stdout and stderr in debug mode
- Fix logging config path resolution landing in src/ instead of project root
- Bundle logging_config.yaml inside the package for pip/uvx installs with safe defaults
- Add yaml files to wheel build includes in pyproject.toml
- Update docs to reflect new tool and corrected logging config path behaviour

## v0.4.0 (2026-04-04)

### Features

- Session recorder with tool, ADB, and security event capture
- Session-isolated directories per server start with tool.log, adb.log, security.log, general.log
- Persistent server.log at log root with daily rotation
- INFO/DEBUG level control per log type; params always logged, responses at DEBUG only
- Startup retention cleanup by session age and count
- FastMCP middleware-based interception, zero changes to individual tool functions
- Security event capture on all allowlist/denylist/shell block paths
- Configurable via logging_config.yaml and MCP_LOG_ENABLED / MCP_LOG_DIR env vars

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