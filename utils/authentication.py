from config import API_TOKEN
from fastapi import HTTPException, Header
from typing import Annotated
from base_logger import logger


def verify_api_token(api_token: Annotated[str, Header()]):
    if api_token == API_TOKEN:
        logger.info("API token is valid.")
        return True
    else:
        logger.error(f"API token is invalid: {api_token}")
        raise HTTPException(status_code=403, detail="API token is invalid.")
