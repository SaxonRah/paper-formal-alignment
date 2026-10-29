# Checkable Papers: Aligning LaTeX Statements with Lean or Rocq

## The problem

A Lean or Rocq proof guarantees that the *formal* theorem is true. It says nothing about whether that formal theorem is the one the paper claims. Formalizations drift: a hypothesis gets added, a definition gets weakened, a conclusion gets narrowed. If the paper and its formalization disagree, reading either one is wasted effort.

## Why this is feasible despite the impossibility results

Recent work (Bastounis et al., *Navier-Stokes lost in translation*, arXiv 2610.08144) shows that faithfully resolving ambiguity in arbitrary natural-language math is harder than the halting problem. That is a worst-case result about a universal procedure. It does not rule out checking specific papers, for the same reason that finding proofs is undecidable while checking a supplied proof is easy.

The fix is to make the author supply the certificate:

1. **Remove ambiguity at the source.** Symbols in the LaTeX are bound to formal definitions, so `u` means `NS.solution`, not "whatever the reader assumes."
2. **Supply the alignment explicitly.** Every hypothesis in a theorem statement is tagged with the formal binder it corresponds to.
3. **Check only what matters.** Proofs never need to match. Only definitions and theorem statements do, which is a small, structured surface.

A mismatch like "the paper assumes a forcing term, the formal statement presents unforced blow-up" becomes an untagged or missing hypothesis, which a script catches.

## Step 1: Semantic macros in LaTeX

A tiny package. Each macro prints normally but carries a formal name a checker can extract.

```latex
% align.sty
\newcommand{\formal}[1]{}        % \formal{Name}: links a statement to its formal theorem
\newcommand{\sym}[2]{#2}         % \sym{FormalName}{display}: binds a symbol to a definition
\newcommand{\hyp}[2]{#2}         % \hyp{binder}{text}: tags a hypothesis with its formal binder
\newcommand{\concl}[2]{#2}       % \concl{FormalName}{text}: tags the conclusion
```

Usage:

```latex
\begin{theorem}\formal{Paper.main_theorem}
Let $u_0$ be \hyp{h_smooth}{smooth} and let the forcing $f$ be
\hyp{h_force}{smooth and compactly supported}. Then the solution
\sym{NS.solution}{$u$} \concl{BlowsUp}{blows up in finite time}.
\end{theorem}
```

The PDF reads like any paper. The source now states exactly which formal objects it means.

## Step 2: The formal statement

Binder names match the tags. (Definitions here are schematic.)

**Lean**

```lean
theorem Paper.main_theorem (u₀ : VelocityField) (f : Forcing)
    (h_smooth : Smooth u₀)
    (h_force : Smooth f ∧ HasCompactSupport f) :
    BlowsUp (NS.solution u₀ f) := by
  sorry
```

**Rocq**

```coq
Theorem main_theorem (u0 : velocity_field) (f : forcing)
  (h_smooth : smooth u0)
  (h_force : smooth f /\ compact_support f) :
  blows_up (ns_solution u0 f).
Proof. Admitted.
```

## Step 3: The alignment check

A script compares the two sides and fails on any mismatch.

- **Extract from LaTeX:** every `\formal`, `\hyp`, `\sym`, `\concl` tag (a regex works for a first version).
- **Extract from the prover:** the theorem's signature, via `#check @Paper.main_theorem` in Lean or `Check main_theorem.` / `About main_theorem.` in Rocq. A Lean metaprogram or Rocq plugin is sturdier than parsing printed output.
- **Compare:**
  - Every `\hyp` tag must name a binder in the formal theorem.
  - Every propositional binder in the formal theorem must be tagged in the paper. An untagged binder means the formalization assumes something the paper does not say.
  - Every `\sym` and `\concl` must name a definition that actually appears in the formal statement.

## Step 4: Cheap extra checks

These catch errors the tag comparison cannot.

