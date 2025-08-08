from linebot.v3.messaging.models import FlexMessage
from apps.common.i18n import t

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
                    {"type": "text", "text": f"💰 {t('income', lang)}", "flex": 2},
                    {"type": "text", "text": f"${income}", "flex": 3, "align": "end"}
                ]
            },
            {
                "type": "box",
                "layout": "baseline",
                "contents": [
                    {"type": "text", "text": f"💸 {t('expense', lang)}", "flex": 2},
                    {"type": "text", "text": f"${expense}", "flex": 3, "align": "end"}
                ]
            },
            {
                "type": "box",
                "layout": "baseline",
                "contents": [
                    {"type": "text", "text": f"🧾 {t('balance', lang)}", "flex": 2},
                    {"type": "text", "text": f"${balance}", "flex": 3, "align": "end"}
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
        record_type = t("income", lang) if record.get("type") == "income" else t("expense", lang)
        detail_rows.append({
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": f"{record_type} | {category}", "flex": 3, "size": "sm"},
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
