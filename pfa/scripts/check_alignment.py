#!/usr/bin/env python3
"""PFA: check that a tagged LaTeX paper's statements match a Lean or Rocq formalization.

    python check_alignment.py paper.tex --lean Formal.lean
    python check_alignment.py paper.tex --rocq Formal.v
    python check_alignment.py paper.tex --lean Formal.lean --lake-project path/to/project
    python check_alignment.py paper.tex --rocq Formal.v --coq-flags "-Q theories MyLib"

The paper marks each statement with \\formal{Name} and tags each variable, hypothesis
and conclusion with its formal reading (see align.sty). For every tagged statement the
checker asks the prover for the real signature and compares:

  * binder names must match exactly (nothing extra, nothing missing);
  * variable types must match;
  * each hypothesis and conclusion must match the formal one, either as text or by an
    equivalence the PROVER proves: an automatic tactic, or a lemma named
    pfa_eq_<theorem>_<binder> / pfa_eq_<theorem>_concl in the formalization;
  * nothing may depend on sorry/Admitted or non-standard axioms.

Proofs are never compared, only statements.
Exit codes: 0 PASS, 1 FAIL (mismatch), 2 INCOMPLETE (untagged statements), 3 tool error.
Environment: LEAN, LAKE, COQC override the prover executables.
"""
import argparse, json, os, re, shlex, shutil, subprocess, sys, tempfile

DEFAULT_ENVS = ["definition", "defn", "theorem", "thm", "lemma", "lem", "proposition",
                "prop", "corollary", "cor", "example", "claim", "fact"]
TAGS = {"formal": 1, "var": 3, "hyp": 3, "concl": 2}

class ToolError(Exception):
    pass

# ======================================================================= LaTeX side

def read_arg(s, i):
    """Read one {...} argument at s[i] (after optional whitespace), honouring \\{ escapes."""
    while i < len(s) and s[i].isspace():
        i += 1
    if i >= len(s) or s[i] != "{":
        raise ToolError(f"expected '{{' near: {s[i:i+40]!r}")
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ToolError(f"unbalanced braces near: {s[i:i+40]!r}")

def find_macros(body, name, nargs):
    out, pos = [], 0
    pat = re.compile(r"\\" + name + r"(?![A-Za-z@])")
    while (m := pat.search(body, pos)):
        args, k = [], m.end()
        for _ in range(nargs):
            a, k = read_arg(body, k)
            args.append(a)
        out.append(args)
        pos = k
    return out

def clean_display(s):
    """Show nested tags in a display argument as the text they print."""
    out, i = [], 0
    pat = re.compile(r"\\(formal|var|hyp|concl)(?![A-Za-z@])")
    while (m := pat.search(s, i)):
        out.append(s[i:m.start()])
        k, args = m.end(), []
        for _ in range(TAGS[m.group(1)]):
            a, k = read_arg(s, k)
            args.append(a)
        out.append("" if m.group(1) == "formal" else clean_display(args[-1]))
        i = k
    return "".join(out) + s[i:]

def split_names(s):
    return [x.strip() for x in s.split(",") if x.strip()]

def parse_paper(path, envs):
    tex = open(path, encoding="utf-8").read()
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    items, untagged = [], []
    env_pat = "|".join(re.escape(e) for e in envs)
    spans = []
    for m in re.finditer(rf"\\begin\{{({env_pat})\*?\}}(.*?)\\end\{{\1\*?\}}", tex, re.S):
        env, body = m.group(1), m.group(2)
        spans.append((m.start(), m.end()))
        f = find_macros(body, "formal", 1)
        if not f:
            first = " ".join(body.split())[:70]
            untagged.append(f"{env}: {first}...")
            continue
        if len(f) > 1:
            raise ToolError(f"{env} has more than one \\formal tag: {[x[0] for x in f]}")
        vars_, hyps = {}, {}
        for names, t, d in find_macros(body, "var", 3):
            for n in split_names(names):
                vars_[n] = (t.strip(), clean_display(d.strip()))
        for names, t, d in find_macros(body, "hyp", 3):
            key = tuple(split_names(names))
            hyps[key] = (t.strip(), clean_display(d.strip()))
        items.append({"env": env, "name": f[0][0].strip(), "vars": vars_, "hyps": hyps,
                      "concl": [(t.strip(), clean_display(d.strip())) for t, d in find_macros(body, "concl", 2)]})
    # tags outside any checked environment are ignored by the checker: say so
    stray = []
    for tag, n in TAGS.items():
        for m in re.finditer(r"\\" + tag + r"(?![A-Za-z@])", tex):
            if not any(a <= m.start() < b for a, b in spans) and "newcommand" not in tex[max(0, m.start()-12):m.start()]:
                stray.append(tex[m.start():m.start() + 50].split("\n")[0])
    return items, untagged, stray