- **No hidden assumptions.** `#print axioms Paper.main_theorem` (Lean) or `Print Assumptions main_theorem.` (Rocq) must show no `sorry`, `Admitted`, or project-specific axioms.
- **Non-vacuity.** Prove the hypotheses can be satisfied, so the theorem is not true because its assumptions are contradictory:
  ```lean
  example : ∃ u₀ f, Smooth u₀ ∧ Smooth f ∧ HasCompactSupport f := ...
  ```
- **Definition tests.** Every concrete fact the paper states about a new definition ("for n = 2 this reduces to...", worked examples) becomes an `example` (Lean) or `Example` (Rocq) that must be proved. Wrong definitions almost always fail one.
- **Independent formalization (optional, strongest).** Formalize the statement twice, independently, from the paper alone, then prove the two versions equivalent. That equivalence is a real formal guarantee.

## What remains for a human

One thing: confirming that each bound definition (`NS.solution`, `BlowsUp`, `Smooth`) means what mathematicians mean by those words. That check happens once per definition, not once per paper, and definitions taken from Mathlib or the Rocq standard library have already had it.

Everything else (does the formal theorem state what the paper states, with the same hypotheses) becomes mechanical.

---

# Triangular Example
An example is provided under triangular folder. 

Read it's README.md for information on usage.

Triangle Example Passing Output:
```powershell
PS C:\triangular\> $env:COQC = "C:\Rocq-Platform~9.0~2025.08\bin\coqc.exe"
PS C:\triangular\> python check_alignment.py paper.tex --rocq Triangular.v
Checked 5 tagged statements against Triangular.v

All definitions, hypotheses and conclusions match.

Human review (does each display text mean its formal reading?)
  definition Paper.T
      (definition)                             <->  read the formal definition once
  example Paper.T_four
      $T(4) = 10$                              <->  T 4 = 10
  theorem Paper.two_mul_T
      $n$                                      <->  nat
      $2\,T(n) = n(n+1)$                       <->  2 * T n = n * (n + 1)
  theorem Paper.T_add_T_pred
      $n$                                      <->  nat
      $n \geq 1$                               <->  1 <= n
      $T(n) + T(n-1) = n^2$                    <->  T n + T (n - 1) = n * n
  example Paper.T_add_T_pred_nonvacuous
      some natural number satisfies $n \geq 1$ <->  exists n : nat, 1 <= n

Result: PASS
```

Triangle Example Failing Output:
```powershell
PS C:\triangular\> python check_alignment.py paper.tex --rocq Triangular_drifted.v
Checked 5 tagged statements against Triangular_drifted.v

MISMATCHES
  XXX: theorem Paper.T_add_T_pred: depends on T_add_T_pred (sorry/Admitted or extra axioms)
  XXX: theorem Paper.T_add_T_pred: 'h_pos' is '1 <= n' in the paper but '2 <= n' formally

Result: FAIL. Paper and formalization do not agree.
```


---

# AI ASSISTANCE
Interestingly this link can be checked/tested and even automagically generated by the AI itself. 

