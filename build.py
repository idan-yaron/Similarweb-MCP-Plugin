#!/usr/bin/env python3
"""
build.py: translator and packager for similarweb-mcp-plugin.

Modes:
  --validate  Structural validation (frontmatter, description cap, file presence). CI-safe.
  --build     Emit five platform bundles plus two companions (codex sub-agents,
              m365 converter input) to dist/.
  --test      Run local tests (requires tests/ directory).
  --ground    Stub: re-grounding is a manual process today (see CONTRIBUTING.md).

Python 3 stdlib only. Runs developer-side. Customers never invoke this.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SKILLS_DIR = REPO_ROOT / "skills"
DIST_DIR = REPO_ROOT / "dist"
PLUGIN_MANIFEST = REPO_ROOT / ".claude-plugin" / "plugin.json"

CLAUDE_AI_DESCRIPTION_CAP = 1024

CANONICAL_FRONTMATTER_ORDER = [
    "name",
    "description",
    "argument-hint",
    "user-invocable",
    "allowed-tools",
]

TEXT_EXTENSIONS = {".sh", ".py", ".md", ".json", ".yml", ".yaml", ".txt", ".toml", ".template", ".html", ".jsx"}
TEXT_FILES = {".gitattributes", "LICENSE", "CONNECTORS.md", "README.md"}

GROUNDED_BODY_HEADER = "## Grounded assertions"

# --- Personal-data / secrets ship-gate ------------------------------------
# Enforced by --validate, which CI runs on every PR and before the release
# workflow attaches any bundle. The automated form of the manual pre-ship scan:
# connector ids, emails, absolute local paths, secrets, the banned commit
# identity, plus any term in the gitignored .pii-blocklist. Matched values are
# redacted in output so a failing (public) CI log never re-leaks them.
PII_SELF_EXCLUDE = {"build.py"}  # the scanner defines the patterns; skip it to avoid self-matches
PII_SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".zip", ".pyc"}
PII_EMAIL_ALLOWLIST = set()  # legitimate shipped emails (none today)
PII_FALLBACK_ROOTS = [
    "skills", "commands", "agents", "hooks", "plugins", ".agents",
    ".claude-plugin", "README.md", "CONNECTORS.md", "CONTRIBUTING.md",
    "docs/install-and-smoke-test.md",
]
PII_PATTERNS = [
    (
        "an account-specific MCP connector id",
        re.compile(r"mcp__[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}__"),
        "Use the mcp__similarweb__ placeholder; the runtime substitutes the live prefix.",
    ),
    (
        "an absolute local filesystem path",
        re.compile(r"(?:[A-Za-z]:\\Users\\|/Users/|/home/)[^\s\"'`)\]]+"),
        "Strip machine-specific paths from shipped files.",
    ),
    (
        "the banned commit identity",
        re.compile(r"buzibully", re.IGNORECASE),
        "The only public identity for this repo is idan-yaron (see feedback_git_author).",
    ),
    (
        "a hardcoded API key or secret",
        re.compile(
            r"(?:api[_-]?key|secret|access[_-]?token|client[_-]?secret|password)"
            r"[\"']?\s*[:=]\s*[\"']?(?!<)[A-Za-z0-9_\-]{16,}",
            re.IGNORECASE,
        ),
        "Use a <placeholder>; never commit a real key or secret value.",
    ),
]
PII_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

CODEX_BRAND_COLOR = "#106DFC"
CODEX_DISPLAY_NAME = "Similarweb"
CODEX_CATEGORY = "Marketing Analytics"
CODEX_WEBSITE_URL = "https://github.com/idan-yaron/similarweb-mcp-plugin"
CODEX_LONG_DESCRIPTION = (
    "Expert co-pilot for the Similarweb MCP server. Seven analyst recipes "
    "(competitive teardown, audience overlap, channel mix, market size, AEO audit, "
    "page mix, keyword opportunity), free-form intent routing, lazy capability "
    "discovery, intent-aware output. Turns the Similarweb MCP from a hundred-plus-tool "
    "flat menu into deterministic multi-tool playbooks."
)
CODEX_DEFAULT_PROMPTS = [
    "Compare nike.com and adidas.com on Similarweb",
    "Break down apple.com traffic channels over the last 90 days",
    "Audit chase.com Answer Engine Optimization posture",
]

CODEX_MARKETPLACE_NAME = "Similarweb"
CODEX_MARKETPLACE_DISPLAY = "Similarweb"

# Per-skill Codex install-card interface. snake_case keys with a SCALAR
# default_prompt is the shape the Codex skill loader honors (camelCase + a list
# default_prompt is silently ignored at the skill layer). Recipes only; the
# router, operators, and foundations get policy-only openai.yaml.
CODEX_SKILL_INTERFACES = {
    "sw-aeo-audit": {
        "display_name": "AEO Audit",
        "short_description": "Answer Engine Optimization posture audit for a domain.",
        "default_prompt": "Audit chase.com Answer Engine Optimization posture",
    },
    "sw-audience-overlap": {
        "display_name": "Audience Overlap",
        "short_description": "Shared-audience analysis between two or more domains.",
        "default_prompt": "Audience overlap for nike.com vs adidas.com",
    },
    "sw-channel-mix": {
        "display_name": "Channel Mix",
        "short_description": "Traffic-channel breakdown with period-over-period deltas.",
        "default_prompt": "Break down apple.com traffic channels over the last 90 days",
    },
    "sw-competitive-teardown": {
        "display_name": "Competitive Teardown",
        "short_description": "Full competitive profile of rank, traffic, channels, audience.",
        "default_prompt": "Compare nike.com vs adidas.com on Similarweb",
    },
    "sw-keyword-opportunity": {
        "display_name": "Keyword Opportunity",
        "short_description": "Keyword-gap analysis between two domains.",
        "default_prompt": "Keyword gaps between notion.so and evernote.com",
    },
    "sw-market-size": {
        "display_name": "Market Size",
        "short_description": "Category market-size and demand estimate.",
        "default_prompt": "Market size for cloud storage software",
    },
    "sw-page-mix": {
        "display_name": "Page Mix",
        "short_description": "Top URLs and leading folders for a domain.",
        "default_prompt": "Top URLs and folders for shopify.com",
    },
}

# Codex per-skill policy.allow_implicit_invocation. Default rule: a skill is
# implicitly invocable unless its SKILL.md sets `user-invocable: false` (pure
# inherited-helper content). The three foundations carry user-invocable: false,
# so they emit allow_implicit_invocation: false and are never auto-selected
# standalone on Codex (which has no slash commands; skills auto-select by
# description). CODEX_FORCE_IMPLICIT overrides to true for background skills that
# SHOULD stay auto-selectable: sw-router is the free-form dispatcher, so it must
# stay implicit for prompts to reach a recipe. CODEX_FORCE_NON_IMPLICIT overrides
# to false for default-invocable skills that should be explicit-only (empty today).
# sw-router is the dispatcher; sw-setup is the capability-probe operator that
# Codex has no slash-command wrapper for, so both must stay auto-selectable by
# intent even though their SKILL.md marks them user-invocable: false for the
# Claude Code command surface.
CODEX_FORCE_IMPLICIT = {"sw-router", "sw-setup"}
CODEX_FORCE_NON_IMPLICIT = set()

# --- M365 Copilot converter-input target ------------------------------------
# emit_m365 stages INPUT for Microsoft's Convert-ClaudePluginToMOS3.ps1 (Copilot
# Cowork), not an installable package. Grounded 2026-07-06 against converter
# SHA-256 335ab2bf7ce02c20ab3900cd122c290cf433097123665c784d84ce786c9726e6:
# tests/grounded/m365-converter-mcp-json-shape, m365-converter-skills-verbatim,
# m365-manifest-shape. The converter reads server entries by bare `url` (DCR is
# live on mcp-auth.similarweb.com, so no auth block belongs here; auth type is
# a converter parameter) and copies skills/ byte-verbatim, so every M365 skill
# transform must happen at emit time.
M365_MCP_SERVERS = {
    "mcpServers": {
        "similarweb": {
            "url": "https://mcp.similarweb.com",
            "description": (
                "Similarweb digital intelligence tools for website traffic, "
                "engagement, keywords, audience, and market analytics."
            ),
        }
    }
}

# Description fragments dropped at M365 emit time. On Microsoft Copilot the word
# "Cowork" reads as Microsoft's product, and the referenced Anthropic-Cowork
# features (deep-dive agent, scheduled grounding, rich-render helper) do not
# exist there. Source skills and the other bundles keep these clauses.
# --validate enforces each fragment still exists verbatim in its source
# description, and emit_m365 hard-fails if any emitted description still
# mentions Cowork after the drops.
M365_DESCRIPTION_DROPS = {
    "sw-competitive-teardown": [
        ", on Cowork when five or more rivals are named "
        "(the competitive deep dive agent handles wide sets)",
    ],
    "sw-config": [
        " Also hosts the opt in Cowork only scheduled grounding sub mode "
        "that re validates fragile MCP assertions on a cadence.",
    ],
    "sw-foundation-render": [
        "; richer rendering ships in a separate Cowork only helper",
    ],
}

M365_ICON_SPECS = (("color.png", 192), ("outline.png", 32))

# The converter copies plugin.json's description verbatim into the M365 app
# manifest description.short/full (tests/grounded/m365-manifest-shape), so the
# rival-platform sentence is dropped from the staged manifest.
M365_MANIFEST_DESCRIPTION_DROPS = [
    " Cross-platform (Claude Code, Codex, Cursor, Claude.ai).",
]


def _m365_transform_description(skill_name, desc):
    """Apply M365_DESCRIPTION_DROPS to one description. Returns (new_desc, stale,
    residual): stale lists fragments that no longer match the source verbatim,
    residual is True when the result still mentions Cowork (case-insensitive).
    Shared by cmd_validate (so violations fail at T0) and emit_m365 (backstop).
    Non-string input (a malformed empty description parses as a list) passes
    through untouched; the frontmatter checks own that failure mode."""
    if not isinstance(desc, str):
        return desc, [], False
    stale = []
    for fragment in M365_DESCRIPTION_DROPS.get(skill_name, ()):
        if fragment in desc:
            desc = desc.replace(fragment, "")
        else:
            stale.append(fragment)
    return desc, stale, "cowork" in desc.lower()


def _codex_allow_implicit(skill_name, skill_fm):
    """Resolve policy.allow_implicit_invocation for one skill's Codex openai.yaml.
    Precedence: explicit FORCE sets win, then the user-invocable frontmatter rule."""
    if skill_name in CODEX_FORCE_NON_IMPLICIT:
        return False
    if skill_name in CODEX_FORCE_IMPLICIT:
        return True
    return str(skill_fm.get("user-invocable", "true")).strip().lower() != "false"


def is_text(path):
    return path.suffix in TEXT_EXTENSIONS or path.name in TEXT_FILES


def parse_grounded_from_body(body):
    """Extract grounded-assertion ids from a `## Grounded assertions` body block.

    The block opens with the header on its own line and contains a markdown
    bulleted list of assertion-ids. Termination: next `##` heading or EOF.
    Returns [] if the header is absent.
    """
    ids = []
    lines = body.split("\n")
    in_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(GROUNDED_BODY_HEADER):
            in_block = True
            continue
        if not in_block:
            continue
        if stripped.startswith("## ") and not stripped.startswith(GROUNDED_BODY_HEADER):
            break
        if stripped.startswith("- "):
            token = stripped[2:].strip()
            if token and " " not in token and "/" not in token:
                ids.append(token)
    return ids


def load_plugin_manifest():
    with open(PLUGIN_MANIFEST, "r", encoding="utf-8") as f:
        return json.load(f)


COWORK_ONLY_SKILLS = {"sw-foundation-render-cowork"}


def list_skills(exclude_cowork_only=False):
    """Return list of (skill_name, skill_md_path) tuples. Cowork-only skills are
    included by default; non-Cowork bundles pass exclude_cowork_only=True."""
    skills = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        if exclude_cowork_only and skill_dir.name in COWORK_ONLY_SKILLS:
            continue
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            skills.append((skill_dir.name, skill_md))
    return skills


def strip_cowork_sections(text):
    """Drop Cowork-only tier sections from a skill body for non-Cowork bundles.
    A Cowork section is any top-level heading that starts with "## Cowork" or carries a
    "(Cowork-only)" tag (recipe Cowork sections, "## Export options (Cowork-only)", and
    sw-config's schedule-grounding step); it runs to the line before the next top-level
    heading (or EOF). Any standalone line carrying a "(Cowork-only)" tag (e.g. a routing
    bullet that references a Cowork-only step) is also dropped. Frontmatter and
    "## Grounded assertions" are not Cowork headings, so they pass through unchanged. Splitting and rejoining on the newline
    character preserves the source line endings (any CR stays attached to its line)."""
    out = []
    skipping = False
    for line in text.split("\n"):
        if line.startswith("## "):
            skipping = line.startswith("## Cowork") or "(Cowork-only)" in line
            if skipping:
                continue
        if skipping:
            continue
        if "(Cowork-only)" in line:
            continue
        out.append(line)
    return "\n".join(out)


CAPMAP_SOURCE_SKILL = "sw-foundation-core"
CAPMAP_CONSUMER_SKILLS = ("sw-setup", "sw-config")


def _skill_shipped_files(name, include_cowork_files):
    """Map skill-relative posix path to source Path for the companion files a skill
    ships beside SKILL.md. Shipping convention: references/*.md and scripts/*.py ship
    to every bundle; references/cowork/* ships only when include_cowork_files is true
    (the Cowork bundle). sw-setup and sw-config additionally receive a build-time copy
    of sw-foundation-core's capmap.py (single source of truth) when it exists; its
    absence is tolerated silently until the script lands."""
    skill_dir = SKILLS_DIR / name
    shipped = {}
    references = skill_dir / "references"
    if references.is_dir():
        for p in sorted(references.glob("*.md")):
            if p.is_file():
                shipped[f"references/{p.name}"] = p
        cowork_dir = references / "cowork"
        if include_cowork_files and cowork_dir.is_dir():
            for p in sorted(cowork_dir.iterdir()):
                if p.is_file():
                    shipped[f"references/cowork/{p.name}"] = p
    scripts = skill_dir / "scripts"
    if scripts.is_dir():
        for p in sorted(scripts.glob("*.py")):
            if p.is_file():
                shipped[f"scripts/{p.name}"] = p
    if name in CAPMAP_CONSUMER_SKILLS:
        capmap_src = SKILLS_DIR / CAPMAP_SOURCE_SKILL / "scripts" / "capmap.py"
        if capmap_src.is_file():
            shipped["scripts/capmap.py"] = capmap_src
    return shipped


def _copy_skills(skills_target, exclude_cowork_only, strip_cowork, include_cowork_files,
                 write_openai_yaml=False):
    """Copy each skill's SKILL.md plus its shipped companion files (see
    _skill_shipped_files) into a bundle's skills dir (already created by the
    caller). Non-Cowork bundles drop the Cowork-only skill, strip Cowork tier
    sections from each body, and pass include_cowork_files=False so
    references/cowork/ stays out. The Cowork bundle copies raw bytes so its
    skills stay byte-identical to source."""
    for name, path in list_skills(exclude_cowork_only=exclude_cowork_only):
        skill_target = skills_target / name
        skill_target.mkdir()
        dest = skill_target / "SKILL.md"
        if strip_cowork:
            with open(path, "r", encoding="utf-8", newline="") as f:
                text = f.read()
            with open(dest, "w", encoding="utf-8", newline="") as f:
                f.write(strip_cowork_sections(text))
        else:
            shutil.copy(path, dest)
        for rel, src in _skill_shipped_files(name, include_cowork_files).items():
            dest_file = skill_target / rel
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dest_file)
        if write_openai_yaml:
            fm, _ = parse_frontmatter(path)
            _write_codex_skill_openai_yaml(skill_target, name, _codex_allow_implicit(name, fm))


def parse_frontmatter(skill_md_path):
    """Return (frontmatter_dict, body_str). Raises ValueError on malformed."""
    text = skill_md_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{skill_md_path}: missing YAML frontmatter opener")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError(f"{skill_md_path}: missing YAML frontmatter closer")
    fm_text = text[4:end]
    body = text[end + 5:]
    fm = {}
    current_key = None
    current_kind = None  # "scalar-fold" | "list"
    for line in fm_text.split("\n"):
        if not line.strip():
            continue
        stripped = line.strip()
        if line[0] not in (" ", "\t") and ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val == ">" or val == "|":
                fm[key] = ""
                current_key = key
                current_kind = "scalar-fold"
            elif val == "":
                fm[key] = []
                current_key = key
                current_kind = "list"
            elif val.startswith("[") and val.endswith("]"):
                items = [x.strip() for x in val[1:-1].split(",") if x.strip()]
                fm[key] = items
                current_key = None
                current_kind = None
            else:
                fm[key] = val
                current_key = None
                current_kind = None
        elif current_kind == "list" and stripped.startswith("- "):
            item = stripped[2:].strip()
            fm[current_key].append(item)
        elif current_kind == "scalar-fold" and line.startswith("  "):
            fm[current_key] = (fm[current_key] + " " + stripped).strip()
    return fm, body


def _load_pii_blocklist():
    """Read the gitignored .pii-blocklist: case-insensitive substring terms, one
    per line, '#' comments. Returns [(line_number, lowercased_term)]; empty if absent."""
    path = REPO_ROOT / ".pii-blocklist"
    if not path.is_file():
        return []
    terms = []
    for idx, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        s = raw.strip()
        if s and not s.startswith("#"):
            terms.append((idx, s.lower()))
    return terms


def _shipped_files():
    """Yield (relpath, Path) for tracked, shippable text files (the public surface).
    Uses `git ls-files`; falls back to a fixed shipped-roots walk when git is
    unavailable. Skips the scanner itself and binary assets."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"], cwd=str(REPO_ROOT),
            capture_output=True, text=True, check=True,
        ).stdout
        names = [n for n in out.split("\0") if n]
    except (OSError, subprocess.CalledProcessError):
        names = []
        for root in PII_FALLBACK_ROOTS:
            rp = REPO_ROOT / root
            if rp.is_file():
                names.append(root)
            elif rp.is_dir():
                names.extend(p.relative_to(REPO_ROOT).as_posix() for p in rp.rglob("*") if p.is_file())
    for name in names:
        if name in PII_SELF_EXCLUDE:
            continue
        p = REPO_ROOT / name
        if p.suffix.lower() in PII_SKIP_SUFFIXES or not p.is_file():
            continue
        yield name, p


def _redact(value, keep=6):
    return value.strip()[:keep] + "***"


def scan_personal_data():
    """Return ERROR strings for personal/account-specific data in shipped files:
    connector ids, emails, absolute local paths, secrets, the banned identity, or
    any .pii-blocklist term. The automated form of the manual pre-ship scan; CI
    runs --validate, so nothing ships unscanned. Matches are redacted in output."""
    errors = []
    blocklist = _load_pii_blocklist()
    for relpath, path in _shipped_files():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, start=1):
            for label, rx, hint in PII_PATTERNS:
                m = rx.search(line)
                if m:
                    errors.append(f"PERSONAL DATA: {relpath}:{i} looks like {label} ('{_redact(m.group(0))}'). {hint}")
            for m in PII_EMAIL_PATTERN.finditer(line):
                if m.group(0).lower() not in PII_EMAIL_ALLOWLIST:
                    errors.append(
                        f"PERSONAL DATA: {relpath}:{i} contains an email address "
                        f"('{_redact(m.group(0))}'). Remove it, or add it to PII_EMAIL_ALLOWLIST if intentional."
                    )
            low = line.lower()
            for idx, term in blocklist:
                if term in low:
                    errors.append(
                        f"PERSONAL DATA: {relpath}:{i} matches .pii-blocklist entry #{idx} "
                        f"(term redacted). Remove the blocklisted term before shipping."
                    )
    return errors


def scan_em_dashes():
    """No-em-dash hard rule: U+2014 may not appear in any shipped file."""
    errors = []
    for relpath, path in _shipped_files():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, start=1):
            if chr(0x2014) in line:
                errors.append(
                    f"EM DASH: {relpath}:{i} contains U+2014; use commas, colons, "
                    f"parentheses, or a sentence break."
                )
    return errors


SKILL_FILE_POINTER_RX = re.compile(r"`((?:references|scripts)/[^`\n]+)`")


def scan_skill_file_pointers():
    """Pointer-integrity and orphan checks for per-skill shipped files.

    Pointer grammar (pinned): a backtick-quoted path starting with references/ or
    scripts/, relative to the skill's own directory. Checked per bundle variant:
    in the raw (Cowork) body every pointer must resolve to a file the Cowork
    bundle ships; in the stripped body every surviving pointer must resolve to a
    file non-Cowork bundles ship, so a references/cowork/ pointer may appear only
    inside sections strip_cowork_sections removes. Inverse check: a file under
    references/ or scripts/ that no pointer in its skill's SKILL.md references is
    an orphan. Exact filename capmap.py is exempt from the orphan check (build-time
    copies; single source in sw-foundation-core)."""
    errors = []
    for name, path in list_skills():
        try:
            _, body = parse_frontmatter(path)
        except ValueError:
            continue  # malformed frontmatter is reported by cmd_validate's main pass
        skill_dir = path.parent
        raw_pointers = SKILL_FILE_POINTER_RX.findall(body)
        shipped_cowork = _skill_shipped_files(name, include_cowork_files=True)
        shipped_noncowork = _skill_shipped_files(name, include_cowork_files=False)
        for ptr in raw_pointers:
            if ptr in shipped_cowork:
                continue
            if (skill_dir / ptr).is_file():
                errors.append(
                    f"{path}: pointer `{ptr}` resolves to a file outside the shipping "
                    f"convention (references/*.md, references/cowork/*, scripts/*.py), "
                    f"so no bundle would carry it. Rename or relocate the file."
                )
            else:
                errors.append(
                    f"{path}: pointer `{ptr}` does not resolve to a file under "
                    f"skills/{name}/. A dangling pointer ships a broken instruction; "
                    f"add the file or fix the path."
                )
        if name not in COWORK_ONLY_SKILLS:
            for ptr in SKILL_FILE_POINTER_RX.findall(strip_cowork_sections(body)):
                if ptr in shipped_noncowork or ptr not in shipped_cowork:
                    continue  # fine, or already reported by the raw pass above
                errors.append(
                    f"{path}: Cowork-only pointer `{ptr}` survives strip_cowork_sections, "
                    f"so non-Cowork bundles would carry a pointer to a file they do not "
                    f"ship. Move it inside a heading starting with '## Cowork' or a line "
                    f"tagged (Cowork-only)."
                )
        pointer_set = set(raw_pointers)
        for sub in ("references", "scripts"):
            sub_dir = skill_dir / sub
            if not sub_dir.is_dir():
                continue
            for f in sorted(sub_dir.rglob("*")):
                if not f.is_file() or f.name == "capmap.py":
                    continue
                rel = f.relative_to(skill_dir).as_posix()
                if rel not in pointer_set:
                    errors.append(
                        f"{path}: {rel} has no backticked pointer in SKILL.md; an "
                        f"orphan file ships dead weight. Reference it as `{rel}` or "
                        f"delete it."
                    )
    return errors


# --- Tool-name drift guard --------------------------------------------------
# The 2026-08 rename wave shipped dead names through five surface types including
# a shell grep pattern and JS strings in an HTML artifact, so the scan reads every
# file type, not just markdown.
TOOL_DRIFT_SCAN_ROOTS = ("skills", "agents", "commands", "hooks", "plugins", ".agents")
TOOL_DRIFT_SCAN_FILES = ("README.md", "CONNECTORS.md", "CONTRIBUTING.md")
TOOL_CATALOG_SNAPSHOT = REPO_ROOT / "tests" / "grounded" / "mcp-tool-catalog-v1.md"
TOOL_CATALOG_SECTIONS = (
    ("current", "### Appendix A: current tool names"),
    ("documented-absent", "### Appendix B: documented-absent tool names"),
    ("retired", "### Appendix C: retired names with successors"),
)
TOOL_CATALOG_ARROW = " -> "

TOOL_NAME_BODY = r"(?:get|post)-[a-z0-9]+(?:-[a-z0-9]+)+"
TOOL_NAME_RX = re.compile(rf"(?<![\w-])({TOOL_NAME_BODY})(?![\w-])")
TOOL_NAME_PREFIXED_RX = re.compile(rf"mcp__[A-Za-z0-9_.\-]+__({TOOL_NAME_BODY})")
TOOL_NAME_FULL_RX = re.compile(rf"{TOOL_NAME_BODY}\Z")


class ToolCatalogError(Exception):
    pass


def _catalog_section_entries(lines, heading_prefix):
    """Return {tool_name: successor_or_None} for the first fenced block following
    the first heading line starting with heading_prefix. Entry grammar: one name
    per line, optionally `retired-name -> successor-name`; `none` as a successor
    means retired outright. Blank and non-tool-shaped lines are tolerated, and an
    empty block is legal (Appendix B empties out when nothing is documented-absent).
    Raises ToolCatalogError when the heading or its fenced block is malformed."""
    for i, line in enumerate(lines):
        if not line.strip().startswith(heading_prefix):
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith("```"):
            if lines[j].strip().startswith("#"):
                raise ToolCatalogError(f"'{heading_prefix}' is not followed by a fenced block")
            j += 1
        if j >= len(lines):
            raise ToolCatalogError(f"'{heading_prefix}' has no fenced block")
        entries = {}
        for raw in lines[j + 1:]:
            if raw.strip().startswith("```"):
                return entries
            name, _, successor = raw.strip().partition(TOOL_CATALOG_ARROW)
            name = name.strip()
            successor = successor.strip()
            if TOOL_NAME_FULL_RX.match(name):
                entries[name] = successor if successor and successor != "none" else None
        raise ToolCatalogError(f"'{heading_prefix}' has an unterminated fenced block")
    raise ToolCatalogError(f"the snapshot has no '{heading_prefix}' heading")


def _load_tool_catalog_snapshot():
    """Return (sections, skip_reason). A MISSING snapshot skips (CI has no tests/);
    a snapshot that exists but will not parse raises, because a broken guard is not
    the same as an absent one and must not pass silently."""
    if not TOOL_CATALOG_SNAPSHOT.is_file():
        return None, "the local catalog snapshot is not present (CI has no tests/)"
    try:
        lines = TOOL_CATALOG_SNAPSHOT.read_text(encoding="utf-8", errors="replace").split("\n")
    except OSError as e:
        raise ToolCatalogError(f"the local catalog snapshot is unreadable ({e})")
    return {key: _catalog_section_entries(lines, heading)
            for key, heading in TOOL_CATALOG_SECTIONS}, None


def _tool_families(sections):
    """First two segments of every known name. A token whose family is unknown is
    prose (`get-started-guide`, `post-mortem-review`), not a mistyped tool."""
    families = set()
    for entries in sections.values():
        for name in entries:
            families.add("-".join(name.split("-")[:2]))
    return families


PAYLOAD_BUDGET_REF = ("skills", "sw-foundation-core", "references", "payload-budget.md")

# Scanned roots. Deliberately NOT the generated mirrors under plugins/ and
# .agents/: they are byte-copies of skills/, so scanning them doubles every
# error and points the author at a file they must never hand-edit. Also not
# hooks/ (shell keyword patterns, no call plans) or README.md (prose).
PAYLOAD_SCAN_ROOTS = ("skills", "agents", "commands")

# A call-plan row is a markdown table row whose FIRST cell is a call number
# (`| 4 |`, `| 5b |`). That is the shape every recipe already uses, and it is
# mechanical: prose that merely mentions a tool is not a call plan, so tool
# inventories, freshness tables and cost tables do not trip the bound check.
CALL_PLAN_ROW_RX = re.compile(r"^\|\s*\d+[a-z]?\s*\|")

# Tokens that count as an explicit bound. `include_shared` and `output_fields`
# qualify because for their tools the bound IS a named parameter decision.
BOUND_TOKENS = ("limit", "metrics", "start_date", "end_date", "window",
                "_id", "output_fields", "include_shared", "granularity")

# Backticked parameter names count as bounds even when the bare word would be
# too common to match on. `domains` is audience-overlap-agg's own bound (2-5
# total); the bare word appears in almost every row, the backticked form does not.
BOUND_PARAM_RX = re.compile(r"`domains`")

# Rows that record a tool as NOT called are not call plans. Without this the
# guard flags the very withdrawals it exists to encourage.
NOT_A_CALL_RX = re.compile(r"withdrawn|not called|never called|no bounded call",
                           re.IGNORECASE)

NEVER_AUTO_INVOKE_PHRASE = "auto-invoke"
PII_PHRASES = ("contact pii", "personal data")


def _load_payload_lists():
    """Return the four authoritative lists from the payload-budget reference.

    Unlike the tool-catalog snapshot (which lives under the gitignored tests/
    and is therefore legitimately absent in CI), this file SHIPS, so absence or
    an unparseable block is a broken guard, never a reason to skip. Hard-error."""
    path = REPO_ROOT.joinpath(*PAYLOAD_BUDGET_REF)
    if not path.exists():
        raise ToolCatalogError(
            f"{'/'.join(PAYLOAD_BUDGET_REF)} is missing; the payload guard reads "
            "its lists from that shipped file, so it cannot run")
    lines = path.read_text(encoding="utf-8").splitlines()
    return {key: set(_catalog_section_entries(lines, f"### List: {key}"))
            for key in ("never-inline", "safe-unbounded",
                        "never-auto-invoke", "pii-contact")}


# Every top-level entry that legitimately ships. A tracked file outside these is
# almost always a stray drop rather than a deliberate addition. Adding a
# genuinely new top-level entry means adding it here too; that friction is the
# point.
ALLOWED_TOP_LEVEL = frozenset({
    ".agents", ".claude-plugin", ".gitattributes", ".github", ".gitignore",
    "CONNECTORS.md", "CONTRIBUTING.md", "LICENSE", "README.md", "SECURITY.md",
    "agents", "assets", "build.py", "commands", "docs", "hooks", "plugins",
    "skills", "tools",
})

# Media and data blobs may only live in an assets directory. Anywhere else they
# are either a stray capture or an export that does not belong in a public repo.
MEDIA_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico",
    ".pdf", ".mp4", ".mov", ".webm", ".zip", ".tar", ".gz",
    ".xlsx", ".xls", ".csv", ".tsv", ".parquet",
)
ALLOWED_MEDIA_PREFIXES = ("assets/", "plugins/similarweb/assets/")


def _tracked_files():
    """Tracked paths per git, or None when git is unavailable.

    Deliberately uses git rather than a filesystem walk: a walk would flag every
    untracked local scratch file, and untracked files are not the hazard. What
    ships is what is TRACKED."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"], cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return [p for p in out.stdout.split("\0") if p]


def scan_repo_hygiene():
    """Fail the build when a tracked file is somewhere it does not belong.

    Two independent checks, either of which alone is sufficient:

    1. Top-level allowlist. A tracked path whose first segment is unknown.
    2. Media placement. A binary or data blob outside an assets directory.

    Returns (errors, warnings). A missing or non-functional git is a SKIP rather
    than a failure, so the guard never blocks a source tarball build."""
    errors, warnings = [], []
    tracked = _tracked_files()
    if tracked is None:
        warnings.append(
            "repo-hygiene guard skipped: could not read the tracked file list "
            "(git unavailable)")
        return errors, warnings

    for path in tracked:
        top = path.split("/", 1)[0]
        if top not in ALLOWED_TOP_LEVEL:
            errors.append(
                f"'{path}' is tracked but '{top}' is not an allowed top-level "
                f"entry. If this is a deliberate addition, add '{top}' to "
                f"ALLOWED_TOP_LEVEL in build.py; if it is a stray file, remove "
                f"it from the index")
            continue
        lower = path.lower()
        if lower.endswith(MEDIA_SUFFIXES) and not path.startswith(ALLOWED_MEDIA_PREFIXES):
            errors.append(
                f"'{path}' is a tracked media or data blob outside an assets "
                f"directory. Move it under assets/, or remove it from the index")
    return errors, warnings


# Recipes are the user-facing playbooks: every skill that is not a foundation,
# an operator, or the router. CODEX_SKILL_INTERFACES is documented "recipes
# only", so the two must agree exactly; that agreement is check 1 below.
NON_RECIPE_SKILLS = {
    "sw-foundation-core", "sw-foundation-data", "sw-foundation-render",
    "sw-foundation-render-cowork", "sw-router", "sw-setup", "sw-config",
}

# "seven recipes", "all 7 recipes", "seven analyst recipes". Deliberately
# requires the PLURAL, so Branch D's "chained 2-recipe plan" (a different
# quantity entirely) is not swept up, and requires the word recipes rather than
# any noun, so README's "seven artifacts" is left alone.
_COUNT_ALT = r"(one|two|three|four|five|six|seven|eight|nine|ten|\d{1,2})"

# Deliberately NARROW: only phrasings that assert the TOTAL number of recipes.
# A broad "<number> recipes" sweep false-fires on every legitimate subset count
# in the tree ("the four recipes whose documented default is us", Branch D's
# "two recipes", Branch B's "2-3 recipes plausibly fit"), and a guard that
# blocks every build gets deleted rather than obeyed. Missing a stray phrasing
# is a cheaper failure than that, so the three forms below are the whole scope.
RECIPE_COUNT_RX = re.compile(
    "|".join([
        rf"\ball\s+{_COUNT_ALT}\s+recipes\b",
        rf"\bnone\s+of\s+the\s+{_COUNT_ALT}\s+recipes\b",
        # The lookbehinds drop ranges ("two or three Similarweb recipes",
        # "two to three"), which name a working subset rather than the total.
        rf"(?<!or )(?<!to )\b{_COUNT_ALT}\s+"
        rf"(?:analyst|user-invocable|deterministic|Similarweb)\s+recipes\b",
    ]),
    re.IGNORECASE,
)
_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                 "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}

RECIPE_COUNT_ROOTS = ("skills", "commands", "agents")
RECIPE_COUNT_EXTRA_FILES = ("README.md",)


def discover_recipes():
    """The recipe skills actually present on disk."""
    if not SKILLS_DIR.is_dir():
        return set()
    return {d.name for d in SKILLS_DIR.iterdir()
            if d.is_dir() and (d / "SKILL.md").is_file()
            and d.name not in NON_RECIPE_SKILLS}


def scan_recipe_count():
    """Cross-check the recipe count against every literal that states it.

    Two failure modes this catches, both of which have to be caught at build
    time because neither surfaces at runtime:

    1. A recipe is added or removed and CODEX_SKILL_INTERFACES is not updated,
       so the Codex install card silently loses (or invents) a recipe.
    2. A recipe is added or removed and the prose still says "seven recipes",
       which then ships as a false statement in a description a user reads.

    Returns (errors, warnings)."""
    errors, warnings = [], []
    recipes = discover_recipes()
    if not recipes:
        return errors, warnings
    n = len(recipes)

    described = set(CODEX_SKILL_INTERFACES)
    for missing in sorted(recipes - described):
        errors.append(
            f"recipe '{missing}' has no CODEX_SKILL_INTERFACES entry; the Codex "
            f"install card would ship without it")
    for extra in sorted(described - recipes):
        errors.append(
            f"CODEX_SKILL_INTERFACES names '{extra}', which is not a recipe skill "
            f"on disk (renamed or removed?)")

    paths = []
    for root in RECIPE_COUNT_ROOTS:
        d = REPO_ROOT / root
        if d.is_dir():
            paths.extend(sorted(d.glob("**/*.md")))
    for name in RECIPE_COUNT_EXTRA_FILES:
        f = REPO_ROOT / name
        if f.is_file():
            paths.append(f)

    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in RECIPE_COUNT_RX.finditer(line):
                # One group per alternation branch; exactly one is populated.
                raw = next((g for g in match.groups() if g), "").lower()
                if not raw:
                    continue
                stated = _NUMBER_WORDS.get(raw)
                if stated is None:
                    try:
                        stated = int(raw)
                    except ValueError:
                        continue
                if stated != n:
                    errors.append(
                        f"{rel}:{lineno} says '{match.group(0).strip()}' but "
                        f"{n} recipe skills exist ({', '.join(sorted(recipes))})")
    return errors, warnings


def scan_payload_budget():
    """Enforce the payload and side-effect rules the foundations state in prose.

    Returns (errors, warnings). Four checks, all keyed on the shipped lists:

    1. A never-inline tool named anywhere must sit in a file that cites the
       payload rule, so the reason it is not called travels with the name.
    2. A tool named in a CALL PLAN row must carry an explicit bound unless it is
       safe-unbounded. Unmeasured tools are in scope by design: the tool that
       caused the original incident had no measurement, so a guard that only
       covered measured tools would have passed it.
    3. A file naming a side-effectful tool must carry the never-auto-invoke rule.
    4. A file naming a contact tool must carry the PII handling rule.
    """
    errors, warnings = [], []
    lists = _load_payload_lists()
    ref_rel = "/".join(PAYLOAD_BUDGET_REF)

    for rel, path in _shipped_files():
        rel = rel.replace("\\", "/")
        if not rel.endswith(".md"):
            continue
        if not any(rel.startswith(r + "/") for r in PAYLOAD_SCAN_ROOTS):
            continue
        # The reference itself names every tool by definition; so does the
        # catalog row that documents a tool's own payload behavior.
        if rel == ref_rel:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        low = text.lower()
        named = set(TOOL_NAME_RX.findall(text))

        for tool in sorted(named & lists["never-inline"]):
            if "payload-budget" not in low:
                errors.append(
                    f"{rel} names never-inline tool '{tool}' without citing "
                    f"§ payload-budget. A reader meeting the name here has no "
                    f"way to learn why it must not be called.")

        for tool in sorted(named & lists["never-auto-invoke"]):
            if NEVER_AUTO_INVOKE_PHRASE not in low:
                errors.append(
                    f"{rel} names side-effectful tool '{tool}' without the "
                    f"never-auto-invoke rule. That prohibition must never "
                    f"travel separately from the tool name.")

        for tool in sorted(named & lists["pii-contact"]):
            if not any(p in low for p in PII_PHRASES):
                errors.append(
                    f"{rel} names contact tool '{tool}' without the PII "
                    f"handling rule stated in the same file.")

        for line in text.splitlines():
            if not CALL_PLAN_ROW_RX.match(line.strip()):
                continue
            if NOT_A_CALL_RX.search(line):
                continue
            row_low = line.lower()
            for tool in sorted(set(TOOL_NAME_RX.findall(line))):
                if tool in lists["safe-unbounded"]:
                    continue
                if any(tok in row_low for tok in BOUND_TOKENS):
                    continue
                if BOUND_PARAM_RX.search(line):
                    continue
                errors.append(
                    f"{rel}: call-plan row for '{tool}' passes no explicit "
                    f"bound. Every tool that accepts one gets one, measured or "
                    f"not; add a limit, metrics list, date window, or id "
                    f"filter, or move it to the safe-unbounded list with a "
                    f"measurement.")
    return errors, warnings


CATALOG_STALE_AFTER_DAYS = 30


def scan_catalog_staleness():
    """WARN when the local tool-catalog snapshot has not been re-enumerated lately.

    Deliberately a warning and deliberately local-only. `tests/` is gitignored,
    so CI checks out no snapshot and this skips by design; and a hard error would
    block a release tag the moment a calendar boundary passed, with no code
    change and nothing a release can do about it.

    It earns its place because the snapshot going stale is not cosmetic: a stale
    snapshot is what let shipped text keep refusing tools that had come back. The
    surface moved four times in three months, so the useful signal is elapsed
    time since the last enumeration, not a diff nobody ran.

    Returns (errors, warnings)."""
    if not TOOL_CATALOG_SNAPSHOT.is_file():
        return [], []
    try:
        text = TOOL_CATALOG_SNAPSHOT.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [], []
    m = re.search(r"^last_validated:\s*(\d{4})-(\d{2})-(\d{2})\s*$", text, re.M)
    if not m:
        return [], ["tool-catalog snapshot has no parseable last_validated date"]
    validated = datetime.date(*(int(g) for g in m.groups()))
    age = (datetime.date.today() - validated).days
    if age <= CATALOG_STALE_AFTER_DAYS:
        return [], []
    return [], [
        f"tool-catalog snapshot last enumerated {age} days ago ({validated}), over "
        f"the {CATALOG_STALE_AFTER_DAYS}-day mark. Re-enumerate the live tool list "
        f"and diff it against Appendix A: names ADDED since the snapshot are the "
        f"case that silently makes shipped guidance wrong."
    ]


# Fixed assertion markers: each states absence as a property of the TOOL rather
# than of one account at one moment. Matched case-insensitively as substrings.
# Deliberately NOT keyed on absence language near a tool name: 27 lines under
# skills/ pair the two and only 3 were ever the harmful kind, so adjacency would
# be almost entirely false positives and would flag the correct exemplars.
ABSENCE_ASSERTION_MARKERS = (
    "do not plan a call",
    "no live tool behind it",
    "is not restored",
    "not on the live surface",
    "only apps tool on the live surface",
)

# Runtime-conditional phrasings. These describe what to do IF a tool turns out to
# be absent, which is the doctrine working, and must never trip the guard. Pinned
# as negative cases in tests/build-guards so the guard's narrowness is enforced
# rather than assumed.
ABSENCE_EXEMPT_PHRASES = (
    "absent or denied",
    "if absent",
    "when absent",
    "pinned absence outcomes",
    "presence varies by account",
    "may be absent",
    "is absent from the live list",
)


def scan_absence_assertions():
    """Fail on shipped text that asserts a tool is absent as a property of the tool.

    Presence is an account-and-moment fact, resolved from the live tool list at
    planning time. Writing it into a shipped file converts one connector's
    enumeration into a permanent claim about every connector, and the file then
    keeps refusing a tool long after the tool comes back.

    That is not hypothetical. Shipped text once carried a literal `Do NOT plan a
    call` on six apps tools; all six later returned HTTP 200 on the reference
    connector, so the plugin was refusing tools that worked. The names had been
    absent across two consecutive enumerations, which felt like enough evidence
    and was not: a third enumeration found every one of them present.

    The guard keys ONLY on fixed assertion markers, never on absence language
    near a tool name. Runtime-conditional phrasing is the doctrine working and is
    explicitly exempt. Returns (errors, warnings)."""
    errors, warnings = [], []
    for rel, path in _shipped_files():
        rel = rel.replace("\\", "/")
        if not rel.endswith(".md"):
            continue
        if not any(rel.startswith(r + "/") for r in PAYLOAD_SCAN_ROOTS):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            if any(ex in low for ex in ABSENCE_EXEMPT_PHRASES):
                continue
            for marker in ABSENCE_ASSERTION_MARKERS:
                if marker in low:
                    errors.append(
                        f"{rel}:{lineno} states absence as a property of the tool "
                        f"({marker!r}). Presence is per-account and per-moment: "
                        f"resolve it from the live tool list and render Pattern 7 "
                        f"when a qualifying list omits the name. Phrase it as "
                        f"'presence varies by account', not as a fact.")
            if low.lstrip().startswith("#") and "documented-absent" in low:
                errors.append(
                    f"{rel}:{lineno} ships a documented-absent section heading. A "
                    f"standing list of absent tools is a claim about every "
                    f"connector; record absence in the capability map at runtime "
                    f"instead.")
    return errors, warnings


def scan_tool_name_drift():
    """Validate every tool-name-shaped token under the shipped dirs against the
    local catalog snapshot. Returns (errors, warnings, notice).

    ERROR only on a token in no section: a typo or an invented name. WARN on a
    documented-absent or retired name and let a human decide. The asymmetry is
    load-bearing: the surface drifts per account and per release (90 tools on
    2026-05-16, 80 on 2026-06-11, 113 on 2026-08-06, 129 on 2026-08-10, same
    connector), so one account's enumeration is not proof a name is gone. Names
    absent across two consecutive enumerations came back on the third, which is
    the case that settles it. Erroring on absence would enforce at build time
    exactly the inference the runtime presence-first doctrine forbids.
    """
    try:
        sections, skip_reason = _load_tool_catalog_snapshot()
    except ToolCatalogError as e:
        return [f"TOOL DRIFT: the catalog snapshot is present but unusable: {e}. "
                f"Fix {TOOL_CATALOG_SNAPSHOT.name} or delete it to skip the check."], [], None
    if sections is None:
        return [], [], f"NOTICE: tool-name drift check skipped; {skip_reason}."
    families = _tool_families(sections)
    errors = []
    warnings = []
    paths = []
    for root in TOOL_DRIFT_SCAN_ROOTS:
        base = REPO_ROOT / root
        if base.is_dir():
            paths.extend(sorted(base.rglob("*")))
    paths.extend(REPO_ROOT / name for name in TOOL_DRIFT_SCAN_FILES)
    for path in paths:
        if not path.is_file() or path.suffix.lower() in PII_SKIP_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        relpath = path.relative_to(REPO_ROOT).as_posix()
        seen = {}
        for i, line in enumerate(text.split("\n"), start=1):
            for rx in (TOOL_NAME_RX, TOOL_NAME_PREFIXED_RX):
                for m in rx.finditer(line):
                    seen.setdefault(m.group(1), i)
        for token, first_line in sorted(seen.items(), key=lambda kv: (kv[1], kv[0])):
            if token in sections["current"]:
                continue
            if token in sections["documented-absent"]:
                warnings.append(
                    f"{relpath}:{first_line} references '{token}', absent from the "
                    f"latest live enumeration but deliberately documented. Keep it "
                    f"only inside an explicit absent-tool annotation."
                )
            elif token in sections["retired"]:
                successor = sections["retired"][token]
                replacement = f"renamed to '{successor}'" if successor else "retired with no successor"
                warnings.append(
                    f"{relpath}:{first_line} references retired tool '{token}' "
                    f"({replacement}). Legitimate only inside a history or "
                    f"name-map note; anywhere else it is a missed rename."
                )
            elif "-".join(token.split("-")[:2]) in families:
                errors.append(
                    f"TOOL DRIFT: {relpath}:{first_line} references '{token}', which "
                    f"appears in no section of {TOOL_CATALOG_SNAPSHOT.name} (not "
                    f"current, not documented-absent, not retired). A name in a known "
                    f"tool family that the catalog has never recorded is a typo or a "
                    f"guess; fix the name, or re-enumerate the live surface and update "
                    f"the snapshot."
                )
    return errors, warnings, None


def cmd_validate():
    """Frontmatter present, descriptions under Claude.ai cap, file presence per target,
    grounding citations resolve, pointer integrity for per-skill shipped files,
    fragility-aware dependency check.

    Fragility-classifier rules (ledger schema v2):
    - validated:      passes silently.
    - fragile:        warning (does not block).
    - pending_manual: error if the dep is NEW or unacknowledged; warning if the
                      assertion has an explicit `acknowledged: true` flag in the
                      ledger (pre-existing operator-required probes for
                      auth-invalid / partial-access envelopes; recipes already
                      handle them as graceful-degradation cases).
    """
    errors = []
    warnings = []
    skills = list_skills()
    if not skills:
        errors.append("no skills found under skills/")
    for name, path in skills:
        try:
            fm, _ = parse_frontmatter(path)
        except ValueError as e:
            errors.append(str(e))
            continue
        required = ["name", "description"]
        for key in required:
            if key not in fm:
                errors.append(f"{path}: missing required frontmatter key '{key}'")
        desc = fm.get("description", "")
        if len(desc) > CLAUDE_AI_DESCRIPTION_CAP:
            errors.append(
                f"{path}: description is {len(desc)} chars; Claude.ai cap is {CLAUDE_AI_DESCRIPTION_CAP}"
            )
        forbidden = []
        for pat in ("<", ">", "[", "]", "--", "..."):
            if pat in desc:
                forbidden.append(pat)
        if forbidden:
            errors.append(
                f"{path}: description contains CLI-flag-shaped pattern(s) {forbidden}. "
                f"Cowork's validator silently rejects skills with <>, [], --, or ... in "
                f"the description (bisect-confirmed 2026-05-19). Rewrite as plain prose. "
                f"CLI flag syntax belongs in commands/<name>.md `argument-hint`, not in "
                f"skill descriptions."
            )
        if ": " in desc:
            errors.append(
                f"{path}: description contains a colon followed by a space; strict YAML "
                f"parsers (PyYAML, js-yaml, and Codex's loader) reject plain scalars "
                f"containing ': ' with 'mapping values are not allowed here', so the skill "
                f"silently fails to load on Codex. Reword without the colon (e.g. 'such as')."
            )
        if " #" in desc:
            errors.append(
                f"{path}: description contains a space followed by '#'; strict YAML parsers "
                f"treat ' #' in a plain scalar as a comment and silently truncate the value. "
                f"Reword without the '#'."
            )
    if not PLUGIN_MANIFEST.exists():
        errors.append(f"missing {PLUGIN_MANIFEST}")

    ledger_path = REPO_ROOT / "tests" / "grounding-ledger.json"
    if ledger_path.exists():
        with open(ledger_path, "r", encoding="utf-8") as f:
            ledger = json.load(f)
        assertions = ledger.get("assertions", {})
        valid_assertions = set(assertions.keys())
        for name, path in skills:
            try:
                fm, body = parse_frontmatter(path)
            except ValueError:
                continue
            if "depends_on" in fm:
                errors.append(
                    f"{path}: 'depends_on' is in YAML frontmatter; Cowork rejects "
                    f"non-canonical fields. Move it to a body block headed "
                    f"`{GROUNDED_BODY_HEADER}` followed by a bulleted list of ids."
                )
                continue
            deps = parse_grounded_from_body(body)
            for dep in deps:
                if dep not in valid_assertions:
                    errors.append(
                        f"{path}: depends_on references '{dep}' which is not in "
                        f"tests/grounding-ledger.json"
                    )
                    continue
                a = assertions[dep]
                fragility = a.get("fragility")
                n_obs = a.get("n_observations", "?")
                acknowledged = bool(a.get("acknowledged"))
                if fragility == "pending_manual":
                    if acknowledged:
                        warnings.append(
                            f"{name} depends on '{dep}' (fragility: pending_manual "
                            f"[acknowledged operator-required gap], n_observations: {n_obs})"
                        )
                    else:
                        errors.append(
                            f"{name} depends on '{dep}' (fragility: pending_manual, "
                            f"n_observations: {n_obs}); cannot ship until upgraded "
                            f"or marked acknowledged: true in the ledger"
                        )
                elif fragility == "fragile":
                    warnings.append(
                        f"{name} depends on '{dep}' (fragility: fragile, "
                        f"n_observations: {n_obs})"
                    )

    commands_dir = REPO_ROOT / "commands"
    if commands_dir.is_dir():
        for cmd_md in sorted(commands_dir.glob("*.md")):
            try:
                cmd_fm, _ = parse_frontmatter(cmd_md)
            except ValueError as e:
                errors.append(f"{cmd_md}: command frontmatter malformed: {e}")
                continue
            if "description" not in cmd_fm:
                errors.append(f"{cmd_md}: command missing required frontmatter key 'description'")

    agents_dir = REPO_ROOT / "agents"
    if agents_dir.is_dir():
        for agent_md in sorted(agents_dir.glob("*.md")):
            try:
                agent_fm, _ = parse_frontmatter(agent_md)
            except ValueError as e:
                errors.append(f"{agent_md}: agent frontmatter malformed: {e}")
                continue
            for key in ("name", "description"):
                if key not in agent_fm:
                    errors.append(
                        f"{agent_md}: agent missing required frontmatter key '{key}'. "
                        f"Codex sub-agent emit needs both fields."
                    )

    for cname, cval in [
        ("CODEX_BRAND_COLOR", CODEX_BRAND_COLOR),
        ("CODEX_DISPLAY_NAME", CODEX_DISPLAY_NAME),
        ("CODEX_CATEGORY", CODEX_CATEGORY),
        ("CODEX_LONG_DESCRIPTION", CODEX_LONG_DESCRIPTION),
    ]:
        if not isinstance(cval, str) or not cval.strip():
            errors.append(f"Codex build constant {cname} must be a non-empty string")
    if not CODEX_DEFAULT_PROMPTS or not all(isinstance(p, str) and p.strip() for p in CODEX_DEFAULT_PROMPTS):
        errors.append("CODEX_DEFAULT_PROMPTS must be a non-empty list of non-empty strings")

    manifest_version = load_plugin_manifest().get("version", "")
    foundation_path = SKILLS_DIR / "sw-foundation-render" / "SKILL.md"
    if foundation_path.exists():
        foundation_body = foundation_path.read_text(encoding="utf-8")
        json_version_literal = f'"version": "{manifest_version}"'
        if json_version_literal not in foundation_body:
            errors.append(
                f"sw-foundation-render/SKILL.md does not contain the literal "
                f"`{json_version_literal}` matching plugin.json version. "
                f"Handoff JSON schema drift; update sw-foundation-render § handoff-json-schema."
            )

    manifest_at = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
    plugin_at = REPO_ROOT / "plugins" / "similarweb" / ".codex-plugin" / "plugin.json"
    if manifest_at.is_file() or plugin_at.is_file():
        if not manifest_at.is_file():
            errors.append(
                f"{REPO_ROOT}: plugins/similarweb is present but the marketplace "
                f"manifest is missing at .agents/plugins/marketplace.json. Codex "
                f"Desktop UI Add-marketplace dialog and the codex CLI both reject "
                f"this with `marketplace root does not contain a supported manifest`. "
                f"Re-run build.py --build."
            )
        elif not plugin_at.is_file():
            errors.append(
                f"{REPO_ROOT}: marketplace manifest present at .agents/plugins/ but "
                f"plugin payload missing at plugins/similarweb/.codex-plugin/plugin.json. "
                f"Layout drift in emit_codex."
            )

    if plugin_at.is_file():
        codex_manifest = json.loads(plugin_at.read_text(encoding="utf-8"))
        if "hooks" in codex_manifest:
            errors.append(
                f"{plugin_at}: Codex plugin manifest carries a 'hooks' key. The Codex "
                f"bundle ships NO hooks as of v0.1.10 (hooks are Cowork-only); emit_codex "
                f"must not set it. See the Codex-hooks note in CLAUDE.md."
            )
        if (plugin_at.parent.parent / "hooks").exists():
            errors.append(
                f"{plugin_at.parent.parent / 'hooks'}: the Codex bundle must not contain a "
                f"hooks/ directory (Codex hooks dropped in v0.1.10; hooks are Cowork-only). "
                f"Re-run build.py --build."
            )
        skills_mirror = plugin_at.parent.parent / "skills"
        for cw in COWORK_ONLY_SKILLS:
            if (skills_mirror / cw).exists():
                errors.append(
                    f"{skills_mirror / cw}: Cowork-only skill must not ship in the Codex "
                    f"bundle (v0.1.11; it is Cowork-only, filtered by emit_codex). "
                    f"Re-run build.py --build."
                )
        for mirror_tree in (REPO_ROOT / ".agents", REPO_ROOT / "plugins"):
            if not mirror_tree.is_dir():
                continue
            for mf in sorted(mirror_tree.rglob("*")):
                if not mf.is_file():
                    continue
                parts = mf.relative_to(mirror_tree).parts
                if any(parts[i] == "references" and parts[i + 1] == "cowork"
                       for i in range(len(parts) - 1)):
                    errors.append(
                        f"{mf}: references/cowork/ content must not ship in the Codex "
                        f"bundle (Cowork-only files; the per-bundle copy filter excludes "
                        f"them). Re-run build.py --build."
                    )
                    continue
                if mf.suffix.lower() in PII_SKIP_SUFFIXES:
                    continue
                offenders = [
                    ln.strip()[:70]
                    for ln in mf.read_text(encoding="utf-8", errors="replace").split("\n")
                    if ln.startswith("## Cowork") or "(Cowork-only)" in ln or "mcp__cowork__" in ln
                ]
                if offenders:
                    errors.append(
                        f"{mf}: Codex bundle still carries Cowork-tier content (v0.1.11 "
                        f"strips it from non-Cowork bundles): {offenders[:3]}. "
                        f"strip_cowork_sections or the copy filter missed it; re-run "
                        f"build.py --build."
                    )

        # Per-skill Codex openai.yaml must use the snake_case shape the skill
        # loader honors, and the three foundations must be non-implicit so Codex
        # never auto-selects a pure inherited helper standalone.
        skills_mirror = plugin_at.parent.parent / "skills"
        codex_foundations = {"sw-foundation-core", "sw-foundation-data", "sw-foundation-render"}
        if skills_mirror.is_dir():
            for sk in sorted(skills_mirror.iterdir()):
                if not sk.is_dir():
                    continue
                oy = sk / "agents" / "openai.yaml"
                if not oy.is_file():
                    errors.append(
                        f"{oy}: missing per-skill Codex openai.yaml. Re-run build.py --build."
                    )
                    continue
                txt = oy.read_text(encoding="utf-8")
                for bad in ("displayName", "defaultPrompt", "shortDescription", "brandColor"):
                    if bad in txt:
                        errors.append(
                            f"{oy}: camelCase key '{bad}' present. The Codex skill loader honors "
                            f"snake_case (display_name, default_prompt, short_description); fix "
                            f"_write_codex_skill_openai_yaml and re-run build.py --build."
                        )
                if "allow_implicit_invocation:" not in txt:
                    errors.append(
                        f"{oy}: missing policy.allow_implicit_invocation. Re-run build.py --build."
                    )
                if re.search(r"default_prompt:\s*\n\s*-\s", txt):
                    errors.append(
                        f"{oy}: default_prompt is a list; the Codex skill loader expects a scalar string."
                    )
                if sk.name in codex_foundations and "allow_implicit_invocation: false" not in txt:
                    errors.append(
                        f"{oy}: foundation skill must emit allow_implicit_invocation: false "
                        f"(pure inherited helper, never auto-selected standalone on Codex)."
                    )

    cc_marketplace = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    if not cc_marketplace.is_file():
        errors.append(
            ".claude-plugin/marketplace.json is missing. The Claude Code "
            "'/plugin marketplace add <git-url>' install path documented in the "
            "README requires it at repo root."
        )
    else:
        try:
            mp = json.loads(cc_marketplace.read_text(encoding="utf-8"))
            entries = mp.get("plugins", [])
            entry = entries[0] if entries else {}
            if entry.get("name") != load_plugin_manifest().get("name"):
                errors.append(
                    ".claude-plugin/marketplace.json plugins[0].name does not match "
                    "plugin.json name"
                )
            if entry.get("version") != manifest_version:
                errors.append(
                    f".claude-plugin/marketplace.json plugins[0].version "
                    f"({entry.get('version')}) != plugin.json version ({manifest_version}); "
                    f"bump both on release"
                )
        except (json.JSONDecodeError, OSError) as e:
            errors.append(f".claude-plugin/marketplace.json unreadable or invalid JSON: {e}")

    # M365 converter-input target: committed icons and drop-table integrity.
    # Icon dimensions are read from the PNG IHDR chunk (the converter itself
    # never validates them; 192/32 are the platform expectations, see
    # tests/grounded/m365-manifest-shape).
    for icon_name, expected in M365_ICON_SPECS:
        icon_path = REPO_ROOT / "assets" / "m365" / icon_name
        if not icon_path.is_file():
            errors.append(f"assets/m365/{icon_name}: missing (emit_m365 stages it at the tree root)")
            continue
        data = icon_path.read_bytes()
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            errors.append(f"assets/m365/{icon_name}: not a valid PNG (or IHDR is not the first chunk)")
            continue
        w, h = struct.unpack(">II", data[16:24])
        if (w, h) != (expected, expected):
            errors.append(
                f"assets/m365/{icon_name}: {w}x{h}; M365 expects {expected}x{expected}"
            )
    known_skills = {s for s, _ in skills}
    for m365_skill in sorted(M365_DESCRIPTION_DROPS):
        if m365_skill not in known_skills:
            errors.append(f"M365_DESCRIPTION_DROPS names missing skill '{m365_skill}'")
    manifest_desc = load_plugin_manifest().get("description", "")
    for fragment in M365_MANIFEST_DESCRIPTION_DROPS:
        if fragment not in manifest_desc:
            errors.append(
                f"plugin.json: M365_MANIFEST_DESCRIPTION_DROPS fragment no longer matches "
                f"the description verbatim; update the drop list in build.py so emit_m365 "
                f"keeps the M365 manifest description clean. Fragment: {fragment!r}"
            )
    for m365_skill, m365_path in list_skills(exclude_cowork_only=True):
        try:
            fm, _ = parse_frontmatter(m365_path)
        except ValueError:
            continue
        _, stale, residual = _m365_transform_description(m365_skill, fm.get("description", ""))
        for fragment in stale:
            errors.append(
                f"{m365_path}: M365_DESCRIPTION_DROPS fragment no longer matches the "
                f"description verbatim; update the drop table in build.py so emit_m365 "
                f"does not ship a stale Cowork clause. Fragment: {fragment!r}"
            )
        if residual:
            errors.append(
                f"{m365_path}: description still mentions Cowork after M365_DESCRIPTION_DROPS; "
                f"on Microsoft Copilot that word reads as Microsoft's product. Extend the "
                f"drop table in build.py (emit_m365 would hard-fail on this at build time)."
            )

    errors.extend(scan_personal_data())
    errors.extend(scan_em_dashes())
    errors.extend(scan_skill_file_pointers())

    drift_errors, drift_warnings, drift_notice = scan_tool_name_drift()
    errors.extend(drift_errors)
    warnings.extend(drift_warnings)
    if drift_notice:
        print(drift_notice)

    try:
        payload_errors, payload_warnings = scan_payload_budget()
        errors.extend(payload_errors)
        warnings.extend(payload_warnings)
        count_errors, count_warnings = scan_recipe_count()
        errors.extend(count_errors)
        warnings.extend(count_warnings)
        hygiene_errors, hygiene_warnings = scan_repo_hygiene()
        errors.extend(hygiene_errors)
        warnings.extend(hygiene_warnings)
        absence_errors, absence_warnings = scan_absence_assertions()
        errors.extend(absence_errors)
        warnings.extend(absence_warnings)
        stale_errors, stale_warnings = scan_catalog_staleness()
        errors.extend(stale_errors)
        warnings.extend(stale_warnings)
    except ToolCatalogError as exc:
        # The lists ship, unlike the tool-catalog snapshot, so a missing or
        # unparseable block is a broken guard rather than a CI-shaped absence.
        errors.append(f"payload guard could not run: {exc}")

    if errors:
        for e in errors:
            print(f"VALIDATION ERROR: {e}", file=sys.stderr)
        if warnings:
            print("WARNINGS:", file=sys.stderr)
            for w in warnings:
                print(f"  - {w}", file=sys.stderr)
        return 1
    print(f"OK: validated {len(skills)} skills, manifest.")
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
    return 0


def _prepare_target_dir(target_dir):
    """Wipe and recreate the per-platform staging directory."""
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True)


