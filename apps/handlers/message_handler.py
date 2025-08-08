# === Standard Library ===
import os
import re
from datetime import datetime, timezone, timedelta

# === LINE SDK ===
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import (
    MessagingApi, ApiClient, Configuration,
    ReplyMessageRequest, TextMessage,
)
from linebot.v3.messaging.models import (
    TemplateMessage, ConfirmTemplate,
    ButtonsTemplate, PostbackAction,
)

# === Common Utilities ===
from apps.common.i18n import t, TEXTS
import apps.common.database as db

# === Services ===
from apps.services.ai_financial_advisor import handle_ai_question
from apps.services.reply_service import get_main_quick_reply
from apps.services.category_classifier import classify_category

# === Handlers ===
from apps.handlers.command_utils import normalize_command
from apps.handlers.reply_service import (
    generate_summary_flex
)
from apps.handlers.chart_handler import generate_expense_chart


configuration = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))

# Handler function for incoming LINE text messages
def handle_message(event: MessageEvent):
    if not isinstance(event.message, TextMessageContent):
        return

    user_id = event.source.user_id
    text = event.message.text.strip()
    command = normalize_command(text)
    lang = db.get_user_language(user_id) 
    print(text)
    with ApiClient(configuration) as api_client:
        bot = MessagingApi(api_client)

        # Asks to check recent records
        if command == "check":
            records = db.get_last_records(user_id)
            if not records:
                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=t("no_records", lang))]
                ))
                return

            actions = [
                PostbackAction(
                    label=t("delete_nth", lang).format(n=i+1),
                    data=f'delete_{i+1}'
                ) for i in range(len(records))
            ]
            text_list = [f'{i+1}. {r["category"]} {r["amount"]}' for i, r in enumerate(records)]
            template = ButtonsTemplate(
                title=t("recent_records_title", lang),
                text="\n".join(text_list),
                actions=actions[:4]
            )
            bot.reply_message(ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TemplateMessage(alt_text=t("recent_records_alt", lang), template=template)]
            ))
            
        # === 新增：修改偏好語言 ===
        elif matches_command_prefix(text, lang, "change_language_prefixes"):
            # 假設 TEXTS["change_language_prefixes"] = {"zh-TW": ["語言", "切換語言"], "en": ["language", "lang"]}
            parts = text.split()
            if len(parts) >= 2:
                new_lang = parts[1]
                db.set_user_language(user_id, new_lang)
                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f"{t('language_changed', new_lang)} ({new_lang})")]
                ))
            else:
                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=t("language_change_format_error", lang))]
                ))
            return
        
        # Requests an expense chart
        elif any(kw in text for kw in ["支出圖", "chart", "週支出圖", "月支出圖", "年支出圖"]):
            try:
                now = datetime.now(timezone.utc)
                time_text = text.replace("支出圖", "").replace("chart", "").strip()

                if time_text in ["週", "week"]:
                    start_time = now - timedelta(days=now.weekday())
                    summary_type = "本週"
                elif time_text in ["月", "month"]:
                    start_time = now.replace(day=1)
                    summary_type = "本月"
                elif time_text in ["年", "year"]:
                    start_time = now.replace(month=1, day=1)
                    summary_type = "今年"
                else:
                    bot.reply_message(ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="請輸入有效的區間，例如：支出圖 週 / 月 / 年")]
                    ))
                    return

                start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
                image_msg = generate_expense_chart(user_id, start_time=start_time, end_time=now)

                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[image_msg]
                ))
            except ValueError as e:
                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=f"{summary_type}內沒有支出資料喔！")]
                ))
            except Exception as e:
                print(f"❌ 支出圖產生失敗: {e}")
                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="圖表生成失敗，請稍後再試")]
                ))

        # Requests a summary of expenses and income
        elif command in ["summary", "weekly", "monthly", "yearly"]:
            from collections import defaultdict
            now = datetime.now(timezone.utc)

            # 計算起始時間
            if command in ["summary", "weekly"]:
                summary_type = "週"
                start_time = now - timedelta(days=now.weekday())  # 本週一
                start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            elif command == "monthly":
                summary_type = "月"
                start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif command == "yearly":
                summary_type = "年"
                start_time = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

            # 查詢範圍內所有紀錄
            records = db.get_user_transactions(user_id, start_time=start_time, end_time=now)

            # 統計收入與支出
            summary = defaultdict(int)
            for r in records:
                # 可以根據你 DB 的實際分類來判斷是收入還是支出
                category = r.get("category", "").lower()
                if category in ["收入", "income"]:
                    summary["income"] += r["amount"]
                else:
                    summary["expense"] += r["amount"]

            income = summary["income"]
            expense = summary["expense"]
            balance = income - expense

            # 建立 FlexMessage 並回覆
            flex_msg = generate_summary_flex(income, expense, balance, summary_type)
            bot.reply_message(ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[flex_msg]
            ))

        # If the user tries to define a custom keyword → category mapping 
        elif matches_command_prefix(text, lang, "add_category_prefixes"):
            print("第一步")
            all_prefixes = TEXTS["add_category_prefixes"]["zh-TW"] + TEXTS["add_category_prefixes"]["en"]
            prefix_pattern = "|".join(re.escape(p) for p in all_prefixes)
            match = re.match(rf"({prefix_pattern})\s*(\S+)\s*=\s*(\S+)", text, re.IGNORECASE)
            print("第二步")
            if match:
                keyword = match.group(2).lower()
                category = match.group(3).lower()
                print(keyword, " " , category)
                # 先刪除再新增（符合修改 spec）
                db.delete_user_category(user_id, keyword)
                db.add_user_category(user_id, keyword, category)
                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text=t("category_added", lang).format(keyword=keyword, category=category)),
                        get_confirm_template(
                            text=t("category_sync_prompt", lang).format(keyword=keyword, category=category),
                            keyword=keyword,
                            category=category
                        )
                    ]
                ))
            else:
                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=t("category_add_format_error", lang))]
                ))

        # If the user tries to delete a custom keyword
        elif matches_command_prefix(text, lang, "delete_category_prefixes"):
            all_prefixes = t["delete_category_prefixes"]["zh-TW"] + t["delete_category_prefixes"]["en"]
            prefix_pattern = "|".join(re.escape(p) for p in all_prefixes)
            match = re.match(rf"({prefix_pattern})\s*(\S+)", text, re.IGNORECASE)

            if match:
                keyword = match.group(2).lower()

                db.delete_user_category(user_id, keyword)

                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=t("category_deleted", lang).format(keyword=keyword))]
                ))
            else:
                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=t("category_delete_format_error", lang))]
                ))
        
        #  Default case – classify and record the expense, or fallback to AI
        else:
            # 模糊分類記帳
            match = re.match(r'^(.+?)\s*(\d+)$', text)
            if match:
                message = match.group(1)
                amount = int(match.group(2))
                category = classify_category(message)
                db.insert_transactions(user_id, category, amount, text)
                category_name = t(category, lang) 
                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=t("recorded_item", lang).format(category=category_name, amount=amount))]
                ))
            else:
                # 其餘的句子（不符合金額格式），一律丟給 AI 處理
                # answer = handle_ai_question(user_id, text)
                # bot.reply_message(ReplyMessageRequest(
                #     reply_token=event.reply_token,
                #     messages=[TextMessage(text=answer)]
                # ))
                # 暫時不啟用 AI 回答，只顯示提示語
                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="目前為 AI 判斷階段，尚未提供回應功能。")]
                ))
# Check if the input text starts with any of the command prefixes for a given key and language.
def matches_command_prefix(text: str, lang: str, key: str) -> bool:
    prefixes = t(key, lang)
    return any(text.lower().startswith(p.lower()) for p in prefixes)

# Generate a ConfirmTemplate message that asks the user whether to synchronize the custom keyword-category mapping.
def get_confirm_template(text, keyword, category):
    return TemplateMessage(
        alt_text=text,
        template=ConfirmTemplate(
            text=text,
            actions=[
                PostbackAction(
                    label="✅ 是",
                    data=f"SYNC_CATEGORY_YES|{keyword}|{category}"
                ),
                PostbackAction(
                    label="❌ 否",
                    data="SYNC_CATEGORY_NO"
                )
            ]
        )
    )