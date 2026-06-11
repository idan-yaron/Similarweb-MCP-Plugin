---
description: Orchestrated competitive teardown for one target domain against an optional set of competitors.
argument-hint: <target-domain> [--vs <competitor>...] [--country <c>] [--window <w>] [--with-amazon-context] [--with-rank-delta]
allowed-tools:
  - Read
  - Write
  - Bash
---

The user invoked `/sw-competitive-teardown $ARGUMENTS`. Follow the `sw-competitive-teardown` skill that ships in this plugin (load it by name via the platform's skill mechanism, or read its SKILL.md from the plugin's installed skills directory, not the current working directory) to fulfill the request, including its argument-parsing, capability-gating, and output-rendering contracts.
