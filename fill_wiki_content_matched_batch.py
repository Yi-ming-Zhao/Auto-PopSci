#!/usr/bin/env python3
import argparse
import json
import re
import sys
import tempfile
import time
from pathlib import Path

import requests
import yaml


SECTION_HEADING_RE = re.compile(r"\n(==\s*[^=\n][^=\n]*\s*==)\n")
DEFAULT_MODEL_PROVIDER = "glm"
DEFAULT_MODEL_KEY = "GLM-4.6V-FlashX"
TERMINAL_BATCH_STATES = {"completed", "failed", "expired", "cancelled"}


def load_auth_config(auth_path: Path, provider: str, model_key: str) -> dict:
    with auth_path.open("r", encoding="utf-8") as fh:
        auth = yaml.safe_load(fh)

    try:
        config = auth[provider][model_key]
    except Exception as exc:
        raise KeyError(
            f"Missing auth.yaml entry for provider={provider!r}, model_key={model_key!r}"
        ) from exc

    required = ("api_key", "base_url", "model")
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise ValueError(f"auth.yaml is missing required fields for {model_key}: {missing}")
    return config


def split_wiki_sections(wiki_content: str) -> list[dict]:
    sections = []
    matches = list(SECTION_HEADING_RE.finditer(wiki_content))

    if not matches:
        stripped = wiki_content.strip()
        if stripped:
            sections.append({"heading": None, "content": stripped})
        return sections

    lead = wiki_content[: matches[0].start()].strip()
    if lead:
        sections.append({"heading": None, "content": lead})

    for idx, match in enumerate(matches):
        heading = match.group(1).strip()
        section_start = match.end()
        section_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(wiki_content)
        content = wiki_content[section_start:section_end].strip()
        sections.append({"heading": heading, "content": content})

    return sections


def build_prompt(record: dict, sections: list[dict]) -> str:
    rubric = (
        "You score how relevant each Wikipedia section is to the popular-science article.\n"
        "Use a lenient scale.\n"
        "10 = same main topic/event and strongly overlapping core content.\n"
        "9 = clearly matching and highly relevant even if not identical.\n"
        "7-8 = same entity/topic with meaningful background overlap.\n"
        "4-6 = partially relevant or tangential.\n"
        "1-3 = weak relevance.\n"
        "0 = unrelated or mostly meta/reference/link material.\n"
    )
    output_spec = (
        'Return JSON only in this exact shape: {"scores":[{"index":0,"score":10}]}\n'
        "The scores array must contain exactly one item for each section index below.\n"
        "Each score must be an integer from 0 to 10.\n"
        "Do not include explanations or markdown fences.\n"
    )
    payload = {
        "popsci_title": record["popsci_title"],
        "popsci_content": record["popsci_content"],
        "wiki_title": record["wiki_title"],
        "sections": [
            {"index": idx, "heading": section["heading"], "content": section["content"]}
            for idx, section in enumerate(sections)
        ],
    }
    return "\n".join([rubric, output_spec, json.dumps(payload, ensure_ascii=False)])


def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