def _zip_target_dir(target_dir, zip_path):
    """Write target_dir tree into zip_path, paths relative to target_dir.
    Text files are normalized to LF endings at zip-time. The Cowork VM is
    Linux and CRLF in YAML folded scalars (description: >) breaks the parser
    on plugin install. All other platforms accept LF too, so this is uniformly
    safe."""
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(target_dir):
            for fn in files:
                fp = Path(root) / fn
                arc = fp.relative_to(target_dir).as_posix()
                if is_text(fp):
                    content = fp.read_bytes().replace(b"\r\n", b"\n")
                    zf.writestr(arc, content)
                else:
                    zf.write(fp, arc)


def cmd_build():
    """Emit five per-platform bundles to dist/. Cowork-native ships the full
    surface (skills + agents + hooks + connectors); the other four are
    skills-only subsets. Companions (codex sub-agents, m365 converter input)
    are built but never release-attached."""
    manifest = load_plugin_manifest()
    version = manifest["version"]
    DIST_DIR.mkdir(exist_ok=True)
    emit_cowork(manifest, version)
    emit_claude_code(manifest, version)
    emit_codex(manifest, version)
    emit_codex_subagents(manifest, version)
    emit_cursor(manifest, version)
    emit_claude_ai(manifest, version)
    emit_m365(manifest, version)
    print(f"OK: built five platform bundles plus codex sub-agents and m365 "
          f"converter-input companions in {DIST_DIR}")
    return 0