# =================================================================== normalization

UNICODE = {"≤": "<=", "≥": ">=", "≠": "<>", "∧": "/\\", "∨": "\\/", "¬": "~",
           "→": "->", "↔": "<->", "∃": "exists ", "∀": "forall "}

def make_norm(namespaces):
    nss = sorted(set(namespaces), key=len, reverse=True)
    def norm(s):
        for u, a in UNICODE.items():
            s = s.replace(u, a)
        for ns in nss:
            s = re.sub(rf"(?<![\w.]){re.escape(ns)}\.", "", s)
        s = re.sub(r"\bNat\b", "nat", s)
        s = " ".join(s.split())
        s = re.sub(r"\b(exists|forall) \((\w+) : ([^()]+)\),", r"\1 \2 : \3,", s)
        while s.startswith("(") and s.endswith(")") and balanced(s[1:-1]):
            s = s[1:-1].strip()
        return s
    return norm

def balanced(s):
    d = 0
    for c in s:
        d += (c == "(") - (c == ")")
        if d < 0:
            return False
    return d == 0

def to_lean(s):
    """Paper readings use one ASCII syntax; make it Lean-parsable."""
    s = s.replace("<->", "↔").replace("<>", "≠")
    s = re.sub(r"(?<![<\-])~(?!~)", "¬", s)
    return re.sub(r"\bnat\b", "Nat", s)

# ===================================================================== processes

WINDOWS_CODES = {0xC0000135: "a DLL it needs was not found (its bin folder is probably not on PATH)",
                 0xC0000005: "it crashed with an access violation"}

def with_bin_on_path(exe, env=None):
    env = dict(env or os.environ)
    d = os.path.dirname(os.path.abspath(shutil.which(exe) or exe))
    env["PATH"] = d + os.pathsep + env.get("PATH", "")
    return env

def run(cmd, check=True, **kw):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", **kw)
    except FileNotFoundError:
        raise ToolError(f"Could not run '{cmd[0]}'. Is it installed and on PATH? "
                        "Set LEAN, LAKE or COQC to point at it.")
    if check and r.returncode != 0:
        msg = f"prover failed (exit {r.returncode}) running: {' '.join(cmd)}"
        if "cwd" in kw:
            msg += f"  (in {kw['cwd']})"
        code = r.returncode & 0xFFFFFFFF
        if code in WINDOWS_CODES:
            msg += f"\nWindows error 0x{code:08X}: {WINDOWS_CODES[code]}."
        raise ToolError(msg + "\n" + ((r.stdout + r.stderr).strip() or "(no output)"))
    return r

# ===================================================================== Lean side

