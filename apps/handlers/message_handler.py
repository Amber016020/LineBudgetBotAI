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

# === Services ===
from apps.services.category_classifier import classify_category_by_embedding
from apps.services.nlp_router import route
from apps.handlers.reply_service import generate_summary_flex
from apps.handlers.chart_handler import generate_expense_chart

configuration = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))
ALLOWED_LANGS = {"zh-TW", "en"}

# ---------- helpers ----------
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
    return TemplateMessage(
        alt_text=text,
        template=ConfirmTemplate(
            text=text,
            actions=[
                PostbackAction(label="✅ 是", data=f"SYNC_CATEGORY_YES|{keyword}|{category}"),
                PostbackAction(label="❌ 否", data="SYNC_CATEGORY_NO"),
            ],
        ),
    )

def resolve_user_category(user_id: str, message: str) -> str | None:
    try:
        user_map = db.get_user_categories(user_id) or {}
    except Exception:
        user_map = {}
    mlow = message.lower()
    for kw, cat in user_map.items():
        if kw.lower() in mlow:
            return cat
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

def flex_recent_records(records, lang):
    def ellipsis(s, n): s = str(s or ""); return s if len(s) <= n else s[:n-1] + "…"
    rows = []
    for i, r in enumerate(records[:10], start=1):
        raw_cat = (r.get("category") or "").strip()
        name = t(raw_cat, lang) if raw_cat else t("uncategorized", lang)
        rows.append({
            "type": "box", "layout": "horizontal",
            "contents": [
                {"type": "text", "text": f"{i}. {ellipsis(name, 14)}", "size": "sm", "flex": 3},
                {"type": "text", "text": str(r.get("amount", "")), "size": "sm", "align": "end", "flex": 1},
            ]
        })
    actions = [{
        "type": "button", "style": "secondary", "height": "sm",
        "action": {"type": "postback", "label": t("delete_nth", lang).format(n=i), "data": f"delete_{i}"}
    } for i in range(1, min(len(records), 4) + 1)]
    bubble = {
        "type": "bubble",
        "body": {"type": "box", "layout": "vertical", "spacing": "md",
                 "contents": [{"type": "text", "text": t("recent_records_title", lang), "weight": "bold", "size": "lg"}, *rows]},
        "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": actions}
    }
    return FlexMessage.from_dict({"type": "flex", "altText": t("recent_records_alt", lang), "contents": bubble})

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

def do_add_category(user_id, event, lang, bot, text=None, **_):
    all_prefixes = TEXTS["add_category_prefixes"]["zh-TW"] + TEXTS["add_category_prefixes"]["en"]
    prefix_pattern = "|".join(re.escape(p) for p in all_prefixes)
    m = re.match(rf"({prefix_pattern})\s*(\S+)\s*=\s*(\S+)", text or "", re.IGNORECASE)
    if not m:
        return send_text(bot, event, t("category_add_format_error", lang))
    kw, cat = m.group(2).lower(), m.group(3).lower()
    db.delete_user_category(user_id, kw)
    db.add_user_category(user_id, kw, cat)
    bot.reply_message(ReplyMessageRequest(
        reply_token=event.reply_token,
        messages=[
            TextMessage(text=t("category_added", lang).format(keyword=kw, category=cat)),
            get_confirm_template(text=t("category_sync_prompt", lang).format(keyword=kw, category=cat), keyword=kw, category=cat),
        ]
    ))

def do_delete_category(user_id, event, lang, bot, text=None, **_):
    all_prefixes = TEXTS["delete_category_prefixes"]["zh-TW"] + TEXTS["delete_category_prefixes"]["en"]
    prefix_pattern = "|".join(re.escape(p) for p in all_prefixes)
    m = re.match(rf"({prefix_pattern})\s*(\S+)", text or "", re.IGNORECASE)
    if not m:
        return send_text(bot, event, t("category_delete_format_error", lang))
    kw = m.group(2).lower()
    db.delete_user_category(user_id, kw)
    return send_text(bot, event, t("category_deleted", lang).format(keyword=kw))

_rec_pat = re.compile(r"^(.+?)\s*([+-]?\d+(?:,\d{3})*)(?:\s*(?:元|ntd))?$", re.IGNORECASE)

def do_record(user_id, event, lang, bot, text=None, rec_desc=None, rec_amt=None, **_):
    # Fallback to regex if router didn't parse amount slots
    if rec_desc is None or rec_amt is None:
        m = _rec_pat.match((text or "").strip())
        if not m:
            return send_text(bot, event, t("not_understood", lang))
        rec_desc, rec_amt = m.group(1), int(m.group(2).replace(",", ""))
    cat = resolve_user_category(user_id, rec_desc) or classify_category_by_embedding(rec_desc)
    db.insert_transactions(user_id, cat, rec_amt, text or f"{rec_desc} {rec_amt}")
    return send_text(bot, event, t("recorded_item", lang).format(category=t(cat, lang), amount=rec_amt))

def do_unknown(user_id, event, lang, bot, **_):
    return send_text(bot, event, t("not_understood", lang))

# intent -> handler mapping
INTENT_MAP = {
    "check": do_check,
    "change_language": do_change_language,
    "chart": do_chart,
    "summary": do_summary,
    "add_category": do_add_category,
    "delete_category": do_delete_category,
    "record": do_record,
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

        # Pass all slots to handler; handlers ignore unused keys
        try:
            handler(user_id, event, lang, bot, **{**r, "text": text})
        except Exception as e:
            # One last safety net
            print(f"[handle_message] intent={intent} error={e}")
            send_text(bot, event, t("not_understood", lang))
