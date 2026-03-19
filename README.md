# PopBench

PopBench is a benchmark for **multi-level science popularization**, introduced in the paper *PopBench: Benchmarking Multi-Level Science Popularization*. The task is to transform complex scientific or Wikipedia-style content into audience-adapted popular science articles for different cognitive levels such as **Child**, **Teen**, and **Adult**.

This project is also available on Hugging Face: https://huggingface.co/yzxbb/PopBench

This repository contains:
- benchmark dataset files
- model outputs for testing the evaluation process
- the evaluation pipeline for coherence, simplicity, vividness, informativeness, and keyfacts
- utility code for dataset processing and keyfact handling

## Overview

According to the paper, PopBench emphasizes two core aspects that are usually missing in prior work:
- **audience-adaptive generation** across multiple cognitive levels
- **multi-dimensional evaluation** beyond readability alone

The current codebase mainly supports evaluation along these dimensions:
- **Coherence**: PPL-based fluency and stability
- **Simplicity**: FKGL readability level
- **Vividness**: figurativeness, emotionality, and decorativeness
- **Informativeness**: precision and recall against source-side keyfacts

## Repository Layout

- [auto_popsci/evaluation](auto_popsci/evaluation): main evaluation pipeline
- [dataset](dataset): flattened benchmark datasets
- [model_outputs](model_outputs): model generations ready for evaluation. Since the whole result can be very large, we only put qwen3-8b zero-shot results here.
- [prompts](prompts): prompt templates used by keyfact and LLM-based evaluation modules
- [results](results): evaluation outputs

## Data Format

The repository now uses a flattened JSON format for both benchmark data and model outputs.

### Benchmark dataset example

Files under [dataset](dataset), such as [adult_test.json](dataset/adult_test.json), follow a compact structure like:

```json
{
  "popsci_title": "...",
  "popsci_content": "...",
  "popsci_url": "...",
  "wiki_title": "...",
  "wiki_content": "...",
  "wiki_url": "...",
  "wiki_keyfacts": [...],
  "source": "...",
  "content_relevance_score": 9
}
```

### Model output example

Files under [model_outputs](model_outputs), such as [adult_without_finetune.json](model_outputs/qwen/adult_without_finetune.json), extend the dataset format with model-specific fields:

```json
{
  "popsci_title": "...",
  "popsci_content": "...",
  "popsci_url": "...",
  "wiki_title": "...",
  "wiki_content": "...",
  "wiki_url": "...",
  "wiki_keyfacts": [...],
  "source": "...",
  "content_relevance_score": 9,
  "model_name": "qwen3-8b-without-finetune",
  "model_title": "...",
  "model_output": "..."
}
```

## Evaluation

The main entry point is [evaluate_dataset.py](auto_popsci/evaluation/evaluate_dataset.py).

### Recommended command for model outputs

```bash
python auto_popsci/evaluation/evaluate_dataset.py \
  --input_file model_outputs/qwen/adult_without_finetune.json \
  --output_file results/qwen_adult_without_finetune_eval.json \
  --popsci_field model_output \
  --original_field wiki_content \
  --reference_field popsci_content \
  --ground_truth_keyfacts_field wiki_keyfacts \
  --llm_type gemini-3-flash-preview \
  --reader_age adult \
  --cuda_devices "0,1" \
  --concurrency 5 \
  --sample 5
```

### Recommended parameter meanings

Only use the parameters shown in the recommended command above unless you clearly know what you are doing. Most other CLI options in the evaluator are mainly for debugging, legacy compatibility, or internal experiments.

- `--input_file model_outputs/qwen/adult_without_finetune.json`: the flattened model output file to evaluate
- `--output_file results/qwen_adult_without_finetune_eval.json`: where the evaluation result JSON will be written
- `--popsci_field model_output`: the field containing the model-generated popular science article
- `--original_field wiki_content`: the field containing the source Wikipedia text used as the original document
- `--reference_field popsci_content`: the field containing the human-written popular science reference
- `--ground_truth_keyfacts_field wiki_keyfacts`: the field containing existing source-side keyfacts; the evaluator reads this field first instead of generating ground-truth keyfacts unnecessarily
- `--llm_type gemini-3-flash-preview`: the model used for LLM-based parts of the evaluation, such as keyfact-related processing when needed
- `--reader_age adult`: the target reader profile for audience-adaptive evaluation
- `--cuda_devices "0,3"`: the GPU devices used for local model-based evaluation components
- `--concurrency 5`: the maximum number of concurrent async evaluation tasks through LLM APIs
- `--sample 5`: evaluate only the first 5 records, and use only those 5 records throughout the entire pipeline

### Notes on current evaluation behavior

- `--ground_truth_keyfacts_field` defaults to `wiki_keyfacts`
- if existing keyfacts are present in the specified field, the evaluator reads them first
- `--sample N` applies to the entire pipeline, not just field detection
- keyfact generation, QA evaluation, local PPL computation, vividness, simplicity, and final statistics all use only the sampled subset

## Output Format

The evaluation output in [results](results) is now intentionally flattened and compact.

Each record in `results` keeps only evaluation-relevant metadata and scores, for example:

```json
{
  "doc_id": 0,
  "model_name": "qwen3-8b-without-finetune",
  "source": "...",
  "content_relevance_score": 9,
  "popsci_title": "...",
  "popsci_url": "...",
  "wiki_title": "...",
  "wiki_url": "...",
  "simplicity_fkgl_score": 8.7,
  "coherence_ppl_score": 32.1,
  "vividness_score": 0.41,
  "figurativeness": 0.12,
  "emotionality": 0.39,
  "decorativeness": 0.58,
  "keyfacts_precision": 0.73,
  "keyfacts_recall": 0.66
}
```


## Auth Configuration

The repository now separates the public template from local secrets:

- [auth.yaml](auth.yaml): checked-in template with empty values

If you run LLM-based evaluation or keyfact generation and evaluation, make sure your local config contains valid values for:
- `api_key`
- `base_url`
- `model`
