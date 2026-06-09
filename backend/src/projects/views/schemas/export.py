from typing import Any

from pydantic import BaseModel


class ProjectExportResponse(BaseModel):
    added: dict[str, dict[str, Any]]
    removed: dict[str, dict[str, Any]]
    modified: dict[str, dict[str, dict[str, Any]]]

    rooms_conflicts: list[dict[str, Any]]
    classes_conflicts: list[dict[str, Any]]
    teacher_conflicts: list[dict[str, Any]]
