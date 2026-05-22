# PaperLab git hooks

Source-controlled git hooks. Install once per clone with:

```bash
git config core.hooksPath tools/hooks
```

After this, `git commit` will use the hooks in this folder instead of the
default `.git/hooks/`. To uninstall:

```bash
git config --unset core.hooksPath
```

## Hooks

### `pre-commit`

Keeps the visualizer dictionary PDF in sync with its markdown source.

When `.cursor/skills/ml-visualization/DICTIONARY.md` is in the staged
changes, this hook:

1. Runs `python -m tools.build_dictionary_pdf`, which regenerates per-entry
   PNG tiles under `.cursor/skills/ml-visualization/symbols/` and assembles
   `.cursor/skills/ml-visualization/DICTIONARY.pdf`.
2. Re-stages the regenerated PDF and tiles so they enter the same commit.
3. Aborts the commit on build failure.

If you want to commit a dictionary edit *without* refreshing the PDF (e.g.
work-in-progress), use `git commit --no-verify`.
