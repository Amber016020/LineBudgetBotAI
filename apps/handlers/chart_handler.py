import os
from datetime import datetime
from supabase import create_client
from linebot.v3.messaging.models import ImageMessage
from apps.common.i18n import t
from apps.common.database import get_user_category_sums_for_chart 
from quickchart import QuickChart

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Generate a category-wise expense summary chart (bar chart).
def generate_expense_chart(user_id: str, start_time: datetime, end_time: datetime, lang: str = "zh-TW") -> ImageMessage:
    
    rows = get_user_category_sums_for_chart(
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        days=None,
    )
    if not rows:
        raise ValueError(t("no_expense_data", lang))

    labels = [r["category"] for r in rows]
    values = [float(r["total"] or 0) for r in rows]

    if sum(values) == 0:
        raise ValueError(t("no_expense_data", lang))

    # Configure QuickChart (Chart.js)
    qc = QuickChart()
    qc.width = 600
    qc.height = 400
    qc.background_color = "#ffffff"

    qc.config = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": t("expense_chart_ylabel", lang),
                "data": values,
                "backgroundColor": "rgba(30, 102, 200, 1)",
                "borderColor": "rgb(30, 102, 200)",
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
                "anchor": "start",        
                "align": "end",           
                "offset": 20,            
                "formatter": "function(value) { return 'NTD ' + new Intl.NumberFormat().format(value); }",
                "font": {"size": 12},
                "color": "#000"           
            }
            },
            "scales": {
                "x": {"ticks": {"font": {"family": "sans-serif"}}},
                "y": {"beginAtZero": True}
            }
        },
        "plugins": ["chartjs-plugin-datalabels"]
    }

    chart_url = qc.get_url()

    return ImageMessage(
        original_content_url=chart_url,
        preview_image_url=chart_url
    )
