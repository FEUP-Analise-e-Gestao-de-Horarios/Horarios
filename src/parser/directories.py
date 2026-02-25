import os
import sqlite3

from django.core.exceptions import BadRequest
from django.http import Http404

from core.models import Person, Project

PLACEHOLDER_ID = 0


def createDir(id: str, name: str) -> tuple[str, int]:
    """
    Creates a new directory and a new SQLite database for a project.

    Creates a directory named "Project" followed by the project ID inside the
    "database" directory. Also creates two SQLite databases in the new directory:
    `general_database.db` and `initial_database.db`, and runs a SQL script on both
    to set up their schema.

    Parameters:
    id (str): Username of the project owner
    name (str): The project name

    Returns:
    tuple[str, int]: A tuple containing the path of the new directory and the project ID

    Raises:
    Http404: If the user is not found.
    BadRequest: If a project with the same name already exists.
    FileNotFoundError: If the SQL script is not found.
    PermissionError: If there are no permissions to create the directory or files.
    sqlite3.DatabaseError: If a database error occurs.

    """

    try:
        Project(project=name, person=Person.objects.get(username=id)).save()

        lastId = Project.objects.values("id").get(project=name)["id"]

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

        # Run the SQL script
        script_path = "database/criar.sql"
        with open(script_path) as f:
            script = f.read()
            cursor.executescript(script)
            cursorOriginal.executescript(script)

        # Close the database connection
        conn.commit()
        conn.close()

        return myPath, lastId

    except Person.DoesNotExist as err:
        raise Http404(f"User '{id}' not found") from err

    except FileExistsError as err:
        raise BadRequest(f"A project with the name '{name}' already exists") from err

    except FileNotFoundError as err:
        raise FileNotFoundError(f"File not found: {err.filename}") from err

    except PermissionError as err:
        raise PermissionError(
            f"Permission denied when accessing '{err.filename}'"
        ) from err

    except sqlite3.DatabaseError as e:
        raise sqlite3.DatabaseError(f"Database error: {e}") from e


def get_directories(path: str) -> list[str]:
    """
    Returns a list of all directories found under the given path.

    Walks the directory tree rooted at the given path and collects the path
    of every directory found.

    Parameters:
    path (str): The root path to search for directories

    Returns:
    list[str]: A list of paths for each directory found.
    Returns an empty list if no directories are found.
    """

    return [
        os.path.join(root, dir) for root, dirs, _files in os.walk(path) for dir in dirs
    ]
