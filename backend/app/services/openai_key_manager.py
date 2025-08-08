import os
from itertools import cycle
from threading import Lock

# Optional Redis coordination (safe across multiple machines)
_USE_REDIS = os.getenv("OPENAI_ROTATION_MODE", "local").lower() == "redis"
_r = None
if _USE_REDIS:
    import redis
    _r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)

class OpenAIKeyManager:
    def __init__(self):
        keys = [k.strip() for k in os.getenv("AZURE_OPENAI_API_KEYS", "").split(",") if k.strip()]
        bases = [b.strip() for b in os.getenv("AZURE_OPENAI_API_BASES", "").split(",") if b.strip()]
        if not keys or not bases or len(keys) != len(bases):
            raise ValueError(
                "AZURE_OPENAI_API_KEYS and AZURE_OPENAI_API_BASES must be set and have the same length."
            )
        self._keys = keys
        self._bases = bases
        self._n = len(keys)

        # Local in-process cycle (fine when a single box or you don’t require cross-worker sync)
        self._cycle = cycle(range(self._n))
        self._lock = Lock()

    def get_next(self):
        """
        Returns (api_key, api_base, index)
        Local mode: thread-safe round-robin.
        Redis mode: cluster-safe round-robin using atomic INCR.
        """
        if _USE_REDIS and _r:
            idx = int(_r.incr("openai_key_index")) % self._n
            return self._keys[idx], self._bases[idx], idx

        with self._lock:
            idx = next(self._cycle)
            return self._keys[idx], self._bases[idx], idx

key_manager = OpenAIKeyManager()