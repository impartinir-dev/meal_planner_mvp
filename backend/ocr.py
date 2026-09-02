import json
import os
import re

RECEIPT_PROMPT = """Du liest einen deutschen Supermarkt-Kassenbon (REWE, Lidl, ALDI, Kaufland, EDEKA).
Ordne jede erkennbare Lebensmittelzeile einem Namen aus dieser Zutatenliste zu (exakter String):
{ingredients}

Antworte NUR mit JSON:
{{"items": [{{"name": "<exakter Listenname>", "quantity": <Zahl>, "unit": "g"|"ml"|"Stück"}}]}}

Wenn die Menge unklar ist, nimm pack_size-typisch 1 Packung in g/Stück.
Ignoriere Pfand, Tüten, Non-Food. Wenn nichts erkennbar: {{"items": []}}.
"""


def _parse_json_payload(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def scan_receipt_image(image_bytes, mime="image/jpeg", ingredient_names=None):
    api_key = os.environ.get("XAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ocr_not_configured")

    import base64
    from openai import OpenAI

    names = ingredient_names or []
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
    response = client.responses.create(
        model="grok-4.6",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": data_url, "detail": "high"},
                    {
                        "type": "input_text",
                        "text": RECEIPT_PROMPT.format(ingredients=", ".join(names)),
                    },
                ],
            }
        ],
    )
    text = getattr(response, "output_text", None) or ""
    data = _parse_json_payload(text)
    items = data.get("items") or []
    allowed = {n.lower(): n for n in names}
    cleaned = []
    for raw in items:
        name = allowed.get(str(raw.get("name") or "").strip().lower())
        if not name:
            continue
        try:
            qty = float(raw.get("quantity") or 0)
        except (TypeError, ValueError):
            continue
        unit = raw.get("unit") or "g"
        if unit not in ("g", "ml", "Stück"):
            unit = "g"
        if qty <= 0:
            continue
        cleaned.append({"name": name, "quantity": qty, "unit": unit})
    return cleaned
