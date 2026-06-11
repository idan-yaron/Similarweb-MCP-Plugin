# Contributing

## Setup

```bash
git clone https://github.com/idan-yaron/similarweb-mcp-plugin.git
cd similarweb-mcp-plugin
python3 build.py --build
# Output: dist/similarweb-<platform>-<version>.zip per platform
```

## Project structure

```
.claude-plugin/plugin.json        plugin manifest (name + description + version + author; optional license, keywords, homepage, repository)
.claude-plugin/marketplace.json   Claude Code marketplace manifest (repo root doubles as a marketplace)
skills/<name>/SKILL.md            per-skill body + frontmatter
commands/<name>.md                slash-command delegate for user-invocable skills (Cowork, Claude Code, Cursor)
agents/<name>.md                  Cowork-only autonomous subprocesses
hooks/                            Cowork-only event-driven automation (hooks.json + scripts/)
build.py                          translator + packager (Python 3 stdlib only)
docs/install-and-smoke-test.md    per-platform install + smoke-test guide (tracked)
docs/cowork-architecture-notes.md Cowork contract + rendering tiers (maintainer-local, gitignored)
docs/superpowers/{specs,plans}/   design specs + implementation plans (maintainer-local, gitignored)
```

The Similarweb MCP server is not bundled with this plugin. Users configure it separately in their AI client per Similarweb's official install instructions. See the README "Prerequisite" section.

Tests live under `tests/` locally; they are gitignored. Each contributor maintains their own.

## Adding a skill

1. Create `skills/<skill-name>/SKILL.md` with frontmatter containing ONLY `name` and `description`. Optionally `user-invocable: false` for background skills that should be hidden from the slash-command menu (foundations, router, setup). The default IS true, so user-invocable recipes do NOT set this field.
2. The `description` MUST be plain prose. NO angle brackets (`<`, `>`), NO square brackets (`[`, `]`), NO double dashes (`--`), NO ellipses (`...`). Cowork's validator silently rejects any SKILL.md whose description contains these patterns (bisect-confirmed 2026-05-19). `build.py --validate` enforces this. CLI flag syntax belongs in `commands/<name>.md` `argument-hint`, where the validator accepts it.
3. If the skill is user-invocable (should appear as `/sw-<name>` slash command on Cowork, Claude Code, and Cursor), also create `commands/sw-<name>.md` with frontmatter:
   - `description`: one short sentence.
   - `argument-hint`: CLI flag syntax IS allowed here.
   - `allowed-tools`: YAML list.

   Body is a one-line wrapper directing the harness to follow the corresponding skill (see existing files for the canonical wording).
4. Use the `/sw-*` namespace prefix.
5. If the skill makes new claims about MCP behavior (status codes, response shapes, parameter semantics, freshness, rate limits, tool availability), list a new assertion id in a `## Grounded assertions` body block at the END of the SKILL.md, and supply the grounding evidence. `tests/` is gitignored, so external contributors paste the evidence (exact calls made plus observed response envelopes) into the PR description; the maintainer lands the `tests/grounded/<assertion-id>.md` file and ledger entry locally. Frontmatter `depends_on:` is REJECTED by Cowork's validator; only the body block works. On maintainer machines, `build.py --validate` parses the body block and fails on unknown citations (the check no-ops on clones without `tests/`).
6. If the recipe outputs richer-than-text data (3+ entities, multi-period, dashboards), optionally add a `## Cowork persistent artifact` section (Tier 3, via `mcp__cowork__create_artifact`) or a `## Cowork chat-side panel` section (Tier 2, via a `.jsx` file written through the Write tool). Reference `docs/cowork-architecture-notes.md` for the contract and CSP rules.
7. Run `python3 build.py --validate` locally; it fails on description violations, grounding-ledger mismatches, and frontmatter `depends_on:` regressions.

## Adding a recipe-level Cowork artifact

Cowork supports three rendering tiers. The choice is per-recipe and per-intent:

