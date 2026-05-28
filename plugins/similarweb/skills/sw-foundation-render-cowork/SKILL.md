---
name: sw-foundation-render-cowork
description: Cowork-only rich-rendering tiers for the Similarweb recipes. Loaded ONLY on Cowork AND when the user explicitly asks for a dashboard, persistent view, interactive panel, artifact, or chart, OR when a recipe's high-dimensionality trigger fires (3+ competitors in a teardown, 3+ overlap domains, 10+ market brands, deep folder trees in a page-mix run). Covers Tier 2 chat-side jsx panels emitted via the Write tool and Tier 3 persistent HTML artifacts emitted via mcp__cowork__create_artifact, including the CSP whitelist, the window.cowork JS bridge, the gridjs and chartjs CDN pins, and the slug pattern for artifact reuse. NEVER loads on Codex, Claude Code, Cursor, or Claude.ai (no equivalent surface). Markdown plus Unicode-bar rendering (Tier 1) is the universal baseline carried by sw-foundation-render section visualizations and ships on every platform without this helper.
user-invocable: false
---
# sw-foundation-render-cowork: Cowork rich-rendering tiers

Loads only on Cowork-shaped turns where a recipe (or the router) decides to emit richer output than the baseline markdown plus Unicode bars (Tier 1, owned by `sw-foundation-render`). Carries the canonical contract for Tier 2 (chat-side `.jsx` panels) and Tier 3 (persistent HTML artifacts) so recipes can delegate the Cowork surface without each one re-deriving the CSP, the CDN pins, the JS bridge, or the slug pattern.

This skill never auto-triggers on bare Similarweb keywords. It loads when:

1. The user asks for an interactive panel, dashboard, persistent view, or artifact in plain language.
2. A recipe's high-dimensionality trigger fires (each recipe documents its own threshold in its `## Cowork chat-side panel` or `## Cowork persistent artifact` section).
3. The intent classifier in `sw-foundation-render` returns `dashboard` or `interactive view`.

## Tier overview

Cowork supports three distinct render surfaces. Markdown is the primary contract everywhere; the two richer tiers are SUPPLEMENTAL and OPT-IN. The markdown answer renders unchanged across all three.

| Tier | Surface | Persistence | Tool | When |
|------|---------|-------------|------|------|
| 1 | Markdown + Unicode bars | Per-message | (none) | Default for every recipe. Documented in sw-foundation-render section visualizations. |
| 2 | Chat-side `.jsx` panel | Per-message (ephemeral) | `Write` (one `.jsx` file) | Recipe output has comparison shape but the user did not ask for a dashboard. |
| 3 | Persistent HTML artifact | Saved at `~/Documents/Claude/Artifacts/<slug>/index.html`, versioned (cap 100), shareable, `cowork-artifact://local/<slug>/index.html` URI | `mcp__cowork__create_artifact` (TWO-STEP: Write the HTML file, then call the tool with the absolute path) | User asks for a dashboard, persistent view, or recipe-specific high-dimensionality trigger fired. |

Tiers 2 and 3 are defined below. Tier 1 stays in `sw-foundation-render`.

## Tier 2: chat-side .jsx panels (inline, ephemeral)

**Trigger.** One of:
- Recipe's intent classifier returns `interactive view` / `explore` / `dashboard` AND the user did NOT ask for a persistent artifact (they want a richer view inline, not a saved page).
- A comparison gets richer than 5 rows (e.g., a 10-channel period-over-period table) and a chart would carry the signal better than a Unicode bar.
- The recipe-specific trigger listed in that recipe's `## Cowork chat-side panel` section fired.

**How.** Use the `Write` tool to emit a SINGLE `.jsx` file with the path under `~/` (Cowork renders any file whose extension is `.md`, `.html`, `.jsx`, `.mermaid`, `.svg`, or `.pdf` inline as a chat panel). The runtime auto-loads these libraries before evaluating the file (no install / import map needed):

`lucide-react`, `recharts`, `d3`, `plotly`, `three`, `mathjs`, `lodash`, `papaparse`, `sheetjs`, `chart.js`, `tone`, `mammoth`, `tensorflow`, `shadcn/ui`.

Tailwind core utility classes work (the base set only; the JIT compiler is not running so arbitrary values like `w-[37px]` fail silently). Hand-roll any custom utility class as inline `style={{ }}`.

**Constraints.** No `localStorage` (chat-side artifacts are scoped to the message). No external scripts (the `.jsx` runtime is sandboxed). Component must default-export.

**Pattern.** One default-exported React component with `props.data` set at the top of the file as a literal object (the runtime LLM inlines MCP result values into the literal). Recharts is simplest for bar / line / area. `chart.js` for stacked bars. `plotly` for sankey / heatmap. No imports needed; the runtime resolves these from the auto-loaded module set.

