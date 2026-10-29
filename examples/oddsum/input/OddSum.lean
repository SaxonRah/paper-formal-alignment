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
