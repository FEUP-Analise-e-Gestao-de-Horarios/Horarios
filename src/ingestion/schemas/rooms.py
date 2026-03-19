from typing import TypedDict


class RoomInfo(TypedDict):
    """A room entry parsed from the menu, with metadata and schedule links.

    Attributes:
        name: Display name of the room (e.g. ``"A101"``). Rooms whose anchor
            is Cloudflare-obfuscated are stored as ``"EaD"``.
        type_: Room category (e.g. ``"Laboratório"``). Defaults to
            ``"Desconhecido"`` when the room is not in the ``ROOMS`` registry.
            The trailing underscore avoids shadowing the built-in ``type``.
        size: Physical capacity description of the room. Defaults to
            ``"Desconhecido"`` when not in the registry.
        seats: Number of seats as a string. Defaults to ``"Desconhecido"``
            when not in the registry.
        link: URL to the room's timetable page.
    """

    name: str
    type_: str
    size: str
    seats: str
    link: str
