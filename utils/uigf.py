import httpx
import json
from utils.redis_utils import redis_conn


def refresh_uigf_dict() -> dict:
    url = "https://api.uigf.org/dict/genshin/all.json"
    response = httpx.get(url)
    if response.status_code == 200:
        if redis_conn:
            redis_conn.set("uigf_dict", response.text, ex=60 * 60 * 3)
            return response.json()
    raise RuntimeError(
        f"Failed to refresh UIGF dict, \nstatus code: {response.status_code}, \ncontent: {response.text}")


def get_genshin_avatar_id(name: str, lang: str) -> int | None:
    # load from redis
    try:
        if redis_conn:
            uigf_dict = json.loads(redis_conn.get("uigf_dict")) if redis_conn else None
        else:
            raise RuntimeError("Redis connection not available, failed to get Genshin avatar id in UIGF module")
    except TypeError:
        # redis_conn.get() returns None
        uigf_dict = refresh_uigf_dict()
    avatar_id = uigf_dict.get(lang, {}).get(name, None)
    return avatar_id
