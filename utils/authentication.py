from fastapi import HTTPException, Header
from typing import Annotated
from config import API_TOKEN, HOMA_SERVER_IP
from base_logger import get_logger
from mysql_app.homa_schemas import HomaPassport
import httpx

logger = get_logger(__name__)


def verify_api_token(api_token: Annotated[str, Header()]) -> bool:
    if api_token == API_TOKEN:
        logger.info("API token is valid.")
        return True
    else:
        logger.error(f"API token is invalid: {api_token}")
        raise HTTPException(status_code=403, detail="API token is invalid.")


def verify_homa_user_level(homa_token: Annotated[str, Header()]) -> HomaPassport:
    if HOMA_SERVER_IP is None:
        logger.error("Homa server IP is not set.")
        raise HTTPException(status_code=500, detail="Homa server IP is not set.")
    if homa_token is None:
        return HomaPassport(user_name="Anonymous", is_developer=False, is_maintainer=False, sponsor_expire_date=None)
    url = f"http://{HOMA_SERVER_IP}/Passport/UserInfo"
    headers = {
        "Authorization": f"Bearer {homa_token}",
        "User-Agent": "Hutao Generic API"
    }
    response = httpx.get(url, headers=headers)
    if response.status_code == 200:
        response = response.json()
        return HomaPassport(
            user_name=response["UserName"],
            is_developer=response["IsLicensedDeveloper"],
            is_maintainer=response["IsMaintainer"],
            sponsor_expire_date=response["GachaLogExpireAt"]
        )
