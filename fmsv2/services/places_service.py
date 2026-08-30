from ..security import api_rate_limit
from . import gemini_client
from .errors import ExternalServiceError, ValidationError

MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 100
RATE_LIMIT_ENDPOINT = "place_suggest"


def _valid_coord(value, low, high):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if low <= f <= high else None


def suggest(db, user_id, query, lat, lng, api_key, model, daily_limit):
    if not api_key:
        raise ExternalServiceError("候補提案機能は現在利用できません。")

    query = (query or "").strip()
    if len(query) < MIN_QUERY_LENGTH:
        return []
    query = query[:MAX_QUERY_LENGTH]

    if not api_rate_limit.is_allowed(db, user_id, RATE_LIMIT_ENDPOINT, daily_limit):
        raise ValidationError("本日の候補提案の利用回数の上限に達しました。", 429)

    lat = _valid_coord(lat, -90, 90)
    lng = _valid_coord(lng, -180, 180)

    api_rate_limit.record_attempt(db, user_id, RATE_LIMIT_ENDPOINT)
    return gemini_client.suggest_places(api_key, model, query, lat, lng)
