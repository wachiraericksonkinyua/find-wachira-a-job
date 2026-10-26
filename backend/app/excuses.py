from pydantic import BaseModel
import time
import threading
from typing import Dict, Tuple, Optional

# Preset Excuses
PRESET_EXCUSES = {
    1: "We froze hiring",
    2: "Looking for 5+ years of senior experience",
    3: "We need someone who has shipped full-stack + AI in production",
    4: "We only hire from big tech companies"
}

class ExcuseRequest(BaseModel):
    excuse_id: int

# In-Memory Cache
# Key: (excuse_id, resume_mtime)
# Value: (cached_text, timestamp)
_cache: Dict[Tuple[int, float], Tuple[str, float]] = {}
_cache_lock = threading.Lock()
TTL_SECONDS = 3600 # 1 hour

def get_cached_excuse(excuse_id: int, resume_mtime: float) -> Optional[str]:
    with _cache_lock:
        entry = _cache.get((excuse_id, resume_mtime))
        if entry:
            text, timestamp = entry
            if time.time() - timestamp < TTL_SECONDS:
                return text
            else:
                # Expired
                del _cache[(excuse_id, resume_mtime)]
        return None

def set_cached_excuse(excuse_id: int, resume_mtime: float, text: str):
    with _cache_lock:
        _cache[(excuse_id, resume_mtime)] = (text, time.time())