LEAN_DUMP = r'''import Lean
import {mod}
open Lean Meta Elab Command
set_option pp.funBinderTypes true

elab "#pfa_dump " id:ident : command => liftTermElabM do
  try
    let name ← realizeGlobalConstNoOverload id
    let ci ← getConstInfo name
    let axs ← collectAxioms name
    forallTelescope ci.type fun xs body => do
      let mut bs : Array Json := #[]
      for x in xs, i in [0:xs.size] do
        let d ← x.fvarId!.getDecl
        let nm := if d.userName.hasMacroScopes then s!"_arg{i+1}" else d.userName.toString
        bs := bs.push <| Json.mkObj [("name", toJson nm),
          ("type", toJson (toString (← ppExpr d.type))),
          ("isProp", toJson (← isProp d.type)),
          ("inst", toJson d.binderInfo.isInstImplicit)]
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
LEAN_TACTICS = ["exact Iff.rfl", "omega", "(simp; done)", "(constructor <;> intro h <;> omega)",
                "(constructor <;> intro h <;> simp_all)", "decide"]

class Lean:
    def __init__(self, src, lake_project=None):
        self.lean = os.environ.get("LEAN", "lean")
        self.tmp = tempfile.mkdtemp(prefix="pfa_")
        self.mod = "PFA_" + re.sub(r"\W", "_", os.path.splitext(os.path.basename(src))[0])
        shutil.copy(src, os.path.join(self.tmp, self.mod + ".lean"))
        base = []
        if lake_project:
            lake = os.environ.get("LAKE", "lake")
            probe = "import os,shutil;print(os.environ.get('LEAN_PATH',''));print(shutil.which('lean') or '')"
            out = run([lake, "env", sys.executable, "-c", probe], cwd=lake_project).stdout.splitlines()
            base = [os.path.normpath(os.path.join(os.path.abspath(lake_project), p))
                    for p in out[0].split(os.pathsep) if p]
            if len(out) > 1 and out[1].strip():
                self.lean = out[1].strip()
        else:
            prefix = run([self.lean, "--print-prefix"], env=with_bin_on_path(self.lean)).stdout.strip()
            base = [os.path.join(prefix, "lib", "lean")]
        self.env = with_bin_on_path(self.lean, dict(os.environ,
                       LEAN_PATH=os.pathsep.join(base + [self.tmp])))
        run([self.lean, "-o", self.mod + ".olean", self.mod + ".lean"], cwd=self.tmp, env=self.env)

    def signatures(self, names):
        dump = LEAN_DUMP.replace("{mod}", self.mod) + "".join(f"#pfa_dump {n}\n" for n in names)
        open(os.path.join(self.tmp, "Dump.lean"), "w", encoding="utf-8").write(dump)
        out = run([self.lean, "Dump.lean"], cwd=self.tmp, env=self.env).stdout
        sigs = {}
        for line in out.splitlines():
            if line.startswith("{"):
                j = json.loads(line)
                if not j.get("missing"):
                    j["bad_axioms"] = [a for a in j["axioms"] if a not in LEAN_OK_AXIOMS]
                    sigs[j["name"]] = j
        return sigs

    def prove(self, obligations, namespaces):
        """Each obligation: dict(ctx=[(name,type)], paper, formal, lemma). Returns list of bools."""
        if not obligations:
            return []
        lines = [f"import {self.mod}"]
        if namespaces:
            lines.append("open " + " ".join(sorted(namespaces)))
        ranges = []
        for k, ob in enumerate(obligations):
            start = len(lines) + 1
            ctx = " ".join(f"({n} : {t})" for n, t in ob["ctx"])
            alts = [f"(apply {ob['lemma']}; done)"] + LEAN_TACTICS
            lines.append(f"theorem pfa_obl_{k} {ctx} : ({to_lean(ob['paper'])}) ↔ ({ob['formal']}) := by")
            lines.append("  first")
            lines += [f"  | {a}" for a in alts]
            ranges.append((start, len(lines)))
        lines += [f"#print axioms pfa_obl_{k}" for k in range(len(obligations))]
        open(os.path.join(self.tmp, "Obl.lean"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
        r = run([self.lean, "Obl.lean"], check=False, cwd=self.tmp, env=self.env)
        out = r.stdout + r.stderr
        bad = {int(m.group(1)) for m in re.finditer(r"Obl\.lean:(\d+):\d+: error", out)}
        # an equivalence lemma proved with sorry must not count: check each obligation's axioms
        clean = set()
        for k in range(len(obligations)):
            if re.search(rf"'pfa_obl_{k}' does not depend on any axioms", out):
                clean.add(k)
            m = re.search(rf"'pfa_obl_{k}' depends on axioms: \[([^\]]*)\]", out)
            if m and all(a.strip() in LEAN_OK_AXIOMS for a in m.group(1).split(",")):
                clean.add(k)
        return [k in clean and not any(a <= b <= z for b in bad) for k, (a, z) in enumerate(ranges)]

# ===================================================================== Rocq side

ROCQ_DUMP = r'''From Align Require Import {mod}.
Ltac pfa_show_binders :=
  repeat match goal with H : ?A |- _ => idtac "BINDER" H ":" A; revert H end.
Ltac pfa_dump thm :=
  let t := type of thm in let D := fresh "pfa_dump" in
  assert t as D; [ intros; match goal with |- ?G => idtac "CONCL" G end;
                   pfa_show_binders; admit | clear D ].
