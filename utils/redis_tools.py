from redis import asyncio as redis
from base_logger import logger


INITIALIZED_REDIS_DATA = {
    "url:china:client-feature": "https://static-next.snapgenshin.com/d/meta/client-feature/{file_path}",
    "url:global:client-feature": "https://hutao-client-pages.snapgenshin.cn/{file_path}",
    "url:fujian:client-feature": "https://client-feature.snapgenshin.com/{file_path}",
    "url:china:enka-network:": "https://profile.microgg.cn/api/uid/{uid}",
    "url:global:enka-network": "https://enka.network/api/uid/{uid}/",
    "url:china:enka-network-info": "https://profile.microgg.cn/api/uid/{uid}?info",
    "url:global:enka-network-info": "https://enka.network/api/uid/{uid}?info",
    "url:china:metadata": "https://static-next.snapgenshin.com/d/meta/metadata/{file_path}",
    "url:global:metadata": "https://hutao-metadata-pages.snapgenshin.cn/{file_path}",
    "url:fujian:metadata": "https://metadata.snapgenshin.com/{file_path}",
    "url:china:static:zip": "https://open-7419b310-fc97-4a0c-bedf-b8faca13eb7e-s3.saturn.xxyy.co:8443/hutao/{file_path}",
    "url:global:static:zip": "https://static-zip.snapgenshin.cn/{file_path}",
    "url:fujian:static:zip": "https://static.snapgenshin.com/{file_path}",
    "url:china:static:raw": "https://open-7419b310-fc97-4a0c-bedf-b8faca13eb7e-s3.saturn.xxyy.co:8443/hutao/{file_path}",
    "url:global:static:raw": "https://static.snapgenshin.cn/{file_path}",
    "url:fujian:static:raw": "https://static.snapgenshin.com/{file_path}",
    "url:global:static:tiny": "https://static-tiny.snapgenshin.cn/{file_type}/{file_path}",
}


async def init_redis_data(r: redis.Redis):
    logger.info("initializing redis data")
    for key, value in INITIALIZED_REDIS_DATA.items():
        current_value = await r.get(key)
        if current_value is not None:
            continue
        await r.set(key, value)
        logger.info(f"set {key} to {value}")
    logger.info("redis data initialized")
