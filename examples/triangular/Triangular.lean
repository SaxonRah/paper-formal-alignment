namespace Paper

/-- Definition 1: triangular numbers. -/
def T : Nat → Nat
  | 0     => 0
  | n + 1 => T n + (n + 1)

/-- Example 1: a definition test. If `T` were defined wrongly, this fails. -/
theorem T_four : T 4 = 10 := rfl

/-- Theorem 1 (closed form). -/
theorem two_mul_T (n : Nat) : 2 * T n = n * (n + 1) := by
  induction n with
  | zero => rfl
  | succ k ih =>
    simp only [T, Nat.mul_add, Nat.add_mul, Nat.mul_one, Nat.one_mul] at *
    omega

/-- Theorem 2. -/
theorem T_add_T_pred (n : Nat) (h_pos : 1 ≤ n) :
    T n + T (n - 1) = n * n := by
  obtain ⟨k, rfl⟩ : ∃ k, n = k + 1 := ⟨n - 1, by omega⟩
  have h := two_mul_T k
  simp only [T, Nat.add_sub_cancel, Nat.mul_add, Nat.add_mul,
    Nat.mul_one, Nat.one_mul] at *
  omega

/-- Non-vacuity: Theorem 2's hypothesis can be satisfied. -/
theorem T_add_T_pred_nonvacuous : ∃ n : Nat, 1 ≤ n := ⟨1, by decide⟩

end Paper
