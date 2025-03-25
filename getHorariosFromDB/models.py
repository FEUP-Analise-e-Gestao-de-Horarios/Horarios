from FeupScheduleEditor.models import AulaChange, AulaInfo
import sqlite3

def generate_node_id():
    """Generates a unique numeric node id on each call."""
    if not hasattr(generate_node_id, "counter"):
        generate_node_id.counter = 0  # Initialize the counter
    node_id = generate_node_id.counter
    generate_node_id.counter += 1
    return node_id

#A node represents an change of an class info
    #AulaChange -> old aula info and the new aula info
    #root_global -> boolean to tell if the node is the starting node of the global graph (only 1 node will have this type)
    #root_local -> boolean to tell if the node is the starting point of a local graph (e.g. the first change for an uc)
class Node:
    def __init__(self, change: AulaChange = None, root_local=False, root_global=False):
        self.id = generate_node_id()
        self.root_local = root_local
        self.root_global = root_global

        if root_local and root_global:
            raise ValueError("A node cannot be both root_local and root_global.")
        
        if change is None and not root_global:
            raise ValueError("Non-global nodes must have a change.")

        self.change = change
    
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
        self.global_ = False

        self.uc = False
        self.turma = False
        
        self.directed = False
        self.direction = 0
    
    def set_direction(self, direction):
        self.directed = True
        self.direction = direction
    
    def remove_direction(self):
        self.directed = False
        self.direction = 0
    
    def __str__(self):
        """Human-readable string representation of the edge."""
        return (f"Edge(node1={self.node1}, node2={self.node2}, "
                f"local={self.local}, global_={self.global_}, uc={self.uc}, turma={self.turma})")
    
class Graph:
    def __init__(self, identifier: str, type: int):
        self.id = identifier  # UC or Turma ID
        self.root = None
        self.nodes = set()  # Nodes that belong to this subgraph
        self.edges = set()
        self.type = type #0 for uc and 1 for turma
        self.uc_name = None

    def add_node(self, node):
        if node not in self.nodes:
            # Add the node
            self.nodes.add(node)

            # Create edges with existing nodes
            for existing_node in self.nodes:
                if existing_node != node:  # Avoid self-loops
                    edge = Edge(node, existing_node)
                    edge.local = True
                    if self.type == 0:
                        edge.uc = True
                    else:
                        edge.turma = True
                    self.edges.add(edge)

    def remove_node(self, node):
        """Remove a node and related edges."""
        if node in self.nodes:
            self.nodes.remove(node)
            # Remove edges involving this node
            self.edges = [edge for edge in self.edges if node not in (edge.node1, edge.node2)]
    
    def get_edges_node(self, node):
        """Return a list of edges that include the given node."""
        return [edge for edge in self.edges if edge.node1 == node or edge.node2 == node]

    def get_unsolved_nodes(self):
        """Will return a list/set of nodes that have conflicts that cant be resolved within the graph """
    
    def __str__(self):
        """Human-readable string representation of the Graph."""
        # First print the graph ID
        graph_info = f"Graph ID: {self.uc_name}\n"
        
        # Then print all the nodes in the graph
        graph_info += "Nodes:\n"
        for node in self.nodes:
            graph_info += f"  {node}\n"  # Assuming Node has a __str__ method that provides useful info
            graph_info += "Edges (start):\n"
            for edge in self.get_edges_node(node):
                graph_info += f"  {edge}\n"
            graph_info += "Edges (end):\n"
        return graph_info
    
class GraphManager:
    def __init__(self):
        self.root = None
        self.ucs = {}
        self.turmas = {}


        self.global_edges = []
        self.global_nodes = []

        self.local_roots = []
    
    def add_node(self, node: Node):
        if node.get_uc() not in self.ucs:
            new = Graph(node.get_uc(), 0)

            new.uc_name = node.change.previous.uc_name
            self.ucs[node.get_uc()] = new
            print(f"Created new subgraph for UC {id}")

        for turma in node.get_turmas():
            if turma not in self.turmas:
                new = Graph(turma, 1)
                new.add_node(node)
                self.turmas[turma] = new
            else:
                self.turmas[turma].add_node(node)
        self.ucs[node.get_uc()].add_node(node)
    
    def get_unsolved_conflicts(self):
        """Will get all the nodes from all the graphs with unsolved conflicts and stores them in the class"""
        
    def add_edges(self):
        """This function will add the global edges to the unsolved conflicts in the class nodes"""
    
    def print_ucs(self):
        for id in self.ucs:
            print(self.ucs[id])
    def print_turmas(self):
        for id in self.turmas:
            print(self.turmas[id])
    
