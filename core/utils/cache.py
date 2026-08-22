import time
import threading
from typing import Any, Optional, Dict, Tuple


class TTLCache:
    """Thread-safe in-memory cache with Time-To-Live (TTL) expiration."""

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            if key not in self._cache:
                return default
            val, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                return default
            return val

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        duration = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + duration
        with self._lock:
            self._cache[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def has(self, key: str) -> bool:
        with self._lock:
            if key not in self._cache:
                return False
            _, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                return False
            return True

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        now = time.time()
        removed = 0
        with self._lock:
            keys_to_del = [k for k, (_, exp) in self._cache.items() if now > exp]
            for k in keys_to_del:
                del self._cache[k]
                removed += 1
        return removed


# Shared global caches
topic_profile_cache = TTLCache(default_ttl=7200)      # 2 hours for extracted profiles
related_papers_cache = TTLCache(default_ttl=3600)     # 1 hour for arXiv related papers
suggested_questions_cache = TTLCache(default_ttl=7200) # 2 hours for question generation
general_cache = TTLCache(default_ttl=1800)             # 30 mins
