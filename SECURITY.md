# Security Policy

## Supported versions

The most recent released version of the Similarweb MCP Plugin receives security
updates. Older versions are not maintained; please upgrade to the latest release
before reporting an issue.

## Reporting a vulnerability

Please do not open a public issue for security vulnerabilities.

Use GitHub's private reporting instead: open the repository's **Security** tab and
choose **Report a vulnerability**. If private reporting is unavailable, open a
minimal issue asking a maintainer to contact you, without disclosing any details.

We aim to acknowledge a report within a few business days and to share a
remediation timeline after triage.

## Scope

This plugin runs on the AI client's native tool surface (Read, Write, Bash, MCP
calls) and processes user-supplied data at runtime. It ships no server and stores
no credentials: your Similarweb API key stays in your own client configuration.

Reports of particular interest:

- A skill or build step that could exfiltrate user data or credentials.
- A supply-chain weakness in the build or release pipeline (workflows, pinned
  actions, release assets).
- Any shipped artifact that leaks non-public information.
