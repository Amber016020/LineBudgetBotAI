from linebot.v3.webhooks import PostbackEvent
from linebot.v3.messaging import MessagingApi, ApiClient, Configuration, ReplyMessageRequest, TextMessage
import apps.common.database as db
from apps.common.i18n import t
import os

configuration = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))

# Handler for PostbackEvent (e.g., button clicks with data payloads)
def handle_postback(event: PostbackEvent):
    user_id = event.source.user_id
    data = event.postback.data
    lang = db.get_user_language(user_id)
    with ApiClient(configuration) as api_client:
        bot = MessagingApi(api_client)

        # Delete a specific transaction record by index
        if data.startswith("delete_"):
            index = int(data.split("_")[1])
            db.delete_record(user_id, index)
            bot.reply_message(ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=t("delete_nth", lang).format(n=index))
                ]
            ))

        # Sync keyword-category mapping to historical records
        elif data.startswith("SYNC_CATEGORY_YES"):
            try:
                _, keyword, category = data.split("|")
                matched_records = db.find_transactions_by_keyword(user_id, keyword)

                for record in matched_records:
                    db.update_transaction_category(record["id"], category)

                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(text=f"✅ {t('category_sync_prompt', lang).format(keyword=keyword, category=category)}\n"
                                         f"{t('category_added', lang).format(keyword=keyword, category=category)}\n"
                                         f"{t('delete_nth', lang).format(n=len(matched_records))}")
                    ]
                ))
            except Exception as e:
                bot.reply_message(ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="❗" + t("category_add_format_error", lang))]  # 可視情況新增一個 error key
                ))

        # User declined to sync category
        elif data.startswith("SYNC_CATEGORY_NO"):
            bot.reply_message(ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=t("category_sync_prompt", lang))]  # 或可以另外新增一個 like `sync_cancelled`
            ))