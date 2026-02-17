import httpx
import os
from openai import OpenAI

api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
if not api_key:
    raise RuntimeError(
        "缺少 OPENROUTER_API_KEY。请先执行: export OPENROUTER_API_KEY='your-key'"
    )

client = OpenAI(
    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=api_key,
    # Ignore shell proxy env vars (e.g. ALL_PROXY=socks://...) to avoid httpx init errors.
    http_client=httpx.Client(trust_env=False),
)

# First API call with reasoning
response = client.chat.completions.create(
    model="nvidia/nemotron-nano-12b-v2-vl:free",
    messages=[
        {
            "role": "user",
            "content": "How many r's are in the word 'strawberry'?",
        }
    ],
    extra_body={"reasoning": {"enabled": True}},
)

# Extract the assistant message with reasoning_details
response = response.choices[0].message
print("First response:", response.content)

# Preserve the assistant message with reasoning_details
messages = [
    {"role": "user", "content": "How many r's are in the word 'strawberry'?"},
    {
        "role": "assistant",
        "content": response.content,
        "reasoning_details": response.reasoning_details,  # Pass back unmodified
    },
    {"role": "user", "content": "Are you sure? Think carefully."},
]

# Second API call - model continues reasoning from where it left off
response2 = client.chat.completions.create(
    model="nvidia/nemotron-nano-12b-v2-vl:free",
    messages=messages,
    extra_body={"reasoning": {"enabled": True}},
)
print("Second response:", response2.choices[0].message.content)
