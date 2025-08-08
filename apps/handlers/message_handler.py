# === Standard Library ===
import os, re
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# === LINE SDK ===
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import (
    MessagingApi, ApiClient, Configuration, ReplyMessageRequest, TextMessage,
)
from linebot.v3.messaging.models import FlexMessage, ImageMessage

# === Common Utilities ===
from apps.common.i18n import t
import apps.common.database as db

# === handlers ===
from apps.handlers.reply_service import generate_summary_flex,flex_recent_records, generate_summary_carousel   
from apps.handlers.chart_handler import generate_expense_chart

# === Services ===
from apps.services.category_classifier import classify_category_by_embedding
from apps.services.nlp_router import route
from apps.services.ai_financial_advisor import handle_ai_question 
from apps.services.reply_service import get_main_quick_reply

from config import ALLOWED_LANGS

configuration = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))

MAX_TMPL_TEXT = 60
MAX_TMPL_TITLE = 40
MAX_TMPL_LABEL = 20
MAX_FLEX_ALT = 300  

# ---------- helpers ----------
def clip(s: str, n: int) -> str:
    s = str(s or "")
    return s if len(s) <= n else s[: n - 1] + "…"

def send_text(bot, event, text, lang="zh-TW"):
    bot.reply_message(ReplyMessageRequest(
        reply_token=event.reply_token,
        messages=[
            TextMessage(
                text=text,
                quick_reply=get_main_quick_reply(lang)
            )
        ]
    ))

def send_flex(bot, event, flex: FlexMessage, lang="zh-TW"):
    flex.quick_reply = get_main_quick_reply(lang)
    bot.reply_message(ReplyMessageRequest(
        reply_token=event.reply_token,
        messages=[flex]
    ))

def send_image(bot, event, image: ImageMessage, lang="zh-TW"):
    image.quick_reply = get_main_quick_reply(lang)
    bot.reply_message(ReplyMessageRequest(
        reply_token=event.reply_token,
        messages=[image]
    ))
    
def canonical_lang(code: str | None) -> str | None:
    if not code: return None
    s = code.strip().replace("－", "-").replace("—", "-").replace("_", "-")
    s = "".join(re.findall(r"[A-Za-z\-]+", s)).lower()
    return {"zh-tw": "zh-TW", "en": "en"}.get(s)

def resolve_user_category(user_id: str, message: str) -> str | None:
    try:
        pairs = db.get_user_categories(user_id) 
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

def do_change_language(user_id, event, lang, bot, **_):
    nl = canonical_lang(lang)
    if nl and nl in ALLOWED_LANGS:
        db.set_user_language(user_id, nl)
        return send_text(bot, event, f"{t('language_changed', nl)} ({nl})")
    return send_text(bot, event, t("language_not_supported", lang))

def do_chart(user_id, event, lang, bot, range=None, **_):
    if not range:
        return send_text(bot, event, t("chart_range_hint", lang), lang=lang)

    now = datetime.now(timezone.utc)
    start, end, key = period_from_label(range, now)
    try:
        img = generate_expense_chart(user_id, start_time=start, end_time=end, lang=lang)
        return send_image(bot, event, img, lang=lang) 
    except ValueError:
        return send_text(bot, event, t("no_expense_in_range", lang).format(range=t(key, lang)), lang=lang)
    except Exception as e:
        print(f"❌ Chart error: {e}")
        return send_text(bot, event, t("chart_failed", lang), lang=lang)

def do_summary(user_id, event, lang, bot, range=None, **_):
    now = datetime.now(timezone.utc)
    start, end, key = period_from_label(range or "week", now)
    records = db.get_user_transactions(user_id, start_time=start, end_time=end)

    sums = defaultdict(int)
    for r in records:
        cat = (r.get("type") or "").lower()
        if cat == "income":
            sums["income"] += r.get("amount", 0)
        else:
            sums["expense"] += r.get("amount", 0)

    income, expense = sums["income"], sums["expense"]
    summary_label = t(key, lang)

    if len(records) > 8:
        flex = generate_summary_carousel(
            income, expense, income - expense,
            records=records,
            summary_type=summary_label,
            lang=lang,
            page_size=8
        )
    else:
        flex = generate_summary_flex(
            income, expense, income - expense,
            records=records, summary_type=summary_label, lang=lang, max_detail_rows=8
        )

    return send_flex(bot, event, flex, lang=lang)

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
    try:
        answer = handle_ai_question(user_id, text or "")
        return send_text(bot, event, answer)
    except Exception as e:
        return send_text(bot, event, t("not_understood", lang))

def do_unknown(user_id, event, lang, bot, text=None, **_):
    return do_ai(user_id, event, lang, bot, text=text)

# intent -> handler mapping
INTENT_MAP = {
    "check": do_check,
    "change_language": do_change_language,
    "chart": do_chart,
    "summary": do_summary,
    "record": do_record,
    "ai": do_ai,           
    "unknown": do_unknown, 
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
        handler = INTENT_MAP.get(intent, do_unknown)

        try:
            handler(user_id, event, lang, bot, **{**r, "text": text})
        except Exception as e:
            print(f"[handle_message] intent={intent} error={e}")
            send_text(bot, event, t("", lang))