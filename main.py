from config import env_result
import uvicorn
import os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from apitally.fastapi import ApitallyMiddleware
from routers import enka_network, metadata, patch, static, net, wallpaper, strategy, crowdin, system_email
from base_logger import logger
from config import (MAIN_SERVER_DESCRIPTION, API_VERSION, TOS_URL, CONTACT_INFO, LICENSE_INFO,
                    CHINA_SERVER_DESCRIPTION, GLOBAL_SERVER_DESCRIPTION)

app = FastAPI(redoc_url=None,
              title="Hutao Generic API (Main Server)",
              summary="Generic API to support various services for Snap Hutao project.",
              version=API_VERSION,
              description=MAIN_SERVER_DESCRIPTION,
              terms_of_service=TOS_URL,
              contact=CONTACT_INFO,
              license_info=LICENSE_INFO,
              openapi_url="/openapi.json")
china_app = FastAPI(title="Hutao Generic API (China Ver.)",
                    summary="Generic API to support various services for Snap Hutao project, specifically for "
                            "Mainland China region.",
                    version=API_VERSION,
                    description=CHINA_SERVER_DESCRIPTION,
                    terms_of_service=TOS_URL,
                    contact=CONTACT_INFO,
                    license_info=LICENSE_INFO,
                    openapi_url="/openapi.json")
global_app = FastAPI(title="Hutao Generic API (Global Ver.)",
                     summary="Generic API to support various services for Snap Hutao project, specifically for "
                             "Global region.",
                     version=API_VERSION,
                     description=GLOBAL_SERVER_DESCRIPTION,
                     terms_of_service=TOS_URL,
                     contact=CONTACT_INFO,
                     license_info=LICENSE_INFO,
                     openapi_url="/openapi.json")

# Enka Network API Routers
china_app.include_router(enka_network.china_router)
global_app.include_router(enka_network.global_router)

# Hutao Metadata API Routers
china_app.include_router(metadata.china_router)
global_app.include_router(metadata.global_router)

# Patch API Routers
china_app.include_router(patch.china_router)
global_app.include_router(patch.global_router)

# Static API Routers
china_app.include_router(static.china_router)
global_app.include_router(static.global_router)

# Network API Routers
china_app.include_router(net.china_router)
global_app.include_router(net.global_router)

# Wallpaper API Routers
china_app.include_router(wallpaper.china_router)
global_app.include_router(wallpaper.global_router)

# Strategy API Routers
china_app.include_router(strategy.china_router)
global_app.include_router(strategy.global_router)


# System Email Router
app.include_router(system_email.admin_router)

# Crowdin Localization API Routers
china_app.include_router(crowdin.china_router)
global_app.include_router(crowdin.global_router)

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

app.add_middleware(
    ApitallyMiddleware,
    client_id=os.getenv("APITALLY_CLIENT_ID"),
    env="dev" if os.getenv("DEBUG") == "1" or os.getenv("APITALLY_DEBUG") == "1" else "prod",
    openapi_url="/openapi.json"
)

app.mount("/cn", china_app, name="Hutao Generic API (China Ver.)")
app.mount("/global", global_app, name="Hutao Generic API (Global Ver.)")


@app.get("/", response_class=RedirectResponse, status_code=301)
@china_app.get("/", response_class=RedirectResponse, status_code=301)
@global_app.get("/", response_class=RedirectResponse, status_code=301)
async def root():
    return "https://hut.ao"


if __name__ == "__main__":
    if env_result:
        logger.info(".env file is loaded")
    uvicorn.run(app, host="0.0.0.0", port=8080, proxy_headers=True, forwarded_allow_ips="*")
