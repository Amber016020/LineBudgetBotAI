# apps/services/openai_embed.py
from openai import OpenAI
import os
_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_MODEL = "text-embedding-3-small"

def embed(texts):
    resp = _client.embeddings.create(input=texts, model=_MODEL)
    return [d.embedding for d in resp.data]
