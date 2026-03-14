from datetime import datetime
from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class SuccessResponse[T](BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    message: str
    data: T
