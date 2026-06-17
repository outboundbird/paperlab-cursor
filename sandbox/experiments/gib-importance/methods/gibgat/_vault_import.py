"""Load GIBGAT Stage-1 ``method.py`` from the vault (outside the workspace).

Backend helper for the extension regime: the audited Stage-1 method lives at
``vault_code_dir("GIBGAT")``, which is outside the Cursor workspace, so a plain
``import`` will not resolve it. Use ``importlib`` against the absolute path
returned by ``tools.paths.vault_code_dir``.
"""

from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType


def _repo_root() -> Path:
    # methods/gibgat/_vault_import.py
    # parents[0]=gibgat, [1]=methods, [2]=gib-importance,
    # [3]=experiments, [4]=sandbox, [5]=repo root
    return Path(__file__).resolve().parents[5]


@lru_cache(maxsize=1)
def load_gibgat_method_module() -> ModuleType:
    """Import ``method.py`` from ``vault_code_dir('GIBGAT')`` via ``importlib``."""
    repo = _repo_root()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))

    from tools.paths import vault_code_dir

    method_path = vault_code_dir("GIBGAT") / "method.py"
    if not method_path.is_file():
        raise FileNotFoundError(f"GIBGAT method.py not found at {method_path}")

    spec = importlib.util.spec_from_file_location("gibgat_vault_method", method_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load spec for {method_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["gibgat_vault_method"] = module
    spec.loader.exec_module(module)
    return module


def gibgat_method_path() -> Path:
    """Absolute path to the vault ``method.py`` (for README / provenance)."""
    repo = _repo_root()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from tools.paths import vault_code_dir

    return vault_code_dir("GIBGAT") / "method.py"
