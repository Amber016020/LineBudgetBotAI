from linebot.v3.webhooks import PostbackEvent
from linebot.v3.messaging import MessagingApi, ApiClient, Configuration, ReplyMessageRequest, TextMessage
import apps.common.database as db
from apps.services.reply_service import get_main_quick_reply
from apps.common.i18n import t
import os

configuration = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))

# Handler for PostbackEvent (e.g., button clicks with data payloads)
def handle_postback(event: PostbackEvent):
    user_id = event.source.user_id
    data = event.postback.data
    lang = db.get_user_language(user_id) or "zh-TW"

    with ApiClient(configuration) as api_client:
        bot = MessagingApi(api_client)

        if data.startswith("delete_"):
            try:
                index = int(data.split("_", 1)[1])
                db.delete_record(user_id, index)
                msg = t("delete_nth", lang).format(n=index)
            except Exception:
                msg = t("delete_failed", lang)

            bot.reply_message(ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(
                        text=msg,
                        quick_reply=get_main_quick_reply(lang) 
                    )
                ]
            ))