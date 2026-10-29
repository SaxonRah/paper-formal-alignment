namespace OddSum

/-- Definition: the sum of the first `n` odd numbers. -/
def S : Nat → Nat
  | 0     => 0
  | n + 1 => S n + (2 * n + 1)

/-- The paper's example. -/
theorem S_three : S 3 = 9 := rfl

/-- Theorem 1. -/
theorem S_eq_sq (n : Nat) : S n = n * n := by
  induction n with
  | zero => rfl
  | succ k ih =>
    simp only [S, ih, Nat.mul_add, Nat.add_mul, Nat.mul_one, Nat.one_mul]
    omega

/-- Theorem 2. -/
theorem S_even (n : Nat) (h_even : n % 4 = 0) : S n % 2 = 0 := by
  rw [S_eq_sq, Nat.mul_mod]
  have : n % 2 = 0 := by omega
  simp [this]

/-- Theorem 3. -/
theorem S_diff (n : Nat) (h_pos : 1 ≤ n) : S n - S (n - 1) = 2 * n - 1 := by
  obtain ⟨k, rfl⟩ : ∃ k, n = k + 1 := ⟨n - 1, by omega⟩
  simp only [S, Nat.add_sub_cancel]
  omega

end OddSum

-- PFA additions (appended; nothing above this line was changed)
namespace OddSum

/-- Paper's `n^2` and the formal `n * n` are the same number. -/
theorem pfa_eq_S_eq_sq_concl (n : Nat) : (S n = n ^ 2) ↔ (S n = n * n) := by
  rw [Nat.pow_two]

/-- "S(n) is even" read as `∃ k, S n = 2 * k` is the formal `S n % 2 = 0`. -/
theorem pfa_eq_S_even_concl (n : Nat) : (∃ k : Nat, S n = 2 * k) ↔ (S n % 2 = 0) := by
  constructor
  · rintro ⟨k, hk⟩; omega
  · intro h; exact ⟨S n / 2, by omega⟩

/-- Definition test: S(0) = 0 and the recursion's first steps (paper's definition). -/
theorem pfa_test_S_small : S 0 = 0 ∧ S 1 = 1 ∧ S 2 = 4 := ⟨rfl, rfl, rfl⟩

/-- Non-vacuity of Theorem 3's hypothesis. -/
theorem pfa_nonvacuous_S_diff : ∃ n : Nat, 1 ≤ n := ⟨1, by decide⟩

/-- Non-vacuity of Theorem 2's formal hypothesis. -/
theorem pfa_nonvacuous_S_even : ∃ n : Nat, n % 4 = 0 := ⟨0, rfl⟩

end OddSum
