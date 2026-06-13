#!/usr/bin/env python3
"""Capability-map operations for the Similarweb plugin.

Single source: skills/sw-foundation-core/scripts/capmap.py. build.py copies it
into sw-setup and sw-config at build time. Subcommands read one JSON document
from stdin (except show) and write $HOME/.similarweb-plugin/capabilities.json
atomically (mkstemp + os.replace, UTF-8, no BOM). Python 3 stdlib only.

  fingerprint  stdin {"tools": [unqualified names], "prefix": str}
               upserts tool_surface; prints changed | first | same
  deny         stdin {"tool": name}
               idempotent sorted append to tools_inaccessible
  absent       stdin {"tools": [names], "observed_under": surface-hash}
               upserts tools_absent entries stamped with the hash
  coverage     stdin {"countries": [codes], "observed_under": surface-hash,
               optional "data_window": {start,end}, "fresh_data": date, "segments": []}
               upserts the coverage block from get-user-segments-describe;
               touches NO state/tools lists; prints ww-only | multi
  init         stdin the full probe-outcome document (see sw-setup Step 2)
               overwrites the map with the v2 full-probe schema
  show         no stdin; renders the human capability summary
"""

import collections
import datetime
import hashlib
import json
import os
import sys
import tempfile

CAPS_PATH = os.path.expanduser("~/.similarweb-plugin/capabilities.json")


def _now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def _stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _surface_hash(names):
    canon = "\n".join(sorted(set(names)))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _read_caps():
    try:
        with open(CAPS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"schema_version": 2, "tools_inaccessible": []}


def _write_caps(caps):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(CAPS_PATH), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(caps, f, indent=2)
    os.replace(tmp, CAPS_PATH)


def _fail(msg):
    print(f"capmap: {msg}", file=sys.stderr)
    return 2


def _stdin_doc():
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("expected a JSON document on stdin")
    return json.loads(raw)


def cmd_fingerprint(doc):
    names = doc.get("tools")
    if not isinstance(names, list) or not names or not all(isinstance(n, str) for n in names):
        return _fail('fingerprint needs {"tools": [non-empty list of names], "prefix": str}')
    os.makedirs(os.path.dirname(CAPS_PATH), exist_ok=True)
    caps = _read_caps()
    prev = caps.get("tool_surface", {}).get("hash", "")
    h = _surface_hash(names)
    now = _stamp(_now_utc())
    caps["tool_surface"] = {"hash": h, "count": len(set(names)), "observed_at": now,
                            "prefix": doc.get("prefix", "")}
    caps["last_updated"] = now
    _write_caps(caps)
    print("changed" if (prev and prev != h) else ("first" if not prev else "same"))
    return 0


def cmd_deny(doc):
    tool = doc.get("tool")
    if not isinstance(tool, str) or not tool:
        return _fail('deny needs {"tool": name}')
    os.makedirs(os.path.dirname(CAPS_PATH), exist_ok=True)
    caps = _read_caps()
    if tool not in caps.get("tools_inaccessible", []):
        caps.setdefault("tools_inaccessible", []).append(tool)
        caps["tools_inaccessible"] = sorted(set(caps["tools_inaccessible"]))
    caps["last_updated"] = _stamp(_now_utc())
    _write_caps(caps)
    return 0


def cmd_absent(doc):
    names = doc.get("tools")
    if not isinstance(names, list) or not names or not all(isinstance(n, str) for n in names):
        return _fail('absent needs {"tools": [non-empty list of names], "observed_under": hash}')
    observed_under = doc.get("observed_under", "")
    os.makedirs(os.path.dirname(CAPS_PATH), exist_ok=True)
    caps = _read_caps()
    now = _stamp(_now_utc())
    entries = caps.setdefault("tools_absent", [])
    for name in names:
        for entry in entries:
            if entry.get("name") == name:
                entry["observed_under"] = observed_under
                entry["observed_at"] = now
                break
        else:
            entries.append({"name": name, "observed_under": observed_under, "observed_at": now})
    caps["last_updated"] = now
    _write_caps(caps)
    return 0


def cmd_coverage(doc):
    countries = doc.get("countries")
    if not isinstance(countries, list) or not all(isinstance(c, str) for c in countries):
        return _fail('coverage needs {"countries": [codes], "observed_under": hash}')
    os.makedirs(os.path.dirname(CAPS_PATH), exist_ok=True)
    caps = _read_caps()
    now = _stamp(_now_utc())
    cov = {
        "countries": sorted({c.strip().lower() for c in countries if c.strip()}),
        # default to the map's current surface hash so the caller need not thread it
        "observed_under": doc.get("observed_under") or caps.get("tool_surface", {}).get("hash", ""),
        "observed_at": now,
    }
    if isinstance(doc.get("data_window"), dict):
        cov["data_window"] = doc["data_window"]
    if isinstance(doc.get("fresh_data"), str):
        cov["fresh_data"] = doc["fresh_data"]
    if isinstance(doc.get("segments"), list):
        cov["segments"] = doc["segments"]
    caps["coverage"] = cov
    caps["last_updated"] = now
    _write_caps(caps)
    # "world" is the describe's alias for "ww"; ww-only = no specific countries.
    effective = set(cov["countries"]) - {"world", "ww"}
    print("multi" if effective else "ww-only")
    return 0


