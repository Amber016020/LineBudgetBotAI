import apps.services.call_openai_chatgpt as ai
import apps.common.database as db
from apps.common.i18n import t

# Generate financial insights from user transactions using AI
def handle_ai_question(user_id, question):
    transactions = db.get_user_transactions(user_id)  
    lang = db.get_user_language(user_id)  

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
        "You are an assistant for a personal finance chatbot.\n"
        "Follow these rules based on the user's question:\n"
        "1. If the user asks about spending, use ONLY the [Transaction Records] below to:\n"
        "   - Group expenses by category (e.g., food, transport, clothing)\n"
        "   - Calculate total and average spending per category\n"
        "   - Identify the highest spending category or unusually high expenses\n"
        "   - Give a short, friendly suggestion or insight if relevant\n"
        "   Keep the reply concise (around 100 words) and in the same language as the user's question.\n"
        "   Do NOT fabricate records or infer income. If data is insufficient, say so politely.\n"
        "2. If the user asks about bot functions, briefly explain with an example such as "
        "`午餐 100` to record an expense or `查帳` to check records.\n"
        "3. If the user is just making small talk, respond casually and keep the conversation light.\n"
        "\n"
        f"[Transaction Records]\n{context}\n\n"
        f"[User Question] \"{question}\"\n"
        "Respond in a single, friendly, and clear paragraph:"
    )


    return ai.call_openai_chatgpt(prompt, lang)
