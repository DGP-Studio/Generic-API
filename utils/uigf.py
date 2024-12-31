import httpx
import json
from redis import asyncio as redis


async def refresh_uigf_dict(redis_client: redis.client.Redis) -> dict:
    url = "https://api.uigf.org/dict/genshin/all.json"
    response = httpx.get(url)
    if response.status_code == 200:
        await redis_client.set("uigf:dict:all", response.text, ex=60 * 60 * 3)
        return response.json()
    raise RuntimeError(
        f"Failed to refresh UIGF dict, \nstatus code: {response.status_code}, \ncontent: {response.text}")


async def get_genshin_avatar_id(redis_client: redis.client.Redis, name: str, lang: str) -> int | None:
    # load from redis
    try:
        uigf_dict = await redis_client.get("uigf:dict:all")
        if uigf_dict:
            uigf_dict = json.loads(uigf_dict)
        else:
            uigf_dict = await refresh_uigf_dict(redis_client)
    except Exception as e:
        raise RuntimeError(f"Failed to get UIGF dict: {e}")
    avatar_id = uigf_dict.get(lang, {}).get(name, None)
    return avatar_id