## Checking:
Edit the `PATH/TO/` areas with your documents.
```
You are checking whether a mathematics paper and its formalization agree, using PFA
(Paper–Formal Alignment): https://github.com/SaxonRah/paper-formal-alignment

Your job is to find out WHETHER they agree, not to MAKE them agree.

INPUTS
- Paper (LaTeX source): <PATH/TO/paper.tex>
- Formalization: <PATH/TO/Formal.lean or Formal.v>   Prover: <Lean | Rocq>
- PFA: triangular/check_alignment.py and triangular/align.sty in the repo.
  Read triangular/README.md and triangular/paper.tex first. They are a complete worked example.

GROUND RULES
1. Never edit the originals. Work in a new folder aligned/ containing copies.
2. In the paper copy you may ONLY add alignment tags. Every word, symbol and formula a
   reader sees must stay exactly as written.
3. In the formalization copy you may NOT change any existing line. You may only append
   a clearly marked section at the end (step 5).
4. Mismatches are findings. If the paper and formalization disagree, never change a tag,
   hypothesis, type or definition to make the check pass. Record it and move on.
5. Never report a pass the checker did not print.

TAG SYNTAX (this is what the checker parses; the top-level README shows an older
2-argument version, so ignore that one)
  \formal{Name}               right after \begin{...}: the formal object this environment states
  \var{name}{type}{display}   a variable of the statement
  \hyp{name}{formal}{display} a hypothesis
  \concl{formal}{display}     the conclusion (exactly one per theorem or example)
- `name` must equal the binder name in the formalization.
- `display` must be the paper's original text, character for character.
- Formal readings use one ASCII syntax for both provers: <= >= <> /\ \/ ~ -> <->,
  "exists x : T, ...", "forall x : T, ...", and Rocq-style type names (nat, not Nat).
- The checker strips only the `Paper.` namespace when comparing. If the formalization
  uses another namespace, run the checker once to see how it prints names (see step 7c).

STEPS
1. Inventory. List every definition, theorem, lemma, proposition, corollary and stated
   example in the paper, and every top-level definition and theorem in the formalization.
   The checker only scans these environments: definition, theorem, lemma, proposition,
   corollary, example. If the paper uses others (thm, lem, prop, ...), add them to the
   `envs` pattern in your copy of the checker and say so in the report. Otherwise they
   are silently skipped.

2. Match. Pair each paper item with its formal counterpart. Report anything unpaired as
   "paper statement not formalized" or "formal statement with no paper counterpart".

3. Write readings FROM THE PAPER. For each paired statement, write the formal reading of
   every variable, hypothesis and conclusion from the paper text alone, BEFORE reading
   the formal statement. From the formalization, look only at names: definition names,
   theorem names and binder names. For example:
     grep -nE "^\s*(theorem|lemma|def|Theorem|Lemma|Definition|Fixpoint|Example)" <file>
   If the paper is ambiguous (does N include 0? does "smooth" mean C^infinity?), pick the
   reading the paper's own conventions support and log the ambiguity.

4. Tag the copy. Add \usepackage{align}, copy align.sty next to the paper, and wrap the
   existing text in tags. Do not reword anything.

5. Strengthen the formal copy (append only). Below a comment line
   "PFA additions (appended; nothing above this line was changed)", add:
   - Definition tests: each concrete fact the paper states about a definition it
     introduces (worked examples, small cases) as a named theorem. If the fact sits in
     its own example environment, point that environment's \formal at the new theorem.
     Otherwise list it in the report.
   - Non-vacuity: for each theorem with hypotheses, prove they can all hold at once.
   - Notational equivalences (step 7a).
   Everything appended must be fully proved: no sorry, Admitted or new axioms. If you
   cannot prove a definition test or non-vacuity lemma, leave it out and report it. A
   failed definition test is a finding about the definition.

6. Run the checker and save its full output:
     python check_alignment.py aligned/paper.tex --lean aligned/Formal.lean
     python check_alignment.py aligned/paper.tex --rocq aligned/Formal.v

7. Put every mismatch in exactly one category:
   a. Notational: the same proposition written differently (n >= 1 vs 1 <= n). You may
      change the tag to the formal side's form ONLY after proving the two equivalent in
      the appended section, with variables quantified as in the theorem, e.g.
        Lean: theorem pfa_eq_h_pos (n : Nat) : (n ≥ 1) ↔ (1 ≤ n) := Iff.rfl
        Rocq: Lemma pfa_eq_h_pos (n : nat) : (n >= 1) <-> (1 <= n). Proof. lia. Qed.
      List every such change with its lemma name.
   b. Substantive: a different hypothesis, type or conclusion, an extra or missing
      binder, or a proof ending in sorry/Admitted. Change nothing. Report it, quote both
      sides, and say which side looks wrong if you can tell, with reasons.
   c. Tooling: the checker failed for environment reasons (prover not found, import or
      build errors, a Lean project that needs Mathlib through `lake env`, a namespace
      other than Paper). You may change how the checker finds, builds and names things.
      Never change what counts as a match. List every change you make to the checker.
   Re-run the checker after any (a) or (c) change.

8. Verify the copy. Write a small script that removes the tags (drop \usepackage{align}
   and \formal{...}; replace \var{a}{b}{c} with c, \hyp{a}{b}{c} with c,
   \concl{a}{b} with b) and diff the result against the original paper. It must be
   identical. If LaTeX is installed, also compile both and compare pdftotext output.

DELIVERABLES in aligned/
- paper.tex (tagged copy) and align.sty
- the formalization copy (original plus the appended section)
- check_alignment.py, only if you changed it
- checker_output.txt (full output of the final run)
- ALIGNMENT_REPORT.md, short, containing:
  - Verdict: ALIGNED, MISALIGNED or INCOMPLETE. ALIGNED requires ALL of: checker PASS;
    tag-strip diff identical; every paper definition and theorem tagged or explained;
    every formal theorem matched or listed; no sorry, Admitted or non-standard axioms.
  - Substantive mismatches, first.
  - Coverage: paper items not formalized, formal items with no paper counterpart.
  - Ambiguities and how you resolved them.
  - Notational adjustments, with lemma names.
  - Definition tests and non-vacuity lemmas: which were proved and which failed.
  - Checker changes, if any.
  - The checker's human-review table, plus the list of definitions a person must read
    once to confirm they mean what the paper says.
```

