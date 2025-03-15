from FeupScheduleEditor.models import AulaChange, AulaInfo

#A node represents an change of an class info
    #AulaChange -> old aula info and the new aula info
    #root_global -> boolean to tell if the node is the starting node of the global graph (only 1 node will have this type)
    #root_local -> boolean to tell if the node is the starting point of a local graph (e.g. the first change for an uc)
class Node:
    def __init__(self, id, change: AulaChange = None, root_local=False, root_global=False):
        self.id = id
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
        if(self.root_global):
            raise ValueError("A global root does not have any change and consequently no uc")
        else:
            return self.change.new.cadeira_id
    
    def get_turmas(self):
        if(self.root_global):
            raise ValueError("A global root does not have any change and consequently no turmas")
        else:
            return self.change.new.turmas_ids
    def output(self):
        #yet to be implemented, will provide an output for the change (considering its type)
        return

class Edge:
    def __init__(self, node1: Node, node2: Node):
        self.node1 = node1
        self.node2 = node2

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
    
    def set_attributes(self):
        if self.node1.root_global or self.node2.root_global:
            return
        
        if (self.node1.get_uc() == self.node2.get_uc()):
            self.local = True
            self.uc = True
        elif set(self.node1.get_turmas()) & set(self.node2.get_turmas()):
            self.local = True
            self.turma = True
        else:
            self.global_ = True
        #dependency attribute yet to be implemented (needs more considerations)
        