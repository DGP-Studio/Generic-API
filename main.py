from config import env_result
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from routers import enka_network, metadata, patch, static
from base_logger import logger

app = FastAPI(redoc_url=None)
app.include_router(enka_network.router)
app.include_router(metadata.router)
app.include_router(patch.router)
app.include_router(static.router)


@app.get("/", response_class=RedirectResponse, status_code=301)
async def root():
    return "https://hut.ao"


if __name__ == "__main__":
    if env_result:
        logger.info(".env file is loaded")
    uvicorn.run(app, host="0.0.0.0", port=8080, proxy_headers=True, forwarded_allow_ips="*")
