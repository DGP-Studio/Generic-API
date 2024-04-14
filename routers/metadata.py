import os
import json
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from utils.dgp_utils import validate_client_is_updated
from utils.redis_utils import redis_conn
from mysql_app.schemas import StandardResponse

scan_duration = int(os.getenv("CENSOR_FILE_SCAN_DURATION", 30)) / 2  # half of the duration

china_router = APIRouter(tags=["Hutao Metadata"], dependencies=[Depends(validate_client_is_updated)],
                         prefix="/metadata")
global_router = APIRouter(tags=["Hutao Metadata"], dependencies=[Depends(validate_client_is_updated)],
                          prefix="/metadata")


def get_banned_files() -> list[str]:
    """
    Get the list of censored files.

    :return: a list of censored files
    """
    if redis_conn:
        metadata_censored_files = redis_conn.get("metadata_censored_files")
        if metadata_censored_files:
            return json.loads(metadata_censored_files)
    return []


@china_router.get("/ban", response_model=StandardResponse)
@global_router.get("/ban", response_model=StandardResponse)
async def get_ban_files_endpoint() -> StandardResponse:
    """
    Get the list of censored files. [FastAPI Endpoint]

    :return: a list of censored files in StandardResponse format
    """
    return StandardResponse(data={"ban": get_banned_files()})


@china_router.get("/{file_path:path}")
async def china_metadata_request_handler(file_path: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    host_for_normal_files = f"https://jihulab.com/DGP-Studio/Snap.Metadata/-/raw/main/{file_path}"
    host_for_censored_files = f"https://metadata.snapgenshin.com/{file_path}"

    if file_path in get_banned_files():
        return RedirectResponse(host_for_censored_files, status_code=302)
    else:
        return RedirectResponse(host_for_normal_files, status_code=302)


@global_router.get("/{file_path:path}")
async def global_metadata_request_handler(file_path: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    host_for_normal_files = f"https://hutao-metadata-pages.snapgenshin.cn/{file_path}"

    return RedirectResponse(host_for_normal_files, status_code=302)
