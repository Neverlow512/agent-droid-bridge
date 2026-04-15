# Workflows

Common multi-tool patterns for automating Android interactions through the MCP server.

## App crash triage

When a build behaves unexpectedly, an agent can run the full diagnostic loop without human intervention. This workflow launches the app, establishes a UI baseline, triggers the action that is known to fail, detects whether the screen changed or froze, reads the resulting state, captures a screenshot for the record, and pulls the device log for offline analysis.

```mermaid
sequenceDiagram
    autonumber
    participant A as Agent
    participant S as Agent Droid Bridge

    A->>+S: launch_app_extra(package)
    S-->>-A: launched

    A->>+S: snapshot_ui()
    S-->>-A: baseline token

    A->>+S: tap_screen(trigger_action)
    S-->>-A: ok

    A->>+S: detect_ui_change(baseline_token, timeout=10)
    Note over S: polls until screen changes or timeout
    S-->>-A: changed / timed out

    A->>+S: get_screen_text()
    S-->>-A: screen text

    Note over S: identifies error state from text

    A->>+S: take_screenshot()
    S-->>-A: base64 PNG

    A->>+S: execute_adb_command(logcat -d)
    S-->>-A: log output
```

`detect_ui_change` returning `timed out` is itself diagnostic — it means the app froze or the expected transition never happened. The agent can branch on this result without any additional tooling.

Requires the `app_manager` pack for `launch_app_extra`.

## UI state-aware automation

A robust agent does not assume the app is in a known state before acting. This workflow reads the current screen first, decides what state the app is in, and takes the appropriate path — skipping steps that are already done and handling unexpected states without failing.

```mermaid
sequenceDiagram
    autonumber
    participant A as Agent
    participant S as Agent Droid Bridge

    A->>+S: launch_app_extra(package)
    S-->>-A: launched

    A->>+S: get_screen_text()
    S-->>-A: screen text

    Note over A,S: agent reads state — logged in or login form?

    alt already logged in
        A->>+S: get_screen_elements(mode=tappable)
        S-->>-A: element list

        A->>+S: tap_screen(target_element)
        S-->>-A: ok
    else login required
        A->>+S: get_screen_elements(mode=input)
        S-->>-A: input fields

        A->>+S: tap_screen + type_text(credentials)
        S-->>-A: ok

        A->>+S: tap_screen(login_button)
        S-->>-A: ok

        A->>+S: detect_ui_change(baseline, timeout=10)
        S-->>-A: changed=true
    end

    A->>+S: take_screenshot()
    S-->>-A: base64 PNG
```

`get_screen_text` is cheap — it reads text already present in the UI hierarchy without any extra ADB round-trip. Reading state before acting prevents the agent from re-entering credentials on an already-authenticated session or tapping the wrong element.

Requires the `app_manager` pack for `launch_app_extra`.

## Exported component discovery and probing

Static analysis alone does not reveal how an app responds to unexpected input. This workflow retrieves an app's exported components, fires an intent at one of them, captures the resulting screen state, and records the response. The full loop — enumerate, probe, observe — runs in a single agent session with no instrumentation required.

```mermaid
sequenceDiagram
    autonumber
    participant A as Agent
    participant S as Agent Droid Bridge

    A->>+S: list_packages(filter=user, search="target")
    S-->>-A: matching packages

    A->>+S: get_app_info(package, sections=[components])
    S-->>-A: exported components

    A->>+S: snapshot_ui()
    S-->>-A: baseline token

    loop exported activities
        A->>+S: inject_intent(action=start, component)
        S-->>-A: ok

        A->>+S: detect_ui_change(baseline_token, timeout=5)
        S-->>-A: changed / timed out

        A->>+S: get_screen_text()
        S-->>-A: screen text

        A->>+S: take_screenshot()
        S-->>-A: base64 PNG
    end
```

`detect_ui_change` after each intent shows whether the component responded — a screen transition is evidence of a live, reachable entry point. A timeout suggests the component exists but did not produce a visible UI change, which is equally useful to record.

Requires the `app_manager` pack.
