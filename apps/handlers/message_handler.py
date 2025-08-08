# === Standard Library ===
import os, re
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# === LINE SDK ===
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import (
    MessagingApi, ApiClient, Configuration, ReplyMessageRequest, TextMessage,
)
from linebot.v3.messaging.models import PostbackAction, ConfirmTemplate, TemplateMessage, FlexMessage

# === Common Utilities ===
from apps.common.i18n import t, TEXTS
import apps.common.database as db

# === handlers ===
from apps.handlers.reply_service import generate_summary_flex,flex_recent_records
from apps.handlers.chart_handler import generate_expense_chart

# === Services ===
from apps.services.category_classifier import classify_category_by_embedding
from apps.services.nlp_router import route
from apps.services.ai_financial_advisor import handle_ai_question 

configuration = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))
ALLOWED_LANGS = {"zh-TW", "en"}

MAX_TMPL_TEXT = 60
MAX_TMPL_TITLE = 40
MAX_TMPL_LABEL = 20
MAX_FLEX_ALT = 300  

# ---------- helpers ----------
def clip(s: str, n: int) -> str:
    s = str(s or "")
    return s if len(s) <= n else s[: n - 1] + "…"

def send_text(bot, event, text):
    bot.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=text)]))

def send_flex(bot, event, flex: FlexMessage):
    bot.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[flex]))

def canonical_lang(code: str | None) -> str | None:
    if not code: return None
    s = code.strip().replace("－", "-").replace("—", "-").replace("_", "-")
    s = "".join(re.findall(r"[A-Za-z\-]+", s)).lower()
    return {"zh-tw": "zh-TW", "en": "en"}.get(s)

def get_confirm_template(text, keyword, category):
    safe_text = clip(text, MAX_TMPL_TEXT)
    return TemplateMessage(
        alt_text=safe_text,
        template=ConfirmTemplate(
            text=safe_text,
            actions=[
                PostbackAction(label=clip("✅ 是", MAX_TMPL_LABEL), data=f"SYNC_CATEGORY_YES|{keyword}|{category}"),
                PostbackAction(label=clip("❌ 否", MAX_TMPL_LABEL), data="SYNC_CATEGORY_NO"),
            ],
        ),
    )

def resolve_user_category(user_id: str, message: str) -> str | None:
    try:
        pairs = db.get_user_categories(user_id)  # [(keyword, root_category), ...]
    except Exception:
        pairs = []

    mlow = (message or "").lower().strip()
    if not mlow:
        return None

    # simple substring match; you can upgrade to tokenized or regex-based matching later
    for keyword, root_cat in pairs:
        if not keyword:
            continue
        if keyword.lower() in mlow:
            return root_cat

    return None

def period_from_label(label: str, now: datetime):
    """label: week|month|year -> (start, end, human_label_key)"""
    if label == "week":
        start = now - timedelta(days=now.weekday())
        key = "week"
    elif label == "month":
        start = now.replace(day=1)
        key = "month"
    else:
        start = now.replace(month=1, day=1)
        key = "year"
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now, key


# ---------- intent handlers ----------
def do_check(user_id, event, lang, bot, **_):
    records = db.get_last_records(user_id)
    if not records:
        return send_text(bot, event, t("no_records", lang))
    return send_flex(bot, event, flex_recent_records(records, lang))

def do_change_language(user_id, event, lang, bot, new_lang=None, **_):
    nl = canonical_lang(new_lang)
    if nl and nl in ALLOWED_LANGS:
        db.set_user_language(user_id, nl)
        return send_text(bot, event, f"{t('language_changed', nl)} ({nl})")
    return send_text(bot, event, t("language_not_supported", lang))

def do_chart(user_id, event, lang, bot, range=None, **_):
    if not range:
        return send_text(bot, event, t("chart_range_hint", lang))
    now = datetime.now(timezone.utc)
    start, end, key = period_from_label(range, now)
    try:
        img = generate_expense_chart(user_id, start_time=start, end_time=end, lang=lang)
        bot.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[img]))
    except ValueError:
        send_text(bot, event, t("no_expense_in_range", lang).format(range=t(key, lang)))
    except Exception as e:
        print(f"❌ Chart error: {e}")
        send_text(bot, event, t("chart_failed", lang))

