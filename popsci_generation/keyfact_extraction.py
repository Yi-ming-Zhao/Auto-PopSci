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
