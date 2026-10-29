# PFA: Paper–Formal Alignment

A Lean or Rocq proof guarantees that the *formal* theorem is true. It says nothing about whether that formal theorem is the one the paper claims. Formalizations drift: a hypothesis gets added, a definition gets weakened, a conclusion gets narrowed. If the paper and its formalization disagree, reading either one is wasted effort.

PFA checks that a LaTeX paper's definitions and theorem statements match its Lean or Rocq formalization, before anyone reads either. Proofs are never compared, only statements, and the prover itself does the comparing.

## Why this is feasible despite the impossibility results

Recent work (Bastounis et al., *Navier-Stokes lost in translation*, arXiv 2610.08144) shows that faithfully resolving ambiguity in arbitrary natural-language math is harder than the halting problem. That is a worst-case result about a universal procedure. It does not rule out checking specific papers, for the same reason that finding proofs is undecidable while checking a supplied proof is easy.

The fix is to supply the certificate:

1. **Remove ambiguity at the source.** Each statement in the LaTeX names the formal object it means, and each hypothesis and conclusion carries an explicit formal reading.
2. **Let the prover compare.** Binder names must match exactly. Where a reading and the formal text differ, the prover must prove them equivalent.
3. **Check only what matters.** Only definitions and theorem statements need to match, a small, structured surface.

A mismatch like "the paper assumes a forcing term, the formal statement presents unforced blow-up" becomes an extra or missing hypothesis, which the checker reports.

## How it works

### 1. Tag the paper

`align.sty` defines four macros. Each prints only its display text, so the PDF is unchanged.

```latex
\usepackage{align}

\begin{theorem}\formal{Paper.T_add_T_pred}
Let \var{n}{nat}{$n$} be a natural number with \hyp{h_pos}{1 <= n}{$n \geq 1$}.
Then \concl{T n + T (n - 1) = n * n}{$T(n) + T(n-1) = n^2$}.
\end{theorem}
```

| Tag | Meaning |
|---|---|
| `\formal{Name}` | the formal declaration this environment states |
| `\var{name}{type}{display}` | a variable; `a,b` tags several |
| `\hyp{name}{reading}{display}` | a hypothesis; `h1,h2` means their conjunction |
| `\concl{reading}{display}` | the conclusion |

Names are the formal binder names. Readings use one ASCII syntax for both provers: `<= >= <> /\ \/ ~ -> <->`, `exists x : T, P`, `nat`.

### 2. The formal statement

Binder names match the tags:

```lean
theorem T_add_T_pred (n : Nat) (h_pos : 1 ≤ n) : T n + T (n - 1) = n * n := ...
```

```coq
Theorem T_add_T_pred (n : nat) (h_pos : 1 <= n) : T n + T (n - 1) = n * n.
```

### 3. Check

```sh
python pfa/scripts/check_alignment.py paper.tex --lean Formal.lean
python pfa/scripts/check_alignment.py paper.tex --rocq Formal.v
```

For every tagged statement the checker asks the prover for the real signature and fails on:

- a formal binder the paper never states, or a tagged one the formalization lacks;
- a variable whose type differs;
- a hypothesis or conclusion whose reading differs from the formal one, unless the prover proves them equivalent, either automatically (`omega`, `simp`, `lia`, ...) or through an appended lemma named `pfa_eq_<theorem>_<binder>`;
- anything that depends on `sorry`, `Admitted` or a non-standard axiom.

It also reports theorem-like environments that were never tagged. Exit codes: 0 PASS, 1 FAIL, 2 INCOMPLETE, 3 TOOL ERROR.

### 4. Cheap extra checks

- **Definition tests.** Concrete facts the paper states about its definitions (worked examples, small cases) become proved theorems. Wrong definitions almost always fail one.
- **Non-vacuity.** Prove each theorem's hypotheses can all hold at once, so it isn't true merely because its assumptions contradict each other.
- **Independent formalization (optional, strongest).** Formalize the statement twice from the paper alone, then prove the versions equivalent.

### What remains for a human

On a pass, the checker prints a review table pairing each piece of display text with its formal reading (`$n \geq 1$ ⟷ 1 <= n`). A person checks that each pair means the same thing, and reads each new definition once to confirm it means what the paper's words mean. Definitions from Mathlib or the Rocq standard library have already had that check.

## Using it with an AI

The `pfa/` folder is also an AI skill. Given an untagged paper and a formalization, an AI using it copies the paper, does the linking itself, writes readings from the paper, runs the checker on its own work, fixes its own linking mistakes, proves notational equivalences, and reports where paper and formalization truly disagree. Mismatches are findings: the skill never changes a reading to make the check pass.

- **Claude:** install `dist/paper-formal-alignment.skill` (claude.ai, where your account allows skills, or unzip it into a Claude Code skills folder).
- **Other AI tools that can run code:** use `prompts/align-without-skills.md`.
- **Already-tagged papers:** use `prompts/check-tagged-paper.md` for an independent check.

`examples/oddsum/` shows a complete run on a paper with a planted mismatch, including the final report.

## Repository layout

```
pfa/                    the tool, and the skill's source
  SKILL.md              the workflow (for AIs, and a precise guide for people)
  scripts/
    check_alignment.py  the checker
    skeleton.py         lists formal declarations and binder names, without statements
    verify_copies.py    proves a tagged copy changed nothing but tags
  assets/align.sty      the tag macros
  references/troubleshooting.md
examples/
  triangular/           a tagged paper, Lean and Rocq formalizations, drifted versions
  oddsum/               a full AI run: untagged input, aligned output, report
prompts/                prompts for AI tools without skill support
dist/                   the packaged skill (rebuild with: python build_skill.py)
```

## Quick start

```sh
cd examples/triangular
python ../../pfa/scripts/check_alignment.py paper.tex --lean Triangular.lean
python ../../pfa/scripts/check_alignment.py paper.tex --rocq Triangular.v
```

Both should print `Result: PASS`. The `_drifted` files should fail. If the prover can't be found or crashes, see `pfa/references/troubleshooting.md` (it covers Windows, Rocq 9 and Mathlib projects).

## Limits

- PFA checks that statements agree. It does not check what definitions mean; that is the human review step.
- Readings are written in the prover's own syntax, so tagging needs some familiarity with Lean or Rocq.
- The checker is tested with Lean 4.19 and Coq 8.18 on Linux, including a small Lake project. An earlier version also ran on Rocq 9.0.1 under Windows. It has not yet been tested on a Mathlib project.

## License

MIT
