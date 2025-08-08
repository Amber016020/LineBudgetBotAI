from linebot.v3.messaging.models import FlexMessage
from apps.common.i18n import t

# --- paging helpers & carousel generators ---

def _chunks(lst, size):
    for i in range(0, len(lst or []), size):
        yield lst[i:i+size]

def generate_summary_carousel(
    income, expense, balance,
    records, summary_type, lang="zh-TW",
    page_size=8
):

    pages = list(_chunks(records, page_size))[:10]
    total_pages = max(1, len(pages))

    if not pages:
        from linebot.v3.messaging.models import FlexMessage
        empty = generate_summary_flex(
            income, expense, balance,
            records=[], summary_type=summary_type, lang=lang, max_detail_rows=page_size
        )
        return empty

    bubbles = []
    for idx, recs in enumerate(pages, start=1):
        page_title = f"{summary_type} · {idx}/{total_pages}"
        bubble_msg = generate_summary_flex(
            income, expense, balance,
            records=recs,
            summary_type=page_title,
            lang=lang,
            max_detail_rows=page_size,
            more_postback_data=None  
        )
        bubbles.append(bubble_msg.contents)  
        
    from linebot.v3.messaging.models import FlexMessage
    return FlexMessage.from_dict({
        "type": "flex",
        "altText": summary_type,
        "contents": {"type": "carousel", "contents": bubbles}
    })

def flex_recent_records_carousel(records, lang="zh-TW", page_size=10):
    from linebot.v3.messaging.models import FlexMessage
    pages = list(_chunks(records, page_size))[:10]
    if not pages:
        return flex_recent_records([], lang)

    bubbles = []
    total_pages = len(pages)
    for idx, recs in enumerate(pages, start=1):
        bubble_msg = flex_recent_records(recs, lang)   
        bubble = bubble_msg.contents                    
        
        try:
            title_node = bubble["body"]["contents"][0]
            if isinstance(title_node, dict) and title_node.get("type") == "text":
                title_node["text"] = f'{title_node.get("text", "")} · {idx}/{total_pages}'
        except Exception:
            pass
        bubbles.append(bubble)

    return FlexMessage.from_dict({
        "type": "flex",
        "altText": t("recent_records_alt", lang),
        "contents": {"type": "carousel", "contents": bubbles}
    })


def generate_summary_flex(
    income,
    expense,
    balance,
    records=None,
    summary_type="week",
    lang="en",
    max_detail_rows=8,           # Max detail rows in one bubble
    more_postback_data=None      # Postback data for "View More"
):
    records = records or []
    title = t("summary_title", lang).format(summary_type=summary_type)
    alt_text = title

    # Summary section
    summary_box = {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": [
            {
                "type": "box",
                "layout": "baseline",
                "contents": [
                    {"type": "text", "text": f"💸 {t('expense', lang)}", "flex": 2},
                    {"type": "text", "text": f"${expense}", "flex": 3, "align": "end"}
                ]
            }
        ]
    }

    # Detail section
    detail_title = t("detail_list_title", lang).format(summary_type=summary_type)
    detail_rows = []
    for record in records[:max_detail_rows]:
        category = record.get("category", t("uncategorized", lang))
        amount = record.get("amount", 0)
        item = record.get("item", "")
        record_type = t("income", lang) if record.get("type") == "income" else t("expense", lang)
        detail_rows.append({
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": f"{record_type} | {category} - {item}", "flex": 7, "size": "sm"},
                {"type": "text", "text": f"${amount}", "flex": 2, "size": "sm", "align": "end"}
            ]
        })

    detail_section = {
        "type": "box",
        "layout": "vertical",
        "spacing": "md",
        "contents": [
            {"type": "text", "text": f"📋 {detail_title}", "weight": "bold", "size": "lg"},
        ] + (detail_rows if detail_rows else [
            {"type": "text", "text": t("no_records", lang), "size": "sm", "color": "#999999"}
        ])
    }

    # Footer for "View More"
    footer = None
    if more_postback_data and len(records) > max_detail_rows:
        footer = {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": t("view_more", lang),
                        "data": more_postback_data
                    }
                }
            ]
        }

    bubble_dict = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "lg",
            "contents": [
                {"type": "text", "text": title, "weight": "bold", "size": "xl", "margin": "md"},
                summary_box,
                {"type": "separator", "margin": "md"},
                detail_section
            ]
        }
    }

    if footer:
        bubble_dict["footer"] = footer

    return FlexMessage.from_dict({
        "type": "flex",
        "altText": alt_text,
        "contents": bubble_dict
    })

def flex_recent_records(records, lang):
    def s(x): return "" if x is None else str(x)
    def ellipsis(x, n):
        x = s(x)
        return x if len(x) <= n else x[:n-1] + "…"

    MAX_ROWS = 10
    rows = []
    for i, r in enumerate(records[:MAX_ROWS], start=1):
        name = (s(r.get("category_name")).strip() or t("uncategorized", lang))
        item = s(r.get("item")).strip()
        display_name = f"{name} - {item}" if item else name
        amount_txt = f"${s(r.get('amount'))}"


        rows.append({
            "type": "box",
            "layout": "horizontal",      
            "spacing": "sm",
            "contents": [
                { "type": "text", "text": f"{i}. {ellipsis(display_name, 18)}", "size": "sm", "flex": 7, "wrap": False },
                { "type": "text", "text": ellipsis(amount_txt, 10), "size": "sm", "align": "end", "flex": 3 },
                {
                    "type": "image",   
                    "url": "https://cdn-icons-png.flaticon.com/512/1214/1214428.png",
                    "size": "xs",
                    "aspectRatio": "1:1",
                    "flex": 1,
                    "gravity": "center",
                    "action": { "type": "postback", "data": f"delete_{i}" }
                }
            ]
        })

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                { "type": "text", "text": t("recent_records_title", lang), "weight": "bold", "size": "lg" },
                *rows
            ]
        }
    }
    return FlexMessage.from_dict({
        "type": "flex",
        "altText": t("recent_records_alt", lang),
        "contents": bubble
    })
