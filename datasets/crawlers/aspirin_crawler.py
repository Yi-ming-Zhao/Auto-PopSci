import requests
from bs4 import BeautifulSoup
import pandas as pd


def tag_p_text(tag):
    return tag.name == "p"


paper_url = "https://www.sciencedirect.com/science/article/pii/S0049384803003797"

try:
    response = requests.get(
        url=paper_url,
        headers={
            "User-Agent": "Opera/9.25 (Windows NT 5.1; U; en)",
        },
    )
    response.raise_for_status()  # 检查请求是否成功
    soup = BeautifulSoup(response.content, "html.parser")
    paper_content = " ".join(
        [p.get_text(strip=True) for p in soup.find_all(tag_p_text)]
    )
    with open(
        "datasets/examples/the_mechanism_of_action_of_aspirin.txt",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(paper_content)
except requests.RequestException as e:
    print(f"Failed to retrieve the page at {paper_url}. Error: {e}")
