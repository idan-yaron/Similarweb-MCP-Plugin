# § visualizations, chart formats (sw-foundation-render reference)

Render a chart when the data shape benefits from one, ALWAYS paired with the underlying table. Skip trivial 2-point or single-cell data.

**Unicode-first.** Primary target is Claude Code, which does NOT render Mermaid (users see raw `mermaid` code blocks: worse than no chart). Recipes emit Unicode block-character charts BY DEFAULT; Mermaid is an OPTIONAL appendix for renderer-aware callers (Cursor, Claude.ai artifacts). Use the block set `█▉▊▋▌▍▎▏` (full through 1/8); one full block ≈ 2 percentage points; cap at ~16-char width.

**Chart-type selection:**
- Ratios across 3+ categories (channel mix, top brands, market share): Unicode horizontal bars.
- Period-over-period deltas: Unicode bars with `▶`/`◀` caps + verdict label.
- Audience overlap N=2: Unicode asymmetry bars + a Unicode absolute-breakdown bar.
- Concentration / threshold (HHI 0-10000): Unicode bar with marker.
- Time series 3+ points: table only by default.
- Single-value / 2-point: NO chart.

**Channel mix (replaces Mermaid pie).** Group cumulative <15% slices as `(N more)`. Side-by-side per domain.

```
adidas.com (April 2026)
  Organic Search  33.6% ████████████████▏
  Direct          24.3% ███████████▋
  Paid Search     15.4% ███████▍
  Display Ads      9.4% ████▌
  Affiliates       6.6% ███▏
  Mail             4.5% ██▎
  (4 more)         6.7% ███▎
```

**Period-over-period delta bars.** Bar width = `|delta_pct| / 3` capped at 20 chars. Positive: full blocks + `▶`. Negative: `◀` + full blocks. Append verdict per § expert-heuristics.

```
Display Ads    +54.4%  ████████████████████▶  (MAJOR)
Direct         +12.1%  █████▶                 (MATERIAL)
Affiliates      -8.0%  ◀███                   (MATERIAL)
Referrals       -0.4%  ░                      (NOISE)
```

**Audience overlap asymmetry (N=2).**

```
27.7% of adidas visits also go to nike   ███████████████▏░░░░░░░░░░░
13.6% of nike visits also go to adidas   ███████▏░░░░░░░░░░░░░░░░░░░
```

**Audience overlap absolute breakdown (replaces Mermaid sankey, N=2).** Shared slice carries its audience-overlap label per § expert-heuristics.

```
Audience map (US, April 2026, total 30.68M)
  Nike-only     19.57M ████████████████████████████████
  Adidas-only    8.03M █████████████
  Shared         3.08M ████ (10.0% of union, COMPLEMENTARY)
```

**Top-N by share (replaces Mermaid pie for top brands / top sites).** Bar width scales to leader.

```
Top brands by revenue_share (Electronics, amazon.com)
1. Apple     28.6%  ██████████████▎
2. Beats     13.7%  ██████▉
3. Sony       5.7%  ██▉
(top-5 = 56.4% of revenue)
```

**HHI threshold position.**

```
HHI: 1,101  ████░░░░░░░░░░░░░░░░  FRAGMENTED
                                  ↑ 1500 MODERATE
                                  ↑ 2500 CONCENTRATED
```

**Hard rules:** always pair the chart with the underlying table; never visualize trivial single-comparison data; Unicode bars use `█▉▊▋▌▍▎▏` + `▶◀░` only; prefer one chart over many; do NOT default to Mermaid (Claude Code does not render it).

**Mermaid appendix (OPTIONAL).** For Cursor / Claude.ai artifacts: `pie`, `xychart-beta`, `sankey-beta`. Recipes do NOT emit Mermaid by default.
