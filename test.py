import openai
client = openai.OpenAI(
    api_key="sk-THlSNbQCmhpYDZMZEjfYiw",
    base_url="https://tritonai-api.ucsd.edu"
)
resp = client.chat.completions.create(
    model="api-gpt-oss-120b",
    max_tokens=200,
    messages=[{"role": "user", "content": "Reply with only the word: hello"}]
)
m = resp.choices[0].message
print('content:', repr(m.content))
print('reasoning:', repr(m.reasoning_content))