def emit_cowork(manifest, version):
    """cowork: flagship Cowork-native bundle. Ships commands + skills + agents +
    hooks + CONNECTORS.md alongside the canonical plugin.json. Cowork runs a
    Linux VM so all text files are normalized to LF at zip-time via
    _zip_target_dir. Missing optional surfaces are skipped cleanly so partial
    builds work end-to-end."""
    target_dir = DIST_DIR / "cowork"
    _prepare_target_dir(target_dir)
    (target_dir / ".claude-plugin").mkdir()
    with open(target_dir / ".claude-plugin" / "plugin.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    skills_target = target_dir / "skills"
    skills_target.mkdir()
    _copy_skills(skills_target, exclude_cowork_only=False, strip_cowork=False,
                 include_cowork_files=True)
    commands_src = REPO_ROOT / "commands"
    if commands_src.is_dir():
        shutil.copytree(commands_src, target_dir / "commands")
    agents_src = REPO_ROOT / "agents"
    if agents_src.is_dir():
        shutil.copytree(agents_src, target_dir / "agents")
    hooks_src = REPO_ROOT / "hooks"
    if hooks_src.is_dir():
        shutil.copytree(hooks_src, target_dir / "hooks")
    connectors_src = REPO_ROOT / "CONNECTORS.md"
    if connectors_src.is_file():
        shutil.copy(connectors_src, target_dir / "CONNECTORS.md")
    readme_src = REPO_ROOT / "README.md"
    if readme_src.is_file():
        shutil.copy(readme_src, target_dir / "README.md")
    zip_path = DIST_DIR / f"similarweb-cowork-{version}.zip"
    _zip_target_dir(target_dir, zip_path)
    print(f"  cowork: {zip_path}")


def emit_claude_code(manifest, version):
    """claude-code: copy skills + commands + plugin.json. MCP server is configured
    separately by the user."""
    target_dir = DIST_DIR / "claude-code"
    _prepare_target_dir(target_dir)
    (target_dir / ".claude-plugin").mkdir()
    with open(target_dir / ".claude-plugin" / "plugin.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    skills_target = target_dir / "skills"
    skills_target.mkdir()
    _copy_skills(skills_target, exclude_cowork_only=True, strip_cowork=True,
                 include_cowork_files=False)
    commands_src = REPO_ROOT / "commands"
    if commands_src.is_dir():
        shutil.copytree(commands_src, target_dir / "commands")
    zip_path = DIST_DIR / f"similarweb-claude-code-{version}.zip"
    _zip_target_dir(target_dir, zip_path)
    print(f"  claude-code: {zip_path}")


def emit_codex(manifest, version):
    """codex: spec-compliant Codex marketplace bundle per developers.openai.com/codex/plugins/build.

    The bundle is shaped as a Codex MARKETPLACE, not a single plugin directory: the
    marketplace manifest lives at .agents/plugins/marketplace.json, the plugin itself
    lives under plugins/<plugin-name>/. That is the layout `codex plugin marketplace add`
    expects (verified live 2026-05-27 against codex-cli 0.133.0-alpha.1; the
    openai-bundled, openai-primary-runtime, and openai-curated marketplaces all use it).

    Plugin payload: .codex-plugin/plugin.json with the full interface block, per-skill
    SKILL.md plus agents/openai.yaml (recipes get displayName + defaultPrompt; operators,
    router, and foundations get policy-only), and .mcp.json.template with the standard
    {mcpServers: ...} wrapper. The optional
    assets/codex-icon.png at repo root, when present, is embedded as the install-card
    composerIcon and logo (Codex-only; not rendered in the README).

    The Similarweb MCP server is configured separately by the user; .mcp.json.template
    documents the shape without auto-spawning.

    Output: built in a gitignored staging directory under dist/codex/, then
    mirrored into REPO_ROOT/.agents/plugins/ + REPO_ROOT/plugins/similarweb/ so
    the Codex Desktop UI Add-marketplace dialog can fetch the marketplace tree
    directly from GitHub via Source + (blank) Sparse-paths. Codex's manifest
    loader looks at the staging ROOT for `.agents/plugins/marketplace.json`, so
    the marketplace files have to live at the cloned-repo root, not under a
    subdirectory (sparse-paths is a fetch filter only, not a root-redirector;
    verified live 2026-05-28 by inspecting the .git/info/sparse-checkout file
    Codex wrote during a UI add attempt). The zipped artifact lands under dist/
    for Releases.
    """
    target_dir = DIST_DIR / "codex"
    _prepare_target_dir(target_dir)
    plugin_name = manifest["name"]

    marketplace_dir = target_dir / ".agents" / "plugins"
    marketplace_dir.mkdir(parents=True)
    marketplace = {
        "name": CODEX_MARKETPLACE_NAME,
        "interface": {"displayName": CODEX_MARKETPLACE_DISPLAY},
        "plugins": [
            {
                "name": plugin_name,
                "source": {"source": "local", "path": f"./plugins/{plugin_name}"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": CODEX_CATEGORY,
            }
        ],
    }
    with open(marketplace_dir / "marketplace.json", "w", encoding="utf-8") as f:
        json.dump(marketplace, f, indent=2)

    plugin_root = target_dir / "plugins" / plugin_name
    plugin_root.mkdir(parents=True)

    (plugin_root / ".codex-plugin").mkdir()
    codex_manifest = {
        "name": plugin_name,
        "version": version,
        "description": manifest["description"],
        "author": manifest["author"],
        "license": manifest.get("license", "MIT"),
        "keywords": manifest.get("keywords", []),
        "skills": "./skills/",
        "interface": {
            "displayName": CODEX_DISPLAY_NAME,
            "shortDescription": manifest["description"],
            "longDescription": CODEX_LONG_DESCRIPTION,
            "developerName": manifest["author"]["name"],
            "category": CODEX_CATEGORY,
            "capabilities": ["Read", "Write", "Bash"],
            "websiteURL": CODEX_WEBSITE_URL,
            "brandColor": CODEX_BRAND_COLOR,
            "defaultPrompt": CODEX_DEFAULT_PROMPTS,
        },
    }
    icon_src = REPO_ROOT / "assets" / "codex-icon.png"
    if icon_src.is_file():
        codex_manifest["interface"]["composerIcon"] = "./assets/logo.png"
        codex_manifest["interface"]["logo"] = "./assets/logo.png"
    with open(plugin_root / ".codex-plugin" / "plugin.json", "w", encoding="utf-8") as f:
        json.dump(codex_manifest, f, indent=2)

    if icon_src.is_file():
        assets_target = plugin_root / "assets"
        assets_target.mkdir()
        shutil.copy(icon_src, assets_target / "logo.png")

    skills_target = plugin_root / "skills"
    skills_target.mkdir()
    _copy_skills(skills_target, exclude_cowork_only=True, strip_cowork=True,
                 include_cowork_files=False, write_openai_yaml=True)

    mcp_template = {
        "mcpServers": {
            "similarweb": {
                "command": "<your-similarweb-mcp-command>",
                "args": ["--stdio"],
                "env": {
                    "SIMILARWEB_API_KEY": "<your-similarweb-api-key>"
                }
            }
        }
    }
    with open(plugin_root / ".mcp.json.template", "w", encoding="utf-8") as f:
        json.dump(mcp_template, f, indent=2)

    _wipe_codex_marketplace_dirs(REPO_ROOT)
    shutil.copytree(target_dir / ".agents", REPO_ROOT / ".agents")
    shutil.copytree(target_dir / "plugins", REPO_ROOT / "plugins")

    zip_path = DIST_DIR / f"similarweb-codex-{version}.zip"
    _zip_target_dir(target_dir, zip_path)
    print(f"  codex: {zip_path}")


def _wipe_codex_marketplace_dirs(root):
    """Selectively wipe the Codex marketplace mirror dirs at repo root
    (.agents/ and plugins/) before re-copying from the staging build. Never
    use _prepare_target_dir on REPO_ROOT directly; that would delete the
    whole working tree."""
    for sub in (".agents", "plugins"):
        sub_path = root / sub
        if sub_path.exists():
            shutil.rmtree(sub_path)


def _write_codex_skill_openai_yaml(skill_dir, skill_name, allow_implicit):
    """Emit skills/<name>/agents/openai.yaml in the snake_case shape the Codex
    skill loader honors. Recipes carry interface.display_name plus a SCALAR
    interface.default_prompt (and a short_description) for the install card.
    policy.allow_implicit_invocation is decided per skill by the caller: pure
    inherited-helper skills (the foundations) emit false so they are never
    auto-selected standalone; user-facing skills emit true. snake_case keys and a
    scalar default_prompt match OpenAI's own Codex plugins; the prior camelCase +
    list default_prompt was silently ignored at the skill layer."""
    agents_dir = skill_dir / "agents"
    agents_dir.mkdir()
    interface = CODEX_SKILL_INTERFACES.get(skill_name)
    lines = []
    if interface:
        lines.append("interface:")
        lines.append(f"  display_name: {interface['display_name']}")
        if interface.get("short_description"):
            lines.append(f'  short_description: "{interface["short_description"]}"')
        lines.append(f'  default_prompt: "{interface["default_prompt"]}"')
    lines.append("policy:")
    lines.append(f"  allow_implicit_invocation: {'true' if allow_implicit else 'false'}")
    (agents_dir / "openai.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def emit_codex_subagents(manifest, version):
    """codex sub-agents companion: emit one TOML per agents/<name>.md. Per
    /codex/subagents, Codex sub-agents live in ~/.codex/agents/ (or .codex/agents/)
    outside any plugin. Users install this companion by copying each TOML into one
    of those directories. Cowork-specific frontmatter (color, model: inherit, tools)
    is dropped because the Codex sub-agent schema does not recognize it."""
    target_dir = DIST_DIR / f"similarweb-codex-subagents-{version}"
    _prepare_target_dir(target_dir)
    agents_src = REPO_ROOT / "agents"
    if not agents_src.is_dir():
        print(f"  codex-subagents: skipped (no agents/ source)")
        return
    count = 0
    for agent_md in sorted(agents_src.glob("*.md")):
        fm, body = parse_frontmatter(agent_md)
        agent_name = fm.get("name", agent_md.stem)
        description = fm.get("description", "").strip()
        developer_instructions = body.strip()
        toml_text = _render_codex_subagent_toml(agent_name, description, developer_instructions)
        toml_path = target_dir / f"{agent_name}.toml"
        toml_path.write_text(toml_text, encoding="utf-8")
        count += 1
    zip_path = DIST_DIR / f"similarweb-codex-subagents-{version}.zip"
    _zip_target_dir(target_dir, zip_path)
    print(f"  codex-subagents: {target_dir} ({count} agents); zipped to {zip_path}")


def _render_codex_subagent_toml(name, description, developer_instructions):
    """Render a TOML body with the three required Codex sub-agent fields. Multi-line
    string values use the literal triple-single-quoted form because the markdown
    body carries backslashes, quotes, and other characters that would otherwise need
    escaping. Triple-single-quote runs inside the content are best-effort sanitized."""
    def lit(s):
        if "'''" in s:
            s = s.replace("'''", "''’")
        return "'''\n" + s + "\n'''"
    name_escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return (
        f'name = "{name_escaped}"\n'
        f'description = {lit(description)}\n'
        f'developer_instructions = {lit(developer_instructions)}\n'
    )


def emit_cursor(manifest, version):
    """cursor: skills + commands under .cursor-plugin/, marketplace.json entry.
    MCP server is configured separately by the user in Cursor's MCP settings."""
    target_dir = DIST_DIR / "cursor"
    _prepare_target_dir(target_dir)
    cursor_plugin_dir = target_dir / ".cursor-plugin"
    cursor_plugin_dir.mkdir()
    with open(cursor_plugin_dir / "plugin.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    marketplace = {
        "plugins": [
            {
                "name": manifest["name"],
                "version": version,
                "description": manifest["description"],
                "author": manifest["author"]["name"],
            }
        ]
    }
    with open(cursor_plugin_dir / "marketplace.json", "w", encoding="utf-8") as f:
        json.dump(marketplace, f, indent=2)
    skills_target = cursor_plugin_dir / "skills"
    skills_target.mkdir()
    _copy_skills(skills_target, exclude_cowork_only=True, strip_cowork=True,
                 include_cowork_files=False)
    commands_src = REPO_ROOT / "commands"
    if commands_src.is_dir():
        shutil.copytree(commands_src, cursor_plugin_dir / "commands")
    zip_path = DIST_DIR / f"similarweb-cursor-{version}.zip"
    _zip_target_dir(target_dir, zip_path)
    print(f"  cursor: {zip_path}")


def _rebuild_frontmatter(fm):
    """Render the frontmatter dict back to YAML using canonical field order.
    Unknown keys are appended after the canonical set in their original order."""
    lines = ["---"]
    seen = set()
    for key in CANONICAL_FRONTMATTER_ORDER:
        if key in fm:
            seen.add(key)
            value = fm[key]
            if isinstance(value, list):
                if not value:
                    lines.append(f"{key}: []")
                else:
                    lines.append(f"{key}:")
                    for item in value:
                        lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")
    for key, value in fm.items():
        if key in seen:
            continue
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def emit_claude_ai(manifest, version):
    """claude-ai: per-skill zips, strip allowed-tools + argument-hint, enforce 1024-char
    description cap. Each zip also carries the skill's shipped companion files minus
    references/cowork/ (and sw-setup/sw-config get their capmap.py copy) so it stays
    self-contained; text payloads are LF-normalized like _zip_target_dir does."""
    target_dir = DIST_DIR / f"similarweb-claude-ai-{version}"
    _prepare_target_dir(target_dir)
    for name, path in list_skills(exclude_cowork_only=True):
        fm, body = parse_frontmatter(path)
        body = strip_cowork_sections(body)
        cleaned_fm = {k: v for k, v in fm.items() if k not in ("allowed-tools", "argument-hint")}
        desc = cleaned_fm.get("description", "")
        if len(desc) > CLAUDE_AI_DESCRIPTION_CAP:
            print(
                f"  WARN: {name} description {len(desc)} chars > {CLAUDE_AI_DESCRIPTION_CAP}; "
                "truncate authoring; build proceeding with raw value (will fail upload)",
                file=sys.stderr,
            )
        rebuilt = _rebuild_frontmatter(cleaned_fm) + "\n" + body
        shipped = _skill_shipped_files(name, include_cowork_files=False)
        skill_zip = target_dir / f"{name}.zip"
        with zipfile.ZipFile(skill_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{name}/SKILL.md", rebuilt)
            for rel in sorted(shipped):
                data = shipped[rel].read_bytes()
                if is_text(shipped[rel]):
                    data = data.replace(b"\r\n", b"\n")
                zf.writestr(f"{name}/{rel}", data)
        print(f"  claude-ai: {skill_zip}")


def emit_m365(manifest, version):
    """m365: staged INPUT for Microsoft's Convert-ClaudePluginToMOS3.ps1, which
    turns it into an M365 Copilot Cowork app package. Companion artifact only:
    NOT release-attached (the zip name matches none of release.yml's globs) and
    NOT installable as-is. Converter behavior grounded 2026-07-06 (see the
    M365 constants block); icons must sit at the tree ROOT as color.png /
    outline.png and .mcp.json is consumed into the manifest, never packaged.
    Runtime behavior on Microsoft's platform (Inherits cross-skill loading,
    user-invocable ingestion, capmap.py execution) is UNVERIFIED pending the
    tenant pilot in docs/m365-copilot-notes.md; commands/ is excluded because
    the converter copies it but the manifest never references it."""
    target_dir = DIST_DIR / "m365"
    _prepare_target_dir(target_dir)
    (target_dir / ".claude-plugin").mkdir()
    # The converter consumes this DIRECTORY (not the LF-normalized zip), so every
    # text write here is LF-normalized explicitly to keep the staged tree
    # byte-identical across build hosts.
    m365_manifest = dict(manifest)
    for fragment in M365_MANIFEST_DESCRIPTION_DROPS:
        m365_manifest["description"] = m365_manifest.get("description", "").replace(fragment, "")
    with open(target_dir / ".claude-plugin" / "plugin.json", "w", encoding="utf-8", newline="") as f:
        json.dump(m365_manifest, f, indent=2)
        f.write("\n")
    skills_target = target_dir / "skills"
    skills_target.mkdir()
    for name, path in list_skills(exclude_cowork_only=True):
        fm, body = parse_frontmatter(path)
        body = strip_cowork_sections(body)
        fm = {k: v for k, v in fm.items() if k not in ("allowed-tools", "argument-hint")}
        desc, stale, residual = _m365_transform_description(name, fm.get("description", ""))
        if stale or residual:
            raise SystemExit(
                f"emit_m365: {name} description failed the M365 transform "
                f"(stale drop fragments or residual Cowork mention); run "
                f"build.py --validate for the specific violation"
            )
        fm["description"] = desc
        skill_target = skills_target / name
        skill_target.mkdir()
        with open(skill_target / "SKILL.md", "w", encoding="utf-8", newline="") as f:
            f.write(_rebuild_frontmatter(fm) + "\n" + body)
        for rel, src in _skill_shipped_files(name, include_cowork_files=False).items():
            dest_file = skill_target / rel
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            data = src.read_bytes()
            if is_text(src):
                data = data.replace(b"\r\n", b"\n")
            dest_file.write_bytes(data)
    with open(target_dir / ".mcp.json", "w", encoding="utf-8", newline="") as f:
        json.dump(M365_MCP_SERVERS, f, indent=2)
        f.write("\n")
    for icon_name, _ in M365_ICON_SPECS:
        icon_src = REPO_ROOT / "assets" / "m365" / icon_name
        if not icon_src.is_file():
            raise SystemExit(
                f"emit_m365: assets/m365/{icon_name} missing; the converter reads "
                f"it from the staged tree root"
            )
        shutil.copy(icon_src, target_dir / icon_name)
    zip_path = DIST_DIR / f"similarweb-m365-converter-input-{version}.zip"
    _zip_target_dir(target_dir, zip_path)
    print(f"  m365: {zip_path} (converter input, not release-attached)")


def cmd_test():
    """Run local tests. Requires tests/ directory."""
    tests_dir = REPO_ROOT / "tests"
    if not tests_dir.exists():
        print("tests/ not present; nothing to do", file=sys.stderr)
        return 1
    runner = tests_dir / "run-tests.sh"
    if not runner.exists():
        print(f"missing test runner: {runner}", file=sys.stderr)
        return 1
    return subprocess.call(["bash", str(runner)])


def cmd_ground():
    """Stub: re-grounding is a manual process today.

    To re-validate the assertions, open each tests/grounded/<assertion-id>.md,
    run the calls listed under "Re-validation notes" against the live MCP,
    and update tests/grounding-ledger.json. Phase 2 may automate this if
    a stable MCP-from-Python surface emerges.
    """
    print("ground mode: manual re-validation required; see tests/grounded/*.md "
          "and CONTRIBUTING.md release checklist step 3.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="similarweb-mcp-plugin build + translator")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--validate", action="store_true")
    g.add_argument("--build", action="store_true")
    g.add_argument("--test", action="store_true")
    g.add_argument("--ground", action="store_true")
    args = parser.parse_args()
    if args.validate:
        sys.exit(cmd_validate())
    if args.build:
        sys.exit(cmd_build())
    if args.test:
        sys.exit(cmd_test())
    if args.ground:
        sys.exit(cmd_ground())


if __name__ == "__main__":
    main()
