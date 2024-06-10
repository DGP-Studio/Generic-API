import os
import redis
import time
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
    patch_redis_conn = redis.Redis(host=REDIS_HOST, port=6379, db=3, decode_responses=True)
    logger.info("Redis connection established for Stats module (db=2)")


def record_device_id(x_device_id: Optional[str] = Header(None), x_region: Optional[str] = Header(None),
                     x_hutao_device_id: Optional[str] = Header(None), user_agent: Optional[str] = Header(None)) -> bool:
    start_time = time.time()  # 记录开始时间

    if not redis_conn:
        logger.warning("Redis connection not established, not recording device ID")
        return False

    captured_device_id = x_hutao_device_id or x_device_id
    if not captured_device_id:
        logger.info(f"Device ID not found in headers, not recording device ID")
        return False

    redis_key_name = {
        "cn": "active_users_cn",
        "global": "active_users_global"
    }.get((x_region or "").lower(), "active_users_unknown")

    redis_conn.sadd(redis_key_name, captured_device_id)

    if user_agent:
        user_agent = user_agent.replace("Snap Hutao/", "")
        patch_redis_conn.sadd(user_agent, captured_device_id)

        end_time = time.time()  # 记录结束时间
        execution_time = (end_time - start_time) * 1000
        print(f"Execution time[1]: {execution_time} ms")
        return True

    end_time = time.time()  # 记录结束时间
    execution_time = (end_time - start_time) * 1000
    print(f"Execution time[2]: {execution_time} ms")

    return False
