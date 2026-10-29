-- The same paper, formalized carelessly. Everything here compiles.
namespace Paper

def T : Nat → Nat
  | 0     => 0
  | n + 1 => T n + (n + 1)

theorem T_four : T 4 = 10 := rfl

-- Drift 1: an extra hypothesis the paper never states.
theorem two_mul_T (n : Nat) (h_even : n % 2 = 0) : 2 * T n = n * (n + 1) := by
  induction n with
  | zero => rfl
  | succ k ih => sorry

-- Drift 2: a hypothesis quietly strengthened from 1 ≤ n to 2 ≤ n.
theorem T_add_T_pred (n : Nat) (h_pos : 2 ≤ n) :
    T n + T (n - 1) = n * n := by
  sorry

theorem T_add_T_pred_nonvacuous : ∃ n : Nat, 1 ≤ n := ⟨1, by decide⟩

end Paper
