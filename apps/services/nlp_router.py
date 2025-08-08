import re
import numpy as np
from apps.services.openai_embed import embed 
from apps.common.i18n import t
from config import INTENTS

_THRESHOLD = 0.20  # intent similarity threshold
_intent_vecs = None

ROOT_KEYS = ["food", "investment", "transport", "entertainment", "shopping", "medical", "others"]

def canonical_root_from_token(token: str, lang: str) -> str | None:
    tok = (token or "").strip().lower()
    if not tok:
        return None
    for k in ROOT_KEYS:
        if tok == k:
            return k
    for k in ROOT_KEYS:
        try:
            if tok == (t(k, lang) or "").strip().lower():
                return k
        except Exception:
            pass
    return None

def _cos(a, b):
    den = (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b)/den) if den else 0.0

def _ensure_intents():
    global _intent_vecs
    if _intent_vecs is not None:
        return
    texts = list(INTENTS.values())
    vecs = embed(texts)
    _intent_vecs = {name: np.array(vecs[i], dtype=np.float32) for i, name in enumerate(INTENTS.keys())}

def parse_slots(text: str, lang: str):
    low = text.lower()
    if any(k in low for k in ["週", "week"]):   rng = "week"
    elif any(k in low for k in ["月", "month"]): rng = "month"
    elif any(k in low for k in ["年", "year"]):  rng = "year"
    else: rng = None

    m_lang = re.match(r".*\b(lang(?:uage)?|語言)\b\s*([a-z]{2}(?:-[A-Z]{2})?)", low)
    new_lang = m_lang.group(2) if m_lang else None

    m_add = re.match(r".*(?:分類|category)\s+(\S+)\s*=\s*(\S+)", text, re.IGNORECASE)
    add_kw, add_cat = (m_add.group(1), m_add.group(2).lower()) if m_add else (None, None)

    m_del = re.match(r".*(?:刪除分類|delete\s*category)\s+(\S+)", text, re.IGNORECASE)
    del_kw = m_del.group(1).lower() if m_del else None

    m_rec = re.match(r"^(.+?)\s*(\d+)$", text.strip())
    rec_desc = m_rec.group(1) if m_rec else None
    rec_amt = int(m_rec.group(2)) if m_rec else None

    m_quick_default = re.match(r"^\s*新增\s+(\S+)\s*$", text)
    add_child_name = None
    add_parent_key = None
    if m_quick_default:
        add_child_name = m_quick_default.group(1).strip()
        add_parent_key = "others"

    m_quick_scoped = re.match(r"^\s*(\S+?)類別內細分(\S+)\s*$", text)
    if m_quick_scoped:
        parent_token = m_quick_scoped.group(1).strip()
        add_child_name = m_quick_scoped.group(2).strip()
        add_parent_key = canonical_root_from_token(parent_token, lang) or "others"

    return {
        "range": rng, "new_lang": new_lang,
        "add_kw": add_kw, "add_cat": add_cat,
        "del_kw": del_kw,
        "rec_desc": rec_desc, "rec_amt": rec_amt,
        "add_parent_key": add_parent_key,
        "add_child_name": add_child_name,
    }

def route(text: str, lang: str):
    _ensure_intents()
    slots = parse_slots(text, lang)

    if slots.get("add_parent_key") and slots.get("add_child_name"):
        return {
            "intent": "add_category_quick",
            "parent_key": slots["add_parent_key"],
            "child_name": slots["add_child_name"],
            **slots,
            "score": 1.0
        }

    v = np.array(embed([text])[0], dtype=np.float32)
    best, sim = "unknown", -1.0
    for name, vec in _intent_vecs.items():
        s = _cos(v, vec)
        if s > sim:
            best, sim = name, s

    if sim < _THRESHOLD:
        if slots["rec_desc"] and slots["rec_amt"] is not None:
            return {"intent": "record", **slots, "score": sim}
        return {"intent": "ai", **slots, "score": sim}

    return {"intent": best, **slots, "score": sim}
