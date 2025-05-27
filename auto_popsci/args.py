import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="args.")

    parser.add_argument(
        "--llm_type", type=str, default="deepseek", help="Type of LLM to use."
    )
    parser.add_argument(
        "--model_type", type=str, default="reasoner", help="Type of the model to use."
    )

    parser.add_argument(
        "--language", type=str, default="en", help="Language of the popsci."
    )
    parser.add_argument(
        "--paper_path",
        type=str,
        default="datasets/examples/the_mechanism_of_action_of_aspirin.txt",
        help="Path to the paper file.",
    )
    parser.add_argument(
        "--paper_mode",
        type=str,
        default="single_paper",
        choices=["dataset", "single_paper"],
        help="Mode of the paper file (dataset or single paper).",
    )
    parser.add_argument(
        "--dataset_format",
        type=str,
        default="json",
        help="Format of the dataset",
    )
    parser.add_argument(
        "--prompt_template",
        type=str,
        help="Name of the prompt template in prompts/prompt_template.json",
    )
    parser.add_argument(
        "--key_fact_output_dir",
        type=str,
        default="output/key_facts/",
        help="Directory to save the extracted key facts.",
    )
    parser.add_argument(
        "--popsci_output_dir",
        type=str,
        default="output/popsci/",
        help="Directory to save the generated popsci.",
    )
    parser.add_argument(
        "--is_paperbody_or_news",
        type=str,
        default="Paper_Body",
        choices=["Paper_Body", "News_Body"],
        help="Whether the input of keyfact extraction is a paper body or a news body.",
    )
    args = parser.parse_args()
    return args
