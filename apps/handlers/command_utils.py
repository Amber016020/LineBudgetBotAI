# apps/handlers/command_utils.py
import re

COMMAND_PATTERNS = {
    "record": [
        r"^記帳$",
        r"^record$",
        r"記.*(一下|起來|一下吧|一下喔)?",
        r"幫我記.*",
        r"我想記.*",
    ],
    "check": [
        r"^查帳$",
        r"^check$",
        r"我要看.*帳",
        r"最近.*帳",
        r"查看.*帳",
        r"清單",
    ],
    "summary": [
        r"^summary$",
        r"^本週總結$",
        r"這週.*(花|支出|收入)",
        r"週報",
        r"^本週總覽$",
        r"^週總結$",
    ],
    "weekly_details": [
        r"^本週明細$",
        r"^這週明細$",
        r"^週明細$",
    ],
    "monthly": [
        r"^本月總結$",
        r"^月總結$",
    ],
    "monthly_details": [
        r"^本月明細$",
        r"^這月明細$",
        r"^月明細$",
    ],
    "yearly": [
        r"^今年總結$",
        r"^年度總結$",
        r"^年總結$",
    ],
    "yearly_details": [
        r"^今年明細$",
        r"^年度明細$",
        r"^年明細$",
    ],
}



def normalize_command(text: str) -> str:
    text = text.strip().lower()

    for command, patterns in COMMAND_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return command

    return ""  # 無法判斷