Skeleton (Recharts bar chart, 30 lines):

```jsx
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts';

const data = [
  { channel: 'Direct',        current: 24.3, prior: 22.0 },
  { channel: 'Organic Search', current: 33.6, prior: 38.2 },
  { channel: 'Paid Search',    current: 15.4, prior: 12.1 }
];

export default function Panel() {
  return (
    <div style={{ padding: 16, background: '#fff', color: '#111', fontFamily: 'system-ui' }}>
      <h2 style={{ fontSize: 16, marginBottom: 8 }}>Channel mix shift (current vs prior)</h2>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="channel" />
          <YAxis label={{ value: 'Share %', angle: -90, position: 'insideLeft' }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="prior"   fill="#9ca3af" name="Prior" />
          <Bar dataKey="current" fill="#2563eb" name="Current" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

Write the file to `~/sw-<recipe>-panel.jsx`. Cowork renders it inline in the chat the moment the file is written; no separate tool call.

## Tier 3: persistent HTML artifacts via `mcp__cowork__create_artifact`

**Trigger.** One of:
- User asks for a dashboard, persistent view, interactive view, or "give me a dashboard".
- Intent classifier returns `mode=dashboard`.
- Recipe-specific high-dimensionality trigger fired (see each recipe's `## Cowork persistent artifact` section: 3+ competitors, 3+ overlap domains, 10+ market brands, etc.).
- Analysis the user is likely to return to (weekly competitive review, ongoing market tracker, recurring audit).

**How.** TWO-STEP:

1. Use `Write` to emit a self-contained HTML file. Recommended path: `~/sw-<recipe>-<target>-<yyyymm>.html`.
2. Call `mcp__cowork__create_artifact` with the file's absolute path.

Tool schema (the REAL schema, not the legacy `{title, content_type, content}` shape):

```
mcp__cowork__create_artifact({
  id:          "sw-<recipe>-<target-slug>-<yyyymm>",
  html_path:   "/absolute/path/to/the/file.html",
  description: "<one-line description shown to the user>",
  mcp_tools:   ["mcp__<server>__<tool>", "..."]
})
```

Field rules:
- `id` is a kebab-case slug; must contain at least one letter or digit. Use the slug pattern `sw-<recipe>-<target>-<yyyymm>` so repeat invocations REUSE the same artifact via `mcp__cowork__update_artifact` instead of creating duplicates. Call `mcp__cowork__list_artifacts` first to detect an existing slug.
- `html_path` is the absolute path the `Write` tool wrote. Do NOT pass content inline.
- `description` is visible in the artifact panel header. Keep it under one line.
- `mcp_tools` is the fully-qualified list of MCP tools the page will call via the JS bridge (see below). Cowork uses this for permission gating; missing tools fail at runtime.

**CSP that the iframe enforces (verbatim):**

```
default-src 'self'; script-src 'self' 'unsafe-inline' <whitelist>; style-src 'self' 'unsafe-inline' <whitelist-css>; img-src 'self' data:; font-src 'self' data:; connect-src 'none'; object-src 'none'; frame-src 'none'; form-action 'none'; base-uri 'self'; webrtc 'block'
```

The script / style whitelist is exactly these three CDNs (SRI-pinned; do NOT change versions):

- `https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.js`
- `https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/gridjs.umd.js` + `https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/theme/mermaid.min.css`
- `https://cdn.jsdelivr.net/npm/mermaid@11.10.0/dist/mermaid.min.js`

**JS bridge available inside the iframe (Cowork injects `window.cowork`):**

- `window.cowork.callMcpTool(name, args)` returns a Promise resolving to the MCP tool's response payload. Cowork enforces a 5-minute read cache (identical args = cached) and a 30-call-per-minute rate cap per artifact. All data flows through this bridge; `fetch` / `XHR` / `WebSocket` / `EventSource` are blocked by `connect-src 'none'`.
- `window.cowork.askClaude(prompt, data?)` runs a single-turn Haiku 4.5 inference (no tools, no system prompt). Use for natural-language summaries the user can ask for in-panel.
- `window.cowork.runScheduledTask(taskId)` triggers a scheduled task; requires a user click + native confirm dialog. Do NOT call from page load.

`localStorage` IS available and persists across reloads of the artifact. Use it to remember the user's filter and sort choices.

