from __future__ import annotations
import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import Any, Callable, Optional

from capabilities.base import CapabilityDeclaration
from capabilities.registry import CapabilityRegistry

logger = logging.getLogger(__name__)


def auto_discover(package_path: str = "capabilities.implementations",
                  registry: Optional[CapabilityRegistry] = None) -> CapabilityRegistry:
    if registry is None:
        registry = CapabilityRegistry()

    try:
        pkg = importlib.import_module(package_path)
    except ImportError:
        logger.warning(f"Package not found: {package_path}")
        return registry

    pkg_path = Path(pkg.__file__).parent if pkg.__file__ else None
    if not pkg_path or not pkg_path.exists():
        return registry

    count = 0
    for importer, modname, ispkg in pkgutil.iter_modules([str(pkg_path)]):
        if ispkg or modname.startswith("_"):
            continue
        full_name = f"{package_path}.{modname}"
        try:
            module = importlib.import_module(full_name)
            registered = _register_from_module(module, registry)
            count += registered
            if registered:
                logger.info(f"Discovered {registered} capabilities in {modname}")
        except Exception as e:
            logger.warning(f"Failed to load {full_name}: {e}")

    logger.info(f"Auto-discovery complete: {count} capabilities registered")
    return registry


def _register_from_module(module: Any, registry: CapabilityRegistry) -> int:
    count = 0
    for name, obj in inspect.getmembers(module):
        if name.startswith("_"):
            continue
        if inspect.isfunction(obj) and hasattr(obj, "_capability_decl"):
            decl = getattr(obj, "_capability_decl")
            registry.register(decl, obj)
            count += 1
    if hasattr(module, "register_capabilities"):
        module.register_capabilities(registry)
        count += 1
    return count


def capability_decl(decl: CapabilityDeclaration) -> Callable:
    def decorator(func: Callable) -> Callable:
        func._capability_decl = decl
        return func
    return decorator
