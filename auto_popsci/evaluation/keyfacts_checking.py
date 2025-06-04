import json
import asyncio
import aiofiles
from openai import AsyncOpenAI
from prompts.prompt_template import prompt
from pprint import pprint
import os
import time
from ..utils.utils import read_yaml_file
from ..args import parse_args


async def get_llm_response(client, prompt_text, current_model):
    """
    Get the response from the LLM.

    Args:
        client (AsyncOpenAI): The OpenAI client.
        prompt_text (str): The prompt text to send to the LLM.
        current_model (str): The model to use.

    Returns:
        str: The response from the LLM.
    """
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
        return result
    else:
        return "No keyfacts found."


async def async_single_paper_keyfacts_precision_calculation(
    ground_truth_path, keyfact_path, args
):
    """
    Calculate the precision of key facts extraction.

    Args:
        ground_truth_path (str): Path to the ground truth key facts file.
        keyfact_path (str): Path to the extracted key facts file.

    Returns:
        float: Precision score.
    """
    async with aiofiles.open(ground_truth_path, "r") as f:
        ground_truth = await f.read()

    async with aiofiles.open(keyfact_path, "r") as f:
        keyfacts = await f.read()

    # Convert JSON strings to dictionaries
    ground_truth_dict = json.loads(ground_truth)
    keyfacts_dict = json.loads(keyfacts)

    tp_plus_fp_overall = len(keyfacts_dict)

    ground_truth_priority_1 = [
        item for item in ground_truth_dict if item["priority"] == 1
    ]
    keyfacts_priority_1 = [item for item in keyfacts_dict if item["priority"] == 1]

    ground_truth_priority_2 = [
        item for item in ground_truth_dict if item["priority"] == 2
    ]
    keyfacts_priority_2 = [item for item in keyfacts_dict if item["priority"] == 2]

    ground_truth_priority_3 = [
        item for item in ground_truth_dict if item["priority"] == 3
    ]
    keyfacts_priority_3 = [item for item in keyfacts_dict if item["priority"] == 3]

    tp_plus_fp_1 = len(keyfacts_priority_1)
    tp_plus_fp_2 = len(keyfacts_priority_2)
    tp_plus_fp_3 = len(keyfacts_priority_3)

    tasks = []
    auth_info = read_yaml_file("auto_popsci/auth.yaml")
    current_api_key = auth_info[args.llm_type][args.model_type]["api_key"]
    current_base_url = auth_info[args.llm_type][args.model_type]["base_url"]
    current_model = auth_info[args.llm_type][args.model_type]["model"]
    client = AsyncOpenAI(
        api_key=current_api_key,
        base_url=current_base_url,
    )
    for i in range(3):
        if i == 0:
            ground_truth = ground_truth_priority_1
            keyfacts = keyfacts_priority_1
        elif i == 1:
            ground_truth = ground_truth_priority_2
            keyfacts = keyfacts_priority_2
        else:
            ground_truth = ground_truth_priority_3
            keyfacts = keyfacts_priority_3

        tasks.append(
            get_llm_response(
                client,
                prompt_text=prompt[args.prompt_template].format(
                    ground_truth_key_facts=ground_truth, generated_key_facts=keyfacts
                ),
                current_model=current_model,
            )
        )
    tasks.append(
        get_llm_response(
            client,
            prompt_text=prompt[args.prompt_template].format(
                ground_truth_key_facts=ground_truth_dict,
                generated_key_facts=keyfacts_dict,
            ),
            current_model=current_model,
        )
    )
    responses = await asyncio.gather(*tasks)
    for i, response in enumerate(responses):
        if i == 0:
            parsed_response = json.loads(response)
            tp_1 = len(parsed_response)
        elif i == 1:
            parsed_response = json.loads(response)
            tp_2 = len(parsed_response)
        elif i == 2:
            parsed_response = json.loads(response)
            tp_3 = len(parsed_response)
        else:
            parsed_response = json.loads(response)
            tp_overall = len(parsed_response)

    precisions = {
        "priority_1": tp_1 / tp_plus_fp_1 if tp_plus_fp_1 > 0 else -1,
        "priority_2": tp_2 / tp_plus_fp_2 if tp_plus_fp_2 > 0 else -1,
        "priority_3": tp_3 / tp_plus_fp_3 if tp_plus_fp_3 > 0 else -1,
        "overall": tp_overall / tp_plus_fp_overall if tp_plus_fp_overall > 0 else -1,
    }
    recalls = {
        "priority_1": (
            tp_1 / len(ground_truth_priority_1)
            if len(ground_truth_priority_1) > 0
            else -1
        ),
        "priority_2": (
            tp_2 / len(ground_truth_priority_2)
            if len(ground_truth_priority_2) > 0
            else -1
        ),
        "priority_3": (
            tp_3 / len(ground_truth_priority_3)
            if len(ground_truth_priority_3) > 0
            else -1
        ),
        "overall": (
            tp_overall / len(ground_truth_dict) if len(ground_truth_dict) > 0 else -1
        ),
    }
    print(f"Recalls for paper: {recalls}")
    print(f"Precision for paper: {precisions}")
    res = {
        "recalls": recalls,
        "precisions": precisions,
    }
    return res


