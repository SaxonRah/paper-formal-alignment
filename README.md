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
PS C:\triangular\>
```