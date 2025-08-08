import re
import numpy as np
from apps.services.openai_embed import embed 
from apps.common.i18n import t

_INTENTS = {
    "check": (
        "list recent records and allow deletion; "
        "查詢最近記錄, 查帳, 查看明細, 看最近花了什麼, 最近消費, 最近帳目, 列出紀錄"
    ),
    "change_language": (
        "change preferred language, e.g., 'language en'; "
        "切換語言, 語言 zh-TW, 語言 en, 語系, 語言設定"
    ),
    "chart": (
        "show expense chart for week/month/year; "
        "支出圖, 圖表, 消費圖, 週支出圖, 月支出圖, 年支出圖, 趨勢圖, 長條圖, 圓餅圖"
    ),
    "summary": (
        "show income/expense/balance summary; "
        "總結, 本週總結, 本月總結, 本年總結, 收支統計, 統計, 總覽"
    ),
     "add_category_quick": (
        "quickly add a subcategory under a root; "
        "新增 子類別, 新增 XXX, <大類>類別內細分<子類別>, 在娛樂底下新增訂閱, 在others底下新增孝親費"
    ),
    "record": (
        "record an expense like '早餐 60'; "
        "記帳, 早餐 60, 午餐 120, 晚餐 200, 咖啡 80, 便當 95, 公車 30, 捷運 50, "
        "uber 150, 計程車 200, 高鐵 1500, 買書 450, 買鞋 1800, momo 999, 蝦皮 320, "
        "星巴克 150, 看電影 300, 唱歌 600, switch 遊戲 1500, 感冒看醫生 300, 藥局 200, "
        "牙醫 800, 股票 5000, 基金 10000, 投資 2000, 房租 25000, 水費 600, 電費 900"
    ),
    "ai": (
        "general chat or question to AI; "
        "我這週花最多錢的是什麼？, 這個月交通花多少？, 早餐平均花多少？, 幫我看看哪一類超支, "
        "有沒有省錢建議, 近三個月趨勢, 我是不是喝太多手搖, 最高單筆是哪一筆, "
        "把最近的娛樂支出列出來, 這週跟上週比較一下, 本月預算剩多少, "
        "幫我看看早餐平均花多少？"
    )
}

_THRESHOLD = 0.20  # intent similarity threshold
_intent_vecs = None

ROOT_KEYS = ["food", "investment", "transport", "entertainment", "shopping", "medical", "others"]

def canonical_root_from_token(token: str, lang: str) -> str | None:
    """
    Map a user-typed root label (e.g., '娛樂' or 'entertainment') to a canonical root key.
    """
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
    texts = list(_INTENTS.values())
    vecs = embed(texts)  # -> list[list[float]]
    _intent_vecs = {name: np.array(vecs[i], dtype=np.float32) for i, name in enumerate(_INTENTS.keys())}

def parse_slots(text: str, lang: str):
    # chart/summary range
    low = text.lower()
    if any(k in low for k in ["週", "week"]):   rng = "week"
    elif any(k in low for k in ["月", "month"]): rng = "month"
    elif any(k in low for k in ["年", "year"]):  rng = "year"
    else: rng = None

    # language change
    m_lang = re.match(r".*\b(lang(?:uage)?|語言)\b\s*([a-z]{2}(?:-[A-Z]{2})?)", low)
    new_lang = m_lang.group(2) if m_lang else None

    # add_category: e.g., "分類 早餐 = food"
    m_add = re.match(r".*(?:分類|category)\s+(\S+)\s*=\s*(\S+)", text, re.IGNORECASE)
    add_kw, add_cat = (m_add.group(1), m_add.group(2).lower()) if m_add else (None, None)

    # delete_category: e.g., "刪除分類 早餐"
    m_del = re.match(r".*(?:刪除分類|delete\s*category)\s+(\S+)", text, re.IGNORECASE)
    del_kw = m_del.group(1).lower() if m_del else None

    # record: "<desc> <amount>"
    m_rec = re.match(r"^(.+?)\s*(\d+)$", text.strip())
    rec_desc = m_rec.group(1) if m_rec else None
    rec_amt = int(m_rec.group(2)) if m_rec else None

    # --- NEW: quick add subcategory ---
    # 1) "新增 孝親費"  -> parent others
    m_quick_default = re.match(r"^\s*新增\s+(\S+)\s*$", text)
    add_child_name = None
    add_parent_key = None
    if m_quick_default:
        add_child_name = m_quick_default.group(1).strip()
        add_parent_key = "others"

    # 2) "娛樂類別內細分訂閱" -> parent = entertainment, child = 訂閱
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
        # new slots:
        "add_parent_key": add_parent_key,
        "add_child_name": add_child_name,
    }

def route(text: str, lang: str):
    _ensure_intents()
    slots = parse_slots(text, lang)

    # 先處理「快速新增子類別」
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
