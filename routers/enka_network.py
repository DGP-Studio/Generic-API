from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from utils.dgp_utils import validate_client_is_updated

router = APIRouter(tags=["category:enka"])


@router.get("/cn/enka/{uid}", dependencies=[Depends(validate_client_is_updated)], tags=["region:cn"])
async def cn_get_enka_raw_data(uid: str):
    """
    Handle requests to metadata files.
    :param uid: User's in-game UID
    :return: HTTP 302 redirect to Enka-API (Hutao Endpoint)
    """
    china_endpoint = f"https://enka-api.hut.ao/{uid}"

    return RedirectResponse(china_endpoint, status_code=302)


@router.get("/global/enka/{uid}", dependencies=[Depends(validate_client_is_updated)], tags=["region:global"])
async def global_get_enka_raw_data(uid: str):
    """
    Handle requests to metadata files.
    :param uid: User's in-game UID
    :return: HTTP 302 redirect to Enka-API (Origin Endpoint)
    """
    china_endpoint = f"https://enka.network/api/uid/{uid}/"

    return RedirectResponse(china_endpoint, status_code=302)
