import os


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

    return [os.path.join(root, dir) for root, dirs, _files in os.walk(path) for dir in dirs]