'''
ROCQ_OK_AXIOMS = {"classic", "functional_extensionality_dep", "proof_irrelevance",
                  "propositional_extensionality"}
ROCQ_TACTICS = ["apply iff_refl", "(intros; split; intros; lia)", "tauto", "(intros; firstorder lia)"]

class Rocq:
    def __init__(self, src, flags=""):
        self.coqc = os.environ.get("COQC", "coqc")
        self.tmp = tempfile.mkdtemp(prefix="pfa_")
        self.mod = "PFA_" + re.sub(r"\W", "_", os.path.splitext(os.path.basename(src))[0])
        shutil.copy(src, os.path.join(self.tmp, self.mod + ".v"))
        self.env = with_bin_on_path(self.coqc)
        self.flags = shlex.split(flags) if flags else []
        # user flags may use paths relative to where the checker was started
        self.flags = [os.path.abspath(f) if os.path.exists(f) else f for f in self.flags]
        self.compile(self.mod + ".v")
        self.resolved = {}

    def compile(self, fname, check=True):
        return run([self.coqc] + self.flags + ["-R", ".", "Align", fname],
                   check=check, cwd=self.tmp, env=self.env)

    def write(self, fname, body):
        open(os.path.join(self.tmp, fname), "w", encoding="utf-8").write(body)

    def locate(self, names):
        """Map each paper name to the Rocq name that resolves (Paper.T -> T, M.t -> M.t)."""
        cands = {n: [".".join(n.split(".")[i:]) for i in range(len(n.split(".")))] for n in names}
        body = f"From Align Require Import {self.mod}.\n"
        for cs in cands.values():
            for c in cs:
                body += f'Goal True. idtac "PFA_LOC {c}". Abort.\nLocate {c}.\n'
        self.write("Locate.v", body)
        out = self.compile("Locate.v").stdout
        found, cur = set(), None
        for line in out.splitlines():
            if line.startswith("PFA_LOC "):
                cur = line.split(" ", 1)[1]
            elif cur and re.match(r"^(Constant|Inductive|Constructor)\s", line):
                found.add(cur)
        for n, cs in cands.items():
            hit = next((c for c in cs if c in found), None)
            if hit:
                self.resolved[n] = hit
        return self.resolved

    def signatures(self, names, kinds):
        self.locate(names)
        body = ROCQ_DUMP.replace("{mod}", self.mod)
        for n in names:
            if n not in self.resolved:
                continue
            s = self.resolved[n]
            if kinds.get(n) == "theorem":
                body += f'Goal True. idtac "THEOREM" "{n}". pfa_dump {s}. Abort.\n'
            body += f'Goal True. idtac "ASSUMPTIONS" "{n}". Abort.\nPrint Assumptions {s}.\n'
        self.write("Dump.v", body)
        out = self.compile("Dump.v").stdout
        sigs, cur, mode = {}, None, None
        def entry(n, kind):
            return sigs.setdefault(n, {"name": n, "kind": kind, "binders": [],
                                       "conclusion": "", "bad_axioms": []})
        for line in out.splitlines():
            if line.startswith("THEOREM "):
                cur, mode = line.split(" ", 1)[1], None
                entry(cur, "theorem")
            elif line.startswith("ASSUMPTIONS "):
                cur, mode = line.split(" ", 1)[1], "axioms"
                entry(cur, "definition")
            elif line.startswith("CONCL "):
                sigs[cur]["conclusion"] = line[6:]
            elif line.startswith("BINDER "):
                n, t = line[7:].split(" : ", 1)
                sigs[cur]["binders"].insert(0, {"name": n, "type": t})
            elif mode and mode.startswith("axioms"):
                if re.match(r"^[A-Z][\w ]*:$", line):
                    mode = "axioms:" + line[:-1]
                elif mode == "axioms:Axioms" and line and not line[0].isspace():
                    ax = re.split(r"\s|:", line, 1)[0]
                    if ax.split(".")[-1] not in ROCQ_OK_AXIOMS:
                        sigs[cur]["bad_axioms"].append(ax)
        return sigs

    def prove(self, obligations, namespaces):
        lemmas = [ob["lemma"] for ob in obligations]
        have = set(self.locate(lemmas).keys()) if lemmas else set()
        results = []
        for k, ob in enumerate(obligations):
            ctx = "".join(f"forall ({n} : {t}), " for n, t in ob["ctx"])
            alts = ([f"exact {self.resolved[ob['lemma']]}"] if ob["lemma"] in have else []) + ROCQ_TACTICS
            stmt = f"{ctx}({ob['paper']}) <-> ({ob['formal']})"
            body = (f"From Align Require Import {self.mod}.\nRequire Import Arith Lia.\n"
                    f"Lemma pfa_obl : {stmt}.\nProof. solve [{' | '.join(alts)}]. Qed.\n"
                    f'Goal True. idtac "ASSUMPTIONS" "pfa_obl". Abort.\nPrint Assumptions pfa_obl.\n')
            self.write(f"Obl{k}.v", body)
            r = self.compile(f"Obl{k}.v", check=False)
            # an equivalence lemma that was Admitted shows up as an axiom: it must not count
            axioms, section = [], None
            for line in r.stdout.split("ASSUMPTIONS", 1)[-1].splitlines():
                if re.match(r"^[A-Z][\w ]*:$", line):
                    section = line[:-1]
                elif section == "Axioms" and line and not line[0].isspace():
                    axioms.append(re.split(r"\s|:", line, 1)[0])
            clean = all(a.split(".")[-1] in ROCQ_OK_AXIOMS for a in axioms)
            results.append(r.returncode == 0 and "ASSUMPTIONS" in r.stdout and clean)
        return results

# ===================================================================== comparison

def compare(items, sigs, norm, prover, prover_name, namespaces):
    fails, notes, review, obligations = [], [], [], []
    for it in items:
        n, sig = it["name"], sigs.get(it["name"])
        tag = f"{it['env']} {n}"
        it["status"] = "ok"
        if sig is None:
            fails.append(f"{tag}: not found in the formalization")
            it["status"] = "fail"
            continue
        if sig["bad_axioms"]:
            fails.append(f"{tag}: depends on {', '.join(sig['bad_axioms'])} (sorry/Admitted or extra axioms)")
            it["status"] = "fail"
        if it["env"] in ("definition", "defn"):
            review.append((tag, "(definition)", "read the formal definition once", None))
            continue
        short = n.split(".")[-1]
        fb = {b["name"]: b for b in sig["binders"]}
        tagged = set(it["vars"]) | {x for key in it["hyps"] for x in key}
        for b in fb.keys() - tagged:
            fails.append(f"{tag}: formal statement has '{b} : {norm(fb[b]['type'])}', which the paper never states")
        for b in tagged - fb.keys():
            fails.append(f"{tag}: paper tags '{b}', which the formal statement lacks")
        for v, (t, d) in it["vars"].items():
            if v in fb:
                if fb[v].get("isProp"):
                    fails.append(f"{tag}: '{v}' is tagged as a variable but is a hypothesis formally")
                elif norm(t) != norm(fb[v]["type"]):
                    fails.append(f"{tag}: variable '{v}' has type '{norm(t)}' in the paper but '{norm(fb[v]['type'])}' formally")
            review.append((tag, d, t, None))
        ctx = [(b["name"], b["type"]) for b in sig["binders"] if b["name"] in it["vars"]]
        def want(paper, formal, label, lemma, display):
            if re.search(r"\b(sorry|admit|Admitted)\b", paper):
                fails.append(f"{tag}: {label} reading contains a proof escape")
                return
            if norm(paper) == norm(formal):
                review.append((tag, display, paper, None))
            else:
                obligations.append({"tag": tag, "label": label, "paper": paper, "formal": formal,
                                    "ctx": ctx, "lemma": lemma, "display": display})
        for key, (t, d) in it["hyps"].items():
            if all(x in fb for x in key):
                conj = " ∧ " if prover_name == "lean" else " /\\ "
                formal = conj.join(f"({fb[x]['type']})" for x in key) if len(key) > 1 else fb[key[0]]["type"]
                want(t, formal, f"hypothesis '{','.join(key)}'", f"pfa_eq_{short}_{'_'.join(key)}", d)
        if len(it["concl"]) != 1:
            fails.append(f"{tag}: needs exactly one \\concl tag (found {len(it['concl'])})")
        else:
            t, d = it["concl"][0]
            want(t, sig["conclusion"], "conclusion", f"pfa_eq_{short}_concl", d)
    if obligations:
        proved = prover.prove(obligations, namespaces)
        for ob, ok in zip(obligations, proved):
            if ok:
                notes.append(f"{ob['tag']}: {ob['label']} '{norm(ob['paper'])}' proved equivalent to formal "
                             f"'{norm(ob['formal'])}'")
                review.append((ob["tag"], ob["display"], ob["paper"], norm(ob["formal"])))
            else:
                fails.append(f"{ob['tag']}: {ob['label']} is '{norm(ob['paper'])}' in the paper but "
                             f"'{norm(ob['formal'])}' formally, and no equivalence could be proved")
    return fails, notes, review

# ===================================================================== main

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="PFA: check a tagged LaTeX paper against ONE formalization.")
    ap.add_argument("paper", help="the tagged LaTeX source (.tex)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--lean", help="Lean file")
    g.add_argument("--rocq", help="Rocq/Coq .v file")
    ap.add_argument("--lake-project", help="Lean project folder (for Mathlib or other dependencies)")
    ap.add_argument("--coq-flags", default="", help='extra coqc flags, e.g. "-Q theories MyLib"')
    ap.add_argument("--namespace", action="append", default=[], help="extra namespace to ignore when comparing")
    ap.add_argument("--env", action="append", default=[], help="extra LaTeX environment name to check")
    ap.add_argument("--require-proved", action="append", default=[],
                    help="formal name that must exist and be fully proved (e.g. appended tests)")
    ap.add_argument("--json", help="also write results as JSON to this file")
    ap.add_argument("--keep-temp", action="store_true", help="keep the prover's temporary folder")
    a = ap.parse_args()
    try:
        if not a.paper.lower().endswith(".tex"):
            raise ToolError(f"'{a.paper}' is not a .tex file; pass the LaTeX source.")
        items, untagged, stray = parse_paper(a.paper, DEFAULT_ENVS + a.env)
        names = [it["name"] for it in items]
        extra = [n for n in a.require_proved if n not in names]
        namespaces = set(a.namespace) | {".".join(n.split(".")[:i]) for n in names + extra
                                         for i in range(1, len(n.split(".")))}
        norm = make_norm(namespaces)
        if a.lean:
            prover, pname = Lean(a.lean, a.lake_project), "lean"
            sigs = prover.signatures(names + extra)
            lean_ns = {ns for ns in namespaces if any(s.startswith(ns + ".") for s in sigs)}
        else:
            prover, pname = Rocq(a.rocq, a.coq_flags), "rocq"
            kinds = {it["name"]: ("definition" if it["env"] in ("definition", "defn") else "theorem") for it in items}
            kinds.update({n: "proved" for n in extra})
            sigs = prover.signatures(names + extra, kinds)
            lean_ns = set()
        fails, notes, review = compare(items, sigs, norm, prover, pname, lean_ns)
        for n in a.require_proved:
            s = sigs.get(n)
            if s is None:
                fails.append(f"required proof {n}: not found")
            elif s["bad_axioms"]:
                fails.append(f"required proof {n}: depends on {', '.join(s['bad_axioms'])}")
    except (ToolError, OSError) as e:
        print(f"TOOL ERROR: {e}")
        sys.exit(3)
    if not a.keep_temp:
        shutil.rmtree(prover.tmp, ignore_errors=True)

    print(f"Checked {len(items)} tagged statements against {a.lean or a.rocq}\n")
    status = "FAIL" if fails else ("INCOMPLETE" if untagged else "PASS")
    if fails:
        print("MISMATCHES")
        for f in fails:
            print("  ✗", f)
        print()
    if untagged:
        print("UNTAGGED STATEMENTS (not checked)")
        for u in untagged:
            print("  ?", u)
        print()
    if stray:
        print("TAGS OUTSIDE A CHECKED ENVIRONMENT (ignored; use --env NAME to include)")
        for s in stray:
            print("  ?", s)
        print()
    if notes:
        print("EQUIVALENCES PROVED BY THE PROVER")
        for n in notes:
            print("  ≡", n)
        print()
    if not fails and review:
        print("Human review (does each display text mean its formal reading?)")
        w = max(len(d) for _, d, _, _ in review)
        last = None
        for tag, d, t, eq in review:
            if tag != last:
                print(f"  {tag}")
                last = tag
            print(f"      {d:<{w}}  ⟷  {t}" + (f"   (≡ {eq})" if eq else ""))
        print()
    msg = {"PASS": "Paper and formalization agree on every tagged statement.",
           "FAIL": "Paper and formalization do not agree.",
           "INCOMPLETE": "Tagged statements agree, but some statements are untagged."}[status]
    print(f"Result: {status}. {msg}")
    if a.json:
        json.dump({"status": status, "fails": fails, "untagged": untagged, "stray": stray,
                   "equivalences": notes, "review": [list(r) for r in review]},
                  open(a.json, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.exit({"PASS": 0, "FAIL": 1, "INCOMPLETE": 2}[status])

if __name__ == "__main__":
    main()
