import networkx as nx
import json
import os
import matplotlib.pyplot as plt
from readerwriterlock import rwlock

lock = rwlock.RWLockFairD()
readerLock = lock.gen_rlock()
writerLock = lock.gen_wlock()
# Create an empty undirected graph

def init_graph(ProjectNumber):
    if(writerLock.acquire(blocking=True, timeout=2)):
        try:
            path = "Project" + str(ProjectNumber)
            file_path = './database/' + path + '/conflicts_graph.json'
            if not os.path.exists(file_path):
                graph = nx.Graph()  # Create an empty graph

                graph_data = nx.node_link_data(graph)
                with open(file_path, 'w') as json_file:
                    json.dump(graph_data, json_file, indent=4)
        finally:
            writerLock.release()


def load_graph_from_json(ProjectNumber):
    path = "Project" + str(ProjectNumber)
    file_path = './database/' + path + '/conflicts_graph.json'
    if os.path.exists(file_path):
        if(readerLock.acquire(blocking=True, timeout=2)):
            try:
                with open(file_path, 'r') as json_file:
                    graph_data = json.load(json_file)
                    if isinstance(graph_data, str):
                        graph_data = json.loads(graph_data)
                    graph = nx.node_link_graph(graph_data)
            finally:
                readerLock.release()
        return graph
    else:
        return None

def save_graph_to_json(graph, ProjectNumber):
    if(writerLock.acquire(blocking=True, timeout=2)):
        try:
            path = "Project" + str(ProjectNumber)
            file_path = './database/' + path + '/conflicts_graph.json'

            if os.path.exists(file_path):
                graph_data = nx.node_link_data(graph)
                with open(file_path, 'w') as json_file:
                    json.dump(graph_data, json_file, indent=4)
        finally:
            writerLock.release()

def print_graph(ProjectNumber):
    graph = load_graph_from_json(ProjectNumber)
    

def print_graph_nodes(ProjectNumber):
    graph = load_graph_from_json(ProjectNumber)
    

def print_graph_edges(ProjectNumber):
    graph = load_graph_from_json(ProjectNumber)
    

def get_all_conflicts(ProjectNumber):
    graph = load_graph_from_json(ProjectNumber)
    full_conflict_list = []
    full_conflict_list.append(get_node_conflicts(ProjectNumber))
    return full_conflict_list

def add_node_to_graph(ProjectNumber, node):
    graph = load_graph_from_json(ProjectNumber)
    graph.add_node(node)
    save_graph_to_json(graph, ProjectNumber)


def remove_conflict_from_graph(ProjectNumber, node1, node2, conflict):
    graph = load_graph_from_json(ProjectNumber)
    if graph.has_edge(node1, node2):
        conflicts = graph[node1][node2]['conflicts']
        if conflict in conflicts:
            conflicts.remove(conflict)
            if len(conflicts) == 0:
                graph.remove_edge(node1, node2)
                if (len(graph.edges(node1))==0):
                    graph.remove_node(node1)
                if (len(graph.edges(node2))==0):
                    graph.remove_node(node2)
                save_graph_to_json(graph, ProjectNumber)
        else:
            raise ValueError("The specified conflict message does not exist for the given edge.")
    else:
        raise ValueError("The specified edge does not exist in the graph.")

def add_edge_to_graph(ProjectNumber, node1, node2, conflicts):
    graph = load_graph_from_json(ProjectNumber)
    if graph.has_edge(node1, node2):
        if 'conflicts' in graph[node1][node2]:
            existing_conflicts = graph[node1][node2]['conflicts']
            if isinstance(existing_conflicts, str):
                existing_conflicts = [existing_conflicts]
            new_conflicts = [conflicts] if conflicts not in existing_conflicts else []
            if new_conflicts:
                updated_conflicts = existing_conflicts + new_conflicts
                graph[node1][node2]['conflicts'] = updated_conflicts
        else:
            graph[node1][node2]['conflicts'] = conflicts
    else:
        graph.add_edge(node1, node2, conflicts=conflicts)
    save_graph_to_json(graph, ProjectNumber)

def get_node_conflicts(ProjectNumber):
    graph = load_graph_from_json(ProjectNumber)
    conflicts = {}
    for edge in graph.edges:
        node1, node2 = edge
        edge_conflicts = graph[node1][node2].get('conflicts')
        if edge_conflicts:
            conflicts[edge] = edge_conflicts
    return conflicts

def handle_conflict_of_same_aulas(ProjectNumber, node, typeOfConflict):
    graph = load_graph_from_json(ProjectNumber)
    affected_edges = [(node1, node2) for (node1, node2) in graph.edges if int(node) == node1 or int(node) == node2]
    for node1, node2 in affected_edges:
        if 'conflicts' in graph[node1][node2]:
            if isinstance(graph[node1][node2]['conflicts'], list):
                conflicts = graph[node1][node2]['conflicts']
            else:
                conflicts = [graph[node1][node2]['conflicts']]
            newConflicts = []
            for x in conflicts:
                if (typeOfConflict not in x):
                    newConflicts.append(x)
            graph[node1][node2]['conflicts'] = newConflicts
            if not conflicts:
                graph.remove_edge(node1, node2)
                print("Edge removed:", node1, node2)
    save_graph_to_json(graph, ProjectNumber)


def get_organized_conflicts(ProjectNumber):
    graph = load_graph_from_json(ProjectNumber)
    conflicts_dict = {}
    
    for node1, node2 in graph.edges:
        if 'conflicts' in graph[node1][node2] and graph[node1][node2]['conflicts'] != []:
            conflicts = graph[node1][node2]['conflicts']
            conflicts_dict[(node1, node2)] = conflicts
    
    return conflicts_dict

def clean_graph(ProjectNumber):
    graph = load_graph_from_json(ProjectNumber)
    isolated_nodes = [node for node in graph.nodes if not any(node in edge for edge in graph.edges)]
    graph.remove_nodes_from(isolated_nodes)
    save_graph_to_json(graph, ProjectNumber)


def draw_graph(ProjectNumber):
    graph = load_graph_from_json(ProjectNumber)
    pos = nx.spring_layout(graph, k=10)
    nx.draw_networkx(graph, pos, width=1.5)
    edge_labels = nx.get_edge_attributes(graph, "conflicts")
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels)
    plt.show()


