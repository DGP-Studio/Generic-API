import httpx
import json
from redis import asyncio as redis


def refresh_uigf_dict(redis_client: redis.client.Redis) -> dict:
    url = "https://api.uigf.org/dict/genshin/all.json"
    response = httpx.get(url)
    if response.status_code == 200:
        redis_client.set("uigf_dict", response.text, ex=60 * 60 * 3)
        return response.json()
    raise RuntimeError(
        f"Failed to refresh UIGF dict, \nstatus code: {response.status_code}, \ncontent: {response.text}")


def get_genshin_avatar_id(redis_client: redis.client.Redis, name: str, lang: str) -> int | None:
    # load from redis
    try:
        uigf_dict = json.loads(redis_client.get("uigf_dict")) if redis_client else None
    except TypeError:
        # redis_conn.get() returns None
        uigf_dict = refresh_uigf_dict(redis_client)
    avatar_id = uigf_dict.get(lang, {}).get(name, None)
    return avatar_id
