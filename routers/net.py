from fastapi import APIRouter, Request, HTTPException

china_router = APIRouter(tags=["Network"])
global_router = APIRouter(tags=["Network"])


@china_router.get("/ip")
def get_client_ip_cn(request: Request):
    """
    Get the client's IP address and division. In this endpoint, the division is always "China".

    :param request: Request object from FastAPI, used to identify the client's IP address

    :return: Standard response with the client's IP address and division
    """
    return {
        "retcode": 0,
        "message": "success",
        "data": {
            "ip": request.client.host,
            "division": "China"
        }
    }


@global_router.get("/ip")
def get_client_ip_global(request: Request):
    """
    Get the client's IP address and division. In this endpoint, the division is always "Oversea".

    :param request: Request object from FastAPI, used to identify the client's IP address

    :return: Standard response with the client's IP address and division
    """
    return {
        "retcode": 0,
        "message": "success",
        "data": {
            "ip": request.client.host,
            "division": "Oversea"
        }
    }
