from redis import asyncio as redis
from base_logger import get_logger


logger = get_logger(__name__)
REINITIALIZED_REDIS_DATA = {
    # 1.14.5
    "url:china:static:zip": None,
    "url:global:static:zip": None,
    "url:fujian:static:zip": None,
    "url:china:static:raw": None,
    "url:global:static:raw": None,
    "url:fujian:static:raw": None,
    "url:china:client-feature": "https://cnb.cool/DGP-Studio/Snap.ClientFeature/-/git/raw/main/{file_path}",
    "url:fujian:client-feature": "https://cnb.cool/DGP-Studio/Snap.ClientFeature/-/git/raw/main/{file_path}",
    "url:china:metadata": "https://cnb.cool/DGP-Studio/Snap.Metadata/-/git/raw/main/{file_path}",
    "url:fujian:metadata": "https://cnb.cool/DGP-Studio/Snap.Metadata/-/git/raw/main/{file_path}",
}

INITIALIZED_REDIS_DATA = {
    # Client Feature
    "url:china:client-feature": "https://cnb.cool/DGP-Studio/Snap.ClientFeature/-/git/raw/main/{file_path}",
    "url:fujian:client-feature": "https://cnb.cool/DGP-Studio/Snap.ClientFeature/-/git/raw/main/{file_path}",
    "url:global:client-feature": "https://hutao-client-pages.snapgenshin.cn/{file_path}",
    # Enka Network
    "url:china:enka-network": "https://profile.microgg.cn/api/uid/{uid}",
    "url:global:enka-network": "https://enka.network/api/uid/{uid}/",
    "url:china:enka-network-info": "https://profile.microgg.cn/api/uid/{uid}?info",
    "url:global:enka-network-info": "https://enka.network/api/uid/{uid}?info",
    # Metadata
    "url:china:metadata": "https://cnb.cool/DGP-Studio/Snap.Metadata/-/git/raw/main/{file_path}",
    "url:fujian:metadata": "https://cnb.cool/DGP-Studio/Snap.Metadata/-/git/raw/main/{file_path}",
    "url:global:metadata": "https://hutao-metadata-pages.snapgenshin.cn/{file_path}",
    # Static - Raw - Original Quality
    "url:china:static:raw:original": "https://cnb.cool/DGP-Studio/Snap.Static/-/git/raw/main/{file_path}",
    "url:fujian:static:raw:original": "https://cnb.cool/DGP-Studio/Snap.Static/-/git/raw/main/{file_path}",
    "url:global:static:raw:original": "https://static.snapgenshin.cn/{file_path}",
    # Static - Raw - High Quality
    "url:china:static:raw:tiny": "https://cnb.cool/DGP-Studio/Snap.Static.Tiny/-/git/raw/main/{file_path}",
    "url:fujian:static:raw:tiny": "https://cnb.cool/DGP-Studio/Snap.Static.Tiny/-/git/raw/main/{file_path}",
    "url:global:static:raw:tiny": "https://static-tiny.snapgenshin.cn/{file_path}",
    # Static - Zip - Original Quality
    "url:china:static:zip:original": "https://static-archive.snapgenshin.cn/original/{file_path}",
    "url:fujian:static:zip:original": "https://static-archive.snapgenshin.cn/original/{file_path}",
    "url:global:static:zip:original": "https://static-archive.snapgenshin.cn/original/{file_path}",
    # Static - Zip - High Quality
    "url:china:static:zip:tiny": "https://static-archive.snapgenshin.cn/tiny/{file_path}",
    "url:fujian:static:zip:tiny": "https://static-archive.snapgenshin.cn/tiny/{file_path}",
    "url:global:static:zip:tiny": "https://static-archive.snapgenshin.cn/tiny/{file_path}",
}


async def reinit_redis_data(r: redis.Redis):
    logger.info(f"Reinitializing redis data")
    for key, value in REINITIALIZED_REDIS_DATA.items():
        if value is None:
            await r.delete(key)
            logger.info(f"Removing {key} from Redis")
        else:
            await r.set(key, value)
            logger.info(f"Reinitialized {key} to {value}")
    logger.info("redis data reinitialized")


async def init_redis_data(r: redis.Redis):
    logger.info("initializing redis data")
    for key, value in INITIALIZED_REDIS_DATA.items():
        current_value = await r.get(key)
        if current_value is not None:
            continue
        await r.set(key, value)
        logger.info(f"Initialized {key} to {value}")
    logger.info("redis data initialized")
