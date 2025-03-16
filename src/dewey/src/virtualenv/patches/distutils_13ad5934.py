```python
"""Patches that are applied at runtime to the virtual environment."""

import os
import sys
from importlib.util import find_spec
from functools import partial
import threading
from types import ModuleType
from typing import Any, Optional, Sequence

VIRTUALENV_PATCH_FILE = os.path.join(__file__)
_DISTUTILS_PATCH: Sequence[str] = ("distutils.dist", "setuptools.dist")


def patch_dist(dist: Any) -> None:
    """
    Patch a distutils distribution object to ignore configuration values that break package installation in virtual environments.

    Distutils allows users to configure some arguments via a configuration file:
    https://docs.python.org/3.11/install/index.html#distutils-configuration-files.

    Some of these arguments don't make sense in the context of virtual environment files, so we fix them up.
    """
    old_parse_config_files = dist.Distribution.parse_config_files

    def parse_config_files(self: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Override the distutils parse_config_files method to modify install options.
        """
        result = old_parse_config_files(self, *args, **kwargs)
        install = self.get_option_dict("install")

        if "prefix" in install:  # the prefix governs where to install the libraries
            install["prefix"] = VIRTUALENV_PATCH_FILE, os.path.abspath(sys.prefix)
        for base in ("purelib", "platlib", "headers", "scripts", "data"):
            key = f"install_{base}"
            if key in install:  # do not allow global configs to hijack venv paths
                install.pop(key, None)
        return result

    dist.Distribution.parse_config_files = parse_config_files


class _Finder:
    """
    A meta path finder that allows patching imported distutils modules.

    This class implements a meta path finder that intercepts imports of specific distutils modules
    and applies a patching function to modify their behavior. This is necessary to prevent
    certain configuration values from breaking package installation in virtual environments.
    """

    fullname: Optional[str] = None
    lock: list[threading.Lock] = []  # noqa: RUF012

    def find_spec(self, fullname: str, path: Optional[Sequence[str]], target: Optional[ModuleType] = None) -> Optional[Any]:  # noqa: ARG002
        """
        Find the spec for the given module name if it's one of the modules to patch.

        Args:
            fullname: The fully qualified name of the module to import.
            path: A sequence of directory paths to search.
            target: The target module (optional).

        Returns:
            The module spec if found and patching is applied, otherwise None.
        """
        if fullname in _DISTUTILS_PATCH and self.fullname is None:
            if not self.lock:
                self.lock.append(threading.Lock())

            with self.lock[0]:
                self.fullname = fullname
                try:
                    spec = find_spec(fullname, path)
                    if spec is not None:
                        is_new_api = hasattr(spec.loader, "exec_module")
                        func_name = "exec_module" if is_new_api else "load_module"
                        old = getattr(spec.loader, func_name)
                        func = self.exec_module if is_new_api else self.load_module
                        if old is not func:
                            try:  # noqa: SIM105
                                setattr(spec.loader, func_name, partial(func, old))
                            except AttributeError:
                                pass
                        return spec
                finally:
                    self.fullname = None
        return None

    @staticmethod
    def exec_module(old: Any, module: ModuleType) -> None:
        """
        Execute the module and apply the patch if necessary (new import API).

        Args:
            old: The original exec_module function.
            module: The module to execute.
        """
        old(module)
        if module.__name__ in _DISTUTILS_PATCH:
            patch_dist(module)

    @staticmethod
    def load_module(old: Any, name: str) -> ModuleType:
        """
        Load the module and apply the patch if necessary (old import API).

        Args:
            old: The original load_module function.
            name: The name of the module to load.

        Returns:
            The loaded module.
        """
        module = old(name)
        if module.__name__ in _DISTUTILS_PATCH:
            patch_dist(module)
        return module


sys.meta_path.insert(0, _Finder())
```
