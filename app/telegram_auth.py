import hashlib, hmac, json
from urllib.parse import parse_qsl
from .config import settings
def validate_init_data(init_data: str) -> dict:
    if not init_data: raise ValueError("Открой Mini App через Telegram")
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", None)
    if not received_hash: raise ValueError("Нет подписи Telegram")
    data_check = "\n".join(f"{k}={v}" for k,v in sorted(values.items()))
    secret = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash): raise ValueError("Неверная подпись Telegram")
    try:
        user=json.loads(values["user"])
        return {"id":int(user["id"]),"username":user.get("username")}
    except (KeyError,ValueError,TypeError,json.JSONDecodeError):
        raise ValueError("Не удалось прочитать пользователя Telegram")
