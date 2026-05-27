#!/usr/bin/env python3
"""
build.py: translator and packager for similarweb-mcp-plugin.

Modes:
  --validate  Structural validation (frontmatter, description cap, file presence). CI-safe.
  --build     Emit four per-platform bundles to dist/.
  --test      Run local tests (requires tests/ directory).
  --ground    Stub: re-grounding is a manual process today (see CONTRIBUTING.md).

Python 3 stdlib only. Runs developer-side. Customers never invoke this.
"""

import argparse
import json
import os
import shutil
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

TEXT_EXTENSIONS = {".sh", ".py", ".md", ".json", ".yml", ".yaml", ".txt", ".toml", ".template"}
TEXT_FILES = {".gitattributes", "LICENSE", "CONNECTORS.md", "README.md"}

GROUNDED_BODY_HEADER = "## Grounded assertions"

CODEX_BRAND_COLOR = "#106DFC"
CODEX_DISPLAY_NAME = "Similarweb"
CODEX_CATEGORY = "Marketing Analytics"
CODEX_WEBSITE_URL = "https://github.com/idan-yaron/similarweb-mcp-plugin"
CODEX_LONG_DESCRIPTION = (
    "Expert co-pilot for the Similarweb MCP server. Seven analyst recipes "
    "(competitive teardown, audience overlap, channel mix, market size, AEO audit, "
    "page mix, keyword opportunity), free-form intent routing, lazy capability "
    "discovery, intent-aware output. Turns the Similarweb MCP from a 90-tool flat "
    "menu into deterministic multi-tool playbooks."
)
CODEX_DEFAULT_PROMPTS = [
    "Compare nike.com and adidas.com on Similarweb",
    "Break down apple.com traffic channels over the last 90 days",
    "Audit chase.com Answer Engine Optimization posture",
]

CODEX_MARKETPLACE_NAME = "similarweb-local"
CODEX_MARKETPLACE_DISPLAY = "Similarweb (local)"

CODEX_SKILL_INTERFACES = {
    "sw-aeo-audit": {
        "displayName": "AEO Audit",
        "defaultPrompt": "Audit chase.com Answer Engine Optimization posture",
    },
    "sw-audience-overlap": {
        "displayName": "Audience Overlap",
        "defaultPrompt": "Audience overlap for nike.com vs adidas.com",
    },
    "sw-channel-mix": {
        "displayName": "Channel Mix",
        "defaultPrompt": "Break down apple.com traffic channels over the last 90 days",
    },
    "sw-competitive-teardown": {
        "displayName": "Competitive Teardown",
        "defaultPrompt": "Compare nike.com vs adidas.com on Similarweb",
    },
    "sw-keyword-opportunity": {
        "displayName": "Keyword Opportunity",
        "defaultPrompt": "Keyword gaps between notion.so and evernote.com",
    },
    "sw-market-size": {
        "displayName": "Market Size",
        "defaultPrompt": "Market size for cloud storage software",
    },
    "sw-page-mix": {
        "displayName": "Page Mix",
        "defaultPrompt": "Top URLs and folders for shopify.com",
    },
}


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


def list_skills():
    """Return list of (skill_name, skill_md_path) tuples."""
    skills = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            skills.append((skill_dir.name, skill_md))
    return skills


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


def cmd_validate():
    """Frontmatter present, descriptions under Claude.ai cap, file presence per target,
    grounding citations resolve, fragility-aware dependency check.

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

    codex_dist = DIST_DIR / "codex"
    if codex_dist.is_dir():
        manifest_at = codex_dist / ".agents" / "plugins" / "marketplace.json"
        plugin_at = codex_dist / "plugins" / "similarweb" / ".codex-plugin" / "plugin.json"
        if not manifest_at.is_file():
            errors.append(
                f"{codex_dist}: marketplace manifest missing at canonical location "
                f".agents/plugins/marketplace.json. Codex CLI rejects this layout with "
                f"`marketplace root does not contain a supported manifest`. Re-run "
                f"build.py --build."
            )
        elif not plugin_at.is_file():
            errors.append(
                f"{codex_dist}: marketplace manifest present but plugin payload missing "
                f"at plugins/similarweb/.codex-plugin/plugin.json. Layout drift in "
                f"emit_codex."
            )

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
    skills-only subsets."""
    manifest = load_plugin_manifest()
    version = manifest["version"]
    DIST_DIR.mkdir(exist_ok=True)
    emit_cowork(manifest, version)
    emit_claude_code(manifest, version)
    emit_codex(manifest, version)
    emit_codex_subagents(manifest, version)
    emit_cursor(manifest, version)
    emit_claude_ai(manifest, version)
    print(f"OK: built five platform bundles plus codex sub-agents companion in {DIST_DIR}")
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
    for name, path in list_skills():
        skill_target = skills_target / name
        skill_target.mkdir()
        shutil.copy(path, skill_target / "SKILL.md")
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
    for name, path in list_skills():
        skill_target = skills_target / name
        skill_target.mkdir()
        shutil.copy(path, skill_target / "SKILL.md")
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
    router, and foundations get policy-only), hooks/ with PLUGIN_ROOT path-var rewrite,
    and .mcp.json.template with the standard {mcpServers: ...} wrapper.

    The Similarweb MCP server is configured separately by the user; .mcp.json.template
    documents the shape without auto-spawning. No install-card icon ships; Codex
    falls back to text-only card rendering.
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
        "hooks": "./hooks/hooks.json",
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
    with open(plugin_root / ".codex-plugin" / "plugin.json", "w", encoding="utf-8") as f:
        json.dump(codex_manifest, f, indent=2)

    skills_target = plugin_root / "skills"
    skills_target.mkdir()
    for name, path in list_skills():
        skill_target = skills_target / name
        skill_target.mkdir()
        shutil.copy(path, skill_target / "SKILL.md")
        _write_codex_skill_openai_yaml(skill_target, name)

    hooks_src = REPO_ROOT / "hooks"
    if hooks_src.is_dir():
        _copy_codex_hooks(hooks_src, plugin_root / "hooks")

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

    zip_path = DIST_DIR / f"similarweb-codex-{version}.zip"
    _zip_target_dir(target_dir, zip_path)
    print(f"  codex: {zip_path}")


