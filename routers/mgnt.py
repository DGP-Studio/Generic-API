import os
from fastapi import APIRouter, Request, HTTPException, Depends
from starlette.responses import StreamingResponse
from utils.redis_tools import INITIALIZED_REDIS_DATA
from mysql_app.schemas import StandardResponse
from redis import asyncio as aioredis
from pydantic import BaseModel
from utils.authentication import verify_api_token


router = APIRouter(tags=["Management"], prefix="/mgnt", dependencies=[Depends(verify_api_token)])


class UpdateRedirectRules(BaseModel):
    """
    Pydantic model for updating the redirect rules.
    """
    rule_name: str
    rule_template: str


@router.get("/redirect-rules", response_model=StandardResponse)
async def get_redirect_rules(request: Request) -> StandardResponse:
    """
    Get the redirect rules for the management page.

    :param request: Request object from FastAPI, used to identify the client's IP address

    :return: Standard response with the redirect rules
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    current_dict = INITIALIZED_REDIS_DATA.copy()
    for key in INITIALIZED_REDIS_DATA:
        current_dict[key] = await redis_client.get(key)
    return StandardResponse(
        retcode=0,
        message="success",
        data=current_dict
    )


@router.post("/redirect-rules", response_model=StandardResponse)
async def update_redirect_rules(request: Request, update_data: UpdateRedirectRules) -> StandardResponse:
    """
    Update the redirect rules for the management page.

    :param request: Request object from FastAPI, used to identify the client's IP address
    :param update_data: Pydantic model for updating the redirect rules

    :return: Standard response with the redirect rules
    """
    redis_client = aioredis.Redis.from_pool(request.app.state.redis)
    if update_data.rule_name not in INITIALIZED_REDIS_DATA:
        raise HTTPException(status_code=400, detail="Invalid rule name")

    await redis_client.set(update_data.rule_name, update_data.rule_template)
    return StandardResponse(
        retcode=0,
        message="success",
        data={
            update_data.rule_name: update_data.rule_template
        }
    )


@router.get("/log", response_model=StandardResponse)
async def list_current_logs() -> StandardResponse:
    """
    List the current logs of the API

    :return: Standard response with the current logs
    """
    log_files = os.listdir("log")
    return StandardResponse(
        retcode=0,
        message="success",
        data=log_files
    )

@router.get("/log/{log_file}")
async def download_log_file(log_file: str) -> StreamingResponse:
    """
    Download the log file specified by the user

    :param log_file: Name of the log file to download

    :return: Streaming response with the log file
    """
    return StreamingResponse(open(f"log/{log_file}", "rb"), media_type="text/plain")