def cmd_init(doc):
    if not isinstance(doc, dict):
        return _fail("init needs the probe-outcome JSON document on stdin")
    now_dt = _now_utc()
    now = _stamp(now_dt)
    tools = doc.get("tools") or []
    h = _surface_hash(tools) if tools else ""
    absent_names = []
    for entry in doc.get("tools_absent", []):
        absent_names.append(entry if isinstance(entry, str) else entry.get("name", "?"))
    caps = {
        "schema_version": 2,
        "mcp_server_version": doc.get("mcp_server_version", "unknown"),
        "last_full_probe": now,
        "last_updated": now,
        "refresh_after": _stamp(now_dt + datetime.timedelta(days=30)),
        "state": doc.get("state", "ready"),
        "tools_available": doc.get("tools_available", {}),
        "tools_inaccessible": doc.get("tools_inaccessible", []),
        "tools_absent": [{"name": n, "observed_under": h, "observed_at": now}
                         for n in absent_names],
    }
    if tools:
        caps["tool_surface"] = {"hash": h, "count": len(set(tools)), "observed_at": now,
                                "prefix": doc.get("prefix", "")}
    caps["categories_available"] = doc.get("categories_available", [])
    os.makedirs(os.path.dirname(CAPS_PATH), exist_ok=True)
    _write_caps(caps)
    return 0


def cmd_show():
    if not os.path.isfile(CAPS_PATH):
        print("No capability map yet. The plugin runs lazily and will discover access as recipes execute.")
        print("Run /sw-config --refresh to force a thorough probe.")
        return 0
    try:
        with open(CAPS_PATH, "r", encoding="utf-8") as f:
            caps = json.load(f)
    except (ValueError, OSError):
        print("Capability map is corrupted; run /sw-config --reset (then optionally --refresh).")
        return 0
    last_updated = caps.get("last_updated") or caps.get("last_full_probe") or caps.get("probed_at", "unknown")
    expires = caps.get("refresh_after", "n/a")
    version = caps.get("mcp_server_version", "unknown")
    state = caps.get("state", "lazy")
    tools = caps.get("tools_available", {})
    inaccessible = caps.get("tools_inaccessible", [])
    surface = caps.get("tool_surface", {})
    absent = caps.get("tools_absent", [])
    legacy = not surface
    legacy_absent = sorted(t for t, s in tools.items() if s is False and t not in inaccessible) if legacy else []
    print(f"Similarweb MCP capabilities (last updated {last_updated}, refresh_after {expires})")
    print(f"State: {state}")
    if surface:
        print(f"Tool surface: {surface.get('count', '?')} tools observed {surface.get('observed_at', 'unknown')}")
    coverage = caps.get("coverage", {})
    if coverage:
        cur = surface.get("hash", "")
        stale = " [stale: tool surface changed; run /sw-config --refresh]" if coverage.get("observed_under") != cur else ""
        countries = coverage.get("countries", [])
        effective = [c for c in countries if c not in ("world", "ww")]
        cov_desc = "worldwide only" if not effective else ", ".join(countries)
        print(f"Country coverage: {cov_desc}{stale}")
        dw = coverage.get("data_window")
        if isinstance(dw, dict):
            print(f"  data window: {dw.get('start', '?')} to {dw.get('end', '?')}; fresh_data {coverage.get('fresh_data', 'unknown')}")
        print(f"  segments defined: {len(coverage.get('segments', []))}")
    if tools:
        by_cat = collections.defaultdict(lambda: [0, 0])
        for tool, status in tools.items():
            if tool in legacy_absent:
                continue
            parts = tool.split("-")
            cat = parts[1] if len(parts) > 1 and parts[0] == "get" else "other"
            by_cat[cat][1] += 1
            if status is True:
                by_cat[cat][0] += 1
        for cat in sorted(by_cat):
            accessible, total = by_cat[cat]
            suffix = ""
            if accessible == 0:
                suffix = " (denied on this plan)"
            elif accessible < total:
                suffix = " (limited plan)"
            print(f"  {cat:16s} {accessible}/{total} probed tools accessible{suffix}")
    else:
        print("  (no full-probe data; lazy mode)")
    if inaccessible:
        print("")
        print("Denied during recipe runs or probes (403 claims; the tool exists on the connector):")
        for t in sorted(inaccessible):
            print(f"  - {t}")
    if absent or legacy_absent:
        print("")
        print("Not exposed on this connector (absent from the tool list; NOT a claims denial):")
        cur = surface.get("hash", "")
        for e in sorted(absent, key=lambda x: x.get("name", "")):
            stale = " [stale: tool surface changed; run /sw-config --refresh to re-check]" if e.get("observed_under") != cur else ""
            print(f"  - {e.get('name', '?')}{stale}")
        for t in legacy_absent:
            print(f"  - {t} [legacy record; re-checked on the next enumerating run]")
    print("")
    print(f"MCP server version: {version}")
    return 0


def main(argv):
    if len(argv) != 2 or argv[1] not in ("fingerprint", "deny", "absent", "coverage", "init", "show"):
        return _fail("usage: capmap.py fingerprint|deny|absent|coverage|init|show (JSON on stdin except show)")
    sub = argv[1]
    if sub == "show":
        return cmd_show()
    try:
        doc = _stdin_doc()
    except ValueError as e:
        return _fail(f"invalid stdin JSON: {e}")
    if sub == "fingerprint":
        return cmd_fingerprint(doc)
    if sub == "deny":
        return cmd_deny(doc)
    if sub == "absent":
        return cmd_absent(doc)
    if sub == "coverage":
        return cmd_coverage(doc)
    return cmd_init(doc)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
