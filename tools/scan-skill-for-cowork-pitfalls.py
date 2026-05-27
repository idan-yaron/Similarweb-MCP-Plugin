#!/usr/bin/env python3
"""Scan one or more SKILL.md files for patterns Cowork may preprocess
or reject. Read-only diagnostic; never modifies."""
import re
import sys
from pathlib import Path


def scan(path: Path):
    text = path.read_text(encoding="utf-8")
    print(f"=== {path} ({len(text)} chars) ===")

    backtick_bang = re.findall(r"!`[^`\n]+`", text)
    fenced_bang = re.findall(r"```!", text)
    dollar_braces = re.findall(r"\$\{[A-Z_][A-Z_0-9]*\}", text)
    dollar_args = re.findall(r"\$ARGUMENTS(?:\[\d+\])?", text)
    dollar_n = re.findall(r"(?:^|[^\$])\$\d+(?:[^\d]|$)", text)

    print(f"  backtick-bang injections (!`cmd`): {len(backtick_bang)}")
    if backtick_bang:
        print(f"    first 5: {backtick_bang[:5]}")
    print(f"  fenced-bang blocks (```!): {len(fenced_bang)}")
    print(f"  ${{VAR}} substitutions: {len(dollar_braces)}")
    if dollar_braces:
        print(f"    uniques: {sorted(set(dollar_braces))[:15]}")
    print(f"  $ARGUMENTS literals: {len(dollar_args)}")
    print(f"  $N positional (rough): {len(dollar_n)}")

    fm_end = text.find("\n---\n", 4)
    if fm_end > 0:
        fm = text[4:fm_end]
        m = re.search(r"^description: (.*?)(?=^[a-z\-]+:|^---|\Z)", fm, re.DOTALL | re.MULTILINE)
        if m:
            desc = m.group(1).strip()
            print(f"  description: {len(desc)} chars")
        for key in ("name", "user-invocable", "argument-hint", "allowed-tools"):
            mk = re.search(rf"^{re.escape(key)}:\s*(.*?)$", fm, re.MULTILINE)
            if mk:
                print(f"  fm key '{key}': present")

    print(f"  code fences (```): {text.count(chr(96) * 3)}")
    print()


if __name__ == "__main__":
    for p in sys.argv[1:]:
        scan(Path(p))
