import shutil
import sqlite3

import networkx as nx

from src.exporter.db_changes import (
    apply_change_to_db,
    check_change_to_db,
    generate_conflicts,
)


class ExportGraphBuilder:
    def __init__(self, project_number, changes_dict):
        self.project_number = project_number
        self.changes_dict = changes_dict
        self.change_order = 1

    def find_best_change(self, conflict, visited):
        print("Finding change for conflict: ", conflict)
        for change in self.changes_dict:
            if change in visited:
                continue
            table, prev, new = self.changes_dict[change]
            print("Checking if change", change, "is a solution...")
            solve_conflict, new_conflicts = check_change_to_db(
                self.project_number,
                conflict,
                table,
                prev,
                new,
            )
            if solve_conflict:
                return change, new_conflicts
        print("ERROR: No solution found for conflict: ", conflict)
        return None, None

    def dfs_visit(self, graph, change, visited):
        print("\n")
        print("Visiting change", change)
        print("Visited changes", visited)
        if change not in visited:
            table, prev, new = self.changes_dict[change]
            visited.add(change)
            conflicts = apply_change_to_db(self.project_number, table, new)
            graph.add_node(change, table=table, prev=prev, new=new, order=self.change_order)
            self.change_order += 1
            print("Conflicts: ", conflicts)
            while len(conflicts) > 0:
                conflict = conflicts.pop(0)
                next_change, _new_conflicts = self.find_best_change(conflict, visited)
                if next_change is None:
                    continue
                table, prev, new = self.changes_dict[next_change]
                graph.add_node(
                    next_change,
                    table=table,
                    prev=prev,
                    new=new,
                    order=self.change_order,
                )
                graph.add_edge(change, next_change)
                conflicts = self.dfs_visit(graph, next_change, visited)
            return conflicts

    def find_independent_changes(self, visited, graph):
        change_num = 1
        while change_num <= len(self.changes_dict):
            table, prev, new = self.changes_dict[change_num]
            print("\nChange", change_num)
            if change_num not in visited and not generate_conflicts(
                self.project_number,
                table,
                prev,
                new,
            ):
                apply_change_to_db(self.project_number, table, new)
                visited.add(change_num)
                graph.add_node(
                    change_num,
                    table=table,
                    prev=prev,
                    new=new,
                    order=self.change_order,
                )
                self.change_order += 1
                change_num = 1
                continue
            change_num += 1

    def build(self):
        src = f"./database/Project{self.project_number}/initial_database.db"
        dst = f"./database/Project{self.project_number}/duplicate_initial_database.db"
        shutil.copy2(src, dst)

        duplicate_initial_db = sqlite3.connect(dst, check_same_thread=False)
        duplicate_initial_db.row_factory = sqlite3.Row
        duplicate_initial_db.close()

        queue = []
        for change in self.changes_dict:
            table, prev, new = self.changes_dict[change]
            queue.append((change, table, prev, new))

        graph = nx.DiGraph()
        visited = set()
        self.change_order = 1

        for change, _table, _prev, _new in queue:
            print("For Loop", change)
            if change not in visited:
                self.dfs_visit(graph, change, visited)

        return graph
