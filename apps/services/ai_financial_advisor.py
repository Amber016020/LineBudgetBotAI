import apps.services.call_openai_chatgpt as ai
import apps.common.database as db
from apps.common.i18n import t
from apps.common.lang_utils import detect_lang_by_text

# Generate financial insights from user transactions using AI
def handle_ai_question(user_id, question):
    transactions = db.get_user_transactions(user_id)  
    lang = detect_lang_by_text(question)  

    if not transactions:
        return t("no_transaction_data", lang)

    # Format transactions into readable lines
    context_lines = []
    for t_data in transactions:
        line = t("record_line_format", lang).format(
            date=t_data['date'].strftime('%Y-%m-%d'),
            category=t_data['category'],
            amount=t_data['amount'],
            message=t_data['message']
        )
        context_lines.append(line)

    context = "\n".join(context_lines)

    # Create AI prompt for financial analysis
    prompt = (
        "Use the [Transaction Records] below to:\n"
        "- Group expenses by category (e.g., food, transport, clothing)\n"
        "- Calculate the total and average spending per category\n"
        "- Detect any unusually high spending\n"
        "- Briefly mention what the user spent most on\n"
        "- If possible, offer a friendly suggestion or insight based on these records\n"
        "\n"
        "Do NOT make up any records or infer income. Only use what is provided.\n"
        "If the data is insufficient or very short, just say so politely.\n"
        "\n"
        f"[Transaction Records]\n{context}\n\n"
        f"[User Question] \"{question}\"\n"
        "\nPlease answer in a single, friendly, and clear paragraph (using the same language as the user's question):"
    )

    return ai.call_openai_chatgpt(prompt)
