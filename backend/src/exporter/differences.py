from src.projects.projects_db.dao.base_dao import BaseDAO
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

    def _get_data(self, dao: BaseDAO):
        return {
            obj.id: {c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name != "id"}
            for obj in dao.get_all()
        }

    def database_differences(self):
        session_dao_initial = SessionDAO(self.initial_session_db)
        session_dao_general = SessionDAO(self.general_session_db)

        def get_map(dao: BaseDAO):
            # Returns {id: {col: val}}
            return {
                str(obj.id): {
                    c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name != "id"
                }
                for obj in dao.get_all()
            }

        current_map = get_map(session_dao_general)
        old_map = get_map(session_dao_initial)

        current_ids = set(current_map.keys())
        old_ids = set(old_map.keys())

        # 1. Added & Removed
        added = {id_: current_map[id_] for id_ in (current_ids - old_ids)}
        removed = {id_: old_map[id_] for id_ in (old_ids - current_ids)}

        # 2. Modified (The "Delta")
        modified = {}
        for id_ in current_ids & old_ids:
            if current_map[id_] != old_map[id_]:
                # Only include the specific keys that changed
                diff = {
                    k: current_map[id_][k]
                    for k in current_map[id_]
                    if current_map[id_][k] != old_map[id_][k]
                }
                modified[id_] = diff

        return {"added": added, "removed": removed, "modified": modified}


# def get_differences_from_databases():
#     handlers = {
#         "aulaSala": handleAulaSala,
#         "docentes": handleDocentes,
#         "salas": handleSalas,
#         "aulaDocente": handleAulaDocente,
#         "aula": handleAulas,
#         "aulaTurmas": handleAulaTurmas,
#         "aulaUC": handleAulaUC,
#     }

#     every_change = []

#     for table1 in tables1:
#         table1_name = table1[0]

#         for table2 in tables2:
#             table2_name = table2[0]

#             if table1_name != table2_name:
#                 continue

#             cursor_db.execute(f"SELECT * FROM {table1_name};")
#             data1 = cursor_db.fetchall()

#             cursor_ini.execute(f"SELECT * FROM {table2_name};")
#             data2 = cursor_ini.fetchall()

#             set1 = set(data1)
#             set2 = set(data2)

#             if set1 != set2:
#                 diff_data1 = set1 - set2
#                 diff_data2 = set2 - set1

#                 primary_key = get_primary_key(conn_db, table1_name)
#                 add_change_to_dict(this.changes_dict, table1_name, primary_key, diff_data1, diff_data2)
#                 every_change.append(handlers[table1_name](set1, set2, project_number))

#             break

#     formatted_changes = [item for sublist in every_change for item in sublist]
#     sorted_changes = sorted(formatted_changes, key=sortChanges)
#     return [string for precedence, string, id in sorted_changes]


def add_change_to_dict(changes_dict, table_name, primary_key, diff_data1, diff_data2):
    new_changes = [dict(row) for row in diff_data1]
    prev_changes = [dict(row) for row in diff_data2]

    for prev in prev_changes:
        for new in new_changes:
            if prev[primary_key] == new[primary_key]:
                changes_dict[len(changes_dict) + 1] = (table_name, prev, new)
                break


def get_primary_key(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for column in columns:
        if column[5]:
            return column[1]
    return None
