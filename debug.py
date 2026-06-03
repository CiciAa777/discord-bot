from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("UCSD_API_KEY")

print("Key loaded:", bool(api_key))
print("Key prefix:", api_key[:10] if api_key else "None")

client = OpenAI(
    api_key=api_key,
    base_url="https://tritonai-api.ucsd.edu",
)

print("\n=== TEST 1: CHAT MODEL ===")

try:
    resp = client.chat.completions.create(
        model="api-gpt-oss-120b",
        messages=[
            {"role": "user", "content": "Say hello"}
        ],
        max_tokens=20,
    )

    print("CHAT SUCCESS")
    print(resp.choices[0].message.content)

except Exception as e:
    print("CHAT FAILED")
    print(type(e).__name__)
    print(e)

print("\n=== TEST 2: EMBEDDING MODEL ===")

try:
    resp = client.embeddings.create(
        model="api-tgpt-embeddings",
        input="hello world",
    )

    print("EMBED SUCCESS")
    print("Embedding length:", len(resp.data[0].embedding))

except Exception as e:
    print("EMBED FAILED")
    print(type(e).__name__)
    print(e)