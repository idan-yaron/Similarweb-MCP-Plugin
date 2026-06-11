---
description: Proxy AEO (Answer Engine Optimization) audit for one brand domain.
argument-hint: <domain> [--country <c>] [--keywords <k1,k2,...>] [--campaign-id <uuid>]
allowed-tools:
  - Read
  - Write
  - Bash
---

The user invoked `/sw-aeo-audit $ARGUMENTS`. Follow the `sw-aeo-audit` skill that ships in this plugin (load it by name via the platform's skill mechanism, or read its SKILL.md from the plugin's installed skills directory, not the current working directory) to fulfill the request, including its argument-parsing, capability-gating, and output-rendering contracts.
