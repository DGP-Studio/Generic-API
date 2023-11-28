from fastapi import APIRouter, Request

router = APIRouter(tags=["category:network"])


@router.get("/cn/ip")
def get_client_ip_cn(request: Request):
    return {
        "ip": request.client.host,
        "division": "CN"
    }


@router.get("/global/ip")
def get_client_ip_global(request: Request):
    return {
        "ip": request.client.host,
        "division": "GLOBAL"
    }