def do_summary(user_id, event, lang, bot, range=None, **_):
    now = datetime.now(timezone.utc)
    start, end, key = period_from_label(range or "week", now)
    records = db.get_user_transactions(user_id, start_time=start, end_time=end)
    sums = defaultdict(int)
    for r in records:
        cat = (r.get("category") or "").lower()
        (sums["income"] if cat in ["收入", "income"] else sums.__setitem__)  # noop line to keep style

    # explicit accumulate (avoid cleverness)
    sums = defaultdict(int)
    for r in records:
        cat = (r.get("category") or "").lower()
        if cat in ["收入", "income"]:
            sums["income"] += r.get("amount", 0)
        else:
            sums["expense"] += r.get("amount", 0)

    income, expense = sums["income"], sums["expense"]
    flex = generate_summary_flex(
        income, expense, income - expense,
        records=records, summary_type=t(key, lang), lang=lang
    )
    return send_flex(bot, event, flex)

_rec_pat = re.compile(r"^(.+?)\s*([+-]?\d+(?:,\d{3})*)(?:\s*(?:元|ntd))?$", re.IGNORECASE)

def do_record(user_id, event, lang, bot, text=None, rec_desc=None, rec_amt=None, **_):
    # Fallback to regex if router didn't parse amount slots
    if rec_desc is None or rec_amt is None:
        m = _rec_pat.match((text or "").strip())
        if not m:
            return do_ai(user_id, event, lang, bot, text=text)
        rec_desc, rec_amt = m.group(1), int(m.group(2).replace(",", ""))

    item = rec_desc.strip()
    category_info = classify_category_by_embedding(item)
    category_name = category_info.get(lang, category_info["key"])
    category_id = db.get_user_category_id(user_id, category_name)
    db.insert_transactions(
        user_id,
        category_id=category_id,
        item=item,
        amount=rec_amt,
        message=text or f"{item} {rec_amt}"
    )

    return send_text(bot, event, t("recorded_item", lang).format(category = category_name, amount=rec_amt))

def do_ai(user_id, event, lang, bot, text=None, **_):
    print("do_ai")
    """把看不懂的訊息交給 AI，並用使用者語言回覆。"""
    try:
        answer = handle_ai_question(user_id, text or "")
        return send_text(bot, event, answer)
    except Exception as e:
        return send_text(bot, event, t("not_understood", lang))

def do_unknown(user_id, event, lang, bot, text=None, **_):
    print("do_unknown")
    """保底：仍然丟給 AI（避免 dead-end）。"""
    return do_ai(user_id, event, lang, bot, text=text)

# intent -> handler mapping
INTENT_MAP = {
    "check": do_check,
    "change_language": do_change_language,
    "chart": do_chart,
    "summary": do_summary,
    "record": do_record,
    "ai": do_ai,            # ← 新增：AI intent
    "unknown": do_unknown,  # ← unknown 也會轉到 AI
}

# ---------- main entry ----------
def handle_message(event: MessageEvent):
    if not isinstance(event.message, TextMessageContent):
        return

    user_id = event.source.user_id
    text = event.message.text.strip()
    lang = db.get_user_language(user_id) or "zh-TW"

    with ApiClient(configuration) as api_client:
        bot = MessagingApi(api_client)
        r = route(text, lang) or {"intent": "unknown"}
        intent = r.get("intent", "unknown")
        print("intent = " , intent)
        handler = INTENT_MAP.get(intent, do_unknown)

        try:
            # 將 slots 與原始 text 都丟進 handler
            handler(user_id, event, lang, bot, **{**r, "text": text})
        except Exception as e:
            print(f"[handle_message] intent={intent} error={e}")
            send_text(bot, event, t("", lang))