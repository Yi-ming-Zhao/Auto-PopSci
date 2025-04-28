from args import parse_args
from keyfact_extraction import extract_keyfacts
import asyncio
from utils import get_paper_content


async def main(args):
    """
    Main function to run AutoPopsci
    """
    paper = get_paper_content(args.paper_path, args.paper_mode)
    key_facts = await extract_keyfacts(args, paper)
    print(key_facts)


if __name__ == "__main__":
    args = parse_args()
    print("=" * 20 + "AutoPopsci is running under following settings" + "=" * 20)
    print(args)
    asyncio.run(main(args))
