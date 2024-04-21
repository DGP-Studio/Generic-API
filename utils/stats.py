import os
import redis
from fastapi import Header
from typing import Optional
from base_logger import logger

if os.getenv("NO_REDIS", "false").lower() == "true":
    logger.info("Skipping Redis connection in Stats module as NO_REDIS is set to true")
    redis_conn = None
else:
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    logger.info(f"Connecting to Redis at {REDIS_HOST} for Stats module")
    redis_conn = redis.Redis(host=REDIS_HOST, port=6379, db=2, decode_responses=True)
    logger.info("Redis connection established for Stats module (db=2)")


def record_device_id(x_device_id: Optional[str] = Header(None), x_region: Optional[str] = Header(None)):
    if x_device_id and redis_conn:
        match x_region.lower():
            case "cn":
                redis_key_name = "active_users_cn"
            case "global":
                redis_key_name = "active_users_global"
            case _:
                redis_key_name = "active_users_unknown"
        if not redis_conn.sismember(redis_key_name, x_device_id):
            redis_conn.sadd(redis_key_name, x_device_id)
        return True
    return False
