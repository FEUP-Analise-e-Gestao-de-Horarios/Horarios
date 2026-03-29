from src.exporter.differences import get_differences_from_databases
from src.exporter.graph_building import ExportGraphBuilder
from src.exporter.visualization import draw_graph, print_changes

projectNumber = 23


def getDifferencesFromDatabases(project_number):
    changes_dict = {}
    return get_differences_from_databases(project_number, changes_dict), changes_dict


def build_export_graph(project_number):
    final_changes, changes_dict = getDifferencesFromDatabases(project_number)
    graph_builder = ExportGraphBuilder(project_number, changes_dict)
    graph = graph_builder.build()
    return final_changes, changes_dict, graph


def main():
    _final_changes, changes_dict, graph = build_export_graph(projectNumber)
    print_changes(changes_dict)
    draw_graph(graph)


if __name__ == "__main__":
    main()
