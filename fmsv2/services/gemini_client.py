import json

from google import genai
from google.genai import types

from .errors import ExternalServiceError

_PROMPT = "このレシート画像から購入日・店名・品目ごとの名称・金額・最も近いカテゴリーを抽出して。"


def _build_schema(category_names):
    return {
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "購入日。YYYY-MM-DD形式。不明なら省略する"},
            "store_name": {"type": "string"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string"},
                        "amount": {"type": "integer"},
                        "category_name": {"type": "string", "enum": category_names},
                    },
                    "required": ["item_name", "amount"],
                },
            },
        },
        "required": ["items"],
    }


def extract_receipt(api_key, model, image_bytes, mime_type, category_names):
    """レシート画像をGeminiに送り、構造化されたJSONを取得する。失敗時はExternalServiceErrorに正規化する。"""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=[
                _PROMPT,
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_build_schema(category_names),
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        raise ExternalServiceError("レシートの読み取りに失敗しました。") from e
