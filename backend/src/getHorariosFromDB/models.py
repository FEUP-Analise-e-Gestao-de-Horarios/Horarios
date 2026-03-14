from src.FeupScheduleEditor.models import AulaChange
from .auxiliar_functions import *

#A node represents an change of an class info
    #AulaChange -> old aula info and the new aula info
    #root_global -> boolean to tell if the node is the starting node of the global graph (only 1 node will have this type)
    #root_local -> boolean to tell if the node is the starting point of a local graph (e.g. the first change for an uc)
class Node:
    def __init__(self, change: AulaChange = None):
        self.id = generate_node_id()
        self.red_conflicts = False
        self.dependency_ids = []
        self.conflict_ids = []
        
        self.dependencies = []
        self.change = change
        self.conflict = False
    
    def has_conflicts(self, value=True):
        self.conflict = value
    
    def has_red_conflicts(self, value=True):    
        """This function will set the red conflicts to true or false"""
        self.red_conflicts = value
    
    def add_dependencies(self, ids):
        for dep_id in ids:
            if dep_id not in self.dependency_ids:
                self.dependency_ids.append(dep_id)
        
    def get_uc(self):
        return str(self.change.new.cadeira_id)
    
    def check_uc(self):
        return self.change.previous.cadeira_id == self.change.new.cadeira_id
  
    def get_turmas(self):
        turmas = set()
        turmas.update(self.change.new.turmas_ids)
        turmas.update(self.change.previous.turmas_ids)
        return turmas
    def __str__(self):
        """Human-readable string representation of the node."""
        return f"Node(id={self.id}, change={self.change})"

class Edge:
    def __init__(self, node1: Node, node2: Node):
        
        self.node1 = node1
        self.node2 = node2
        if self.node2.id < self.node1.id:
            self.node1 = node2
            self.node2 = node1

        self.local = False
        self.dependency = False
        self.solution = False

        self.uc = False
        self.turma = False
            
    def __str__(self):
        """Human-readable string representation of the edge."""
        return (f"Edge(node1={self.node1}, node2={self.node2}, "
                f"local={self.local}, global_={self.global_}, uc={self.uc}, turma={self.turma})")

class Graph:
    def __init__(self, identifier: str, type: int, uc_name):
        self.id = identifier
        self.root = None

        self.nodes = set()  
        self.edges = []

        self.unsolved_nodes = set()
        self.type = type    
        self.uc_name = uc_name
        self.ordered_list = set()

        self.original = None

    def add_node(self, node):
        if node not in self.nodes:
            self.nodes.add(node)

    def remove_node(self, node):
        if node in self.nodes:
            self.nodes.remove(node)
            self.edges = [edge for edge in self.edges if node not in (edge.node1, edge.node2)]
    
    def create_edges(self):
        nodes_to_remove = []
        self.original = len(self.nodes)
        for node in self.nodes:
            if node.conflict:
                for tmp in self.nodes:
                    for id in node.dependency_ids:
                        if tmp.change.previous.id == id:
                            edge = Edge(node, tmp)
                            edge.local = True
                            edge.dependency = True
                            edge.uc = True
                            if not tmp.conflict:
                                edge.solution = True
                            if edge not in self.edges:
                                self.edges.append(edge)
                            node.dependency_ids.remove(id)
                        else:
                            self.unsolved_nodes.add(node)
            else:
                nodes_to_remove.append(node)
                self.ordered_list.add(node)
        for node in nodes_to_remove:
            self.nodes.remove(node)
    
    def update_list(self):
        for edge in self.edges:
            if edge.solution:
                node = edge.node1
                if (node.conflict):
                    node = edge.node2
                    self.follow_dependency(node)
    
    def follow_dependency(self, node):
        edges = self.get_node_edges(node)
        if node not in self.ordered_list:
            self.nodes.remove(node)
            self.ordered_list.add(node)
        for edge in edges:
            if edge.solution and edge.node1.id == node.id or edge.node2.id == node.id:
                self.edges.remove(edge)
            cur = edge.node1
            if edge.node1.id == node.id:
                cur = edge.node2
            if len(self.get_node_edges(cur)) == 0:
                cur.has_conflicts(value=False)
                self.follow_dependency(cur)
            else:
                self.update_list()

    def get_node_edges(self, node):
        """Return a list of edges that include the given node."""
        return [edge for edge in self.edges if edge.node1 == node or edge.node2 == node]
    
    def __str__(self):
        """Human-readable string representation of the Graph."""
        # First print the graph ID
        graph_info = f"Graph ID: {self.uc_name}\n"
        graph_info += f"Original Nodes: {self.original}\n"
        graph_info += f"Solved Nodes: {len(self.ordered_list)}\n"
        graph_info += f"Unsolved Nodes: {len(self.unsolved_nodes)}\n"
        for node in self.ordered_list:
             graph_info += f"  {node}\n"  
        for node in self.unsolved_nodes:
            graph_info += f"  {node}\n"  
            #graph_info += "Edges (start):\n"
            #for edge in self.get_node_edges(node):
            #    graph_info += f"  {edge}\n"
            #graph_info += "Edges (end):\n"
        return graph_info

