import os
from datetime import datetime
from supabase import create_client
from linebot.v3.messaging.models import ImageMessage
from apps.common.database import get_user_transactions
from apps.common.i18n import t
from quickchart import QuickChart

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_expense_chart(user_id: str, start_time: datetime, end_time: datetime, lang: str = "zh-TW") -> ImageMessage:
    transactions = get_user_transactions(user_id, start_time=start_time, end_time=end_time)
    category_sums = {}

    # Sum expenses by category
    for r in transactions:
        category = r.get("category") or t("default_category", lang)
        amount = r.get("amount", 0)
        # 跳過收入類型
        if category.lower() in [t("income", lang).lower()]:
            continue
        category_sums[category] = category_sums.get(category, 0) + amount

    if not category_sums:
        raise ValueError(t("no_expense_data", lang))

    # Configure QuickChart
    qc = QuickChart()
    qc.width = 600
    qc.height = 400
    qc.background_color = "#ffffff"

    qc.config = {
        "type": "bar",
        "data": {
            "labels": list(category_sums.keys()),
            "datasets": [{
                "label": t("expense_chart_ylabel", lang),
                "data": list(category_sums.values()),
                "backgroundColor": "rgba(54, 162, 235, 0.5)",
                "borderColor": "rgb(54, 162, 235)",
                "borderWidth": 1
            }]
        },
        "options": {
            "plugins": {
                "title": {
                    "display": True,
                    "text": t("expense_chart_title", lang),
                    "font": {"size": 18}
                },
                "legend": {"display": False},
                "datalabels": {
                    "anchor": "end",
                    "align": "end",
                    "formatter": "function(value) { return 'NTD ' + new Intl.NumberFormat().format(value); }",
                    "font": {"size": 12}
                }
            },
            "scales": {
                "x": {
                    "ticks": {"font": {"family": "sans-serif"}}
                }
            }
        }
    }

    # Get chart image URL from QuickChart
    chart_url = qc.get_url()

    return ImageMessage(
        original_content_url=chart_url,
        preview_image_url=chart_url
    )
