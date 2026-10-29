# Prompt: align a paper with its formalization (no skill support)

For AI tools that can run code but can't install skills. Replace the three placeholders.

````text
Use PFA (Paper–Formal Alignment) to find out whether a mathematics paper and its
formalization agree. Your job is to find out WHETHER they agree, not to MAKE them agree.

Inputs:
- Paper (LaTeX source): <PATH/TO/paper.tex>
- Formalization: <PATH/TO/Formal.lean or Formal.v>
- PFA: clone https://github.com/SaxonRah/paper-formal-alignment

Read pfa/SKILL.md in the repository and follow it exactly, step by step. It explains how to
link the paper to the formalization, how to tag a copy of the paper, how to run the checker
and what to do with each kind of mismatch. In the repository the skill folder is pfa/ (so its
scripts are in pfa/scripts/) and the worked examples are in examples/ at the repository root.
Read examples/oddsum/aligned/ALIGNMENT_REPORT.md before writing your own report.

Deliver the aligned/ folder that SKILL.md describes, and finish by quoting the report's verdict
and its substantive mismatches.
````
