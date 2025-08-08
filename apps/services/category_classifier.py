import os
import threading
import logging
import numpy as np
from functools import lru_cache
from openai import OpenAI
from config import CORE_CATEGORIES

# --- Setup ---
_API_KEY = os.getenv("OPENAI_API_KEY")
if not _API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing")
_client = OpenAI(api_key=_API_KEY)

_LOCK = threading.Lock()
_category_vectors: dict[str, np.ndarray] | None = None
_EMBED_MODEL = "text-embedding-3-small"
_FALLBACK_CATEGORY = "others"
_SIM_THRESHOLD = 0.30
_VEC_DIM = 1536  # will be corrected on first successful embed

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("category-classifier")


def _embed(texts: list[str]) -> list[list[float]]:
    resp = _client.embeddings.create(input=texts, model=_EMBED_MODEL)
    return [d.embedding for d in resp.data]


def _ensure_category_vectors():
    """Compute and cache category embedding vectors exactly once."""
    global _category_vectors, _VEC_DIM
    if _category_vectors is not None:
        return

    with _LOCK:
        if _category_vectors is not None:
            return
        try:
            # Use items() to keep name <-> keywords aligned
            names, blobs = zip(*[(name, meta["keywords"]) for name, meta in CORE_CATEGORIES.items()])
            vecs = _embed(list(blobs))
            if not vecs:
                raise RuntimeError("Empty embedding result for categories")

            _VEC_DIM = len(vecs[0])  # correct dimension from model
            _category_vectors = {name: np.array(vecs[i], dtype=np.float32) for i, name in enumerate(names)}
            # log.info("Category vectors initialized (%d dims).", _VEC_DIM)
        except Exception as e:
            log.exception("Failed to init category vectors: %s", e)
            # Safe fallback: zeros so cosine = 0
            _category_vectors = {name: np.zeros(_VEC_DIM, dtype=np.float32) for name in CORE_CATEGORIES.keys()}


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0


@lru_cache(maxsize=512)
def _embed_single(text: str) -> np.ndarray:
    v = _embed([text])[0]
    return np.array(v, dtype=np.float32)


def classify_category_by_embedding(text: str) -> dict:
    """Return best-matched category with key + localized names."""
    cleaned = (text or "").strip()
    if not cleaned:
        meta = CORE_CATEGORIES.get(_FALLBACK_CATEGORY, {})
        return {"key": _FALLBACK_CATEGORY, "en": meta.get("en", "Others"), "zh-TW": meta.get("zh-TW", "其他")}

    _ensure_category_vectors()

    try:
        v = _embed_single(cleaned)
    except Exception as e:
        log.exception("Embed failed for input '%s': %s", cleaned, e)
        meta = CORE_CATEGORIES.get(_FALLBACK_CATEGORY, {})
        return {"key": _FALLBACK_CATEGORY, "en": meta.get("en", "Others"), "zh-TW": meta.get("zh-TW", "其他")}

    best_key, best_sim = _FALLBACK_CATEGORY, -1.0
    for name, vec in _category_vectors.items():
        sim = _cosine(v, vec)
        if sim > best_sim:
            best_key, best_sim = name, sim

    key = best_key if best_sim >= _SIM_THRESHOLD else _FALLBACK_CATEGORY
    meta = CORE_CATEGORIES.get(key, {})
    return {"key": key, "en": meta.get("en", key.capitalize()), "zh-TW": meta.get("zh-TW", key)}
