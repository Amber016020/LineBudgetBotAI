from linebot.v3.messaging import QuickReply, QuickReplyItem, MessageAction
from apps.common.i18n import t



def get_main_quick_reply(lang="zh-TW"):
    return QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label=t("check", lang), text=t("check", lang))),
            QuickReplyItem(action=MessageAction(label=t("week_summary", lang), text=t("week_summary", lang))),
            QuickReplyItem(action=MessageAction(label=t("week_summary_bar", lang), text=t("week_summary_bar", lang))),
        ]
    )
    
