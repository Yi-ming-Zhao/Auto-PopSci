import os
os.environ["CUDA_VISIBLE_DEVICES"] = "5"
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
current_time = time.strftime("%Y-%m-%d__%H:%M", time.localtime())
log_dir = f"baselines/meta-llama/Meta-Llama-3.1-8B-Instruct/runs/{current_time}"
my_writer = SummaryWriter(log_dir=log_dir)

# bitsandbytes configuration
compute_dtype = getattr(torch, "float16")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=compute_dtype,
    bnb_4bit_use_double_quant=False,
)


# Check GPU compatibility with bfloat16
if compute_dtype == torch.float16 and use_4bit:
    major, _ = torch.cuda.get_device_capability()
    if major >= 8:
        print("=" * 80)
        print("Your GPU supports bfloat16: accelerate training with bf16=True")
        print("=" * 80)

# Load model, tokenizer and dataset
model = AutoModelForCausalLM.from_pretrained(model_name, quantization_config=bnb_config)
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"
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

instruct = "Suppose that you are a scientist who is very capable of writing science popularization articles. You have just published a paper on a new scientific discovery. You want to write a news article to introduce this discovery to the public. The following is the content of the paper. Please write the corresponding news article."


def preprocess_function(examples):
    inputs = [instruct + " " + paper_body for paper_body in examples["Paper_Body"]]
    pprint("inputs", inputs)
    model_inputs = tokenizer(
        examples["Paper_Body"], padding="max_length", truncation=True
    )
    pprint("tokenized_model_inputs", model_inputs)
    labels = tokenizer(
        text_target=examples["News_Body"], padding="max_length", truncation=True
    )
    pprint("tokenized_labels", labels)
    model_inputs["labels"] = labels["input_ids"]
    pprint("model_inputs_with_summary", model_inputs)

    # 确保输入和标签的长度一致
    # for i in range(len(model_inputs["input_ids"])):
    #     if len(model_inputs["input_ids"][i]) != len(model_inputs["labels"][i]):
    #         min_length = min(len(model_inputs["input_ids"][i]), len(model_inputs["labels"][i]))
    #         model_inputs["input_ids"][i] = model_inputs["input_ids"][i][:min_length]
    #         model_inputs["labels"][i] = model_inputs["labels"][i][:min_length]

    return model_inputs


tokenized_dataset = dataset.map(preprocess_function, batched=True)
dataset["train"] = tokenized_dataset["train"].select(range(800))
dataset["validation"] = tokenized_dataset["validation"].select(range(100))
dataset["test"] = tokenized_dataset["test"].shuffle(seed=42).select(range(100))

# model = get_peft_model(model, lora_config)

training_args = TrainingArguments(
    output_dir="./results/Llama-3.1-8B-Instruct",
    logging_dir="./logs/Llama-3.1-8B-Instruct",
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    gradient_accumulation_steps=1,
    evaluation_strategy="steps",
    eval_steps=5,
    optim="paged_adamw_32bit",
    learning_rate=2e-4,
    num_train_epochs=3,
    logging_steps=5,
    save_steps=5,
    fp16=False,
    bf16=False,
    weight_decay=0.001,
    group_by_length=True,
    lr_scheduler_type="constant",
    packing=False,
    report_to="tensorboard",
)

trainer = SFTTrainer(
    model=model,
    peft_config=lora_config,
    args=training_args,
    tokenizer=tokenizer,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["validation"],
)

# 训练模型并记录损失值
for step, batch in enumerate(trainer.get_train_dataloader()):
    outputs = trainer.training_step(model, batch)
    loss = outputs.loss
    my_writer.add_scalar("Loss/train", loss, step)

    # 计算 ROUGE 分数
    rouge = Rouge()
    predictions = model.generate(batch["input_ids"])
    decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
    decoded_labels = tokenizer.batch_decode(batch["labels"], skip_special_tokens=True)
    rouge_scores = rouge.get_scores(decoded_preds, decoded_labels, avg=True)
    my_writer.add_scalar("ROUGE-1/train", rouge_scores["rouge-1"]["f"], step)
    my_writer.add_scalar("ROUGE-2/train", rouge_scores["rouge-2"]["f"], step)
    my_writer.add_scalar("ROUGE-L/train", rouge_scores["rouge-l"]["f"], step)

# 保存最终模型
trainer.save_model("./results/Llama-3.1-8B-Instruct/final_model")

# 关闭 TensorBoardX
my_writer.close()
