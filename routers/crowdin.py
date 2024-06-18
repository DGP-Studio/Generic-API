from fastapi import APIRouter
from mysql_app.schemas import StandardResponse
import requests
import os

china_router = APIRouter(tags=["Localization"], prefix="/localization")
global_router = APIRouter(tags=["Localization"], prefix="/localization")

API_KEY = os.environ.get("CROWDIN_API_KEY", None)
CROWDIN_HOST = "https://api.crowdin.com/api/v2"
SNAP_HUTAO_PROJECT_ID = 565845


def fetch_snap_hutao_translation_process():
    if not API_KEY:
        return {}

    result_output = {}
    url = f"{CROWDIN_HOST}/projects/{SNAP_HUTAO_PROJECT_ID}"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    resp = requests.get(url, headers=headers).json()
    hutao_target_language_ids = resp["data"]["targetLanguageIds"]
    for language_id in hutao_target_language_ids:
        url = f"{CROWDIN_HOST}/projects/{SNAP_HUTAO_PROJECT_ID}/languages/{language_id}/progress"
        resp = requests.get(url, headers=headers).json()
        total_count = resp["data"][0]["data"]["words"]["total"]
        translated_count = resp["data"][0]["data"]["words"]["translated"]
        result_output[language_id] = {
            "total": total_count,
            "translated": translated_count
        }
    return result_output


@china_router.get("/status", response_model=StandardResponse)
@global_router.get("/status", response_model=StandardResponse)
async def get_latest_status() -> StandardResponse:
    status = fetch_snap_hutao_translation_process()
    return StandardResponse(
        retcode=0,
        message="success",
        data=status
    )
