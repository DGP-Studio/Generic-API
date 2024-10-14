from inspect import trace

from config import env_result
import uvicorn
import os
import uuid
import json
from redis import asyncio as redis
from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from apitally.fastapi import ApitallyMiddleware
from datetime import datetime
from contextlib import asynccontextmanager
from routers import enka_network, metadata, patch_next, static, net, wallpaper, strategy, crowdin, system_email, \
    client_feature
from starlette.middleware.base import BaseHTTPMiddleware
from base_logger import logger
from config import (MAIN_SERVER_DESCRIPTION, TOS_URL, CONTACT_INFO, LICENSE_INFO, VALID_PROJECT_KEYS, IMAGE_NAME, DEBUG)
from mysql_app.database import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("enter lifespan")
    # Redis connection
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    redis_pool = redis.ConnectionPool.from_url(f"redis://{REDIS_HOST}", db=0)
    app.state.redis = redis_pool
    redis_client = redis.Redis.from_pool(connection_pool=redis_pool)
    logger.info("Redis connection established")
    # MySQL connection
    app.state.mysql = SessionLocal()

    # Patch module lifespan
    try:
        logger.info(f"Got mirrors from Redis: {await redis_client.get("snap-hutao:version")}")
    except (TypeError, AttributeError):
        for key in VALID_PROJECT_KEYS:
            r = await redis_client.set(f"{key}:version", json.dumps({"version": None}))
            logger.info(f"Set [{key}:mirrors] to Redis: {r}")
    # Initial patch metadata
    from routers.patch_next import update_snap_hutao_latest_version, update_snap_hutao_deployment_version
    await update_snap_hutao_latest_version(redis_client)
    await update_snap_hutao_deployment_version(redis_client)

    logger.info("ending lifespan startup")
    yield
    logger.info("entering lifespan shutdown")


def get_version():
    if os.path.exists("build_number.txt"):
        with open("build_number.txt", 'r') as f:
            build_number = f"Build {f.read().strip()}"
        logger.info(f"Server is running with Build number: {build_number}")
    else:
        build_number = f"Runtime {datetime.now().strftime('%Y.%m.%d.%H%M%S')}"
        logger.info(f"Server is running with Runtime version: {build_number}")
    if DEBUG:
        build_number += " DEBUG"
    return build_number


app = FastAPI(redoc_url=None,
              title="Hutao Generic API",
              summary="Generic API to support various services for Snap Hutao project.",
              version=get_version(),
              description=MAIN_SERVER_DESCRIPTION,
              terms_of_service=TOS_URL,
              contact=CONTACT_INFO,
              license_info=LICENSE_INFO,
              openapi_url="/openapi.json",
              lifespan=lifespan,
              debug=DEBUG)


class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = str(uuid.uuid4())
        try:
            response = await call_next(request)
        except Exception:
            # re-throw error for traceback
            import traceback
            tb = traceback.format_exc()
            if DEBUG:
                body = {
                    "detail": tb
                }
            else:
                body = {
                    "detail": "Internal Server Error"
                }
            response = JSONResponse(
                body,
                500
            )
        response.headers["X-Powered-By"] = "Hutao Generic API"
        response.headers["X-Generic-ID"] = trace_id
        return response


app.add_middleware(TraceIDMiddleware)

china_root_router = APIRouter(tags=["China Router"], prefix="/cn")
global_root_router = APIRouter(tags=["Global Router"], prefix="/global")
fujian_root_router = APIRouter(tags=["Fujian Router"], prefix="/fj")

# Enka Network API Routers
china_root_router.include_router(enka_network.china_router)
global_root_router.include_router(enka_network.global_router)
fujian_root_router.include_router(enka_network.fujian_router)

# Hutao Metadata API Routers
china_root_router.include_router(metadata.china_router)
global_root_router.include_router(metadata.global_router)
fujian_root_router.include_router(metadata.fujian_router)

# Patch API Routers
china_root_router.include_router(patch_next.china_router)
global_root_router.include_router(patch_next.global_router)
fujian_root_router.include_router(patch_next.fujian_router)

# Static API Routers
china_root_router.include_router(static.china_router)
global_root_router.include_router(static.global_router)
fujian_root_router.include_router(static.fujian_router)

# Network API Routers
china_root_router.include_router(net.china_router)
global_root_router.include_router(net.global_router)
fujian_root_router.include_router(net.fujian_router)

# Wallpaper API Routers
china_root_router.include_router(wallpaper.china_router)
global_root_router.include_router(wallpaper.global_router)
fujian_root_router.include_router(wallpaper.fujian_router)

# Strategy API Routers
china_root_router.include_router(strategy.china_router)
global_root_router.include_router(strategy.global_router)
fujian_root_router.include_router(strategy.fujian_router)

# System Email Router
app.include_router(system_email.admin_router)

# Crowdin Localization API Routers
china_root_router.include_router(crowdin.china_router)
global_root_router.include_router(crowdin.global_router)
fujian_root_router.include_router(crowdin.fujian_router)

# Client feature routers
china_root_router.include_router(client_feature.china_router)
global_root_router.include_router(client_feature.global_router)
fujian_root_router.include_router(client_feature.fujian_router)

app.include_router(china_root_router)
app.include_router(global_root_router)
app.include_router(fujian_root_router)

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if IMAGE_NAME != "" and "dev" not in IMAGE_NAME:
    app.add_middleware(
        ApitallyMiddleware,
        client_id=os.getenv("APITALLY_CLIENT_ID"),
        env="dev" if "alpha" in IMAGE_NAME else "prod",
        openapi_url="/openapi.json"
    )
else:
    logger.info("Apitally is disabled as the image is not a production image.")


@app.get("/", response_class=RedirectResponse, status_code=301)
@china_root_router.get("/", response_class=RedirectResponse, status_code=301)
@global_root_router.get("/", response_class=RedirectResponse, status_code=301)
@fujian_root_router.get("/", response_class=RedirectResponse, status_code=301)
async def root():
    return "https://hut.ao"


@app.get("/error")
@china_root_router.get("/error")
@global_root_router.get("/error")
@fujian_root_router.get("/error")
async def get_sample_error():
    raise RuntimeError(
        "This is endpoint for debug purpose; you should receive a Runtime error with this message in debug mode, else you will only see a 500 error")


if __name__ == "__main__":
    if env_result:
        logger.info(".env file is loaded")
    uvicorn.run(app, host="0.0.0.0", port=8080, proxy_headers=True, forwarded_allow_ips="*")
