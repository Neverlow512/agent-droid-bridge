# Security Policy

## Supported Versions

Only the latest release receives security fixes. Older versions are not patched.

## Reporting a Vulnerability

Use GitHub's private security advisories to report a vulnerability:
[https://github.com/Neverlow512/agent-droid-bridge/security/advisories/new](https://github.com/Neverlow512/agent-droid-bridge/security/advisories/new)

Do not open a public issue for security vulnerabilities. The advisory system keeps the report private until a fix is available.

## What to Include

- Version affected
- Description of the vulnerability
- Steps to reproduce
- Potential impact

## Response Timeline

Acknowledgement within 48 hours. Critical issues patched within 14 days. Lower-severity issues may take longer, but you will receive a status update before 14 days.

I am maintaining this as a single developer. If a deadline cannot be met, communication will happen before it passes.

## Scope

**In scope:**

- Shell injection through ADB command handling
- Insecure defaults that expose the device without explicit user configuration
- Credential or token exposure
- Authentication or authorisation issues in the MCP server
- Unsafe handling of user-supplied input that could affect the host machine
- Dependencies with known critical CVEs that introduce exploitable risk
- Information disclosure beyond what the tool is designed to expose

**Out of scope:**

- Vulnerabilities in ADB itself or the Android OS
- Issues requiring physical access to the host machine
- Android device compromise resulting from the device's own state
- Vulnerabilities that require the attacker to already have access to the host machine running the server
- Security issues in third-party dependencies that have no exploitable path through this project
- Findings from automated scanners without a demonstrated exploit

## Disclosure Policy

Coordinate disclosure before going public. A 30-day embargo applies from the date of acknowledgement. If more time is needed, communicate that before the window closes and it can be extended.