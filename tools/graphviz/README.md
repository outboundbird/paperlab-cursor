# Portable graphviz (per-machine)

This folder is **git-ignored**. It exists to hold a per-machine copy of the
graphviz toolchain (`dot`, `neato`, etc.) for machines where the user does
not have admin rights to install graphviz system-wide.

## When this folder is used

The resolver `tools.paths.graphviz_dot()` looks here first; if it finds a
`Graphviz-*/bin/dot[.exe]` it returns that path. Otherwise it falls back
to system `dot` on `PATH`.

So:

- **Linux / macOS with admin:** ignore this folder. Just
  `sudo apt install graphviz` (or equivalent) and the resolver picks up the
  system binary.
- **Windows without admin:** download the portable release into this folder
  (see below).

## How to install the portable build (Windows, no admin)

Latest tested version: **Graphviz 14.1.5**, from the upstream GitLab releases.

```bash
cd tools/graphviz
curl -L -o graphviz-portable.zip \
  "https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/14.1.5/windows_10_cmake_Release_Graphviz-14.1.5-win64.zip"
unzip -q graphviz-portable.zip
rm graphviz-portable.zip
```

After extraction, `tools/graphviz/Graphviz-14.1.5-win64/bin/dot.exe` should
exist. Verify with:

```bash
python -m tools.paths dot
# expected: an absolute path to dot.exe ending in /bin/dot.exe
```

## Why this is git-ignored

Binary blobs in git are slow and platform-specific. Each machine downloads
its own copy on first use. The Linux desktop will not need this folder at
all (system install covers it).
