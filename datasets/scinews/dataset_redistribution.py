import os

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
import json
import torch
import bitsandbytes
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import Trainer, TrainingArguments, DataCollatorForLanguageModeling
from rich import print
from rich.pretty import pprint
from trl import SFTTrainer
from tensorboardX import SummaryWriter
from rouge import Rouge
import time

model_name = "meta-llama/Meta-Llama-3.1-8B-Instruct"
dataset_name = "dongqi-me/SciNews"
current_time = time.strftime("%Y-%m-%d--%H:%M", time.localtime())
log_dir = f"baselines/meta-llama/Meta-Llama-3.1-8B-Instruct/runs/{current_time}"
my_writer = SummaryWriter(log_dir=log_dir)

# Load model, tokenizer and dataset
# model = AutoModelForCausalLM.from_pretrained(
#     model_name,
# )
# tokenizer = AutoTokenizer.from_pretrained(model_name)
# tokenizer.pad_token = tokenizer.eos_token
# tokenizer.padding_side = "right"
dataset = load_dataset(dataset_name)

# Lora configuration
lora_config = LoraConfig(
    r=32,
    lora_alpha=64,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0,
    bias="none",
    task_type="CAUSAL_LM",
)


instruction = "Suppose that you are a scientist who is very capable of writing science popularization articles. You have just published a paper on a new scientific discovery. You want to write a news article to introduce this discovery to the public. The following is the content of the paper. Please write the corresponding news article."


def convert_to_conversation(sample):
    conversation = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": instruction},
                {"type": "text", "text": sample["Paper_Body"]},
            ],
        },
        {
            "role": "assistant",
            "content": [{"type": "text", "text": sample["News_Body"]}],
        },
    ]
    return {"messages": conversation}


raw_dataset_train = dataset["train"].select(range(800))
converted_dataset_train = [
    convert_to_conversation(sample) for sample in raw_dataset_train
]
pprint(converted_dataset_train)
raw_dataset_test = dataset["test"].select(range(100))
converted_dataset_test = [
    convert_to_conversation(sample) for sample in raw_dataset_test
]
raw_dataset_eval = dataset["validation"].select(range(100))
converted_dataset_eval = [
    convert_to_conversation(sample) for sample in raw_dataset_eval
]

save_path = "Auto-PopSci/datasets/scinews"

# 确保目录存在
os.makedirs(save_path, exist_ok=True)

# 保存转换后的训练数据集
with open(
    os.path.join(save_path, "sampled_converted_scinews_train.json"),
    "w",
    encoding="utf-8",
) as train_file:
    json.dump(converted_dataset_train, train_file, ensure_ascii=False, indent=4)

# 保存转换后的测试数据集
with open(
    os.path.join(save_path, "sampled_converted_scinews_test.json"),
    "w",
    encoding="utf-8",
) as test_file:
    json.dump(converted_dataset_test, test_file, ensure_ascii=False, indent=4)

# 保存转换后的验证数据集
with open(
    os.path.join(save_path, "sampled_converted_scinews_eval.json"),
    "w",
    encoding="utf-8",
) as eval_file:
    json.dump(converted_dataset_eval, eval_file, ensure_ascii=False, indent=4)

print(f"Datasets have been saved to {save_path}.")
