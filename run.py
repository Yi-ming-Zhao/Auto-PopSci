from args import parse_args
from keyfact_extraction import async_multiple_keyfacts_extraction
from popsci_generation import async_multiple_popsci_generation
import asyncio
from utils import get_paper_content, get_paper_titles, save_key_facts_to_file


def main(args):
    """
    Main function to run AutoPopsci
    """

    # keyfact_paths = asyncio.run(async_multiple_keyfacts_extraction(args))
    stri = "output/key_facts/the_mechanism_of_action_of_aspirin_key_facts.json"
    keyfact_paths = [stri]

    popsci_paths = asyncio.run(async_multiple_popsci_generation(args, keyfact_paths))


if __name__ == "__main__":
    args = parse_args()
    main(args)
