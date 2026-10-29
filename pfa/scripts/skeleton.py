#!/usr/bin/env python3
"""List a formalization's declarations with their binder NAMES only, hiding types and
statements, so a paper can be linked without first reading the formal statements.

    python skeleton.py Formal.lean
    python skeleton.py Formal.v

Heuristic (regex-based): it reads declaration headers, not the elaborated terms. Use it
to choose \\formal names and binder names; the checker is what actually verifies.
"""
import re, sys

LEAN_KW = r"(theorem|lemma|def|abbrev|structure|class|inductive|instance|example)"
ROCQ_KW = r"(Theorem|Lemma|Definition|Fixpoint|Example|Corollary|Proposition|Fact|Remark|Inductive|Record)"

def binder_names(header):
    """Names from (a b : T), {a : T}, [inst : C], ⦃a : T⦄ groups at depth 0 of the header."""
    names, depth, i = [], 0, 0
    opens, closes = "({[⦃", ")}]⦄"
    while i < len(header):
        c = header[i]
        if c in opens and depth == 0:
            j, d = i, 0
            while j < len(header):
                if header[j] in opens: d += 1
                elif header[j] in closes:
                    d -= 1
                    if d == 0: break
                j += 1
            group = header[i + 1:j]
            if ":" in group:
                lhs = group.split(":", 1)[0]
                names += [n for n in lhs.split() if re.match(r"^[\w'₀-₉]+$", n)]
            elif c == "[":
                names.append("_inst")
            i = j + 1
            continue
        if c == ":" and depth == 0:
            break
        i += 1
    return names

def strip_comments(src, lean):
    if lean:
        src = re.sub(r"/-(?!-).*?-/", "", src, flags=re.S)        # block comments, keep docstrings
        return re.sub(r"(?<!/)--(?!/).*", "", src)
    return src

def main(path):
    src = open(path, encoding="utf-8").read()
    lean = path.endswith(".lean")
    kw = LEAN_KW if lean else ROCQ_KW
    ns, out = [], []
    text = strip_comments(src, lean)
    tokens = re.finditer(rf"(?m)^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+)*{kw}\s+([\w.'₀-₉]+)?|^\s*namespace\s+([\w.]+)|^\s*end\s+([\w.]+)|(/--.*?-/)|(\(\*.*?\*\))",
                         text, re.S)
    doc = None
    for m in tokens:
        if m.group(3):
            ns.append(m.group(3)); continue
        if m.group(4):
            if ns and ns[-1] == m.group(4): ns.pop()
            continue
        if m.group(5) or m.group(6):
            doc = " ".join((m.group(5) or m.group(6)).strip("/-*() ").split())[:90]
            continue
        kind, name = m.group(1), m.group(2) or "(anonymous)"
        rest = text[m.end():]
        stop = re.search(r":=|\bwhere\b|\|\s|\.\s*(\n|$)" if lean else r":=|\.\s*(\n|$)", rest)
        header = rest[:stop.start()] if stop else rest[:300]
        full = ".".join(ns + [name]) if lean and name != "(anonymous)" else name
        out.append((kind, full, binder_names(header), doc))
        doc = None
    for kind, full, bs, doc in out:
        line = f"{kind:<11} {full}"
        if bs:
            line += "   binders: " + ", ".join(bs)
        print(line)
        if doc:
            print(f"{'':<12}doc: {doc}")

if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].endswith((".lean", ".v")):
        sys.exit("usage: python skeleton.py Formal.lean | Formal.v")
    main(sys.argv[1])
