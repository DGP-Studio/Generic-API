from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from utils.dgp_utils import validate_client_is_updated

china_router = APIRouter(tags=["Enka Network"], prefix="/enka")
global_router = APIRouter(tags=["Enka Network"], prefix="/enka")


@china_router.get("/{uid}", dependencies=[Depends(validate_client_is_updated)])
async def cn_get_enka_raw_data(uid: str) -> RedirectResponse:
    """
    Handle requests to Enka-API detail data with Hutao proxy.

    :param uid: User's in-game UID

    :return: HTTP 302 redirect to Enka-API (Hutao Endpoint)
    """
    china_endpoint = f"https://enka-api.hut.ao/{uid}"

    return RedirectResponse(china_endpoint, status_code=302)


@global_router.get("/{uid}", dependencies=[Depends(validate_client_is_updated)])
async def global_get_enka_raw_data(uid: str) -> RedirectResponse:
    """
    Handle requests to Enka-API detail data.

    :param uid: User's in-game UID

    :return: HTTP 302 redirect to Enka-API (Origin Endpoint)
    """
    china_endpoint = f"https://enka.network/api/uid/{uid}/"

    return RedirectResponse(china_endpoint, status_code=302)


@china_router.get("/{uid}/info", dependencies=[Depends(validate_client_is_updated)])
async def cn_get_enka_info_data(uid: str) -> RedirectResponse:
    """
    Handle requests to Enka-API info data with Hutao proxy.

    :param uid: User's in-game UID

    :return: HTTP 302 redirect to Enka-API (Hutao Endpoint)
    """
    china_endpoint = f"https://enka-api.hut.ao/{uid}/info"

    return RedirectResponse(china_endpoint, status_code=302)


@global_router.get("/{uid}/info", dependencies=[Depends(validate_client_is_updated)])
async def global_get_enka_info_data(uid: str) -> RedirectResponse:
    """
    Handle requests to Enka-API info data.

    :param uid: User's in-game UID

    :return: HTTP 302 redirect to Enka-API (Origin Endpoint)
    """
    china_endpoint = f"https://enka.network/api/uid/{uid}?info"

    return RedirectResponse(china_endpoint, status_code=302)