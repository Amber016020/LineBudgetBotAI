# Standard library
import os
import tempfile
from datetime import datetime

# Data & Plotting
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter
import numpy as np

# External services
from supabase import create_client
from storage3.types import FileOptions

# LINE SDK
from linebot.v3.messaging.models import ImageMessage

# Internal modules
from apps.common.database import get_user_transactions
from apps.common.i18n import t

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Delete existing charts for a user to avoid cluttering storage
def delete_old_charts_for_user(user_id: str):
    files = supabase.storage.from_("charts").list()
    to_delete = [f["name"] for f in files if f["name"].startswith(f"chart_{user_id}_")]
    if to_delete:
        supabase.storage.from_("charts").remove(to_delete)

# Upload local chart image to Supabase storage and return public URL
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

# Generate an expense bar chart based on user transactions and return it as a LINE image message
def generate_expense_chart(user_id: str, start_time: datetime, end_time: datetime, lang: str = "zh-TW") -> ImageMessage:

    plt.rcParams['font.family'] = 'Microsoft JhengHei'

    transactions = get_user_transactions(user_id, start_time=start_time, end_time=end_time)
    category_sums = {}
    
    for r in transactions:
        category = r.get("category") or t("default_category", lang)
        amount = r.get("amount", 0)
        income_keywords = [t("income", lang).lower()]
        if category.lower() in income_keywords:
            continue
        category_sums[category] = category_sums.get(category, 0) + amount

    if not category_sums:
        raise ValueError(t("no_expense_data", lang))

    fig, ax = plt.subplots(figsize=(6, 4))

    categories = list(category_sums.keys())
    values = list(category_sums.values())

    # Use Seaborn color palette for a soft, consistent look
    palette = sns.color_palette("Set2", len(categories))
    colors = palette.as_hex()  # Convert to hex format

    # Create figure with wider size and auto layout
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    bars = ax.bar(categories, values, color=colors)

    # Set chart title and axis labels
    ax.set_title(t("expense_chart_title", lang), fontsize=16, weight="bold", pad=12)
    ax.set_ylabel(t("expense_chart_ylabel", lang), fontsize=13)
    ax.set_xticks(np.arange(len(categories)))
    ax.set_xticklabels(categories, rotation=30, ha="right", fontsize=11)
    ax.margins(x=0.05)

    # Format y-axis labels with thousands separator
    formatter = FuncFormatter(lambda x, _: f"{int(x):,}")
    ax.yaxis.set_major_formatter(formatter)

    # Add value labels above each bar
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"NTD {int(height):,}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 6),
            textcoords="offset points",
            ha='center',
            va='bottom',
            fontsize=10,
            color="#333"
        )

    # Remove top and right borders for a cleaner look
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()

    tmp_path = os.path.join(tempfile.gettempdir(), f"expense_chart_{user_id}.png")
    plt.savefig(tmp_path, format="png")
    plt.close(fig)

    public_url = upload_chart_to_supabase(tmp_path, user_id)
    os.remove(tmp_path)

    return ImageMessage(
        original_content_url=public_url,
        preview_image_url=public_url
    )
