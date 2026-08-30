import json
import re

from google import genai
from google.genai import types

from .errors import ExternalServiceError

_PROMPT = "このレシート画像から購入日・店名・品目ごとの名称・金額・最も近いカテゴリーを抽出して。"

_REVIEW_PREFIX_RE = re.compile(r"^Review of ")
_MAPS_SUFFIX_RE = re.compile(r" - Google Maps$")


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


def suggest_places(api_key, model, query, lat, lng):
    """クエリ文字列と現在地からGoogle Maps Groundingで店舗/場所の候補を取得する。

    Groundingツールはresponse_schema（構造化JSON出力）と併用できないため、
    本文は使わずgrounding_metadata.grounding_chunksから候補を抽出する。
    """
    retrieval_config = None
    if lat is not None and lng is not None:
        retrieval_config = types.RetrievalConfig(lat_lng=types.LatLng(latitude=lat, longitude=lng))

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=f"「{query}」に近い名前の店舗・場所を教えて。",
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_maps=types.GoogleMaps())],
                tool_config=(
                    types.ToolConfig(retrieval_config=retrieval_config)
                    if retrieval_config
                    else None
                ),
            ),
        )
        chunks = response.candidates[0].grounding_metadata.grounding_chunks or []
    except Exception as e:
        raise ExternalServiceError("候補の取得に失敗しました。") from e

    seen_ids = set()
    results = []
    for chunk in chunks:
        maps = getattr(chunk, "maps", None)
        if not maps or not maps.title:
            continue
        if maps.place_id in seen_ids:
            continue
        seen_ids.add(maps.place_id)
        title = _REVIEW_PREFIX_RE.sub("", maps.title)
        title = _MAPS_SUFFIX_RE.sub("", title)
        results.append(title)
    return results


def _build_chat_schema(category_names, payment_method_names):
    return {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["complete", "need_more_info"]},
            "question": {"type": "string"},
            "date": {"type": "string", "description": "YYYY-MM-DD形式"},
            "description": {"type": "string"},
            "amount": {"type": "integer"},
            "type": {"type": "string", "enum": ["income", "expense"]},
            "category_name": {"type": "string", "enum": category_names},
            "payment_method_name": {"type": "string", "enum": payment_method_names},
        },
        "required": ["status"],
    }


def _chat_system_prompt(today):
    return (
        "あなたは家計簿アプリの入力アシスタント。ユーザーの発言から取引情報"
        "（日付・内容・金額・種別・カテゴリー・決済手段）を抽出する。"
        "amountとdescriptionは必須。どちらかでも確信を持って確定できなければ"
        "status=need_more_infoとし、questionに一問だけ聞く。"
        "十分な情報があればstatus=completeとし、可能な項目を埋める"
        "（category_name・payment_method_nameは分からなければ省略してよい）。"
        f"今日の日付: {today}"
    )


def parse_transaction_chat(api_key, model, messages, category_names, payment_method_names, today):
    """チャットのやり取り（messages）から取引情報を抽出する。情報不足ならquestionを返す。"""
    contents = [types.Content(role=m["role"], parts=[types.Part(text=m["text"])]) for m in messages]
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=_chat_system_prompt(today),
                response_mime_type="application/json",
                response_schema=_build_chat_schema(category_names, payment_method_names),
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        raise ExternalServiceError("解析に失敗しました。") from e