def _write_codex_skill_openai_yaml(skill_dir, skill_name):
    """Emit skills/<name>/agents/openai.yaml. Recipes carry displayName + defaultPrompt
    for the Codex install card. Operators, router, and foundations get policy-only
    (allow_implicit_invocation: true), matching the per-skill metadata adjunct shape
    documented at developers.openai.com/codex/plugins/build."""
    agents_dir = skill_dir / "agents"
    agents_dir.mkdir()
    interface = CODEX_SKILL_INTERFACES.get(skill_name)
    if interface:
        content = (
            "interface:\n"
            f"  displayName: {interface['displayName']}\n"
            "  defaultPrompt:\n"
            f"    - \"{interface['defaultPrompt']}\"\n"
            "policy:\n"
            "  allow_implicit_invocation: true\n"
        )
    else:
        content = "policy:\n  allow_implicit_invocation: true\n"
    (agents_dir / "openai.yaml").write_text(content, encoding="utf-8")


def _copy_codex_hooks(hooks_src, hooks_target):
    """Copy hooks/ into the Codex bundle. hooks.json gets its CLAUDE_PLUGIN_ROOT
    placeholder rewritten to PLUGIN_ROOT, the spec-canonical name per /codex/hooks
    (Codex accepts both, but PLUGIN_ROOT is what the spec documents)."""
    hooks_target.mkdir()
    for item in hooks_src.iterdir():
        if item.is_file():
            content = item.read_text(encoding="utf-8")
            if item.name == "hooks.json":
                content = content.replace("${CLAUDE_PLUGIN_ROOT}", "${PLUGIN_ROOT}")
            (hooks_target / item.name).write_text(content, encoding="utf-8")
        elif item.is_dir():
            sub = hooks_target / item.name
            sub.mkdir()
            for f in item.iterdir():
                if f.is_file():
                    shutil.copy(f, sub / f.name)


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
    for name, path in list_skills():
        skill_target = skills_target / name
        skill_target.mkdir()
        shutil.copy(path, skill_target / "SKILL.md")
    commands_src = REPO_ROOT / "commands"
    if commands_src.is_dir():
        shutil.copytree(commands_src, cursor_plugin_dir / "commands")
    zip_path = DIST_DIR / f"similarweb-cursor-{version}.zip"
    _zip_target_dir(target_dir, zip_path)
    print(f"  cursor: {zip_path}")


def _format_fm_value(value):
    if isinstance(value, list):
        return value
    return value


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
    """claude-ai: per-skill zips, strip allowed-tools + argument-hint, enforce 1024-char description cap."""
    target_dir = DIST_DIR / f"similarweb-claude-ai-{version}"
    _prepare_target_dir(target_dir)
    for name, path in list_skills():
        fm, body = parse_frontmatter(path)
        cleaned_fm = {k: v for k, v in fm.items() if k not in ("allowed-tools", "argument-hint")}
        desc = cleaned_fm.get("description", "")
        if len(desc) > CLAUDE_AI_DESCRIPTION_CAP:
            print(
                f"  WARN: {name} description {len(desc)} chars > {CLAUDE_AI_DESCRIPTION_CAP}; "
                "truncate authoring; build proceeding with raw value (will fail upload)",
                file=sys.stderr,
            )
        rebuilt = _rebuild_frontmatter(cleaned_fm) + "\n" + body
        skill_zip = target_dir / f"{name}.zip"
        with zipfile.ZipFile(skill_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{name}/SKILL.md", rebuilt)
        print(f"  claude-ai: {skill_zip}")


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
