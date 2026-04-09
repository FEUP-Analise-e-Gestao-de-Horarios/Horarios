from typing import Any

from src.exporter.conflicts import (
    class_conflicts,
    room_conflicts,
    serialize_conflicts,
    teacher_conflicts,
)
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.paths import general_db, initial_db
from src.projects.projects_db.registry import get_session


class Comparator:
    def __init__(self, proj_id: int):
        self.proj_id = proj_id
        self.general_session_db = get_session(general_db(proj_id))
        self.initial_session_db = get_session(initial_db(proj_id))
        self.changes_dict = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.general_session_db.close()
        self.initial_session_db.close()

    def database_differences(self) -> dict[str, Any]:
        session_dao_initial = SessionDAO(self.initial_session_db)
        session_dao_general = SessionDAO(self.general_session_db)

        current_map = session_dao_general.get_diff_map()
        old_map = session_dao_initial.get_diff_map()

        current_ids = set(current_map.keys())
        old_ids = set(old_map.keys())

        # 1. Added & Removed
        added = {id_: current_map[id_] for id_ in (current_ids - old_ids)}
        removed = {id_: old_map[id_] for id_ in (old_ids - current_ids)}

        # 2. Modified (The "Delta")
        modified = {}
        for id_ in current_ids & old_ids:
            if current_map[id_] != old_map[id_]:
                diff = {
                    k: {"from": old_map[id_][k], "to": current_map[id_][k]}
                    for k in current_map[id_]
                    if current_map[id_][k] != old_map[id_][k]
                }
                modified[id_] = diff

        return {"added": added, "removed": removed, "modified": modified}

    def database_conflicts(self):
        session_dao_general = SessionDAO(self.general_session_db)
        general_sessions = session_dao_general.get_all()

        return {
            "rooms_conflicts": serialize_conflicts(room_conflicts(general_sessions)),
            "classes_conflicts": serialize_conflicts(class_conflicts(general_sessions)),
            "teacher_conflicts": serialize_conflicts(teacher_conflicts(general_sessions)),
        }
