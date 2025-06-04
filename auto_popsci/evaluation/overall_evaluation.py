from ..utils.utils import cal_ppl, cal_sari, get_papers_from_dataset
from ..args import parse_args
import os
import json


def main(args):
    popsci = []
    popsci_path = "auto_popsci/popsci_generation/output/dev_5/popsci_from_keyfacts/"
    popsci_files = [f for f in os.listdir(popsci_path)]
    popsci_paths = [os.path.join(popsci_path, f) for f in popsci_files]
    print("Popsci paths:", popsci_paths)
    for i, popsci_path in enumerate(popsci_paths):
        with open(popsci_path, "r") as f:
            popsci_data = f.read()
            popsci.append(popsci_data)
            print(f"Popsci {i + 1} content: {popsci_data}")
    print(f"Number of popsci: {len(popsci)}")

    papers, titles, news = get_papers_from_dataset(
        args.paper_path, args.dataset_format, args.is_paperbody_or_news
    )
    result = []
    for i, popsci_text in enumerate(popsci):
        print(f"Popsci {i + 1} text: {popsci_text}")
        print(f"Paper title {i + 1}: {titles[i]}")
        print(f"Paper content {i + 1}: {papers[i]}")
        print(f"News content {i + 1}: {news[i]}")
        # Calculate SARI score
        sari_score = cal_sari(popsci_text, papers[i], titles[i])
        print(f"SARI score for popsci {i + 1}: {sari_score}")
        # Calculate perplexity
        ppl_score = cal_ppl(popsci_text)
        print(f"Perplexity score for popsci {i + 1}: {ppl_score}")
        result.append(
            {
                "title": titles[i],
                "popsci_text": popsci_text,
                "sari_score": sari_score,
                "ppl_score": ppl_score,
            }
        )
        with open(
            "auto_popsci/evaluation/output/dev_5/popsci_evaluation.json", "w"
        ) as f:
            json.dump(result, f, indent=4)


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
