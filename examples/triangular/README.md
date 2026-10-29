# Example: triangular numbers

A one-page paper on triangular numbers, already tagged, with faithful Lean and Rocq
formalizations and one drifted formalization in each prover. Use it to check that your
setup works and to see what tagging looks like.

| File | What it is |
|---|---|
| `paper.tex`, `paper.pdf` | The paper, with alignment tags in the source. The PDF shows no tags. |
| `align.sty` | The four tag macros (a copy of `pfa/assets/align.sty`). |
| `Triangular.lean` | Faithful Lean 4 formalization (core Lean, no Mathlib). |
| `Triangular.v` | Faithful Rocq formalization. |
| `Triangular_drifted.lean` | Compiles, but adds a hypothesis, strengthens another, and uses `sorry`. |
| `Triangular_drifted.v` | Compiles, but strengthens a hypothesis and uses `Admitted`. |

## How the tags work

Each statement names its formal counterpart, and every variable, hypothesis and conclusion
carries its formal reading next to the text readers see:

```latex
\begin{theorem}\label{thm:square}\formal{Paper.T_add_T_pred}
Let \var{n}{nat}{$n$} be a natural number with \hyp{h_pos}{1 <= n}{$n \geq 1$}.
Then \concl{T n + T (n - 1) = n * n}{$T(n) + T(n-1) = n^2$}.
\end{theorem}
```

The checker asks the prover for the real signature of `Paper.T_add_T_pred` and compares
binder by binder. Where a reading and the formal text differ, it asks the prover to prove
them equivalent.

## Run it

From this folder:

```sh
python ../../pfa/scripts/check_alignment.py paper.tex --lean Triangular.lean
python ../../pfa/scripts/check_alignment.py paper.tex --rocq Triangular.v

python ../../pfa/scripts/check_alignment.py paper.tex --lean Triangular_drifted.lean   # fails
python ../../pfa/scripts/check_alignment.py paper.tex --rocq Triangular_drifted.v      # fails
```

The checker needs `lean` or `coqc` on your PATH, or the `LEAN` / `COQC` environment variable.
Setup problems are covered in `pfa/references/troubleshooting.md`.

A passing run:

```
Checked 5 tagged statements against Triangular.v

Human review (does each display text mean its formal reading?)
  definition Paper.T
      (definition)                              ⟷  read the formal definition once
  example Paper.T_four
      $T(4) = 10$                               ⟷  T 4 = 10
  theorem Paper.two_mul_T
      $n$                                       ⟷  nat
      $2\,T(n) = n(n+1)$                        ⟷  2 * T n = n * (n + 1)
  theorem Paper.T_add_T_pred
      $n$                                       ⟷  nat
      $n \geq 1$                                ⟷  1 <= n
      $T(n) + T(n-1) = n^2$                     ⟷  T n + T (n - 1) = n * n
  example Paper.T_add_T_pred_nonvacuous
      some natural number satisfies $n \geq 1$  ⟷  exists n : nat, 1 <= n

Result: PASS. Paper and formalization agree on every tagged statement.
```

The drifted Lean file:

```
Checked 5 tagged statements against Triangular_drifted.lean

MISMATCHES
  ✗ theorem Paper.two_mul_T: depends on sorryAx (sorry/Admitted or extra axioms)
  ✗ theorem Paper.two_mul_T: formal statement has 'h_even : n % 2 = 0', which the paper never states
  ✗ theorem Paper.T_add_T_pred: depends on sorryAx (sorry/Admitted or extra axioms)
  ✗ theorem Paper.T_add_T_pred: hypothesis 'h_pos' is '1 <= n' in the paper but '2 <= n' formally, and no equivalence could be proved

Result: FAIL. Paper and formalization do not agree.
```

An extra hypothesis, a quietly strengthened hypothesis and unfinished proofs are all flagged,
even though the file compiles. On Rocq, an `Admitted` theorem is reported as depending on
itself, because Rocq records it as an axiom.

## What stays human

On a pass, the review table pairs each piece of display text with its formal reading. A person
checks that each pair means the same thing, and reads the definition of `T` once. Example 1
(`T(4) = 10`) is a definition test that most wrong definitions of `T` would fail, and Example 2
proves Theorem 2's hypothesis can be satisfied.

Tested with Lean 4.19 and Coq 8.18 on Linux. An earlier version of the checker also ran on Rocq 9.0.1 under Windows.
