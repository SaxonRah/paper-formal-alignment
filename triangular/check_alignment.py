#!/usr/bin/env python3
"""Check that a LaTeX paper's tagged statements match a Lean or Rocq formalization.

Usage:
    python3 check_alignment.py paper.tex --lean Triangular.lean
    python3 check_alignment.py paper.tex --rocq Triangular.v

Environment variables LEAN and COQC override the prover executables.

The paper marks each definition, theorem and example with \\formal{Name}, and
tags each variable, hypothesis and conclusion with its formal reading (see
align.sty). The checker asks the prover for the real signature of each named
object and compares, failing on any mismatch. Proofs are never compared:
only statements.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

# ---------------------------------------------------------------- LaTeX side

def read_arg(s, i):
    """Read one {...} argument starting at s[i] (skipping spaces); return (text, end)."""
    while s[i].isspace():
        i += 1
    assert s[i] == "{", f"expected '{{' at: {s[i:i+30]!r}"
    depth, j = 0, i
    while True:
        if s[j] == "{": depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1

def macros(body, name, nargs):
    out, pos = [], 0
    pat = re.compile(r"\\" + name + r"(?![A-Za-z])")
    while (m := pat.search(body, pos)):
        args, k = [], m.end()
        for _ in range(nargs):
            a, k = read_arg(body, k)
            args.append(a)
        out.append(args)
        pos = k
    return out

def parse_paper(path):
    tex = open(path, encoding="utf-8").read()
    tex = re.sub(r"(?<!\\)%.*", "", tex)                      # drop comments
    items = []
    envs = r"definition|theorem|lemma|proposition|corollary|example"
    for env, body in re.findall(rf"\\begin\{{({envs})\}}(.*?)\\end\{{\1\}}", tex, re.S):
        f = macros(body, "formal", 1)
        if not f:
            continue
        items.append({
            "env": env,
            "name": f[0][0].strip(),
            "vars": {n.strip(): (t.strip(), d.strip()) for n, t, d in macros(body, "var", 3)},
            "hyps": {n.strip(): (t.strip(), d.strip()) for n, t, d in macros(body, "hyp", 3)},
            "concl": [(t.strip(), d.strip()) for t, d in macros(body, "concl", 2)],
        })
    return items

# ------------------------------------------------------------ normalization

UNICODE = {"≤": "<=", "≥": ">=", "≠": "<>", "∧": "/\\", "∨": "\\/", "¬": "~",
           "→": "->", "↔": "<->", "∃": "exists ", "∀": "forall "}

def norm(s):
    for u, a in UNICODE.items():
        s = s.replace(u, a)
    s = re.sub(r"\bPaper\.", "", s)          # namespace prefix (Lean) vs bare names (Rocq)
    s = re.sub(r"\bNat\b", "nat", s)          # Lean's Nat is Rocq's nat
    s = " ".join(s.split())
    s = re.sub(r"\b(exists|forall) \((\w+) : ([^()]+)\),", r"\1 \2 : \3,", s)   # Lean's ∃ (n : T),
    while s.startswith("(") and s.endswith(")") and balanced(s[1:-1]):
        s = s[1:-1].strip()
    return s

def balanced(s):
    d = 0
    for c in s:
        d += (c == "(") - (c == ")")
        if d < 0:
            return False
    return d == 0

# --------------------------------------------------------------- Lean side

LEAN_DUMP = r'''import Lean
import {mod}
open Lean Meta Elab Command
set_option pp.funBinderTypes true

elab "#align_dump " id:ident : command => liftTermElabM do
  try
    let name ← realizeGlobalConstNoOverload id
    let ci ← getConstInfo name
    let axs ← collectAxioms name
    forallTelescope ci.type fun xs body => do
      let mut bs : Array Json := #[]
      for x in xs do
        let d ← x.fvarId!.getDecl
        bs := bs.push <| Json.mkObj [("name", toJson d.userName.toString),
          ("type", toJson (toString (← ppExpr d.type)))]
      IO.println <| Json.compress <| Json.mkObj [
        ("name", toJson id.getId.toString),
        ("kind", toJson (if ci matches .thmInfo _ then "theorem" else "definition")),
        ("binders", Json.arr bs),
        ("conclusion", toJson (toString (← ppExpr body))),
        ("axioms", toJson (axs.map (·.toString)))]
  catch _ =>
    IO.println <| Json.compress <| Json.mkObj [("name", toJson id.getId.toString), ("missing", true)]
'''

LEAN_OK_AXIOMS = {"propext", "Quot.sound", "Classical.choice"}

WINDOWS_CODES = {
    0xC0000135: "a DLL it needs was not found (its bin folder is probably not on PATH)",
    0xC0000005: "it crashed with an access violation",
}

def with_bin_on_path(exe, env=None):
    """Prover installs on Windows load DLLs and helper programs from their own
    bin folder, so put that folder first on PATH for the child process."""
    env = dict(env or os.environ)
    d = os.path.dirname(os.path.abspath(shutil.which(exe) or exe))
    env["PATH"] = d + os.pathsep + env.get("PATH", "")
    return env

def run(cmd, **kw):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", **kw)
    except FileNotFoundError:
        sys.exit(f"Could not run '{cmd[0]}'. Is it installed and on your PATH? "
                 "You can also point to it with the LEAN or COQC environment variable.")
    if r.returncode != 0:
        where = f" (in {kw['cwd']})" if "cwd" in kw else ""
        code = r.returncode & 0xFFFFFFFF
        if code in WINDOWS_CODES:
            where += f"\nWindows error 0x{code:08X}: {WINDOWS_CODES[code]}."
        sys.exit(f"Prover failed with exit code {r.returncode} running:\n  {' '.join(cmd)}{where}\n"
                 f"{(r.stdout + r.stderr).strip() or '(it printed nothing)'}")
    return r.stdout

def lean_signatures(src, names):
    lean = os.environ.get("LEAN", "lean")
    prefix = run([lean, "--print-prefix"], env=with_bin_on_path(lean)).strip()
    tmp = tempfile.mkdtemp()
    mod = re.sub(r"\W", "_", os.path.splitext(os.path.basename(src))[0])
    shutil.copy(src, f"{tmp}/{mod}.lean")
    run([lean, "-o", f"{mod}.olean", f"{mod}.lean"], cwd=tmp, env=with_bin_on_path(lean))
    dump = LEAN_DUMP.format(mod=mod) + "".join(f"#align_dump {n}\n" for n in names)
    open(f"{tmp}/Dump.lean", "w", encoding="utf-8").write(dump)
    env = with_bin_on_path(lean, dict(os.environ,
          LEAN_PATH=os.pathsep.join([os.path.join(prefix, "lib", "lean"), tmp])))
    out = run([lean, "Dump.lean"], env=env, cwd=tmp)
    sigs = {}
    for line in out.splitlines():
        if line.startswith("{"):
            j = json.loads(line)
            if j.get("missing"):
                continue
            j["bad_axioms"] = [a for a in j["axioms"] if a not in LEAN_OK_AXIOMS]
            sigs[j["name"]] = j
    return sigs

# --------------------------------------------------------------- Rocq side

ROCQ_DUMP = r'''From Align Require Import {mod}.
Ltac show_binders :=
  repeat match goal with H : ?A |- _ => idtac "BINDER" H ":" A; revert H end.
Ltac align_dump thm :=
  let t := type of thm in let D := fresh "dump" in
  assert t as D; [ intros; match goal with |- ?G => idtac "CONCL" G end;
                   show_binders; admit | clear D ].
'''

ROCQ_OK_AXIOMS = {"classic", "functional_extensionality_dep", "proof_irrelevance"}

def rocq_signatures(src, names, kinds):
    coqc = os.environ.get("COQC", "coqc")
    tmp = tempfile.mkdtemp()
    mod = re.sub(r"\W", "_", os.path.splitext(os.path.basename(src))[0])
    shutil.copy(src, f"{tmp}/{mod}.v")
    env = with_bin_on_path(coqc)
    run([coqc, "-R", ".", "Align", f"{mod}.v"], cwd=tmp, env=env)
    short = {n: n.split(".")[-1] for n in names}
    # Pass 1: which names exist?
    open(f"{tmp}/Exists.v", "w", encoding="utf-8").write(f"From Align Require Import {mod}.\n" +
        "".join(f"Locate {s}.\n" for s in short.values()))
    loc = run([coqc, "-R", ".", "Align", "Exists.v"], cwd=tmp, env=env)
    present = {n for n, s in short.items() if re.search(rf"Constant \S*\b{re.escape(s)}\b", loc)}
    # Pass 2: dump statements and assumptions.
    body = ROCQ_DUMP.format(mod=mod)
    for n in names:
        if n in present:
            s = short[n]
            if kinds[n] != "definition":
                body += f'Goal True. idtac "THEOREM" "{n}". align_dump {s}. Abort.\n'
            body += f'Goal True. idtac "ASSUMPTIONS" "{n}". Abort.\nPrint Assumptions {s}.\n'
    open(f"{tmp}/Dump.v", "w", encoding="utf-8").write(body)
    out = run([coqc, "-R", ".", "Align", "Dump.v"], cwd=tmp, env=env)
    sigs, cur, mode = {}, None, None
    for line in out.splitlines():
        if line.startswith("THEOREM "):
            cur = line.split(" ", 1)[1]
            sigs[cur] = {"name": cur, "kind": "theorem", "binders": [], "conclusion": "", "bad_axioms": []}
        elif line.startswith("ASSUMPTIONS "):
            cur, mode = line.split(" ", 1)[1], "axioms"
            sigs.setdefault(cur, {"name": cur, "kind": "definition", "binders": [],
                                  "conclusion": "", "bad_axioms": []})
        elif line.startswith("CONCL "):
            sigs[cur]["conclusion"], mode = line[6:], None
        elif line.startswith("BINDER "):
            n, t = line[7:].split(" : ", 1)
            sigs[cur]["binders"].insert(0, {"name": n, "type": t})
        elif mode == "axioms" and re.match(r"^\S+ :", line):
            ax = line.split(" :")[0]
            if ax not in ROCQ_OK_AXIOMS:
                sigs[cur]["bad_axioms"].append(ax)
    return sigs

# ------------------------------------------------------------------ compare

def check(items, sigs):
    fails, review = [], []
    for it in items:
        n, sig = it["name"], sigs.get(it["name"])
        tag = f"{it['env']} {n}"
        if sig is None:
            fails.append(f"{tag}: not found in the formalization")
            continue
        if sig["bad_axioms"]:
            fails.append(f"{tag}: depends on {', '.join(sig['bad_axioms'])} (sorry/Admitted or extra axioms)")
        if it["env"] == "definition":
            review.append((tag, "(definition)", "read the formal definition once"))
            continue
        formal = {b["name"]: norm(b["type"]) for b in sig["binders"]}
        paper = {**{k: norm(t) for k, (t, _) in it["vars"].items()},
                 **{k: norm(t) for k, (t, _) in it["hyps"].items()}}
        for b in formal.keys() - paper.keys():
            fails.append(f"{tag}: formal statement assumes '{b} : {formal[b]}', which the paper never states")
        for b in paper.keys() - formal.keys():
            fails.append(f"{tag}: paper states '{b}', which the formal statement lacks")
        for b in formal.keys() & paper.keys():
            if formal[b] != paper[b]:
                fails.append(f"{tag}: '{b}' is '{paper[b]}' in the paper but '{formal[b]}' formally")
        if len(it["concl"]) != 1:
            fails.append(f"{tag}: needs exactly one \\concl tag")
        elif norm(it["concl"][0][0]) != norm(sig["conclusion"]):
            fails.append(f"{tag}: conclusion is '{norm(it['concl'][0][0])}' in the paper "
                         f"but '{norm(sig['conclusion'])}' formally")
        for k, (t, d) in {**it["vars"], **it["hyps"]}.items():
            review.append((tag, d, t))
        for t, d in it["concl"]:
            review.append((tag, d, t))
    return fails, review

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(
        description="Check a tagged LaTeX paper against ONE formalization (Lean or Rocq).",
        epilog="example: python check_alignment.py paper.tex --lean Triangular.lean")
    ap.add_argument("paper", help="the paper's LaTeX source (.tex), not the PDF")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--lean")
    g.add_argument("--rocq")
    a = ap.parse_args()
    if not a.paper.lower().endswith(".tex"):
        sys.exit(f"'{a.paper}' isn't a .tex file. Pass the LaTeX source: the tags live there, not in the PDF.")
    items = parse_paper(a.paper)
    names = [it["name"] for it in items]
    if a.lean:
        sigs = lean_signatures(a.lean, names)
    else:
        sigs = rocq_signatures(a.rocq, names, {it["name"]: it["env"] for it in items})
    fails, review = check(items, sigs)
    print(f"Checked {len(items)} tagged statements against {a.lean or a.rocq}\n")
    if fails:
        print("MISMATCHES")
        for f in fails:
            print("  XXX:", f)
        print("\nResult: FAIL. Paper and formalization do not agree.")
        sys.exit(1)
    print("All definitions, hypotheses and conclusions match.\n")
    print("Human review (does each display text mean its formal reading?)")
    w = max(len(d) for _, d, _ in review)
    last = None
    for tag, d, t in review:
        if tag != last:
            print(f"  {tag}")
            last = tag
        print(f"      {d:<{w}} <->  {t}")
    print("\nResult: PASS")

if __name__ == "__main__":
    main()
