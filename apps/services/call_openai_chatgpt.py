from openai import OpenAI
from apps.common.lang_utils import detect_lang_by_text
from apps.common.i18n import t
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
def call_openai_chatgpt(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": ( "You are a financial assistant who helps users analyze their expense records and offers simple, practical suggestions. "
                                                "Please respond in the same language the user uses. "
                                                "If the user writes in Chinese, reply in clear, conversational Traditional Chinese. "
                                                "If the user writes in English, reply in English. "
                                                "Avoid sounding overly formal or academic — your tone should be friendly, approachable, and helpful, like a smart everyday assistant."
                                            )},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI Error:", e)
        lang = detect_lang_by_text(prompt)
        return t("openai_error", lang)