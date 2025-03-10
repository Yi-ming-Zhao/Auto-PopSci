from datasets import load_dataset

dataset = load_dataset("dongqi-me/SciNews")

from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "decapoda-research/llama-7b-hf"
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

def generate_summary(article):
    inputs = tokenizer.encode(article, return_tensors="pt")
    outputs = model.generate(inputs, max_length=1024, num_beams=5, early_stopping=True)
    summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return summary

dataset = dataset.map(lambda x: {"generated_news": generate_summary(x["article"])})

from rouge_score import rouge_scorer

scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
scores = scorer.score(reference_news, generated_news)
