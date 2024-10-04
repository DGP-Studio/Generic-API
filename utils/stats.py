import time
from fastapi import Header, Request
from redis import asyncio as aioredis
from typing import Optional
from base_logger import logger


async def record_device_id(request: Request, x_region: Optional[str] = Header(None),
                           x_hutao_device_id: Optional[str] = Header(None),
                           user_agent: Optional[str] = Header(None)) -> bool:
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    start_time = time.time()

    if not x_hutao_device_id:
        logger.info(f"Device ID not found in headers, not recording device ID")
        return False

    redis_key_name = {
        "cn": "stat:active_users:cn",
        "global": "stat:active_users:global"
    }.get((x_region or "").lower(), "stat:active_users:unknown")

    await redis_client.sadd(redis_key_name, x_hutao_device_id)

    if user_agent:
        user_agent = user_agent.replace("Snap Hutao/", "")
        user_agent = f"stat:user_agent:{user_agent}"
        await redis_client.sadd(user_agent, x_hutao_device_id)

        end_time = time.time()
        execution_time = (end_time - start_time) * 1000
        print(f"Execution time[1]: {execution_time} ms")
        return True

    end_time = time.time()
    execution_time = (end_time - start_time) * 1000
    print(f"Execution time[2]: {execution_time} ms")

    return False


def record_email_requested(request: Request) -> bool:
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    redis_client.incr("stat:email_requested")
    return True


def add_email_sent_count(request: Request) -> bool:
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    redis_client.incr("stat:email_sent")
    return True


def add_email_failed_count(request: Request) -> bool:
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    redis_client.incr("stat:email_failed")
    return True
