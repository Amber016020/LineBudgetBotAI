import os
import tempfile
from datetime import datetime
import plotly.graph_objects as go
from supabase import create_client
from storage3.types import FileOptions
from linebot.v3.messaging.models import ImageMessage
from apps.common.database import get_user_transactions
from apps.common.i18n import t

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def delete_old_charts_for_user(user_id: str):
    files = supabase.storage.from_("charts").list()
    to_delete = [f["name"] for f in files if f["name"].startswith(f"chart_{user_id}_")]
    if to_delete:
        supabase.storage.from_("charts").remove(to_delete)

def upload_chart_to_supabase(local_file_path, user_id):
    delete_old_charts_for_user(user_id) 
    file_name = f"chart_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png"
    with open(local_file_path, "rb") as f:
        supabase.storage.from_("charts").upload(
            path=file_name,
            file=f,
            file_options=FileOptions(content_type="image/png")
        )
    return f"{SUPABASE_URL}/storage/v1/object/public/charts/{file_name}"

def generate_expense_chart(user_id: str, start_time: datetime, end_time: datetime, lang: str = "zh-TW") -> ImageMessage:
    transactions = get_user_transactions(user_id, start_time=start_time, end_time=end_time)
    category_sums = {}
    
    for r in transactions:
        category = r.get("category") or t("default_category", lang)
        amount = r.get("amount", 0)
        if category.lower() in [t("income", lang).lower()]:
            continue
        category_sums[category] = category_sums.get(category, 0) + amount

    if not category_sums:
        raise ValueError(t("no_expense_data", lang))

    categories = list(category_sums.keys())
    values = list(category_sums.values())

    fig = go.Figure(
        data=[
            go.Bar(
                x=categories,
                y=values,
                text=[f"NTD {int(v):,}" for v in values],
                textposition="outside",
                marker_color="LightSkyBlue"
            )
        ]
    )

    fig.update_layout(
        title=t("expense_chart_title", lang),
        yaxis_title=t("expense_chart_ylabel", lang),
        xaxis_tickangle=-30,
        margin=dict(l=40, r=20, t=50, b=100),
        font=dict(family="Microsoft JhengHei", size=12)
    )

    # 儲存為 PNG
    tmp_path = os.path.join(tempfile.gettempdir(), f"expense_chart_{user_id}.png")
    fig.write_image(tmp_path, format="png", engine="kaleido")

    public_url = upload_chart_to_supabase(tmp_path, user_id)
    os.remove(tmp_path)

    return ImageMessage(
        original_content_url=public_url,
        preview_image_url=public_url
    )
