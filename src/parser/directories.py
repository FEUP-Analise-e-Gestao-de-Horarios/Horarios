import os
import sqlite3
import shutil
from core.models import Project, Person

PLACEHOLDER_ID = 0

def createDir(id: str, name: str) -> tuple[str, int]:
    '''
    Cria um novo diretório e uma nova base de dados SQLite para um projeto.

    A função cria um novo diretório chamado "Project" seguido do ID do projeto, dentro
    do diretório "database". Também cria duas bases de dados SQLite no novo diretório:
    `general_database.db` e `initial_database.db`. Executa um script SQL em ambas para
    criar a sua estrutura.
    
    Parameters:
    id (str): Username do owner do projeto
    name (str): O nome do projeto

    Returns:
    tuple[str, int]: Um tuplo contendo o path do novo diretório o ID do projeto

    Raises:
    Exception: Se o diretório já existir ou ocorrer um erro durante a criação
    do diretório ou das bases de dados. Devolve (None, None) nesse caso.

    '''
    
    try:
        Project(project = name, person = Person.objects.get(username = id)).save()

        lastId = Project.objects.values("id").get(project = name)["id"]

        myPath = "database/Project" + str(lastId)

        os.mkdir(myPath)
        path_name = "general_database.db"
        db_path = os.path.join(myPath, path_name)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        original_name = "initial_database.db"
        db_path_original = os.path.join(myPath, original_name)
        connOriginal = sqlite3.connect(db_path_original)
        cursorOriginal = connOriginal.cursor()

        # Corre o script SQL
        script_path = "database/criar.sql" 
        with open(script_path, 'r') as f:
            script = f.read()
            cursor.executescript(script)
            cursorOriginal.executescript(script)

        # Fecha a ligação à base de dados
        conn.commit()
        conn.close()

        return myPath, lastId
    except:
        print("Diretório já existe")
        return None, None


def get_directories(path: str)-> list[str]:
    '''
    Obtém uma lista de todos os diretórios dentro do path fornecido.

    Esta função percorre a árvore de diretórios do path fornecido e junta o path
    de cada diretório que encontra a uma lista.

    Parameters:
    path (str): O path onde encontrar diretórios

    Returns:
    list[str]: Uma lista de paths para cada diretório encontrado.
    Caso nenhum diretório seja encontrado, devolve uma lista vazia.
    '''
    directories = []
    for root, dirs, files in os.walk(path):
        for dir in dirs:
            directories.append(os.path.join(root, dir))
    return directories
