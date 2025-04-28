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


def get_paper_titles(path, mode):
    """
    Reads the titles of papers from a file and returns them as a list.

    Args:
        path (str): The path to the file.
        mode (str): The mode in which to open the file (dataset or single paper).

    Returns:
        str: The title of the paper.
    """
    if mode == "dataset":
        raise NotImplementedError("Reading in dataset mode is not implemented yet.")
    elif mode == "single_paper":
        with open(path, "r") as file:
            # print("file name:", path.split("/")[-1].split(".")[0])
            return path.split("/")[-1].split(".")[0]
    else:
        raise ValueError("Invalid mode. Use 'dataset' or 'single_paper'.")


def save_key_facts_to_file(key_facts, output_dir, output_file_name):
    """
    Saves the extracted key facts to a file.

    Args:
        key_facts (list): The list of key facts to save.
        output_dir (str): The directory to save the key facts.
    """
    import os
    import json

    json_key_facts = json.loads(key_facts)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_file = os.path.join(output_dir, output_file_name)
    with open(output_file, "w") as file:
        json.dump(json_key_facts, file, indent=4)

    return output_file


def save_popsci_to_file(popsci, output_dir, output_file_name):
    """
    Saves the generated popsci to a file.

    Args:
        popsci (str): The generated popsci to save.
        output_dir (str): The directory to save the popsci.
    """
    import os
    import json

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_file = os.path.join(output_dir, output_file_name)
    with open(output_file, "w") as file:
        json.dump(popsci, file, indent=4)

    return output_file
