---
name: paper-formal-alignment
description: Link a LaTeX mathematics paper to its Lean or Rocq (Coq) formalization by tagging the paper's definitions and theorem statements with their formal readings, then machine-check with PFA that every tagged statement matches the formal one, and report where they disagree. Use this whenever someone wants to know whether a paper and its formalization agree, asks to align, link or tag a paper to Lean/Rocq/Coq code, asks whether an autoformalization or AI-generated formal proof is faithful to the paper, or mentions PFA, align.sty, \formal tags or check_alignment.py, even if they never say "alignment".
---

# Paper–Formal Alignment (PFA)

A Lean or Rocq proof guarantees the *formal* theorem. It says nothing about whether that
theorem is the one the paper claims. This skill closes that gap for definitions and theorem
statements (never proofs):

1. **You link.** In a copy of the paper, you tag every definition and theorem with the formal
   object it corresponds to, and tag each variable, hypothesis and conclusion with its formal
   reading, written from the paper.
2. **PFA checks.** `scripts/check_alignment.py` asks the prover for the real signatures and
   compares binder by binder. Where your reading and the formal text differ, it asks the prover
   to prove them equivalent. Anything unproved is a mismatch.
3. **You report.** A tagged copy that passes, or a precise list of where paper and formalization
   disagree.

The whole value rests on one thing: **your readings come from the paper, and the checker compares
them to the formalization.** If you copy readings from the formal statements, the check becomes
circular and certifies nothing. A mismatch is a result to report, not a bug to make disappear.

## Bundled files

Paths below are relative to the skill folder. If you are working from the GitHub repository
instead of an installed skill, the skill folder is `pfa/` and `examples/` is at the repository root.

- `scripts/check_alignment.py`: the checker. Run with `--help` for all options.
- `scripts/skeleton.py`: lists formal declarations with binder *names* only (no statements).
- `scripts/verify_copies.py`: proves your copies changed nothing they weren't allowed to.
- `assets/align.sty`: the four tag macros.
- `examples/triangular/`: a tagged paper with matching Lean and Rocq files, plus a drifted Lean
  file that fails. Use it to confirm the setup works, and as a model of good tagging.
- `examples/oddsum/`: a complete run of this workflow. `input/` is an untagged paper and a Lean
  file with a planted mismatch; `aligned/` is the result, including equivalence lemmas, tests and
  the report. Read its `ALIGNMENT_REPORT.md` before writing your first report.
- `references/troubleshooting.md`: prover setup (Windows, Rocq 9, Mathlib/lake projects). Read it
  when the checker reports a TOOL ERROR.

## Ground rules

1. **Never edit the originals.** Work in a new `aligned/` folder.
2. **Paper copy: tags only.** Every character a reader sees stays exactly as written.
   `verify_copies.py` enforces this byte for byte.
3. **Formal copy: append only.** You may add a section at the end, starting with a comment line
   containing `PFA additions`. Existing lines never change.
4. **Readings come from the paper.** Look at the formalization for *names* (declarations and
   binders) via `skeleton.py`. Do not read the formal statements before you have written the
   readings. If formal statements were already in your context (the user pasted them, say), you
   cannot unsee them: say so under "Independence" in the report.
5. **Fix only your own mistakes.** A wrong link, a typo, an unparseable reading or a misreading
   of the paper is yours to fix. A difference in meaning between paper and formalization is a
   finding: leave the tag as the paper says and report it.

## Workflow

### 1. Set up

```bash
mkdir aligned
cp PAPER.tex aligned/paper.tex
cp FORMAL.lean aligned/          # or FORMAL.v
cp <skill>/assets/align.sty aligned/
```

Confirm the prover works by running the checker on `examples/triangular` (Lean:
`--lean Triangular.lean`, Rocq: `--rocq Triangular.v`). It must print `Result: PASS`. If it
prints `TOOL ERROR`, read `references/troubleshooting.md`.

