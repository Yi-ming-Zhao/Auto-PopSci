from utils.utils import (
    read_yaml_file,
    get_paper_titles,
    get_paper_content,
    save_key_facts_to_file,
)
import asyncio
from prompts.prompt_template import prompt
from openai import AsyncOpenAI
from pprint import pprint
import time
import json


async def generate_popsci_ordinary(args, paper, paper_title):
    """
    Generate popsci from the provided paper, with out plotting.
    Output should be a list of popsci, each popsci should be formatted as a dictionary with the following keys: "title", "content".
    """
    start_time = time.time()
    print(f"Generating popsci from the paper: {paper_title}")
    auth_info = read_yaml_file("auth.yaml")
    current_api_key = auth_info[args.llm_type][args.model_type]["api_key"]
    current_base_url = auth_info[args.llm_type][args.model_type]["base_url"]
    current_model = auth_info[args.llm_type][args.model_type]["model"]
    client = AsyncOpenAI(api_key=current_api_key, base_url=current_base_url)
    prompt_text = prompt["popsci_generation_ordinary"].format(paper=paper)

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
        print(f"Popsci generation result: {result}")
        end_time = time.time()
        print(f"Popsci generation took {end_time - start_time:.2f} seconds.")
        return result
    else:
        return "No popsci generated."


async def async_multiple_popsci_generation_ordinary(args):
    """
    Generates popsci from the provided paper, with out plotting.
    """
    # get popsci from the paper
    papers = []
    paper_titles = []
    if args.paper_mode == "dataset":
        raise NotImplementedError("Reading in dataset mode is not implemented yet.")
    elif args.paper_mode == "single_paper":
        body = get_paper_content(args.paper_path, args.paper_mode)
        papers.append(body)
        title = get_paper_titles(args.paper_path, args.paper_mode)
        paper_titles.append(title)
    else:
        raise ValueError("Invalid mode. Use 'dataset' or 'single_paper'.")

    for i, paper in enumerate(papers):
        paper_title = paper_titles[i]
        popsci = await generate_popsci_ordinary(args, paper, paper_title)
        save_key_facts_to_file(
            popsci, args.popsci_output_dir, f"{paper_title}_ordinary_popsci.json"
        )


async def generate_popsci_from_keyfacts(args, key_facts, paper_title, paper):
    """
    Generate popsci from the provided key facts.
    Output should be a list of popsci, each popsci should be formatted as a dictionary with the following keys: "title", "content".
    """
    start_time = time.time()
    print(f"Generating popsci from the key facts: {paper_title}")
    auth_info = read_yaml_file("auth.yaml")
    current_api_key = auth_info[args.llm_type][args.model_type]["api_key"]
    current_base_url = auth_info[args.llm_type][args.model_type]["base_url"]
    current_model = auth_info[args.llm_type][args.model_type]["model"]
    client = AsyncOpenAI(api_key=current_api_key, base_url=current_base_url)
    prompt_text = prompt["popsci_generation_from_keyfacts"].format(
        key_facts=key_facts, paper=paper
    )

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
        print(f"Popsci generation result: {result}")
        end_time = time.time()
        print(f"Popsci generation took {end_time - start_time:.2f} seconds.")
        return result
    else:
        return "No popsci generated."


async def async_multiple_popsci_generation_from_keyfact(args, key_fact_paths):
    """
    Generates popsci from the provided key facts.
    """
    # get popsci from the key facts
    papers = []
    paper_titles = []
    if args.paper_mode == "dataset":
        raise NotImplementedError("Reading in dataset mode is not implemented yet.")
    elif args.paper_mode == "single_paper":
        body = get_paper_content(args.paper_path, args.paper_mode)
        papers.append(body)
        title = get_paper_titles(args.paper_path, args.paper_mode)
        paper_titles.append(title)
    else:
        raise ValueError("Invalid mode. Use 'dataset' or 'single_paper'.")

    for i, paper in enumerate(papers):
        key_fact_path = key_fact_paths[i]
        with open(key_fact_path, "r") as file:
            key_facts = json.load(file)
        paper_title = paper_titles[i]
        popsci = await generate_popsci_from_keyfacts(
            args, key_facts, paper_title, paper
        )
        save_key_facts_to_file(
            popsci, args.popsci_output_dir, f"{paper_title}_popsci.json"
        )
