import json
from pathlib import Path


def flatten_entry(entry: dict) -> dict:
    orig_root = entry.get("original_data", {})
    orig = orig_root.get("original_data", {})
    analysis = orig_root.get("analysis", {})

    popsci = orig.get("popsci_article", {})
    wiki = orig.get("wikipedia_article", {})

    model_name = None
    model_title = None
    model_output = None
    models = entry.get("models") or {}
    for name, details in models.items():
        model_name = name
        model_title = details.get("title")
        model_output = details.get("content")
        break

    return {
        "popsci_title": popsci.get("title"),
        "popsci_content": popsci.get("content"),
        "popsci_url": popsci.get("url"),
        "wiki_title": wiki.get("title"),
        "wiki_content": wiki.get("content"),
        "wiki_url": wiki.get("url"),
        "wiki_keyfacts": wiki.get("keyfacts") or [],
        "source": orig.get("source"),
        "content_relevance_score": analysis.get("内容关联性评分"),
        "model_name": model_name,
        "model_title": model_title,
        "model_output": model_output,
    }


def main():
    src_dir = Path("baselines/qwen")
    dst_dir = Path("model_outputs/qwen")
    dst_dir.mkdir(parents=True, exist_ok=True)

    for path in sorted(src_dir.glob("*_without_finetune.json")):
        with path.open("r", encoding="utf-8") as f:
            records = json.load(f)

        flat_records = [flatten_entry(entry) for entry in records]

        out_path = dst_dir / path.name
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(flat_records, f, ensure_ascii=False, indent=2)

        jsonl_path = out_path.with_suffix(".jsonl")
        with jsonl_path.open("w", encoding="utf-8") as out:
            for record in flat_records:
                out.write(json.dumps(record, ensure_ascii=False))
                out.write("\n")


if __name__ == "__main__":
    main()
