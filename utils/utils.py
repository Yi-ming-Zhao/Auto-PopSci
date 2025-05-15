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
    import pandas as pd
    import tqdm

    if mode == "dataset":
        with open(path, "r") as file:
            df = pd.read_parquet(file)
            # Remove rows with NaN values in the 'paper_url' column
            df = df.dropna(subset=["paper_content"])
            # Select specific columns
            selected_columns = df[["title", "paper_content", "content"]]
            # Convert to string
            return selected_columns
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


async def extract_keyfacts(args, paper, paper_title):
    """
    Extract keyfacts from the provided paper.
    Output should be a list of key facts, each fact should be formatted as a dictionary with the following keys: "entity", "behavior", "context".
    """
    start_time = time.time()
    print(f"Extracting key facts from the paper: {paper_title}")
    auth_info = read_yaml_file("auth.yaml")
    current_api_key = auth_info[args.llm_type][args.model_type]["api_key"]
    current_base_url = auth_info[args.llm_type][args.model_type]["base_url"]
    current_model = auth_info[args.llm_type][args.model_type]["model"]
    client = AsyncOpenAI(
        api_key=current_api_key,
        base_url=current_base_url,
    )
    prompt_text = prompt["key_fact_extraction"].format(paper=paper)
    # print(prompt_text)
    try:
        response = await client.chat.completions.create(
            model=current_model,
            messages=[
                {
                    "role": "user",
                    "content": prompt_text,
                }
            ],
        )
    except Exception as e:
        print(f"Error: {e}")
        return "API connection Error: " + str(e)

    if response and response.choices:
        result = response.choices[0].message.content
        print(f"Key facts extraction result: {result}")
        end_time = time.time()
        print(f"Key facts extraction took {end_time - start_time:.2f} seconds.")
        return result
    else:
        return "No keyfacts found."


async def async_multiple_keyfacts_extraction(args):
    """
    Saves the extracted key facts to a file.
    """
    # get key facts from the paper
    papers = []
    paper_titles = []
    keyfacts_paths = []
    if args.paper_mode == "dataset":
        raise NotImplementedError("Reading in dataset mode is not implemented yet.")
    elif args.paper_mode == "single_paper":
        body = get_paper_content(args.paper_path, args.paper_mode)
        papers.append(body)
        title = get_paper_titles(args.paper_path, args.paper_mode)
        paper_titles.append(title)
    else:
        raise ValueError("Invalid mode. Use 'dataset' or 'single_paper'.")
    key_facts_extraction_tasks = [
        extract_keyfacts(args, paper, paper_titles[i]) for i, paper in enumerate(papers)
    ]
    key_facts_of_papers = await asyncio.gather(*key_facts_extraction_tasks)

    for i, key_facts in enumerate(key_facts_of_papers):
        output_file_name = f"{paper_titles[i]}_key_facts.json"
        current_keyfacts_path = save_key_facts_to_file(
            key_facts, args.key_fact_output_dir, output_file_name
        )
        keyfacts_paths.append(current_keyfacts_path)
        print(f"Key facts for paper {i} saved to {current_keyfacts_path}")

    return keyfacts_paths