Check for macro clashes: if the paper or its preamble already defines `\formal`, `\var`, `\hyp` or
`\concl`, stop and report it. Tagging would change the paper's meaning.

### 2. Inventory both sides

- **Paper:** list every definition, theorem, lemma, proposition, corollary and example. The checker
  scans `definition, defn, theorem, thm, lemma, lem, proposition, prop, corollary, cor, example,
  claim, fact`. For other environment names, pass `--env NAME` on every run.
- **Formalization:** `python scripts/skeleton.py aligned/FORMAL.lean` lists names, binder names and
  doc comments, not statements. It is regex-based, so treat it as a guide.

### 3. Link

Pair each paper item with a formal declaration, using numbering in doc comments, names, binder
names and roles. Keep a list of anything unpaired on either side for the report. An unpaired paper
item stays untagged, and the checker will report it as untagged.

### 4. Write readings and tag the copy

Add `\usepackage{align}` to the preamble on its own line. Then tag, using the formal binder names:

| Tag | Use | Prints |
|---|---|---|
| `\formal{Name}` | right after `\begin{env}` (and any `[title]` or `\label`), no added whitespace | nothing |
| `\var{name}{type}{display}` | a variable; `name` may be `a,b` for several | display |
| `\hyp{name}{reading}{display}` | a hypothesis; `h1,h2` means their conjunction | display |
| `\concl{reading}{display}` | the conclusion, exactly one per theorem or example | display |

`display` is the paper's original text, character for character. Wrap the smallest span that
states the thing. Example, from the bundled paper:

```latex
\begin{theorem}\label{thm:square}\formal{Paper.T_add_T_pred}
Let \var{n}{nat}{$n$} be a natural number with \hyp{h_pos}{1 <= n}{$n \geq 1$}.
Then \concl{T n + T (n - 1) = n * n}{$T(n) + T(n-1) = n^2$}.
\end{theorem}
```

Readings are written from the paper in one ASCII syntax for both provers:

- Operators: `<= >= <> /\ \/ ~ -> <->`, `exists x : T, P`, `forall x : T, P`, `=`, `+ - * / ^ mod`
  as the prover spells them (Lean `n % 2`, Rocq `n mod 2`).
- Types: `nat` for natural numbers. Other types use the prover's names (Lean `Int`, `Real`;
  Rocq `Z`, `R`).
- Names: drop the namespace (`T n`, not `Paper.T n`). The checker opens it.
- When a reading differs textually from the formal one, the prover parses it, so it must be valid in
  that prover. For Lean the checker converts `~` to `¬`, `<>` to `≠`, `<->` to `↔` and `nat` to `Nat`.

Situations that come up:

- **Ambiguity** (does ℕ include 0? does "smooth" mean C^∞?): choose the reading the paper's own
  conventions support, and log the choice in the report.
- **Standing assumptions** stated outside the environment ("Throughout, p is an odd prime"): tag
  with an empty display, `\hyp{hp}{reading}{}`, and list it in the report with where the paper
  states it.
- **A formal binder the paper never states:** do not tag it. The checker will flag it, and that is
  a finding.
- **The paper states something the formalization lacks:** tag it anyway. The checker will flag it.

### 5. Verify the paper copy

```bash
python scripts/verify_copies.py --paper PAPER.tex aligned/paper.tex
```

It must say `PAPER: OK`. If not, the diff shows what your tagging changed. Fix it.

### 6. Run the checker and iterate

```bash
python scripts/check_alignment.py aligned/paper.tex --lean aligned/FORMAL.lean --json aligned/pfa.json
```

Exit codes: 0 PASS, 1 FAIL, 2 INCOMPLETE (untagged statements), 3 TOOL ERROR. Sort every mismatch
into one category:

- **Your linking error:** wrong `\formal` target, binder name typo, reading that doesn't parse,
  a misreading of the paper. Fix it by re-reading the *paper*, never by copying the formal side.
