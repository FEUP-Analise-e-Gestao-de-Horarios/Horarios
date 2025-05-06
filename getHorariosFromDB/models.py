from FeupScheduleEditor.models import AulaChange, AulaInfo
from .auxiliar_functions import *

#A node represents an change of an class info
    #AulaChange -> old aula info and the new aula info
    #root_global -> boolean to tell if the node is the starting node of the global graph (only 1 node will have this type)
    #root_local -> boolean to tell if the node is the starting point of a local graph (e.g. the first change for an uc)
class Node:
    def __init__(self, change: AulaChange = None, root_local=False, root_global=False):
        self.id = generate_node_id()
        self.root_local = root_local
        self.root_global = root_global
        self.dependency_ids = []

        if root_local and root_global:
            raise ValueError("A node cannot be both root_local and root_global.")
        
        if change is None and not root_global:
            raise ValueError("Non-global nodes must have a change.")
        
        self.change = change
        self.conflict = False
    
    def has_conflicts(self, value=True):
        self.conflict = value
    
    def add_dependencies(self, ids):
        for dep_id in ids:
            if dep_id not in self.dependency_ids:
                self.dependency_ids.append(dep_id)
    
    def is_local_root(self, value=True):
        self.root_local = value
    
    def get_uc(self):
        if(self.root_global or not self.check_uc()):
            raise ValueError("Change from one uc to another?")
        else:
            return str(self.change.new.cadeira_id)
    
    def check_uc(self):
        return self.change.previous.cadeira_id == self.change.new.cadeira_id
  
    def get_turmas(self):
        if(self.root_global):
            raise ValueError("A global root does not have any change and consequently no turmas")
        else:
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
        self.id = identifier  # UC or Turma ID
        self.root = None

        self.nodes = set()  # Nodes that belong to this subgraph
        self.edges = []

        self.unsolved_nodes = set()
        self.type = type    #0 for uc and 1 for turma
        self.uc_name = uc_name
        self.ordered_list = set()

        self.original = None

    def add_node(self, node):
        if node not in self.nodes:
            self.nodes.add(node)

    def remove_node(self, node):
        if node in self.nodes:
            self.nodes.remove(node)
            # Remove edges involving this node
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
        if node in self.ordered_list:
            print("In the ordered_list")
        elif node in self.nodes:
            print("In the nodes")
        elif node in self.unsolved_nodes:
            print("In the unsolved_nodes")
        else:
            print("Not found")
        edges = self.get_node_edges(node)
        if node not in self.ordered_list:
            self.nodes.remove(node)
            self.ordered_list.add(node)
        for edge in edges:
            cur = edge.node1
            if edge.node1.id == node.id:
                cur = edge.node2
            cur.has_conflicts(value=False)
            self.edges.remove(edge)
            self.follow_dependency(cur)

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

class ConflictManager:
    def __init__(self):
        self.current = set()
    def update(self, change: AulaChange):
        self.current.add(change.new)

class GraphManager:
    def __init__(self, project_number):
        self.root = None
        self.ucs = {}
        self.turmas = {}
        self.project_number = project_number

        self.conflicts = set()
        self.conflicts_ucs = {}

        self.global_edges = set()
        self.global_nodes = set()
        self.unsolved_nodes = set()

        self.local_roots = []

        self.ordered_list = []
    
    def add_node(self, node: Node):
        checker = check_aula_change_conflicts(node.change, self.project_number)
        if checker:
            print("IM HERE")
            node.has_conflicts()
            node.add_dependencies(checker)
            
        uc_id = node.get_uc()  # Get the UC ID first
        if uc_id not in self.ucs:
            new = Graph(uc_id, 0, node.change.new.uc_name)
            print(f"{node.change.new.uc_name}")
            self.ucs[uc_id] = new
            print(f"Created new subgraph for UC {uc_id}")  # Use uc_id instead of id
        self.ucs[uc_id].add_node(node)
    
        for turma in node.get_turmas():
            if turma not in self.turmas:
                new = Graph(turma, 1, None)
                new.add_node(node)
                self.turmas[turma] = new
            else:
                self.turmas[turma].add_node(node)

    def order_ucs(self):
        # Filter keys not already in ordered_list
        remaining_keys = [key for key in self.ucs if key not in self.ordered_list]

        # Sort by the number of unsolved nodes (ascending)
        sorted_keys = sorted(remaining_keys, key=lambda k: len(self.ucs[k].unsolved_nodes))

        # Extend ordered_list with the sorted keys
        self.ordered_list.extend(sorted_keys)


    def print_conflicts(self):
        for id in self.ucs:
            aux = 0
            graph = self.ucs[id]
            for node in graph.nodes:
                if node.conflict:
                    aux+=1
            print(f"Total nodes: {len(graph.nodes)}\n")
            print(f"Number of conflicts: {aux}\n")

    def create_local_edges(self):
        for key in self.ucs:
            graph = self.ucs[key]
            graph.create_edges()
            self.global_nodes.update(graph.unsolved_nodes)
    
    def update_local_edges(self):
        for key in self.ucs:
            graph = self.ucs[key]
            graph.update_list()
    
    def create_global_edges(self):
        for node in self.global_nodes:
            for tmp in self.global_nodes:
                    for id in node.dependency_ids:
                        if tmp.change.previous.id == id:
                            edge = Edge(node, tmp)
                            edge.dependency = True
                            edge.uc = True
                            node.dependency_ids.remove(id)
                        else:
                            self.unsolved_nodes.add(tmp)

    def get_unsolved_conflicts(self):
        """Will get all the nodes from all the graphs with unsolved conflicts and stores them in the class"""
        
    def add_edges(self):
        """This function will add the global edges to the unsolved conflicts in the class nodes"""
    
    def print_ucs(self):
        print("Before order:")
        for id in self.ucs:
            print(self.ucs[id])
        print("After order:")
        for uc in self.ordered_list:
            print(self.ucs[uc])
        

    def print_turmas(self):
        for id in self.turmas:
            print(self.turmas[id])
    
