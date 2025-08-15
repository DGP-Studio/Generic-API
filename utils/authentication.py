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
