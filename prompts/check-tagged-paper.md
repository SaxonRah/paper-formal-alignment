# Prompt: check a paper that is already tagged

For when the paper's author has already added PFA tags and you only want an independent check.

````text
A LaTeX paper has been tagged with PFA (Paper–Formal Alignment) tags that link its
statements to a formalization. Check it. Do not edit either file.

Inputs:
- Tagged paper (LaTeX source): <PATH/TO/paper.tex>
- Formalization: <PATH/TO/Formal.lean or Formal.v>
- PFA: clone https://github.com/SaxonRah/paper-formal-alignment

1. Run the checker and save its full output:
     python pfa/scripts/check_alignment.py <paper.tex> --lean <Formal.lean>
     python pfa/scripts/check_alignment.py <paper.tex> --rocq <Formal.v>
   On TOOL ERROR, read pfa/references/troubleshooting.md and fix the environment only.
2. If the paper has theorem-like environments the checker didn't scan, rerun with
   --env NAME for each.
3. Read every line of the human review table and say, for each, whether the display text
   really means the formal reading next to it. The checker can't judge this; you can.
4. Report: the checker's result line, every mismatch quoted with what differs, every review
   line you disagree with and why, any untagged statements, and the definitions a person
   still needs to read once. Do not report PASS unless the checker printed it.
````
