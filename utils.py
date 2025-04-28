def read_yaml_file(file_path):
    """
    Reads a YAML file and returns its content as a dictionary.

    Args:
        file_path (str): The path to the YAML file.

    Returns:
        dict: The content of the YAML file.
    """
    import yaml

    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def get_paper_content(path, mode):
    """
    Reads the content of a file and returns it as a string.

    Args:
        path (str): The path to the file.
        mode (str): The mode in which to open the file (dataset or single paper).

    Returns:
        str: The content of the file.
    """
    if mode == "dataset":
        raise NotImplementedError("Reading in dataset mode is not implemented yet.")
    elif mode == "single_paper":
        with open(path, "r") as file:
            return file.read()
    else:
        raise ValueError("Invalid mode. Use 'dataset' or 'single_paper'.")
