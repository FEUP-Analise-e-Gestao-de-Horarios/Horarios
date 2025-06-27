from FeupScheduleEditor.models import AulaChange, AulaInfo
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
            if edge.solution:
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


class GraphManager:
    def __init__(self, project_number, mode):
        self.root = None
        self.ucs = {}
        self.turmas = {}
        self.project_number = project_number
        self.mode = mode

        self.conflicts = set()
        self.conflicts_ucs = {}

        self.global_edges = set()
        self.global_nodes = set()
        self.unsolved_nodes = set()

        self.local_roots = []

        self.ordered_list = []

    def get_aula_details(self, project_number, aula_id):
        db_path = Path(f'./database/Project{project_number}/initial_database.db')

        try:
            connection = sqlite3.connect(str(db_path))
            cursor = connection.cursor()

            # Get basic aula information
            cursor.execute("""
                SELECT id, horaInicial, duracao, diaSemana, teorico, semanaInicial, semanaFinal
                FROM aula
                WHERE id = ?
            """, (aula_id,))
            aula_data = cursor.fetchone()

            if not aula_data:
                print(f"No aula found with id {aula_id}")
                return

            # Get associated UCs
            cursor.execute("""
                SELECT uc.codigo, uc.nome
                FROM aulaUC
                JOIN uc ON aulaUC.idUC = uc.codigo
                WHERE aulaUC.idAula = ?
            """, (aula_id,))
            ucs = cursor.fetchall()

            # Get associated salas
            cursor.execute("""
                SELECT salas.numero, salas.tipo, salas.capacidade
                FROM aulaSala
                JOIN salas ON aulaSala.idSala = salas.numero
                WHERE aulaSala.idAula = ?
            """, (aula_id,))
            salas = cursor.fetchall()

            # Get associated docentes
            cursor.execute("""
                SELECT docentes.numeroMecanografico, docentes.nome, docentes.abreviacao
                FROM aulaDocente
                JOIN docentes ON aulaDocente.idDocente = docentes.numeroMecanografico
                WHERE aulaDocente.idAula = ?
            """, (aula_id,))
            docentes = cursor.fetchall()

            # Get associated turmas
            cursor.execute("""
            SELECT turmas.codigo
            FROM aulaTurmas
            JOIN turmas ON aulaTurmas.idTurma = turmas.codigo
            WHERE aulaTurmas.idAula = ?
            """, (aula_id,))
            turmas = cursor.fetchall()

            # Format and print the information
            print("\n" + "="*50)
            print(f" DETAILS FOR AULA ID: {aula_id}")
            print("="*50)

            # Basic info
            hora_inicial = converter_horario(aula_data[1])
            hora_final = converter_horario(calculate_hora_final(str(aula_data[1]), aula_data[2]))
            print(f"\n[Basic Information]")
            print(f"  • Time: {hora_inicial} - {hora_final} ({aula_data[2]} blocks)")
            print(f"  • Day: {aula_data[3]}")
            print(f"  • Type: {'Theoretical' if aula_data[4] else 'Practical'}")
            print(f"  • Period: {aula_data[5]} to {aula_data[6]}")

            # UCs
            print("\n[Associated UCs]")
            for uc in ucs:
                print(f"  • {uc[0]} - {uc[1]}")

            # Salas
            print("\n[Associated Rooms]")
            for sala in salas:
                print(f"  • {sala[0]} ({sala[1]}, Capacity: {sala[2]})")

            # Docentes
            print("\n[Associated Professors]")
            for docente in docentes:
                print(f"  • {docente[0]}: {docente[1]} ({docente[2]})")

            # Turmas - simplified output
            print("\n[Associated Classes]")
            if turmas:
                for turma in turmas:
                    print(f"  • {turma[0]}")
            else:
                print("  • No classes associated")

            print("\n" + "="*50 + "\n")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()
    
    def get_aula_details_new(self, project_number, aula_id):
        db_path = Path(f'./database/Project{project_number}/general_database.db')

        try:
            connection = sqlite3.connect(str(db_path))
            cursor = connection.cursor()

            # Get basic aula information
            cursor.execute("""
                SELECT id, horaInicial, duracao, diaSemana, teorico, semanaInicial, semanaFinal
                FROM aula
                WHERE id = ?
            """, (aula_id,))
            aula_data = cursor.fetchone()

            if not aula_data:
                print(f"No aula found with id {aula_id}")
                return

            # Get associated UCs
            cursor.execute("""
                SELECT uc.codigo, uc.nome
                FROM aulaUC
                JOIN uc ON aulaUC.idUC = uc.codigo
                WHERE aulaUC.idAula = ?
            """, (aula_id,))
            ucs = cursor.fetchall()

            # Get associated salas
            cursor.execute("""
                SELECT salas.numero, salas.tipo, salas.capacidade
                FROM aulaSala
                JOIN salas ON aulaSala.idSala = salas.numero
                WHERE aulaSala.idAula = ?
            """, (aula_id,))
            salas = cursor.fetchall()

            # Get associated docentes
            cursor.execute("""
                SELECT docentes.numeroMecanografico, docentes.nome, docentes.abreviacao
                FROM aulaDocente
                JOIN docentes ON aulaDocente.idDocente = docentes.numeroMecanografico
                WHERE aulaDocente.idAula = ?
            """, (aula_id,))
            docentes = cursor.fetchall()

            # Get associated turmas
            cursor.execute("""
            SELECT turmas.codigo
            FROM aulaTurmas
            JOIN turmas ON aulaTurmas.idTurma = turmas.codigo
            WHERE aulaTurmas.idAula = ?
            """, (aula_id,))
            turmas = cursor.fetchall()

            # Format and print the information
            print("\n" + "="*50)
            print(f" DETAILS FOR AULA ID: {aula_id}")
            print("="*50)

            # Basic info
            hora_inicial = converter_horario(aula_data[1])
            hora_final = converter_horario(calculate_hora_final(str(aula_data[1]), aula_data[2]))
            print(f"\n[Basic Information]")
            print(f"  • Time: {hora_inicial} - {hora_final} ({aula_data[2]} blocks)")
            print(f"  • Day: {aula_data[3]}")
            print(f"  • Type: {'Theoretical' if aula_data[4] else 'Practical'}")
            print(f"  • Period: {aula_data[5]} to {aula_data[6]}")

            # UCs
            print("\n[Associated UCs]")
            for uc in ucs:
                print(f"  • {uc[0]} - {uc[1]}")

            # Salas
            print("\n[Associated Rooms]")
            for sala in salas:
                print(f"  • {sala[0]} ({sala[1]}, Capacity: {sala[2]})")

            # Docentes
            print("\n[Associated Professors]")
            for docente in docentes:
                print(f"  • {docente[0]}: {docente[1]} ({docente[2]})")

            # Turmas - simplified output
            print("\n[Associated Classes]")
            if turmas:
                for turma in turmas:
                    print(f"  • {turma[0]}")
            else:
                print("  • No classes associated")

            print("\n" + "="*50 + "\n")

        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()

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
        checker = check_aula_change_conflicts(node.change, self.project_number, self.mode)
        if checker and "red" not in checker:
            node.has_conflicts()
            node.add_dependencies(checker)
        #if "red" in checker:
        #    node.has_red_conflicts()
        uc_id = node.get_uc()
        if uc_id not in self.ucs:
            new = Graph(uc_id, 0, node.change.new.uc_name)
            self.ucs[uc_id] = new
        self.ucs[uc_id].add_node(node)
    
        for turma in node.get_turmas():
            if turma not in self.turmas:
                new = Graph(turma, 1, None)
                new.add_node(node)
                self.turmas[turma] = new
            else:
                self.turmas[turma].add_node(node)

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

