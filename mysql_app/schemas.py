from pydantic import BaseModel
from typing import Optional
import datetime


class Wallpaper(BaseModel):
    url: str
    display_date: Optional[datetime.date | None] = None
    last_display_date: Optional[datetime.date | None] = None
    source_url: str
    author: str
    uploader: str
    disabled: Optional[int | bool] = False
