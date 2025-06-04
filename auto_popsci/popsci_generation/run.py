from auto_popsci.args import parse_args

# from keyfact_extraction import async_multiple_keyfacts_extraction
from .popsci_generation import (
    async_multiple_popsci_generation_from_keyfact,
    async_multiple_popsci_generation_ordinary,
)
import asyncio
from ..utils.utils import get_paper_content, get_paper_titles, save_key_facts_to_file
import os
import json


def main(args):
    """
    Main function to run AutoPopsci
    """

    # keyfact_paths = asyncio.run(async_multiple_keyfacts_extraction(args))
    # stri = "output/key_facts/the_mechanism_of_action_of_aspirin_key_facts.json"
    # keyfact_paths = [stri]
    keyfact_path = "auto_popsci/evaluation/output/dev_5/R1_ground_truth/with_priority/reference_keyfacts/"
    keyfact_paths = [
        f"{keyfact_path}{file}" for file in sorted(os.listdir(keyfact_path))
    ]
    print(f"Key fact paths: {keyfact_paths}")

    popsci_paths = asyncio.run(
        async_multiple_popsci_generation_from_keyfact(args, keyfact_paths)
    )
    # asyncio.run(async_multiple_popsci_generation_ordinary(args))


if __name__ == "__main__":
    args = parse_args()
    args.paper_mode = "dataset"
    args.dataset_format = "json"
    args.paper_path = "datasets/scinews/dev_dataset_5.json"
    args.popsci_output_dir = (
        "auto_popsci/popsci_generation/output/dev_5/popsci_from_keyfacts/"
    )
    args.is_paperbody_or_news = "All"
    args.popsci_output_dir = (
        "auto_popsci/popsci_generation/output/dev_5/popsci_from_keyfacts/"
    )
    main(args)
