#!/usr/bin/env bash
set -euo pipefail

MODEL_NAME="${1:-glm-4-plus}"
POLL_INTERVAL="${POLL_INTERVAL:-30}"

files=(
  "dataset/adult_test.jsonl"
  "dataset/adult_train.jsonl"
  "dataset/adult_validation.jsonl"
  "dataset/child_test.jsonl"
  "dataset/child_train.jsonl"
  "dataset/child_validation.jsonl"
  "dataset/teen_test.jsonl"
  "dataset/teen_train.jsonl"
  "dataset/teen_validation.jsonl"
)

for file in "${files[@]}"; do
  echo "=== Processing ${file} with model ${MODEL_NAME} ==="
  python3 fill_wiki_content_matched_batch.py "${file}" --model-name "${MODEL_NAME}" --poll-interval "${POLL_INTERVAL}"
  git add fill_wiki_content_matched_batch.py run_fill_wiki_content_matched_batches.sh "${file}"
  git commit -m "Fill wiki_content_matched for $(basename "${file}")"
  git push origin main
done
