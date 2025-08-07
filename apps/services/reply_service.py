from linebot.v3.messaging import QuickReply, QuickReplyItem, MessageAction
from apps.common.i18n import t

def get_main_quick_reply(lang="zh-TW"):
    return QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label=t("record", lang), text=t("record", lang))),
            QuickReplyItem(action=MessageAction(label=t("check", lang), text=t("check", lang))),
            QuickReplyItem(action=MessageAction(label=t("summary", lang), text=t("summary", lang))),
        ]
    )