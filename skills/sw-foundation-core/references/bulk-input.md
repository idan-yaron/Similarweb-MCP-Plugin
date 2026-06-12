# § bulk-input-from-context, detection steps (sw-foundation-core reference)

When a recipe accepts a LIST of inputs (multiple domains, brands, or keywords), use whatever the user already shared in the current conversation: a pasted list, an @-mentioned file the agent already read into context, args in the prompt itself.

DO NOT scan the working directory or do filesystem globbing. Bulk-input detection is context-derived only; identical across Claude Code, Codex, Cursor, Claude.ai.

1. Inspect the conversation context for a list-shaped artifact relevant to the recipe (domains for a website recipe, brands for a brand recipe, keywords for a keyword recipe).
2. If found and count > 25: ask one confirmation question ("competitors.csv has 47 items; process top 25, all, or pick a range?"). Default option is "top 25 by rank".
3. If found and shape is ambiguous (could be domains or brand names or keywords): ask ONE crisp disambiguation question with explicit options. Never open-ended.
4. If not found, the recipe runs on its explicit args only.
