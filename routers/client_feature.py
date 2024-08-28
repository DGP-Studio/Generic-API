from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from utils.dgp_utils import validate_client_is_updated

china_router = APIRouter(tags=["Client Feature"], prefix="/client")
global_router = APIRouter(tags=["Client Feature"], prefix="/client")


@china_router.get("/{file_path:path}")
async def china_client_feature_request_handler(file_path: str) -> RedirectResponse:
    """
    Handle requests to client feature metadata files.

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    host_for_normal_files = f"https://client-feature.snapgenshin.com/{file_path}"

    return RedirectResponse(host_for_normal_files, status_code=302)


@global_router.get("/{file_path:path}")
async def global_client_feature_request_handler(file_path: str) -> RedirectResponse:
    """
    Handle requests to client feature metadata files.

    :param file_path: Path to the metadata file

    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    host_for_normal_files = f"https://hutao-client-pages.snapgenshin.cn/{file_path}"

    return RedirectResponse(host_for_normal_files, status_code=302)
