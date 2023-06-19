import os.path


def initialising_folders(path):
    """
    This function receive the path, detect whether the path exists, if not create it.
    And return the path itself to save as a variable
    """

    if not os.path.exists(path):
        os.makedirs(path)
    return path
