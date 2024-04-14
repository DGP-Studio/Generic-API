from fastapi import APIRouter, Request
from mysql_app.schemas import StandardResponse

china_router = APIRouter(tags=["Network"])
global_router = APIRouter(tags=["Network"])


@china_router.get("/ip", response_model=StandardResponse)
def get_client_ip_cn(request: Request) -> StandardResponse:
    """
    Get the client's IP address and division. In this endpoint, the division is always "China".

    :param request: Request object from FastAPI, used to identify the client's IP address

    :return: Standard response with the client's IP address and division
    """
    return StandardResponse(
        retcode=0,
        message="success",
        data={
            "ip": request.client.host,
            "division": "China"
        }
    )


@global_router.get("/ip", response_model=StandardResponse)
def get_client_ip_global(request: Request) -> StandardResponse:
    """
    Get the client's IP address and division. In this endpoint, the division is always "Oversea".

    :param request: Request object from FastAPI, used to identify the client's IP address

    :return: Standard response with the client's IP address and division
    """
    return StandardResponse(
        retcode=0,
        message="success",
        data={
            "ip": request.client.host,
            "division": "Oversea"
        }
    )
