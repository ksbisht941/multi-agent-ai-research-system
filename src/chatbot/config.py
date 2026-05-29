import os
"""Compatibility shim: expose `settings` from `core.config` for older imports."""
from core.config import settings, Settings  # re-export for backward compatibility

__all__ = ["settings", "Settings"]