# AI SKILL:
You can give an AI the ability or skill to automagically link a formulation and it's paper.

PFA is now a skill: `paper-formal-alignment.skill`. Install it in an AI like Claude by unzipping it into a Claude Code skills folder. When someone hands an AI a paper and a Lean or Rocq file and asks whether they agree, the AI copies the paper, does the linking itself, runs PFA on its own work, iterates on its own mistakes, and returns a tagged copy plus a report.

**The workflow** in SKILL.md, in order:

1. Copy both files into an `aligned/` folder and check for macro clashes.
2. Run skeleton.py, which lists the formal declarations and binder names without their statements.
3. Link each paper item to a formal declaration.
4. Tag the copy, writing readings from the paper.
5. Prove the copy is untouched with verify_copies.py.
6. Run the checker and sort each mismatch into "my linking error, fix it," "equivalent, prove it," "substantive, report it," or "tool problem."
7. Append definition tests and non-vacuity lemmas.
8. Write the report.

**The main change here: equivalences are now proved, not string-matched.** In the earlier version, an AI writing an honest reading like `n >= 1` against a formal `1 <= n` would fail. It would then be tempted to copy the formal text, which makes the check circular. Now, when the texts differ, the checker asks the prover to prove them equivalent: `omega`, `simp`, `lia` and similar first, then any `pfa_eq_...` lemma the AI writes for harder cases like "even" versus `n % 2 = 0`. I tested that these lemmas can't be used to cheat. One proved with `sorry` or `Admitted` is rejected, and so is one that states a true but different equivalence.

**Other improvements:**

- The checker reports theorem-like environments that were never tagged, as INCOMPLETE.
- Namespaces are handled automatically.
- `--lake-project` supports Mathlib-style Lean projects, and `--coq-flags` supports Rocq projects with dependencies.
- Several binders can share one hypothesis tag, for phrases like "positive even integer."
- verify_copies.py checks byte for byte that the tagged paper is the original plus tags and the formal copy is append-only.

**The test run.** I ran the skill on a new paper about sums of odd numbers, untagged, with a Lean file where Theorem 2 quietly assumes `n % 4 = 0` instead of "n is even." The run proved two notational equivalences automatically through lemmas (`n^2` versus `n * n`, and "S(n) is even" versus `S n % 2 = 0`). It flagged the divisible-by-4 hypothesis as a substantive mismatch no lemma could bridge, and noted that the paper's corollary was never formalized. ALIGNMENT_REPORT.md is what that run produced, and it's bundled in `examples/oddsum` as a model.

I tested with Lean 4.19 and Coq 8.18 on Linux, including a small lake project, but not with Mathlib or on Windows. The new check_alignment.py also supersedes the one in your repo's `triangular/` folder.
