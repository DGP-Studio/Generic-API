from pydantic import BaseModel
from datetime import datetime


class PatchMeta(BaseModel):
    version: str
    url: list[str]
    archive_url: list[str] = []
    validation: str
    patch_note: dict
    url_type: str
    cache_time: datetime
