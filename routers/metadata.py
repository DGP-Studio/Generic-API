from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from fastapi_utils.tasks import repeat_every
from utils.git_utils import jihulab_regulatory_checker, scan_duration
from utils.dgp_utils import validate_client_is_updated

router = APIRouter(tags=["category:metadata"], dependencies=[Depends(validate_client_is_updated)])
metadata_censored_files = jihulab_regulatory_checker("DGP-Studio/Snap.Metadata", "DGP-Studio/Snap.Metadata", "main")


@repeat_every(seconds=60 * scan_duration)
async def refresh_metadata_censored_files() -> None:
    """
    Refresh metadata_censored_files every 30 minutes.
    """
    print(f"Start {scan_duration*60}-min scheduled refreshing metadata_censored_files")
    global metadata_censored_files
    metadata_censored_files = jihulab_regulatory_checker("DGP-Studio/Snap.Metadata", "DGP-Studio/Snap.Metadata", "main")


@router.get("/cn/ban")
@router.get("/global/ban")
async def get_banned_files():
    global metadata_censored_files
    return metadata_censored_files


@router.get("/cn/metadata/{file_path:path}", tags=["region:cn"])
async def china_metadata_request_handler(file_path: str):
    """
    Handle requests to metadata files.
    :param file_path: Path to the metadata file
    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    host_for_normal_files = f"https://jihulab.com/DGP-Studio/Snap.Metadata/-/raw/main/{file_path}"
    host_for_censored_files = f"https://metadata.snapgenshin.com/{file_path}"

    if file_path in metadata_censored_files:
        return RedirectResponse(host_for_censored_files, status_code=302)
    else:
        return RedirectResponse(host_for_normal_files, status_code=302)


@router.get("/global/metadata/{file_path:path}", tags=["region:global"])
async def global_metadata_request_handler(file_path: str):
    """
    Handle requests to metadata files.
    :param file_path: Path to the metadata file
    :return: HTTP 302 redirect to the file based on censorship status of the file
    """
    host_for_normal_files = f"https://hutao-metadata-pages.snapgenshin.cn/{file_path}"

    return RedirectResponse(host_for_normal_files, status_code=302)
