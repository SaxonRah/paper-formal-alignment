#!/usr/bin/env python3
"""Build dist/paper-formal-alignment.skill from pfa/ and examples/.

    python build_skill.py

A .skill file is a zip whose top folder is the skill's name. The installed skill has
SKILL.md, scripts/, assets/ and references/ from pfa/, plus examples/ from the repo root.
"""
import os, re, sys, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = "paper-formal-alignment"
SKIP_DIRS = {"__pycache__", ".lake", ".git"}
SKIP_EXT = (".olean", ".ilean", ".vo", ".vok", ".vos", ".glob", ".aux", ".log", ".pyc")

def files(base):
    for d, dirs, fs in os.walk(base):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")]
        for f in sorted(fs):
            if not f.endswith(SKIP_EXT) and not f.startswith("."):
                yield os.path.join(d, f)

def main():
    skill_md = open(os.path.join(ROOT, "pfa", "SKILL.md"), encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n", skill_md, re.S)
    if not m or f"name: {NAME}" not in m.group(1) or "description:" not in m.group(1):
        sys.exit("pfa/SKILL.md needs front matter with 'name: paper-formal-alignment' and a description")
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", f"{NAME}.skill")
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for src, prefix in [("pfa", ""), ("examples", "examples")]:
            base = os.path.join(ROOT, src)
            for f in files(base):
                rel = os.path.relpath(f, base)
                z.write(f, "/".join(p for p in (NAME, prefix, rel.replace(os.sep, "/")) if p))
                count += 1
    print(f"Wrote {os.path.relpath(out, ROOT)} ({count} files)")

if __name__ == "__main__":
    main()
