import time
from typing import Any, Callable, Dict, Optional
import streamlit as st

class CacheManager:
    """Manages cache TTL and invalidation tokens for UI and service layer."""
    _instance = None
    
    def __init__(self):
        # Invalidation generation counter
        self._invalidation_counter = 0

    @classmethod
    def get_instance(cls) -> "CacheManager":
        if cls._instance is None:
            cls._instance = CacheManager()
        return cls._instance

    def invalidate(self, tag: Optional[str] = None):
        """Invalidate caches by clearing streamlit cache or bumping counter."""
        self._invalidation_counter += 1
        try:
            st.cache_data.clear()
        except Exception:
            pass

    @property
    def version(self) -> int:
        return self._invalidation_counter

cache_mgr = CacheManager.get_instance()

def invalidate_caches(reason: str = "mutation"):
    """Helper to invalidate cached queries on mutations."""
    cache_mgr.invalidate(reason)
