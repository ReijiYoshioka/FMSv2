from ..security import receipt_rate_limit
from . import gemini_client
from .errors import ExternalServiceError, ValidationError

MAX_RECEIPT_BYTES = 8 * 1024 * 1024
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def read_receipt(db, user_id, file_storage, api_key, model, daily_limit):
    if not api_key:
        raise ExternalServiceError("レシート読取機能は現在利用できません。")
    if not receipt_rate_limit.is_allowed(db, user_id, daily_limit):
        raise ValidationError("本日のレシート読取回数の上限に達しました。", 429)

    mime_type = file_storage.mimetype
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValidationError("対応していない画像形式です（JPEG/PNG/WEBPのみ）。")
    raw = file_storage.read()
    if len(raw) > MAX_RECEIPT_BYTES:
        raise ValidationError("画像サイズは8MB以内にしてください。")

    categories = db.execute("SELECT id, name FROM categories ORDER BY id").fetchall()
    name_to_id = {row["name"]: row["id"] for row in categories}

    receipt_rate_limit.record_attempt(db, user_id)
    category_names = list(name_to_id.keys())
    extracted = gemini_client.extract_receipt(api_key, model, raw, mime_type, category_names)

    items = extracted.get("items") or []
    if not items:
        raise ValidationError("レシートを読み取れませんでした。画像を確認して再試行してください。")

    result_items = [
        {
            "item_name": item.get("item_name", ""),
            "amount": item.get("amount", 0),
            "category_id": name_to_id.get(item.get("category_name")),
        }
        for item in items
    ]
    return {
        "date": extracted.get("date"),
        "description": extracted.get("store_name"),
        "items": result_items,
    }
