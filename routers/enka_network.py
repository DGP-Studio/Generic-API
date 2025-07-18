from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from redis import asyncio as aioredis
from cloudflare_security_utils.safety import validate_client_is_updated


china_router = APIRouter(tags=["Enka Network"], prefix="/enka")
global_router = APIRouter(tags=["Enka Network"], prefix="/enka")
fujian_router = APIRouter(tags=["Enka Network"], prefix="/enka")


@china_router.get("/{uid}", dependencies=[Depends(validate_client_is_updated)])
@fujian_router.get("/{uid}", dependencies=[Depends(validate_client_is_updated)])
async def cn_get_enka_raw_data(request: Request, uid: str) -> RedirectResponse:
    """
    Handle requests to Enka-API detail data

    :param request: Request object

    :param uid: User's in-game UID

    :return: HTTP 301 redirect to Enka-API
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    endpoint = await redis_client.get("url:china:enka-network")
    endpoint = endpoint.decode("utf-8").format(uid=uid)

    return RedirectResponse(endpoint, status_code=301)


@global_router.get("/{uid}", dependencies=[Depends(validate_client_is_updated)])
async def global_get_enka_raw_data(request: Request, uid: str) -> RedirectResponse:
    """
    Handle requests to Enka-API detail data.

    :param request: Request object

    :param uid: User's in-game UID

    :return: HTTP 301 redirect to Enka-API (Origin Endpoint)
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    endpoint = await redis_client.get("url:global:enka-network")
    endpoint = endpoint.decode("utf-8").format(uid=uid)

    return RedirectResponse(endpoint, status_code=301)


@china_router.get("/{uid}/info", dependencies=[Depends(validate_client_is_updated)])
@fujian_router.get("/{uid}/info", dependencies=[Depends(validate_client_is_updated)])
async def cn_get_enka_info_data(request: Request, uid: str) -> RedirectResponse:
    """
    Handle requests to Enka-API info data.

    :param request: Request object

    :param uid: User's in-game UID

    :return: HTTP 301 redirect to Enka-API
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    endpoint = await redis_client.get("url:china:enka-network-info")
    endpoint = endpoint.decode("utf-8").format(uid=uid)

    return RedirectResponse(endpoint, status_code=301)


@global_router.get("/{uid}/info", dependencies=[Depends(validate_client_is_updated)])
async def global_get_enka_info_data(request: Request, uid: str) -> RedirectResponse:
    """
    Handle requests to Enka-API info data.

    :param request: Request object

    :param uid: User's in-game UID

    :return: HTTP 301 redirect to Enka-API (Origin Endpoint)
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    endpoint = await redis_client.get("url:global:enka-network-info")
    endpoint = endpoint.decode("utf-8").format(uid=uid)

    return RedirectResponse(endpoint, status_code=301)
