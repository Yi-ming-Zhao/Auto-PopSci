from datasets import load_dataset
from pprint import pprint

dataset_name = "dongqi-me/SciNews"

dataset = load_dataset(dataset_name)

pprint(dataset)

dataset_50 = dataset["train"].select(range(50))
dataset_5 = dataset["train"].select(range(5))

dataset_50 = dataset_50.select_columns(
    column_names=["Paper_Body", "News_Body", "News_Title", "Topic"]
)
dataset_5 = dataset_5.select_columns(
    column_names=["Paper_Body", "News_Body", "News_Title", "Topic"]
)

dataset_50.to_json("datasets/scinews/dev_dataset_50.json", lines=False)
dataset_5.to_json("datasets/scinews/dev_dataset_5.json", lines=False)

pprint(dataset_50)
pprint(dataset_5)
