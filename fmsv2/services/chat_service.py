from datetime import datetime

from ..security import api_rate_limit
from . import gemini_client
from .errors import ExternalServiceError, ValidationError

MAX_TURNS = 6
MAX_MESSAGE_LENGTH = 300
RATE_LIMIT_ENDPOINT = "chat"
VALID_ROLES = {"user", "model"}


def _validate_messages(messages):
    if not isinstance(messages, list) or not messages:
        raise ValidationError("messagesは必須です。")
    if len(messages) > MAX_TURNS * 2:
        raise ValidationError("やり取りが長くなりすぎました。フォームに直接入力してください。")
    cleaned = []
    for m in messages:
        if not isinstance(m, dict):
            raise ValidationError("messagesの形式が不正です。")
        role = m.get("role")
        text = str(m.get("text", "")).strip()
        if role not in VALID_ROLES or not text:
            raise ValidationError("messagesの形式が不正です。")
        cleaned.append({"role": role, "text": text[:MAX_MESSAGE_LENGTH]})
    return cleaned


def parse(db, user_id, messages, api_key, model, daily_limit):
    if not api_key:
        raise ExternalServiceError("チャット入力機能は現在利用できません。")
    messages = _validate_messages(messages)

    if not api_rate_limit.is_allowed(db, user_id, RATE_LIMIT_ENDPOINT, daily_limit):
        raise ValidationError("本日のチャット入力の利用回数の上限に達しました。", 429)

    categories = db.execute("SELECT id, name FROM categories ORDER BY id").fetchall()
    payment_methods = db.execute("SELECT id, name FROM payment_methods ORDER BY id").fetchall()
    cat_name_to_id = {row["name"]: row["id"] for row in categories}
    pay_name_to_id = {row["name"]: row["id"] for row in payment_methods}

    api_rate_limit.record_attempt(db, user_id, RATE_LIMIT_ENDPOINT)
    today = datetime.now().strftime("%Y-%m-%d")
    result = gemini_client.parse_transaction_chat(
        api_key, model, messages, list(cat_name_to_id.keys()), list(pay_name_to_id.keys()), today
    )

    if result.get("status") == "need_more_info":
        question = result.get("question") or "もう少し詳しく教えてください。"
        return {"status": "need_more_info", "question": question}

    return {
        "status": "complete",
        "date": result.get("date"),
        "description": result.get("description"),
        "amount": result.get("amount"),
        "type": result.get("type"),
        "category_id": cat_name_to_id.get(result.get("category_name")),
        "payment_method_id": pay_name_to_id.get(result.get("payment_method_name")),
    }
