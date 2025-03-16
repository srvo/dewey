```python
"""Patches that are applied at runtime to the virtual environment."""

import os
import sys
from typing import Any, Optional

VIRTUALENV_PATCH_FILE = os.path.join(__file__)


def _patch_dist_config(dist: Any) -> None:
    """Patch distutils to prevent reading global configuration files.

    Distutils allows user to configure some arguments via a configuration file:
    https://docs.python.org/3.11/install/index.html#distutils-configuration-files.

    Some of these arguments don't make sense in the context of virtual environment files, so let's fix them up.
    """
    old_parse_config_files = dist.Distribution.parse_config_files

    def parse_config_files(self: Any, *args: Any, **kwargs: Any) -> Any:
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


def patch_dist(module: Any) -> None:
    """Apply patches to the distutils module."""
    _patch_dist_config(module)


# Import hook that patches some modules to ignore configuration values that break package installation in case
# of virtual environments.
_DISTUTILS_PATCH = "distutils.dist", "setuptools.dist"
# https://docs.python.org/3/library/importlib.html#setting-up-an-importer


class _Finder:
    """A meta path finder that allows patching the imported distutils modules."""

    fullname: Optional[str] = None

    # lock[0] is threading.Lock(), but initialized lazily to avoid importing threading very early at startup,
    # because there are gevent-based applications that need to be first to import threading by themselves.
    # See https://github.com/pypa/virtualenv/issues/1895 for details.
    lock: list[Any] = []  # noqa: RUF012

    def find_spec(self, fullname: str, path: Any, target: Any = None) -> Optional[Any]:  # noqa: ARG002
        """Find the module spec, and patch the module if necessary."""
        if fullname in _DISTUTILS_PATCH and self.fullname is None:
            # initialize lock[0] lazily
            if len(self.lock) == 0:
                import threading

                lock = threading.Lock()
                # there is possibility that two threads T1 and T2 are simultaneously running into find_spec,
                # observing .lock as empty, and further going into hereby initialization. However due to the GIL,
                # list.append() operation is atomic and this way only one of the threads will "win" to put the lock
                # - that every thread will use - into .lock[0].
                # https://docs.python.org/3/faq/library.html#what-kinds-of-global-value-mutation-are-thread-safe
                self.lock.append(lock)

            from functools import partial
            from importlib.util import find_spec

            with self.lock[0]:
                self.fullname = fullname
                try:
                    spec = find_spec(fullname, path)
                    if spec is not None:
                        # https://www.python.org/dev/peps/pep-0451/#how-loading-will-work
                        is_new_api = hasattr(spec.loader, "exec_module")
                        func_name = "exec_module" if is_new_api else "load_module"
                        old = getattr(spec.loader, func_name)
                        func = self.exec_module if is_new_api else self.load_module
                        if old is not func:
                            try:  # noqa: SIM105
                                setattr(spec.loader, func_name, partial(func, old))
                            except AttributeError:
                                pass  # C-Extension loaders are r/o such as zipimporter with <3.7
                        return spec
                finally:
                    self.fullname = None
        return None

    @staticmethod
    def exec_module(old: Any, module: Any) -> None:
        """Execute the module and apply patches."""
        old(module)
        if module.__name__ in _DISTUTILS_PATCH:
            patch_dist(module)

    @staticmethod
    def load_module(old: Any, name: str) -> Any:
        """Load the module and apply patches."""
        module = old(name)
        if module.__name__ in _DISTUTILS_PATCH:
            patch_dist(module)
        return module


sys.meta_path.insert(0, _Finder())
```