**Constraints persistent artifacts MUST respect:**
- No `fetch`, `XHR`, `WebSocket`, `EventSource`. All data goes through `window.cowork.callMcpTool`.
- No `<iframe>`, no `<object>`, no Tailwind CDN. Hand-roll utility CSS inline.
- HTML must be self-contained: inline CSS + JS, base64 or `data:` URIs for fonts and images. Max 10 MiB. Max 1M chars when sharing.
- `:root { color-scheme: light }` is mandated.
- Reload button is built into the panel header. Do NOT add your own.
- Slug pattern `sw-<recipe>-<target>-<yyyymm>` so monthly refreshes update the same artifact via `mcp__cowork__update_artifact`. Check via `mcp__cowork__list_artifacts` first; if the slug exists, prefer `update_artifact` over `create_artifact`.

Skeleton (~60 lines, Chart.js + Grid.js + one MCP call on load):

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>sw-teardown-target-202605</title>
  <style>
    :root { color-scheme: light; }
    body { font: 14px/1.4 system-ui; margin: 0; padding: 16px; background: #fff; color: #111; }
    header { display: flex; gap: 12px; align-items: baseline; margin-bottom: 12px; }
    h1 { font-size: 16px; margin: 0; }
    .meta { color: #6b7280; }
    .grid-wrap { margin-top: 16px; }
    .toolbar button { padding: 4px 10px; margin-right: 6px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; }
    .toolbar button[aria-pressed="true"] { background: #2563eb; color: #fff; border-color: #2563eb; }
  </style>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/theme/mermaid.min.css" integrity="sha384-..." crossorigin="anonymous">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.0/dist/chart.umd.js" integrity="sha384-..." crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/gridjs@5.0.2/dist/gridjs.umd.js" integrity="sha384-..." crossorigin="anonymous"></script>
</head>
<body>
  <header>
    <h1>Competitive teardown: target.com</h1>
    <span class="meta">US | last 90 days | last_updated 2026-04-30</span>
  </header>
  <div class="toolbar" id="toolbar"></div>
  <canvas id="channel-chart" height="200"></canvas>
  <div class="grid-wrap" id="comp-grid"></div>
  <script>
    const COMPETITORS = ['target.com', 'rival-a.com', 'rival-b.com'];
    const SORT_KEY = localStorage.getItem('sw-teardown-sort') || 'visits';
    async function load() {
      const ranks = await Promise.all(COMPETITORS.map(d =>
        window.cowork.callMcpTool('mcp__b2421424-145a-4829-8eea-9a34e56b8ade__get-websites-website-rank',
          { domain: d, country: 'ww', start_date: '2026-01-01', end_date: 'latest' })));
      const rows = COMPETITORS.map((d, i) => ({ domain: d, rank: ranks[i]?.data?.[0]?.country_rank ?? null }));
      new gridjs.Grid({ columns: ['Domain', 'Global rank'], data: rows.map(r => [r.domain, r.rank]), sort: true })
        .render(document.getElementById('comp-grid'));
    }
    load().catch(e => { document.body.insertAdjacentHTML('beforeend', `<pre>${e.message}</pre>`); });
  </script>
</body>
</html>
```

The runtime LLM fills in the actual SRI hashes (Cowork provides them in the iframe's CSP `integrity` directives), the real domain list, and the real call chain. The skeleton fixes the page STRUCTURE: head with three SRI-pinned CDN script tags, body with a toolbar + a Chart.js canvas + a Grid.js container, an async `load()` that pulls data via `window.cowork.callMcpTool`, and `localStorage` for user preferences.

## Failure handling

If `mcp__cowork__create_artifact` is unavailable (non-Cowork runtime, or the tool returns an error), emit a one-line note in the markdown `## Caveats` block: "Persistent dashboard skipped: artifact tool unavailable." The markdown answer continues unchanged. NEVER block the markdown delivery on artifact failures.

If the Tier 2 `.jsx` write fails (no `Write` permission on the path, disk error), drop to Tier 1 silently; the recipe's markdown render is identical with or without the panel.

## Hard rules

- Markdown output ALWAYS renders. Tier 2 and Tier 3 are SUPPLEMENTAL.
- NEVER include user-identifying or PII content in artifacts (CLAUDE.md global rule).
- Persistent artifacts MUST self-contain: no external network calls beyond the 3 whitelisted CDNs, no localhost references, no Tailwind CDN.
- Persistent artifacts MUST route all data through `window.cowork.callMcpTool`. `fetch` / `XHR` are blocked by CSP.
- Slug pattern is `sw-<recipe>-<target-slug>-<yyyymm>`. Check existing artifacts via `mcp__cowork__list_artifacts` before creating; prefer `update_artifact` for refreshes.

## What this skill does NOT do

It does not call MCP tools (recipes do that), produce visible markdown (sw-foundation-render plus the recipe own that), or load on non-Cowork platforms. Tier 1 (the universal markdown + Unicode-bar baseline) lives in `sw-foundation-render` section visualizations and ships on every platform without this helper.
