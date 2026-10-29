# Example: a tiny paper aligned with Lean and Rocq

A one-page paper on triangular numbers, formalized in Lean and Rocq, plus a
checker that confirms the paper's definitions and theorem statements match the
formal ones. Proofs are never compared, only statements.

| File | What it is |
|---|---|
| `paper.tex`, `paper.pdf` | The paper, with alignment tags in the source |
| `align.sty` | The four tagging macros (`\formal`, `\var`, `\hyp`, `\concl`) |
| `Triangular.lean` | Faithful Lean 4 formalization (core Lean, no Mathlib) |
| `Triangular.v` | Faithful Rocq formalization |
| `Triangular_drifted.lean` | A careless formalization that still compiles |
| `check_alignment.py` | The checker |

## How the tags work

Each tagged environment names its formal counterpart, and every variable,
hypothesis and conclusion carries its formal reading next to the text readers see:

```latex
\begin{theorem}\formal{Paper.T_add_T_pred}
Let \var{n}{nat}{$n$} be a natural number with \hyp{h_pos}{1 <= n}{$n \geq 1$}.
Then \concl{T n + T (n - 1) = n * n}{$T(n) + T(n-1) = n^2$}.
\end{theorem}
```

The PDF shows only the display text. The checker reads the tags, asks the prover
for the real signature of `Paper.T_add_T_pred`, and compares binder by binder.

## Run it

```sh
python3 check_alignment.py paper.tex --lean Triangular.lean
python3 check_alignment.py paper.tex --rocq Triangular.v

python3 check_alignment.py paper.tex --lean Triangular_drifted.lean   # fails
python3 check_alignment.py paper.tex --rocq Triangular_drifted.v      # fails
```

Pass the `.tex` source, not the PDF, and one prover at a time. The checker needs
`lean` or `coqc` installed and on your `PATH`, or pointed to with an environment
variable. In PowerShell:

```powershell
$env:LEAN = "$HOME\.elan\bin\lean.exe"
$env:COQC = "C:\path\to\rocq\bin\coqc.exe"

# For Example:
$env:COQC = "C:\Rocq-Platform~9.0~2025.08\bin\coqc.exe"
```

Triangle Example Output:
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

```powershell
PS C:\triangular\> python check_alignment.py paper.tex --rocq Triangular_drifted.v
Checked 5 tagged statements against Triangular_drifted.v

MISMATCHES
  XXX: theorem Paper.T_add_T_pred: depends on T_add_T_pred (sorry/Admitted or extra axioms)
  XXX: theorem Paper.T_add_T_pred: 'h_pos' is '1 <= n' in the paper but '2 <= n' formally

Result: FAIL. Paper and formalization do not agree.
PS C:\triangular\>
```

Tested with Lean 4.19.0 and Coq 8.18 on Linux and Rocq 9.0 on Windows.

## What it catches

On the drifted formalization:

```
MISMATCHES
  XXX theorem Paper.two_mul_T: depends on sorryAx (sorry/Admitted or extra axioms)
  XXX theorem Paper.two_mul_T: formal statement assumes 'h_even : n % 2 = 0', which the paper never states
  XXX theorem Paper.T_add_T_pred: depends on sorryAx (sorry/Admitted or extra axioms)
  XXX theorem Paper.T_add_T_pred: 'h_pos' is '1 <= n' in the paper but '2 <= n' formally

Result: FAIL. Paper and formalization do not agree.
```

An extra hypothesis, a quietly strengthened hypothesis, and unfinished proofs are
all flagged, even though the file compiles. The same kind of check would flag a
forcing term that appears in one version of a theorem and not the other.

## What stays human

On a pass, the checker prints a short side-by-side table (`$n \geq 1$ ⟷ 1 <= n`,
`$T(n) + T(n-1) = n^2$ ⟷ T n + T (n - 1) = n * n`) and lists each new
definition. Those are the only things a person needs to read: that each display
text means its tag, and that `T` is defined as the paper says. Example 1
(`T(4) = 10`) is a definition test that would fail for most wrong definitions of `T`,
and Example 2 proves Theorem 2's hypothesis can be satisfied.

## Limits of this toy

The formal syntax in tags is matched as normalized text, so `1 <= n` and `n >= 1`
count as different. A real version would compare elaborated terms, or ask the
prover to check `paper_statement ↔ formal_statement` by `Iff.rfl`. The Rocq
side reads binder names by introducing them in a throwaway goal, which works for
ordinary statements but would need a plugin for anything fancy.
