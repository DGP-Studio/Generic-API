import os
import redis
from base_logger import logger

if os.getenv("NO_REDIS", "false").lower() == "true":
    logger.info("Skipping Redis connection in Redis_utils module as NO_REDIS is set to true")
    redis_conn = None
else:
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    logger.info(f"Connecting to Redis at {REDIS_HOST} for Redis_utils module")
    redis_conn = redis.Redis(host=REDIS_HOST, port=6379, db=1, decode_responses=True)
    logger.info("Redis connection established for Redis_utils module")


"""
Redis data map

# Static Module

- static_files_size
    - dict of static files size
    - 3 hours expiration

# Strategy Module

- avatar_strategy
    - dict of avatar strategy

# Wallpapers Module

- bing_wallpaper_global
- bing_wallpaper_cn
- bing_wallpaper_global
- hutao_today_wallpaper
    - dict of Wallpaper object
    - 24 hours expiration

# Metadata Module

- metadata_censored_files
    - Shared with jihu_utils container
    
# Patch Module

- overwritten_china_url
- snap_hutao_latest_version
- snap_hutao_deployment_latest_version

# dgp-utils Module

- allowed_user_agents
    - list of allowed user agents
    - 5 minutes expiration
"""