async def async_multiple_keyfacts_precision_calculation(
    ground_truth_paths, keyfact_paths, args
):
    """
    Calculate the precision of key facts extraction for multiple papers.

    Args:
        ground_truth_path (str): Path to the ground truth key facts file.
        keyfact_paths (list): List of paths to the extracted key facts files.

    Returns:
        list: List of precision scores for each paper.
    """
    precision_scores = []
    tasks = []
    for i, keyfact_path in enumerate(keyfact_paths):
        print(f"Calculating precision for paper {i + 1}/{len(keyfact_paths)}")
        tasks.append(
            async_single_paper_keyfacts_precision_calculation(
                ground_truth_paths[i], keyfact_path, args
            )
        )
    scores = await asyncio.gather(*tasks)
    return scores


async def main(args):
    """
    Main function to run the precision calculation.
    """
    ground_truth_path = "auto_popsci/evaluation/output/dev_5/R1_ground_truth/with_priority/reference_keyfacts/"
    keyfact_path = "auto_popsci/evaluation/output/dev_5/scinews_keyfacts/with_priority/reference_keyfacts/"

    # List of ground truth paths
    ground_truth_files = [
        f for f in os.listdir(ground_truth_path) if f.endswith(".json")
    ]
    keyfact_files = [f for f in os.listdir(keyfact_path) if f.endswith(".json")]
    print("Ground truth files:", ground_truth_files)
    print("Key fact files:", keyfact_files)

    # Ensure both lists are of the same length
    if len(ground_truth_files) != len(keyfact_files):
        raise ValueError("Mismatch in number of ground truth and key fact files.")
    ground_truth_paths = [
        os.path.join(ground_truth_path, f) for f in ground_truth_files
    ]
    keyfact_paths = [os.path.join(keyfact_path, f) for f in keyfact_files]
    print("Ground truth paths:", ground_truth_paths)
    print("Key fact paths:", keyfact_paths)
    # Calculate precision scores
    scores = await async_multiple_keyfacts_precision_calculation(
        ground_truth_paths, keyfact_paths, args
    )
    # Print precision scores
    for i, score in enumerate(scores):
        print(f"Precision for paper {i + 1}: ", score["precisions"])
        print(f"Recall for paper {i + 1}: ", score["recalls"])

    # Save precision scores to a file
    output_file = os.path.join(
        "auto_popsci/evaluation/output/dev_5/", "precision_scores.json"
    )

    with open(output_file, "w") as f:
        json.dump(
            scores,
            f,
            indent=4,
        )
    print(f"Precision scores saved to {output_file}")


if __name__ == "__main__":
    args = parse_args()
    args.prompt_template = "keyfact_alignment"
    asyncio.run(main(args))
