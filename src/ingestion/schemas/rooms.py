from typing import TypedDict


class RoomLinks(TypedDict):
    name: str
    type_: str
    size: str
    seats: str
    links: list[str]