1. **Markdown + Unicode bars** (baseline floor): every recipe ships this. Monospace code blocks with `█▉▊▌` characters give passable bar charts. Use this for narrative + table + slide intents.
2. **Chat-side `.jsx` panel** (Tier 2): write a single `.jsx` file via the Write tool; Cowork renders it inline. Pre-loaded: `lucide-react`, `recharts`, `d3`, `plotly`, `three`, `mathjs`, `lodash`, `papaparse`, `sheetjs`, `chart.js`, `tone`, `mammoth`, `tensorflow`, `shadcn/ui`. Tailwind core base classes work (no JIT, no custom values). NO localStorage in chat-side artifacts. Ephemeral per message.
3. **Persistent HTML artifact** (Tier 3): two-step. Write a self-contained HTML file via the Write tool, then call `mcp__cowork__create_artifact({ id, html_path, description, mcp_tools })`. Survives across sessions. Strict CSP, only three SRI-pinned CDNs allowed (chart.js, gridjs, mermaid). See the full rules in `docs/cowork-architecture-notes.md`.

The contract for which tier each recipe targets lives in `sw-foundation-render` § visualizations and § handoff-json-schema. Hand-rolled CDN versions or `fetch` calls inside Tier 3 artifacts will be blocked by the CSP.

## Branches and commits

- Branch names are type-prefixed: `feature/`, `fix/`, `refactor/`, `docs/`.
- Commit subject is concise; commit body is 4-6 lines explaining the why.
- Conventional commit prefix: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `build:`.
- Keep PRs focused on a single change.
- Every commit requires explicit user authorization. Never auto-commit.
- No `Co-Authored-By` trailer.

## Release checklist (local responsibility)

Before tagging a release:

1. `python3 build.py --validate` passes (frontmatter, descriptions under cap, description pattern check, grounding ledger, and the personal-data/secrets gate: connector ids, emails, absolute local paths, secrets, banned identity, and `.pii-blocklist` terms across every tracked file, with matches redacted in output).
2. `python3 build.py --test` passes locally (stub-MCP behavioral contract).
3. Re-run each grounded assertion's "Re-validation notes" block manually against the live MCP (or via an AI client session with MCP access). Update `tests/grounding-ledger.json` if any assertion's shape drifted. The `build.py --ground` mode is a stub today; the manual re-run is the contract.
4. `python3 build.py --build` produces clean per-platform zips.
5. The personal-data/secrets gate runs automatically inside `build.py --validate` (step 1) and in CI, scanning every tracked file. The optional `tests/translator/lint-pii.sh` (gitignored, local) remains as a convenience for scanning a single directory against `.pii-blocklist` only; the `--validate` gate is the enforced contract and covers more (connector ids, emails, paths, secrets, identity, plus the blocklist).
6. Bump the version per semver in THREE places (the validator enforces all three staying in sync): `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (plugins[0].version), and the handoff-JSON version literal in `skills/sw-foundation-render/SKILL.md`. Do NOT bump for failed install attempts.
7. Confirm grounding ledger has no `status: pending_manual` assertions blocking ship. The three acknowledged operator-required gaps (`auth-invalid-envelope-shape`, `partial-access-envelope-shape`, `aeo-tool-availability`) ship with caveats. Five additional forward-looking pending_manual entries (`keywords-competitors-exact-3-months`, `pages-tools-web-source-total`, `apps-tool-constraints`, `clicks-share-per-brand-only`, `keywords-overview-3-month-max`) do not block (their `depended_on_by` is empty). Document the acknowledged caveats in release notes.
8. When uploading a new version of a same-named plugin to Cowork, UNINSTALL the old one first. Cowork uploads with `overwrite=false` and the marketplace API rejects same-name uploads, surfacing as the generic "Plugin validation failed."
9. `git tag v<version>` and push (with user approval per the commit rule above).

CI (`.github/workflows/release.yml`) runs `--validate` and `--build`, then publishes the platform zips as release assets. Because the personal-data/secrets gate lives in `--validate`, a leak fails the workflow before any bundle is attached.

## Refactor watchlist

- When a pattern appears in two or more recipe bodies (normalization rules, window derivations, rendering contracts), promote it into the matching sw-foundation helper section and have the recipes cite the section, so recipe bodies shrink to their unique tool sequence plus analysis logic.

## Reporting issues

[GitHub Issues](https://github.com/idan-yaron/similarweb-mcp-plugin/issues). Bug reports and recipe requests are both welcome.
