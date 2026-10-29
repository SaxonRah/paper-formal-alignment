# Alignment report: Sums of Odd Numbers

**Verdict:** MISALIGNED
Theorem 2's formal statement assumes `n % 4 = 0` where the paper assumes only that n is even, and the paper's corollary has no formal counterpart.

## Substantive mismatches

- **Theorem 2** (`OddSum.S_even`). The paper says "If $n$ is even, then $S(n)$ is even." The formal hypothesis is `h_even : n % 4 = 0`, which says n is divisible by 4. That is strictly stronger than "even" (n = 2 is even but excluded), so the formal theorem is weaker than the paper's. The formalization looks wrong: the paper's statement is true as written (S(n) = n², and n even makes n² even), so nothing forces the stronger hypothesis.

## Coverage

- Paper items not formalized: the Corollary ("$S(n)$ is odd if and only if $n$ is odd").
- Formal declarations with no paper counterpart: none.

## Readings that needed judgment

- "Even" is read as `exists k : nat, n = 2 * k`, the usual definition. The formal conclusion's `S n % 2 = 0` was proved equivalent to it.
- Theorem 2 never says what kind of number n is. The paper's standing convention ($\mathbb{N} = \{0, 1, 2, \dots\}$) is used: n : nat, including 0.

## Equivalence lemmas added

- `pfa_eq_S_eq_sq_concl`: the paper's `n ^ 2` is the formal `n * n` (by `Nat.pow_two`).
- `pfa_eq_S_even_concl`: "S(n) is even" as `∃ k, S n = 2 * k` is the formal `S n % 2 = 0`.
- No lemma could be given for Theorem 2's hypothesis: the two readings are not equivalent.

## Definition tests and non-vacuity

- `OddSum.S_three` (the paper's Example, S(3) = 9) is tagged and checked.
- `pfa_test_S_small`: S(0) = 0, S(1) = 1, S(2) = 4. Proved.
- `pfa_nonvacuous_S_diff` (some n ≥ 1) and `pfa_nonvacuous_S_even` (some n with n % 4 = 0). Proved.

## Independence

Readings were written from the paper with only `skeleton.py` output (names and binder names) in view. This is a test run of the skill by the same author as the formalization, so independence is nominal.

## For the human reviewer

From `pfa.json`: each display text against its reading, with the formal form where an equivalence was proved.

| Statement | Paper says | Reading | Formal (if different) |
|---|---|---|---|
| Example `S_three` | $S(3) = 1 + 3 + 5 = 9$ | `S 3 = 9` | |
| Theorem 1 `S_eq_sq` | $n \in \mathbb{N}$ | `nat` | |
| | $S(n) = n^2$ | `S n = n ^ 2` | `S n = n * n` |
| Theorem 2 `S_even` | $n$ is even | `exists k : nat, n = 2 * k` | `n % 4 = 0` (**not equivalent**) |
| | $S(n)$ is even | `exists k : nat, S n = 2 * k` | `S n % 2 = 0` |
| Theorem 3 `S_diff` | $n \geq 1$ | `1 <= n` | |
| | $S(n) - S(n-1) = 2n - 1$ | `S n - S (n - 1) = 2 * n - 1` | |

Definition to read once: `OddSum.S` (S 0 = 0, S (n + 1) = S n + (2n + 1)), against the paper's Definition.
