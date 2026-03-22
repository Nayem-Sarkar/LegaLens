import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip()
client = genai.Client(api_key=api_key)

try:
    models = list(client.models.list())
    for m in models:
        print(m.name)
except Exception as e:
    print(f"Error checking models: {e}")
