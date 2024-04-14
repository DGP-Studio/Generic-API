import httpx
import redis
import os
import json
from base_logger import logger

if os.getenv("NO_REDIS", "false").lower() == "true":
    logger.info("Skipping Redis connection in UIGF module as NO_REDIS is set to true")
    redis_conn = None
else:
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    logger.info(f"Connecting to Redis at {REDIS_HOST} for patch module")
    redis_conn = redis.Redis(host=REDIS_HOST, port=6379, db=1, decode_responses=True)
    logger.info("Redis connection established for UIGF module")


def refresh_uigf_dict() -> dict:
    url = "https://api.uigf.org/dict/genshin/all.json"
    response = httpx.get(url)
    if response.status_code == 200:
        redis_conn.set("uigf_dict", response.text, ex=60 * 60 * 3)
        return response.json()
    raise RuntimeError(
        f"Failed to refresh UIGF dict, \nstatus code: {response.status_code}, \ncontent: {response.text}")


def get_genshin_avatar_id(name: str, lang: str) -> int | None:
    # load from redis
    try:
        uigf_dict = json.loads(redis_conn.get("uigf_dict")) if redis_conn else None
    except TypeError:
        # redis_conn.get() returns None
        uigf_dict = refresh_uigf_dict()
    avatar_id = uigf_dict.get(lang, {}).get(name, None)
    return avatar_id
