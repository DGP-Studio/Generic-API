from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from redis import asyncio as aioredis
from cloudflare_security_utils.safety import enhanced_safety_check, uid_ban_check_middleware


china_router = APIRouter(tags=["Client Feature"], prefix="/client")
global_router = APIRouter(tags=["Client Feature"], prefix="/client")
fujian_router = APIRouter(tags=["Client Feature"], prefix="/client")


async def _apply_uid_ban_middleware(request: Request):
    """Helper to run uid_ban_check_middleware and raise 403 if banned."""
    async def dummy_call_next(req):
        return req
    await uid_ban_check_middleware(request, dummy_call_next)
    status = getattr(request.state, 'uid_ban_status', {"banned": False})
    if status.get("banned"):
        raise HTTPException(status_code=403, detail={
            "message": f"banned until {status.get('banned_until')}",
            "banned_until": status.get('banned_until')
        })


@china_router.get("/{file_path:path}")
async def china_client_feature_request_handler(
    request: Request,
    file_path: str,
    safety_check: bool | RedirectResponse = Depends(enhanced_safety_check)
) -> RedirectResponse:
    # UID ban middleware first
    await _apply_uid_ban_middleware(request)

    if isinstance(safety_check, RedirectResponse):
        return safety_check

    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    host_for_normal_files = await redis_client.get("url:china:client-feature")
    host_for_normal_files = host_for_normal_files.decode("utf-8").format(file_path=file_path)

    return RedirectResponse(host_for_normal_files, status_code=301)


@global_router.get("/{file_path:path}")
async def global_client_feature_request_handler(
    request: Request,
    file_path: str,
    safety_check: bool | RedirectResponse = Depends(enhanced_safety_check)
) -> RedirectResponse:
    await _apply_uid_ban_middleware(request)

    if isinstance(safety_check, RedirectResponse):
        return safety_check

    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    host_for_normal_files = await redis_client.get("url:global:client-feature")
    host_for_normal_files = host_for_normal_files.decode("utf-8").format(file_path=file_path)

    return RedirectResponse(host_for_normal_files, status_code=301)


@fujian_router.get("/{file_path:path}")
async def fujian_client_feature_request_handler(
    request: Request,
    file_path: str,
    safety_check: bool | RedirectResponse = Depends(enhanced_safety_check)
) -> RedirectResponse:
    await _apply_uid_ban_middleware(request)

    if isinstance(safety_check, RedirectResponse):
        return safety_check

    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    host_for_normal_files = await redis_client.get("url:fujian:client-feature")
    host_for_normal_files = host_for_normal_files.decode("utf-8").format(file_path=file_path)

    return RedirectResponse(host_for_normal_files, status_code=301)
