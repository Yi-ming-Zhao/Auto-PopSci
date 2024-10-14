import pandas as pd
from tqdm import tqdm

df = pd.read_parquet("datasets/popsci.parquet")

for index, rows in tqdm(df.iterrows(), total=df.shape[0]):
    substr = ""
    substr = df.loc[index, "content"]
    deleted = substr[:16]
    substr = substr[16:]
    print(deleted)
    df.loc[index, "content"] = substr[16:]

df.to_parquet("datasets/popsci.parquet", engine="pyarrow", index=False)
