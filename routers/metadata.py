import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from utils.dgp_utils import validate_client_is_updated
from mysql_app.schemas import StandardResponse
from redis import asyncio as redis

china_router = APIRouter(tags=["Hutao Metadata"], prefix="/metadata")
global_router = APIRouter(tags=["Hutao Metadata"], prefix="/metadata")
fujian_router = APIRouter(tags=["Hutao Metadata"], prefix="/metadata")


@china_router.get("/{file_path:path}", dependencies=[Depends(validate_client_is_updated)])
async def china_metadata_request_handler(file_path: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    cn_metadata_url = f"https://static-next.snapgenshin.com/d/meta/metadata/{file_path}"

    return RedirectResponse(cn_metadata_url, status_code=302)


@global_router.get("/{file_path:path}", dependencies=[Depends(validate_client_is_updated)])
async def global_metadata_request_handler(file_path: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    global_metadata_url = f"https://hutao-metadata-pages.snapgenshin.cn/{file_path}"

    return RedirectResponse(global_metadata_url, status_code=302)


@fujian_router.get("/{file_path:path}", dependencies=[Depends(validate_client_is_updated)])
async def fujian_metadata_request_handler(file_path: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    fujian_metadata_url = f"https://metadata.snapgenshin.com/{file_path}"

    return RedirectResponse(fujian_metadata_url, status_code=302)