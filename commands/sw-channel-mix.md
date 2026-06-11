---
description: Channel-mix breakdown for a target domain with optional period-over-period deltas, top inbound referrers, PPC investment, and ad-network share.
argument-hint: <target-domain> [--window <range>] [--vs-period <previous>] [--country <iso-2>] [--currency <usd|eur|gbp|aud|jpy>] [--with-share-tool]
allowed-tools:
  - Read
  - Write
  - Bash
---

The user invoked `/sw-channel-mix $ARGUMENTS`. Follow the `sw-channel-mix` skill that ships in this plugin (load it by name via the platform's skill mechanism, or read its SKILL.md from the plugin's installed skills directory, not the current working directory) to fulfill the request, including its argument-parsing, capability-gating, and output-rendering contracts.
