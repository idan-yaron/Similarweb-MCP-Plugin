---
description: Inspect, refresh, or reset the Similarweb plugin's capability map.
argument-hint: "[--show | --refresh | --reset | --schedule-grounding <weekly|monthly|off> (Cowork only)]"
allowed-tools:
  - Read
  - Write
  - Bash
---

The user invoked `/sw-config $ARGUMENTS`. Follow the `sw-config` skill that ships in this plugin (load it by name via the platform's skill mechanism, or read its SKILL.md from the plugin's installed skills directory, not the current working directory) to fulfill the request, including its argument-parsing, capability-gating, and output-rendering contracts.
