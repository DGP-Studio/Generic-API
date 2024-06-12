from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Literal, Dict, TypedDict


class PatchMirrorMetadata(TypedDict):
    mirror_name: Literal["GitHub", "JiHuLAB", "LenovoAppStore", "CodingAssets", "gh-proxy"]
    mirror_url: str

    @field_validator('mirror_name', mode='before')
    @staticmethod
    def validate_mirror_name(value):
        print(f"Validating mirror name: {value}")
        if value not in ["GitHub", "JiHuLAB", "LenovoAppStore", "CodingAssets", "gh-proxy"]:
            raise ValueError(f"Invalid mirror name: {value}")
        return value


class PatchMeta(BaseModel):
    version: str
    url: list[str]
    archive_url: list[str] = []
    validation: str
    patch_note: dict
    url_type: str
    cache_time: datetime
    mirrors: Dict[str, PatchMirrorMetadata] = Field(default_factory=dict)

    @field_validator('mirrors', mode='before')
    @staticmethod
    def validate_mirrors(value):
        if isinstance(value, dict):
            for key, val in value.items():
                if not isinstance(val, dict) or 'mirror_name' not in val or 'mirror_url' not in val:
                    raise ValueError(
                        f"Each mirror must be a dict containing 'mirror_name' and 'mirror_url'. Invalid entry: {key}: {val}")
                if val['mirror_name'] != key:
                    print(f"Mirror name in value ({val['mirror_name']}) does not match key ({key}).")
                    raise ValueError(f"Mirror name in value ({val['mirror_name']}) does not match key ({key}).")
        else:
            raise ValueError("mirrors must be a dictionary")
        return value

    def add_mirror(self, mirror_metadata: PatchMirrorMetadata):
        print(f"Adding mirror: {mirror_metadata}")
        mirror_name = mirror_metadata['mirror_name']
        self.mirrors[mirror_name] = PatchMirrorMetadata(**mirror_metadata)

    def __repr__(self):
        return f"schema.PatchMeta({self.dict()})"
