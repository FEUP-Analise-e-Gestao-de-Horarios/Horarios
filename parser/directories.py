import os
import sqlite3
import shutil
from core.models import Project, Person


PLACEHOLDER_ID = 0

def createDir(id, name):
    
    try:

        Project(project = name, person = Person.objects.get(username = id)).save()

        lastId = Project.objects.values("id").get(project = name)["id"]


        myPath = "database/Project" + str(lastId)

        os.mkdir(myPath)
        path_name = "general_database.db"
        original_name = "initial_database.db"
        db_path = os.path.join(myPath, path_name)
        db_path_original = os.path.join(myPath, original_name)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        connOriginal = sqlite3.connect(db_path_original)
        cursorOriginal = connOriginal.cursor()

        # Run your script to populate the database
        script_path = "database/criar.sql"  # Update file extension to .sql
        with open(script_path, 'r') as f:
            script = f.read()
            cursor.executescript(script)
            cursorOriginal.executescript(script)

        # Close the database connection
        conn.commit()
        conn.close()


        return myPath, lastId
    except:
        print("Diretório já existe")
        return None, None


def get_directories(path):
    directories = []
    for root, dirs, files in os.walk(path):
        for dir in dirs:
            directories.append(os.path.join(root, dir))
    return directories