- **Equivalent, but the prover's tactics couldn't show it:** the checker tries `Iff.rfl`, `omega`,
  `simp`, `decide` (Lean) or `iff_refl`, `lia`, `tauto`, `firstorder` (Rocq). If you are
  confident the two say the same thing (`n ^ 2` vs `n * n`, "even" as `exists k, n = 2 * k` vs
  `n % 2 = 0`), append a fully proved lemma to the formal copy named
  `pfa_eq_<theorem>_<binder>` (or `pfa_eq_<theorem>_concl`, and `pfa_eq_<theorem>_h1_h2` for a
  comma tag), stating `∀ variables, reading ↔ formal`:
  ```lean
  theorem pfa_eq_S_eq_sq_concl (n : Nat) : (S n = n ^ 2) ↔ (S n = n * n) := by
    rw [Nat.pow_two]
  ```
  `<theorem>` is the last component of the `\formal` name. The checker finds the lemma and uses
  it to close the obligation, and the prover checks that its statement is exactly the obligation.
  A lemma stating anything else is simply not used. If you cannot prove it, they may not be
  equivalent: treat it as substantive.
- **Substantive:** a different hypothesis, type or conclusion, an extra or missing binder, or a
  proof that relies on `sorry`, `Admitted` or a non-standard axiom. Change nothing. Report it.
- **Tool error:** see `references/troubleshooting.md`. Never edit the checker's comparison logic.

### 7. Strengthen the formal copy (append only)

In the appended `PFA additions` section, add fully proved:

- **Definition tests:** concrete facts the paper states about its own definitions (worked
  examples, small cases). If a fact has its own example environment, point its `\formal` at the
  test. Wrong definitions usually fail one.
- **Non-vacuity:** for each theorem with hypotheses, a proof that they can all hold at once, so
  the theorem is not true merely because its assumptions are contradictory.

Pass each untagged one to the checker as `--require-proved NAME` so its proof is checked. A test
you cannot prove is a finding about the definition: leave it out and report it.

### 8. Final run and report

Run the checker once more (saving its output to `aligned/checker_output.txt`) and
`verify_copies.py` with both `--paper` and `--formal`. Then write `aligned/ALIGNMENT_REPORT.md`:

```markdown
# Alignment report: <paper title>

**Verdict:** ALIGNED | MISALIGNED | INCOMPLETE
<one sentence on why>

## Substantive mismatches
<each: paper statement (quoted display text), formal statement, what differs,
which side looks wrong and why. "None." if none.>

## Coverage
<paper items not formalized; formal declarations with no paper counterpart>

## Readings that needed judgment
<ambiguities and standing assumptions, with the choice made>

## Equivalence lemmas added
<pfa_eq_* lemmas, one line each on why the two forms are the same>

## Definition tests and non-vacuity
<what was proved; anything that failed>

## Independence
<"Readings written before reading formal statements", or what was seen early>

## For the human reviewer
<the checker's review table, and the definitions a person must read once>
```

**Verdict rules.** ALIGNED requires all of: checker `Result: PASS`, `verify_copies.py` OK for both
copies, every paper definition and theorem tagged, every substantive formal declaration matched or
listed. MISALIGNED: at least one substantive mismatch. INCOMPLETE: anything else (untagged items,
tool errors, unresolved equivalences). Report the verdict the evidence supports, and never ALIGNED
without a checker PASS from the final files.

Deliver `aligned/` containing: `paper.tex` (tagged), `align.sty`, the formal copy,
`checker_output.txt`, `pfa.json` and `ALIGNMENT_REPORT.md`.

## What PFA does not check

Say so in the report when relevant, rather than overclaiming:

- **What definitions mean.** PFA checks that statements use the same definitions, not that those
  definitions mean what the paper's words mean. That is the human reviewer's one job.
- **Proofs.** The prover checks those.
- **Display text against its reading.** Whether `$n \geq 1$` really means `1 <= n` is the review
  table's job.
