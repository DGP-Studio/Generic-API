from fastapi import APIRouter, Request, HTTPException
from mysql_app.schemas import StandardResponse

china_router = APIRouter(tags=["Network"])
global_router = APIRouter(tags=["Network"])
fujian_router = APIRouter(tags=["Network"])


@china_router.get("/ip", response_model=StandardResponse)
@global_router.get("/ip", response_model=StandardResponse)
@fujian_router.get("/ip", response_model=StandardResponse)
def get_client_ip_geo(request: Request) -> StandardResponse:
    """
    Get the client's IP address and division.

    :param request: Request object from FastAPI, used to identify the client's IP address

    :return: Standard response with the client's IP address and division
    """
    req_path = request.url.path
    if req_path.startswith("/cn"):
        division = "China"
    elif req_path.startswith("/global"):
        division = "Oversea"
    elif req_path.startswith("/fj"):
        division = "Fujian - China"
    else:
        raise HTTPException(status_code=400, detail="Invalid router")

    return StandardResponse(
        retcode=0,
        message="success",
        data={
            "ip": request.client.host,
            "division": division
        }
    )

@china_router.get("/ips")
@global_router.get("/ips")
@fujian_router.get("/ips")
def return_ip_addr(request: Request):
    """
    Get the client's IP address.

    :param request: Request object from FastAPI, used to identify the client's IP address

    :return: Raw IP address
    """
    return request.client.host.replace('"', '')
