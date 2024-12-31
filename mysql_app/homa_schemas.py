from datetime import datetime
from pydantic import BaseModel
from typing import Optional





class HomaPassport(BaseModel):
    user_name: str = "Anonymous"
    is_developer: bool = False
    is_maintainer: bool = False
    sponsor_expire_date: Optional[datetime | None] = None
