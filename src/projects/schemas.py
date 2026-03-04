import re

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ParseProjectInput(BaseModel):
    name: str = Field(max_length=30)
    url: HttpUrl

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9_\-]+", v):
            raise ValueError("name can only contain letters, numbers, '_' and '-'")
        return v
