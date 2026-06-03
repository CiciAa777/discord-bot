import base64
import openai
from config import UCSD_API_KEY, UCSD_BASE_URL, LLM_VISION_MODEL

_client = openai.OpenAI(api_key=UCSD_API_KEY, base_url=UCSD_BASE_URL)

VISION_PROMPT = """Describe this screenshot concisely. Include:
- What type of content it is (product listing, article, recipe, social post, etc.)
- Key details: names, prices, dates, locations, quantities
- The main point or action the user likely saved this for

Be factual. Output plain text only."""


def extract(image_bytes: bytes) -> str:
    """Returns a natural-language description of the image using UCSD Gemma Vision."""
    # Convert raw download bytes directly to base64 format string
    b64_string = base64.b64encode(image_bytes).decode('utf-8')
    
    # Call the vision-capable model
    response = _client.chat.completions.create(
        model=LLM_VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": VISION_PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_string}"
                        }
                    }
                ]
            }
        ]
    )
    return response.choices[0].message.content.strip()