class BigModelBatchClient:
    def __init__(self, api_key: str, base_url: str, timeout: int) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def upload_file(self, file_path: Path) -> dict:
        with file_path.open("rb") as fh:
            response = self.session.post(
                f"{self.base_url}/files",
                files={"file": (file_path.name, fh, "application/jsonl")},
                data={"purpose": "batch"},
                timeout=self.timeout,
            )
        response.raise_for_status()
        return response.json()

    def create_batch(self, input_file_id: str, metadata: dict) -> dict:
        response = self.session.post(
            f"{self.base_url}/batches",
            headers={"Content-Type": "application/json"},
            data=json.dumps(
                {
                    "input_file_id": input_file_id,
                    "endpoint": "/v4/chat/completions",
                    "auto_delete_input_file": True,
                    "metadata": metadata,
                }
            ),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def retrieve_batch(self, batch_id: str) -> dict:
        response = self.session.get(
            f"{self.base_url}/batches/{batch_id}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def download_file(self, file_id: str, output_path: Path) -> None:
        with self.session.get(
            f"{self.base_url}/files/{file_id}/content",
            timeout=self.timeout,
            stream=True,
        ) as response:
            response.raise_for_status()
            with output_path.open("wb") as fh:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        fh.write(chunk)


def create_batch_input(
    dataset_path: Path,
    temp_dir: Path,
    model_name: str,
) -> tuple[Path, list[dict], dict]:
    records = []
    batch_input_path = temp_dir / f"{dataset_path.stem}.batch-input.jsonl"
    with dataset_path.open("r", encoding="utf-8") as src, batch_input_path.open(
        "w", encoding="utf-8"
    ) as out:
        for line_idx, line in enumerate(src):
            record = json.loads(line)
            sections = split_wiki_sections(record["wiki_content"])
            if not sections:
                raise ValueError(f"{dataset_path} line {line_idx + 1} has no wiki sections")
            custom_id = f"{dataset_path.stem}:{line_idx}"
            records.append(
                {
                    "custom_id": custom_id,
                    "line_idx": line_idx,
                    "record": record,
                    "sections": sections,
                }
            )
            request_obj = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v4/chat/completions",
                "body": {
                    "model": model_name,
                    "messages": [{"role": "user", "content": build_prompt(record, sections)}],
                    "temperature": 0.0,
                },
            }
            out.write(json.dumps(request_obj, ensure_ascii=False))
            out.write("\n")
    metadata = {
        "description": f"Fill wiki_content_matched for {dataset_path.name}",
        "project": "auto-popsci-wiki-content-matched",
        "dataset_file": dataset_path.name,
    }
    return batch_input_path, records, metadata


def wait_for_batch(client: BigModelBatchClient, batch_id: str, poll_interval: int) -> dict:
    while True:
        batch = client.retrieve_batch(batch_id)
        status = batch["status"]
        print(f"Batch {batch_id} status: {status}")
        if status in TERMINAL_BATCH_STATES:
            return batch
        time.sleep(poll_interval)


def parse_scores(raw_text: str, expected_count: int, custom_id: str) -> list[int]:
    cleaned = strip_code_fences(raw_text)
    payload = json.loads(cleaned)
    scores = payload.get("scores")
    if not isinstance(scores, list) or len(scores) != expected_count:
        raise ValueError(
            f"{custom_id}: expected {expected_count} scores, got {len(scores) if isinstance(scores, list) else 'invalid'}"
        )

    parsed_scores = [None] * expected_count
    for item in scores:
        if not isinstance(item, dict):
            raise ValueError(f"{custom_id}: invalid score item {item!r}")
        index = item.get("index")
        score = item.get("score")
        if not isinstance(index, int) or not 0 <= index < expected_count:
            raise ValueError(f"{custom_id}: invalid section index {index!r}")
        if not isinstance(score, int) or not 0 <= score <= 10:
            raise ValueError(f"{custom_id}: invalid score {score!r}")
        parsed_scores[index] = score

    if any(score is None for score in parsed_scores):
        raise ValueError(f"{custom_id}: missing scores for some sections")
    return parsed_scores


def load_batch_outputs(output_path: Path) -> dict:
    outputs = {}
    with output_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            item = json.loads(line)
            outputs[item["custom_id"]] = item
    return outputs


def merge_results(records: list[dict], outputs: dict, dataset_path: Path) -> list[dict]:
    merged_records = []
    missing_ids = [record["custom_id"] for record in records if record["custom_id"] not in outputs]
    if missing_ids:
        raise RuntimeError(
            f"Missing batch outputs for {dataset_path.name}: {missing_ids[:5]}{'...' if len(missing_ids) > 5 else ''}"
        )

    for record_info in records:
        output = outputs[record_info["custom_id"]]
        response = output.get("response", {})
        status_code = response.get("status_code")
        if status_code != 200:
            raise RuntimeError(
                f"{record_info['custom_id']} failed with status_code={status_code}: {json.dumps(output, ensure_ascii=False)}"
            )
        try:
            content = response["body"]["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RuntimeError(f"{record_info['custom_id']} has malformed output payload") from exc

        parsed_scores = parse_scores(
            content,
            expected_count=len(record_info["sections"]),
            custom_id=record_info["custom_id"],
        )
        matched = []
        for section, score in zip(record_info["sections"], parsed_scores):
            matched.append(
                {
                    "heading": section["heading"],
                    "content": section["content"],
                    "score": score,
                }
            )
        updated = dict(record_info["record"])
        updated["wiki_content_matched"] = json.dumps(matched, ensure_ascii=False)
        merged_records.append(updated)
    return merged_records


def atomic_rewrite_jsonl(dataset_path: Path, merged_records: list[dict]) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=dataset_path.parent, delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
        for record in merged_records:
            tmp.write(json.dumps(record, ensure_ascii=False))
            tmp.write("\n")
    tmp_path.replace(dataset_path)


def process_dataset_file(
    client: BigModelBatchClient,
    dataset_path: Path,
    model_name: str,
    poll_interval: int,
    keep_temp: bool,
    resume_batch_id: str | None,
) -> None:
    print(f"Processing {dataset_path}")
    temp_manager = None
    if keep_temp:
        temp_dir = Path(tempfile.mkdtemp(prefix=f"{dataset_path.stem}-batch-"))
    else:
        temp_manager = tempfile.TemporaryDirectory(prefix=f"{dataset_path.stem}-batch-")
        temp_dir = Path(temp_manager.name)
    try:
        batch_input_path, records, metadata = create_batch_input(dataset_path, temp_dir, model_name)
        if resume_batch_id:
            batch_id = resume_batch_id
            print(f"Resuming existing batch: {batch_id}")
        else:
            upload_info = client.upload_file(batch_input_path)
            print(f"Uploaded batch input file: {upload_info['id']}")

            batch_info = client.create_batch(upload_info["id"], metadata)
            batch_id = batch_info["id"]
            print(f"Created batch: {batch_id}")

        final_batch = wait_for_batch(client, batch_id, poll_interval)
        status = final_batch["status"]
        if status != "completed":
            raise RuntimeError(f"Batch {batch_id} ended with status={status}")

        if final_batch.get("error_file_id"):
            error_path = temp_dir / f"{dataset_path.stem}.batch-errors.jsonl"
            client.download_file(final_batch["error_file_id"], error_path)
            raise RuntimeError(
                f"Batch {batch_id} produced errors. See {error_path}"
            )

        output_file_id = final_batch.get("output_file_id")
        if not output_file_id:
            raise RuntimeError(f"Batch {batch_id} completed without output_file_id")

        output_path = temp_dir / f"{dataset_path.stem}.batch-output.jsonl"
        client.download_file(output_file_id, output_path)
        outputs = load_batch_outputs(output_path)
        merged_records = merge_results(records, outputs, dataset_path)
        atomic_rewrite_jsonl(dataset_path, merged_records)
        print(f"Updated {dataset_path}")
    finally:
        if keep_temp:
            print(f"Keeping temporary files in {temp_dir}")
        elif temp_manager is not None:
            temp_manager.cleanup()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fill wiki_content_matched in dataset jsonl files with BigModel Batch API."
    )
    parser.add_argument("dataset_files", nargs="+", help="One or more dataset .jsonl files")
    parser.add_argument("--auth-path", default="auth.yaml")
    parser.add_argument("--provider", default=DEFAULT_MODEL_PROVIDER)
    parser.add_argument("--model-key", default=DEFAULT_MODEL_KEY)
    parser.add_argument(
        "--model-name",
        default=None,
        help="Override the API model name used inside batch requests without changing auth.yaml",
    )
    parser.add_argument("--poll-interval", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--keep-temp", action="store_true")
    parser.add_argument(
        "--resume-batch-id",
        default=None,
        help="Resume waiting/downloading for an existing batch id instead of creating a new one",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    auth_path = Path(args.auth_path)
    config = load_auth_config(auth_path, args.provider, args.model_key)
    model_name = args.model_name or config["model"]
    client = BigModelBatchClient(
        api_key=config["api_key"],
        base_url=config["base_url"],
        timeout=args.timeout,
    )

    dataset_paths = [Path(path) for path in args.dataset_files]
    invalid = [str(path) for path in dataset_paths if path.suffix != ".jsonl"]
    if invalid:
        raise ValueError(f"Only .jsonl files are supported: {invalid}")

    for dataset_path in dataset_paths:
        process_dataset_file(
            client=client,
            dataset_path=dataset_path,
            model_name=model_name,
            poll_interval=args.poll_interval,
            keep_temp=args.keep_temp,
            resume_batch_id=args.resume_batch_id,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise
