import pandas as pd
from tqdm import tqdm

# 读取 Parquet 文件
df = pd.read_parquet("datasets/popsci.parquet")

# 删除包含 NaN 的行
new_df = df.dropna(subset=["paper_url"])

# 选择特定列
selected_columns = new_df[["title", "paper_url"]]

# 输出选定的列
print(selected_columns.to_string())
