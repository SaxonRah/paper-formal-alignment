Require Import Arith Lia.

(* Definition 1: triangular numbers. *)
Fixpoint T (n : nat) : nat :=
  match n with
  | 0 => 0
  | S k => T k + S k
  end.

(* Example 1: a definition test. If T were defined wrongly, this fails. *)
Theorem T_four : T 4 = 10.
Proof. reflexivity. Qed.

(* Theorem 1 (closed form). *)
Theorem two_mul_T (n : nat) : 2 * T n = n * (n + 1).
Proof. induction n as [|k IH]; simpl; [reflexivity | nia]. Qed.

(* Theorem 2. *)
Theorem T_add_T_pred (n : nat) (h_pos : 1 <= n) :
  T n + T (n - 1) = n * n.
Proof.
  destruct n as [|k]; [lia|].
  pose proof (two_mul_T k). simpl. rewrite Nat.sub_0_r. nia.
Qed.

(* Non-vacuity: Theorem 2's hypothesis can be satisfied. *)
Theorem T_add_T_pred_nonvacuous : exists n, 1 <= n.
Proof. exists 1. lia. Qed.