class Conflict_Manager:
    def __init__(self, project_number, conflicts):
        self.project_number = project_number
        self.conflicts = conflicts

        self.conflicts_turmas = {}
        self.conflicts_docentes = {}
        self.conflicts_salas = {}
    
    def grouping(self):
        for conflict in self.conflicts:
            for turma in conflict.turmas_ids:
                tmp = aula_conflicts(conflict, self.conflicts, turma, "turma")
                if tmp:
                    tmp.add(conflict)
                if turma not in self.conflicts_turmas:
                    self.conflicts_turmas[turma] = set()
                self.conflicts_turmas[turma].update(tmp)
            for sala in conflict.salas_ids:
                tmp = aula_conflicts(conflict, self.conflicts, sala, "sala")
                if tmp:
                    tmp.add(conflict)
                if sala not in self.conflicts_salas:
                    self.conflicts_salas[sala] = set()
                self.conflicts_salas[sala].update(tmp)
            for docente in conflict.docentes_ids:
                tmp = aula_conflicts(conflict, self.conflicts, docente, "docente")
                if tmp:
                    tmp.add(conflict)
                if docente not in self.conflicts_docentes:
                    self.conflicts_docentes[docente] = set()
                self.conflicts_docentes[docente].update(tmp)
        self.remove_single_conflicts()
        self.organize_dicts()

    def organize_dicts(self):
        for key in self.conflicts_turmas:
            self.conflicts_turmas[key] = sort_by_day(self.conflicts_turmas[key])
        for key in self.conflicts_salas:
            self.conflicts_salas[key] = sort_by_day(self.conflicts_salas[key])  
        for key in self.conflicts_docentes:
            self.conflicts_docentes[key] = sort_by_day(self.conflicts_docentes[key])
    

    def remove_single_conflicts(self):
        """Remove all dictionary entries with 1 or fewer conflicts"""
        def clean_dict(d):
            # Create list of keys to avoid modifying dict during iteration
            keys_to_remove = [k for k, v in d.items() if len(v) <= 1]
            for k in keys_to_remove:
                del d[k]
            return len(keys_to_remove)

        removed_turmas = clean_dict(self.conflicts_turmas)
        removed_salas = clean_dict(self.conflicts_salas)
        removed_docentes = clean_dict(self.conflicts_docentes)
    
        #print(f"Removed: {removed_turmas} turmas, {removed_salas} salas, {removed_docentes} docentes")
        
    def get_turma_conflicts(self):
        for turma in self.conflicts_turmas:
            for aula in self.conflicts_turmas[turma]:
                continue
                

class GraphManager:
    def __init__(self, project_number, mode):
        self.root = None
        self.ucs = {}
        self.project_number = project_number
        self.mode = mode

        self.conflicts = set()
        self.conflicts_ucs = {}

        self.global_edges = set()
        self.global_nodes = set()
        self.unsolved_nodes = set()

        self.local_roots = []

        self.ordered_list = []
    

    def get_all_nodes(self):
        """
        Returns a list of all nodes from all UCs in the ordered list.
        """
        all_nodes = []
        for uc in self.ordered_list:
            graph = self.ucs[uc]
            nodes = list(graph.ordered_list) + list(graph.unsolved_nodes)
            for node in nodes:
                if node not in all_nodes:
                    all_nodes.append(node)
        return all_nodes
    
    def get_node(self, id):
        all_nodes = self.get_all_nodes()
        for node in all_nodes:
            if node.id == id:
                return node
        return None
    
    def get_node_by_aula_id(self, aula_id):
        all_nodes = self.get_all_nodes()
        for node in all_nodes:
            #print(f"DEBUG: PREVIOUS ID: {node.change.previous.id} - AULA ID: {aula_id}")
            if node.change.new.id == aula_id:
                return node
        return None
    
    def add_node(self, node: Node):
        true_checker = check_aula_change_conflicts(node.change, self.project_number, "general")
        #true checker not enough
        checker = check_aula_change_conflicts(node.change, self.project_number, self.mode)
        #checker = list(set(checker + true_checker))
        
        if checker:
            node.has_conflicts()
            node.add_dependencies(checker)
        if true_checker:
            node.conflict_ids = true_checker
        #if "red" in checker:
        #    node.has_red_conflicts()
        uc_id = node.get_uc()
        if uc_id not in self.ucs:
            new = Graph(uc_id, 0, node.change.new.uc_name)
            self.ucs[uc_id] = new
        if not true_checker:
            self.ucs[uc_id].add_node(node)
        else:
            self.ucs[uc_id].unsolved_nodes.add(node)
    
        

    def order_ucs(self):
        remaining_keys = [key for key in self.ucs if key not in self.ordered_list]

        sorted_keys = sorted(remaining_keys, key=lambda k: len(self.ucs[k].unsolved_nodes))

        self.ordered_list.extend(sorted_keys)
    
    def default_order(self):
        self.ordered_list = sorted(self.ucs.keys())

    def print_conflicts(self):
        for id in self.ucs:
            aux = 0
            graph = self.ucs[id]
            for node in graph.nodes:
                if node.conflict:
                    aux+=1
    def create_local_edges(self):
        for key in self.ucs:
            graph = self.ucs[key]
            graph.create_edges()
            self.global_nodes.update(graph.unsolved_nodes)
    
    def update_local_edges(self):
        for key in self.ucs:
            graph = self.ucs[key]
            graph.update_list()

    
    def print_ucs(self):
        for id in self.ucs:
            print(self.ucs[id])
        for uc in self.ordered_list:
            print(self.ucs[uc])
    
    def get_all_nodes_with_counter(self):
        """
        Returns a dict {node.id: counter}, assigning an incremental counter to each node
        from all UCs in the ordered list, keeping the count across UCs.
        """
        all_nodes = []
        for uc in self.ordered_list:
            graph = self.ucs[uc]
            nodes = list(graph.ordered_list) + list(graph.unsolved_nodes)
            for node in nodes:
                if node not in all_nodes:
                    all_nodes.append(node)
        node_counter_dict = {}
        counter = 1
        for node in all_nodes:
            node_counter_dict[node.id] = counter
            counter += 1
        return node_counter_dict
        

    def print_turmas(self):
        for id in self.turmas:
            print(self.turmas[id])
