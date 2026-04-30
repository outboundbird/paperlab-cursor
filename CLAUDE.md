# PaperLab: agent-assisted reading of ML methods papers
The goal is to help user understand mathematics in machine learning, deep learning papers.

- all python code uses type hints, follows PEP8 and has docstrings in Numpy format.
- code examples and reading reference code assume PyTorch and pytorch_geometric conventions
- papers are stored in papers/
- paper naming convention: papers/<slug>
- Each paper folder contains:
  - `<slug>.pdf` — the paper itself
  - `spec.md` — structured extraction (Dissector's output)
  - `explanation.md` — prose walkthrough (Explainer's output)
  - `code_map.md` — annotated mapping from paper to official code (Implementer's output)
  - `notes.md` — user's own notes
  - `upstream/` — cloned official GitHub repo (if available)

- test all algorithms in the sandbox/ folder
- When a paper is ambiguous or you cannot determine something from the source, flag it explicitly rather than guessing. Prefix such flags with ⚠️ UNCERTAIN:

## Agent pipeline

For each paper, run agents in this order:

```
@acquirer <slug> <paper-url>       # Sets up folder, PDF, upstream/
@dissector <slug>                  # Produces spec.md
@implementer process <slug>        # Produces code_map.md
@critic audit <slug>               # (Future) produces critique.md

```

`@explainer` runs on-demand, any time after Dissector:

```
@explainer <concept> <slug>                     # Single concept
@explainer synthesize: <question>               # Multi-concept synthesis
@implementer deep <slug> <component>            # Deep dive on one code component
```
