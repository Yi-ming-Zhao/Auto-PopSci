from ..utils.utils import async_multiple_keyfacts_extraction
from ..args import parse_args
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
    args.dataset_format = "json"
    args.paper_path = "datasets/scinews/dev_dataset_5.json"
    args.key_fact_output_dir = "auto_popsci/evaluation/output/dev_5/scinews_keyfacts/with_priority/reference_keyfacts/"
    args.is_paperbody_or_news = "News_Body"
    args.prompt_template = "key_fact_extraction_with_priority"
    main(args)
