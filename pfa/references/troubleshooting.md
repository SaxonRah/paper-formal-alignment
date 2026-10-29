# Prover setup and TOOL ERRORs

The checker runs the prover itself, so it must be able to find it.

## Pointing at the prover

- `LEAN`, `LAKE`, `COQC` environment variables override the executables.
- The checker puts the prover's own `bin` folder first on PATH for the child process.

## Lean

- **Plain files (no imports beyond core):** `--lean File.lean` is enough.
- **Mathlib or other dependencies:** pass the project folder: `--lake-project path/to/project`.
  The checker asks `lake env` for the project's `LEAN_PATH` and `lean`. Build the project first
  (`lake build`) so dependencies have `.olean` files.
- **`unknown module prefix`:** the file imports something not on `LEAN_PATH`; use `--lake-project`.
- **Names:** `\formal` must be the full Lean name (`OddSum.S_eq_sq`). Namespaces in `\formal`
  names are ignored automatically when comparing; add others with `--namespace NS`.
- **Anonymous binders** (instance arguments like `[Group G]`) show up as `_arg<k>`, k = position.
  Tag them with that name.

## Rocq / Coq

- **Library dependencies:** pass load-path flags: `--coq-flags "-Q theories MyLib -R deps Dep"`.
- **`cannot guess a path for Rocq libraries`:** set `ROCQLIB` (Rocq 9) or `COQLIB` (Coq 8) to the
  folder containing `theories`. Find it by searching the install for `Init/Prelude.vo`, then cut
  the path at `theories`.
- **Exit code 3221225781 / 0xC0000135 on Windows:** a DLL was not found. Put the install's `bin`
  folder on PATH: `$env:PATH = "C:\Rocq-Platform...\bin;$env:PATH"`.
- **`From Coq Require`** works on Coq 8 and, with a deprecation warning, on Rocq 9. Plain
  `Require Import Arith Lia.` works on both.
- **Names:** `\formal{Paper.T}` resolves to the first suffix Rocq can `Locate` (`Paper.T`, then `T`).

## Windows

- Pass the `.tex` source, never the PDF.
- Use `python`, not `python3`, in PowerShell.
- To make variables permanent:
  `[Environment]::SetEnvironmentVariable("ROCQLIB", "<path>", "User")`.

## Still failing

The error message includes the exact command and the temporary folder it ran in (temporary
folders are kept after a TOOL ERROR, and after any run with `--keep-temp`). Run that command
yourself in that folder to see the prover's full output.
