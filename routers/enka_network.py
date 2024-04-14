from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from utils.dgp_utils import validate_client_is_updated

china_router = APIRouter(tags=["Enka Network"], prefix="/enka")
global_router = APIRouter(tags=["Enka Network"], prefix="/enka")


@china_router.get("/{uid}", dependencies=[Depends(validate_client_is_updated)])
async def cn_get_enka_raw_data(uid: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param uid: User's in-game UID

    :return: HTTP 302 redirect to Enka-API (Hutao Endpoint)
    """
    china_endpoint = f"https://enka-api.hut.ao/{uid}"

    return RedirectResponse(china_endpoint, status_code=302)


@global_router.get("/{uid}", dependencies=[Depends(validate_client_is_updated)])
async def global_get_enka_raw_data(uid: str) -> RedirectResponse:
    """
    Handle requests to metadata files.

    :param uid: User's in-game UID

    :return: HTTP 302 redirect to Enka-API (Origin Endpoint)
    """
    china_endpoint = f"https://enka.network/api/uid/{uid}/"

    return RedirectResponse(china_endpoint, status_code=302)
