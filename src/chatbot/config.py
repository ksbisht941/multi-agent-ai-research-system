import os
"""Compatibility shim: expose `settings` and `BASE_DIR` from `core.config` for older imports."""
from core.config import BASE_DIR, settings, Settings  # re-export for backward compatibility

__all__ = ["settings", "Settings", "BASE_DIR"]
