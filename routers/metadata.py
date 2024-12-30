from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from redis import asyncio as aioredis
from utils.dgp_utils import validate_client_is_updated


china_router = APIRouter(tags=["Hutao Metadata"], prefix="/metadata")
global_router = APIRouter(tags=["Hutao Metadata"], prefix="/metadata")
fujian_router = APIRouter(tags=["Hutao Metadata"], prefix="/metadata")


@china_router.get("/{file_path:path}", dependencies=[Depends(validate_client_is_updated)])
async def china_metadata_request_handler(request: Request, file_path: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param request: Request object

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    china_metadata_endpoint = await redis_client.get("china:metadata")
    china_metadata_endpoint = china_metadata_endpoint.decode("utf-8").format(file_path=file_path)

    return RedirectResponse(china_metadata_endpoint, status_code=302)


@global_router.get("/{file_path:path}", dependencies=[Depends(validate_client_is_updated)])
async def global_metadata_request_handler(request: Request, file_path: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param request: Request object

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    global_metadata_endpoint = await redis_client.get("global:metadata")
    global_metadata_endpoint = global_metadata_endpoint.decode("utf-8").format(file_path=file_path)

    return RedirectResponse(global_metadata_endpoint, status_code=302)


@fujian_router.get("/{file_path:path}", dependencies=[Depends(validate_client_is_updated)])
async def fujian_metadata_request_handler(request: Request, file_path: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param request: Request object

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)

    fujian_metadata_endpoint = await redis_client.get("fujian:metadata")
    fujian_metadata_endpoint = fujian_metadata_endpoint.decode("utf-8").format(file_path=file_path)

    return RedirectResponse(fujian_metadata_endpoint, status_code=302)
