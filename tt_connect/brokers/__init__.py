"""Auto-discover and import all broker packages to trigger registration."""

import importlib
import pkgutil


def _discover() -> None:
    """Import every subpackage of tt_connect.brokers to trigger registration."""
    for info in pkgutil.iter_modules(__path__, prefix=__name__ + "."):
        if info.ispkg:
            importlib.import_module(info.name)


_discover()
