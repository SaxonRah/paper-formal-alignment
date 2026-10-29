#!/usr/bin/env python3
"""Verify that PFA's working copies changed nothing they were not allowed to change.

    python verify_copies.py --paper ORIGINAL.tex TAGGED.tex
    python verify_copies.py --formal ORIGINAL.lean COPY.lean
    (both flags may be given at once)

Paper: removing every PFA tag from the tagged copy must give back the original
byte for byte. Formal: the copy must be the original plus an appended section that
starts with a line containing "PFA additions".
Exit code 0 if everything verifies, 1 otherwise.
"""
import argparse, difflib, re, sys

def read_arg(s, i):
    j0 = i
    while i < len(s) and s[i].isspace():
        i += 1
    if i >= len(s) or s[i] != "{":
        raise ValueError(f"expected '{{' near: {s[j0:j0+40]!r}")
    depth, j = 0, i
    while j < len(s):
        if s[j] == "\\":
            j += 2
            continue
        depth += (s[j] == "{") - (s[j] == "}")
        if depth == 0:
            return s[i + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced braces")

def strip_tags(tex):
    tex = re.sub(r"\\usepackage\{align\}[ \t]*\r?\n?", "", tex, count=1)
    out, i = [], 0
    pat = re.compile(r"\\(formal|var|hyp|concl)(?![A-Za-z@])")
    keep = {"formal": None, "var": 2, "hyp": 2, "concl": 1}
    nargs = {"formal": 1, "var": 3, "hyp": 3, "concl": 2}
    while (m := pat.search(tex, i)):
        out.append(tex[i:m.start()])
        name, k, args = m.group(1), m.end(), []
        for _ in range(nargs[name]):
            a, k = read_arg(tex, k)
            args.append(a)
        if keep[name] is not None:
            out.append(strip_tags(args[keep[name]]) if "\\" in args[keep[name]] else args[keep[name]])
        i = k
    out.append(tex[i:])
    return "".join(out)

def show_diff(a, b, la, lb):
    d = list(difflib.unified_diff(a.splitlines(), b.splitlines(), la, lb, lineterm="", n=1))
    print("\n".join(d[:60]) + ("\n..." if len(d) > 60 else ""))

def check_paper(orig, tagged):
    o = open(orig, encoding="utf-8").read()
    t = open(tagged, encoding="utf-8").read()
    if "\\usepackage{align}" not in t:
        print("PAPER: tagged copy does not load align.sty")
        return False
    s = strip_tags(t)
    if s == o:
        print("PAPER: OK. Removing the tags gives back the original exactly.")
        return True
    print("PAPER: CHANGED. Removing the tags does not give back the original:")
    show_diff(o, s, orig, tagged + " (tags removed)")
    return False

def check_formal(orig, copy):
    o = open(orig, encoding="utf-8").read()
    c = open(copy, encoding="utf-8").read()
    if c == o:
        print("FORMAL: OK. Copy is identical to the original (nothing appended).")
        return True
    if not c.startswith(o.rstrip("\n")):
        print("FORMAL: CHANGED. The copy edits the original instead of only appending:")
        show_diff(o, c[:len(o) + 200], orig, copy)
        return False
    added = c[len(o.rstrip("\n")):]
    first = next((l for l in added.splitlines() if l.strip()), "")
    if "PFA additions" not in first:
        print("FORMAL: the appended section must start with a line containing 'PFA additions'.")
        return False
    names = re.findall(r"^\s*(?:theorem|lemma|example|Theorem|Lemma|Example|Fact|Corollary)\s+([\w.']+)", added, re.M)
    print(f"FORMAL: OK. Original unchanged; appended: {', '.join(names) or '(no named declarations)'}")
    return True

ap = argparse.ArgumentParser()
ap.add_argument("--paper", nargs=2, metavar=("ORIGINAL", "TAGGED"))
ap.add_argument("--formal", nargs=2, metavar=("ORIGINAL", "COPY"))
a = ap.parse_args()
if not (a.paper or a.formal):
    ap.error("give --paper and/or --formal")
ok = True
if a.paper:
    ok &= check_paper(*a.paper)
if a.formal:
    ok &= check_formal(*a.formal)
sys.exit(0 if ok else 1)
