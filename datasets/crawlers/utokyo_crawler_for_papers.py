import requests
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm


def tag_p_text(tag):
    return tag.name == "p"


df = pd.DataFrame()
df = pd.read_parquet("datasets/popsci.parquet")
df["paper_content"] = None

for (
    index,
    rows,
) in tqdm(df.iterrows(), total=df.shape[0]):
    paper_url = rows["paper_url"]
    if rows["paper_url"] is not None:
        try:
            response = requests.get(paper_url)
            response.raise_for_status()  # 检查请求是否成功
            soup = BeautifulSoup(response.content, "html.parser")
            paper_content = " ".join(
                [p.get_text(strip=True) for p in soup.find_all(tag_p_text)]
            )
            df.at[index, "paper_content"] = paper_content
        except requests.RequestException as e:
            print(f"Failed to retrieve the page at {paper_url}. Error: {e}")
            continue

df.to_parquet("datasets/popsci.parquet", engine="pyarrow", index=False)
