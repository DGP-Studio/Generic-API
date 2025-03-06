from config import env_result
import uvicorn
import os
import json
from typing import Annotated
from redis import asyncio as aioredis
from fastapi import FastAPI, APIRouter, Request, Header, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from apitally.fastapi import ApitallyMiddleware, ApitallyConsumer
from datetime import datetime
from contextlib import asynccontextmanager
from routers import (enka_network, metadata, patch_next, static, net, wallpaper, strategy, crowdin, system_email,
                     client_feature, mgnt)
from base_logger import logger
from config import (MAIN_SERVER_DESCRIPTION, TOS_URL, CONTACT_INFO, LICENSE_INFO, VALID_PROJECT_KEYS,
                    IMAGE_NAME, DEBUG, SERVER_TYPE, REDIS_HOST, SENTRY_URL)
from mysql_app.database import SessionLocal
from utils.redis_tools import init_redis_data
import sentry_sdk
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("enter lifespan")
    # System config
    now = datetime.now()
    utc_offset = datetime.now().astimezone().utcoffset().total_seconds() / 3600
    logger.info(f"Current system timezone: {now.astimezone().tzname()} (UTC{utc_offset:+.0f})")
    # Create cache folder
    os.makedirs("cache", exist_ok=True)
    # Redis connection
    redis_pool = aioredis.ConnectionPool.from_url(f"redis://{REDIS_HOST}", db=0)
    app.state.redis = redis_pool
    redis_client = aioredis.Redis.from_pool(connection_pool=redis_pool)
    logger.info("Redis connection established")
    # MySQL connection
    app.state.mysql = SessionLocal()

    # Patch module lifespan
    try:
        redis_cached_version = await redis_client.get("snap-hutao:version")
        redis_cached_version = redis_cached_version.decode("utf-8")
        logger.info(f"Got mirrors from Redis: {redis_cached_version}")
    except (TypeError, AttributeError):
        for key in VALID_PROJECT_KEYS:
            r = await redis_client.set(f"{key}:version", json.dumps({"version": None}))
            logger.info(f"Set [{key}:mirrors] to Redis: {r}")
    # Initial patch metadata
    from routers.patch_next import (update_snap_hutao_latest_version, update_snap_hutao_deployment_version,
                                    fetch_snap_hutao_alpha_latest_version)
    await update_snap_hutao_latest_version(redis_client)
    await update_snap_hutao_deployment_version(redis_client)
    await fetch_snap_hutao_alpha_latest_version(redis_client)

    # Initial Redis data
    await init_redis_data(redis_client)

    logger.info("ending lifespan startup")
    yield
    logger.info("entering lifespan shutdown")


def get_version():
    if os.path.exists("build_number.txt"):
        with open("build_number.txt", 'r') as f:
            build_number = f"{IMAGE_NAME}-{SERVER_TYPE} Build {f.read().strip()}"
        logger.info(f"Server is running with Build number: {build_number}")
    else:
        build_number = f"Runtime {datetime.now().strftime('%Y.%m.%d.%H%M%S')}"
        logger.info(f"Server is running with Runtime version: {build_number}")
    if DEBUG:
        build_number += " DEBUG"
    if os.path.exists("current_commit.txt"):
        with open("current_commit.txt", 'r') as f:
            commit_hash = f.read().strip()
            build_number += f" {commit_hash[:7]}"
    return build_number


def get_commit_hash_str():
    commit_desc = ""
    if os.path.exists("current_commit.txt"):
        with open("current_commit.txt", 'r') as f:
            commit_hash = f.read().strip()
        logger.info(f"Server is running with Commit hash: {commit_hash}")
        commit_desc = f"Build hash: [**{commit_hash}**](https://github.com/DGP-Studio/Generic-API/commit/{commit_hash})"
    if DEBUG:
        commit_desc += "\n\n**Debug mode is enabled.**"
        commit_desc += "\n\n![Image](https://github.com/user-attachments/assets/64ce064c-c399-4d2f-ac72-cac4379d8725)"
    return commit_desc


def identify_user(request: Request) -> None:
    # Extract headers
    reqable_id = request.headers.get("Reqable-Id", None)
    user_agent = request.headers.get("User-Agent", "unknown-UA")

    # Assign to Apitally consumer
    request.state.apitally_consumer = ApitallyConsumer(
        identifier="Reqable" if reqable_id else user_agent,
        group="Reqable" if reqable_id else "Snap Hutao"
    )


sentry_sdk.init(
    dsn=SENTRY_URL,
    send_default_pii=True,
    traces_sample_rate=1.0,
    integrations=[
        StarletteIntegration(
            transaction_style="url",
            failed_request_status_codes={403, *range(500, 599)},
        ),
        FastApiIntegration(
            transaction_style="url",
            failed_request_status_codes={403, *range(500, 599)},
        ),
    ],
    profiles_sample_rate=1.0,
    release=SERVER_TYPE,
    dist=get_version(),
    server_name="US1",
)


app = FastAPI(redoc_url=None,
              title="Hutao Generic API",
              summary="Generic API to support various services for Snap Hutao project.",
              version=get_version(),
              description=MAIN_SERVER_DESCRIPTION + "\n" + get_commit_hash_str(),
              terms_of_service=TOS_URL,
              contact=CONTACT_INFO,
              license_info=LICENSE_INFO,
              openapi_url="/openapi.json",
              lifespan=lifespan,
              debug=DEBUG,
              dependencies=[Depends(identify_user)])


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

# Misc
app.include_router(system_email.admin_router)
app.include_router(mgnt.router)

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

if SERVER_TYPE != "" and "dev" not in os.getenv("SERVER_TYPE"):
    app.add_middleware(
        ApitallyMiddleware,
        client_id=os.getenv("APITALLY_CLIENT_ID"),
        env="dev" if "alpha" in SERVER_TYPE else "prod",
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
