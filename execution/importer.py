"""
Restricted importer — only allowlisted modules may be imported inside the execution sandbox.
"""
import sys
import importlib
from importlib.abc import MetaPathFinder, Loader
from importlib.machinery import ModuleSpec

ALLOWLIST = {
    "pandas", "numpy", "duckdb", "plotly", "plotly.express", "plotly.graph_objects",
    "datetime", "math", "json", "re", "collections", "functools", "itertools",
    "typing", "decimal", "statistics",
    # pandas sub-modules
    "pandas.core", "pandas.io",
}


def _is_allowed(name: str) -> bool:
    return any(name == a or name.startswith(a + ".") for a in ALLOWLIST)


class RestrictedFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if _is_allowed(fullname):
            return None  # let normal machinery handle it
        raise ImportError(
            f"Import of '{fullname}' is not allowed in the execution sandbox. "
            f"Allowed modules: {sorted(ALLOWLIST)}"
        )


def install():
    sys.meta_path.insert(0, RestrictedFinder())
