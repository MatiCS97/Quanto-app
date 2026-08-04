import base64
import os

from anthropic import Anthropic
from fastapi import APIRouter, UploadFile

router = APIRouter()

VISION_PROMPT = """Identifica el producto en esta imagen. Responde solo con JSON:
{"brand": "...", "model": "...", "category": "...", "search_query": "..."}
Si no reconoces el producto con confianza, responde {"search_query": null}."""


@router.post("/identify")
async def identify_product(file: UploadFile):
    image_bytes = await file.read()
    image_b64 = base64.b64encode(image_bytes).decode()

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": file.content_type or "image/jpeg",
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": VISION_PROMPT},
                ],
            }
        ],
    )
    return {"raw": response.content[0].text}
