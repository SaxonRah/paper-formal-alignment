# Example: a full run of the PFA skill

This is what the skill produces when an AI is given an untagged paper and a formalization
and asked whether they agree.

- `input/oddsum.tex`: a short paper on sums of odd numbers, with no tags.
- `input/OddSum.lean`: its Lean formalization. It compiles, but Theorem 2 quietly assumes
  `n % 4 = 0` where the paper says "n is even", and the paper's corollary was never formalized.
- `aligned/`: the result. `paper.tex` is the tagged copy, `OddSum.lean` is the original plus an
  appended `PFA additions` section, and `ALIGNMENT_REPORT.md` is the report.

The run proved two notational differences equivalent with appended lemmas (`n ^ 2` vs `n * n`,
and "S(n) is even" as `∃ k, S n = 2 * k` vs `S n % 2 = 0`), added definition tests and
non-vacuity lemmas, and reported Theorem 2's hypothesis as a substantive mismatch that no lemma
could bridge. Verdict: MISALIGNED.

Reproduce the check from the `aligned/` folder:

```sh
python ../../../pfa/scripts/verify_copies.py --paper ../input/oddsum.tex paper.tex --formal ../input/OddSum.lean OddSum.lean
python ../../../pfa/scripts/check_alignment.py paper.tex --lean OddSum.lean \
  --require-proved OddSum.pfa_test_S_small --require-proved OddSum.pfa_nonvacuous_S_diff \
  --require-proved OddSum.pfa_nonvacuous_S_even
```
