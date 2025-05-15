from keyfact_extraction import async_multiple_keyfacts_extraction
from args import parse_args
import asyncio


def main(args):
    """
    Main function to run keyfacts extraction
    """

    # Extract key facts from the paper
    asyncio.run(async_multiple_keyfacts_extraction(args))


if __name__ == "__main__":
    args = parse_args()
    args.paper_mode = "dataset"
    args.paper_path = "datasets/scinews/dev_dataset_5.json"
    args.key_fact_output_dir = "evaluation/reference_keyfacts/"
    main(args)
