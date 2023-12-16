from fastapi import APIRouter, Request, HTTPException

router = APIRouter(tags=["category:network"])


@router.get("/cn/ip")
def get_client_ip_cn(request: Request):
    return {
        "retcode": 0,
        "message": "success",
        "data": {
            "ip": request.client.host,
            "division": "China"
        }
    }


@router.get("/global/ip")
def get_client_ip_global(request: Request):
    return {
        "retcode": 0,
        "message": "success",
        "data": {
            "ip": request.client.host,
            "division": "Oversea"
        }
    }