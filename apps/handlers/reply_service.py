from linebot.v3.messaging.models import FlexMessage
from apps.common.i18n import t 


def generate_summary_flex(income, expense, balance, summary_type="week", lang="zh-TW"):
    title = t("summary_title", lang).format(summary_type=summary_type)
    alt_text = title

    bubble_dict = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "weight": "bold",
                    "size": "xl",
                    "margin": "md"
                },
                {
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
            ]
        }
    }

    return FlexMessage.from_dict({
        "type": "flex",
        "altText": alt_text,
        "contents": bubble_dict
    })


def generate_detail_list_flex(records, summary_type="week", lang="zh-TW"):
    contents = []

    for record in records:
        category = record.get("category", t("uncategorized", lang))
        amount = record.get("amount", 0)
        record_type = t("income", lang) if record.get("type") == "income" else t("expense", lang)
        contents.append({
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": f"{record_type}｜{category}", "flex": 3, "size": "sm"},
                {"type": "text", "text": f"${amount}", "flex": 2, "size": "sm", "align": "end"}
            ]
        })

    title = t("detail_list_title", lang).format(summary_type=summary_type)

    bubble_dict = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": f"📋 {title}", "weight": "bold", "size": "lg"}
            ] + contents
        }
    }

    return FlexMessage.from_dict({
        "type": "flex",
        "altText": title,
        "contents": bubble_dict
    })
