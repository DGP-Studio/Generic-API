from redis import asyncio as redis

INITIALIZED_REDIS_DATA = {
    "china:client-feature": "https://static-next.snapgenshin.com/d/meta/client-feature/{file_path}",
    "global:client-feature": "https://hutao-client-pages.snapgenshin.cn/{file_path}",
    "fujian:client-feature": "https://client-feature.snapgenshin.com/{file_path}",
    "china:enka-network:": "https://profile.microgg.cn/api/uid/{uid}",
    "global:enka-network": "https://enka.network/api/uid/{uid}/",
    "china:enka-network-info": "https://profile.microgg.cn/api/uid/{uid}?info",
    "global:enka-network-info": "https://enka.network/api/uid/{uid}?info",
    "china:metadata": "https://static-next.snapgenshin.com/d/meta/metadata/{file_path}",
    "global:metadata": "https://hutao-metadata-pages.snapgenshin.cn/{file_path}",
    "fujian:metadata": "https://metadata.snapgenshin.com/{file_path}",
    "china:static:zip": "https://open-7419b310-fc97-4a0c-bedf-b8faca13eb7e-s3.saturn.xxyy.co:8443/hutao/{file_path}",
    "global:static:zip": "https://static-zip.snapgenshin.cn/{file_path}",
    "fujian:static:zip": "https://static.snapgenshin.com/{file_path}",
    "china:static:raw": "https://open-7419b310-fc97-4a0c-bedf-b8faca13eb7e-s3.saturn.xxyy.co:8443/hutao/{file_path}",
    "global:static:raw": "https://static.snapgenshin.cn/{file_path}",
    "fujian:static:raw": "https://static.snapgenshin.com/{file_path}",
    "global:static:tiny": "https://static-tiny.snapgenshin.cn/{file_type}/{file_path}",
}


async def init_redis_data(r: redis.Redis):
    for key, value in INITIALIZED_REDIS_DATA.items():
        if r.exists(key):
            continue
        await r.set(key, value)
