import requests
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm


def tag_p_with_no_class(tag):
    return tag.name == "p" and not tag.has_attr("class")


# 目标URL
url = "https://www.u-tokyo.ac.jp/focus/en/press/index.php?pageID=1"

df = pd.DataFrame()

article_list = []
try:
    df = pd.read_parquet("datasets/popsci.parquet")
except FileNotFoundError:
    print("File not found. Creating a new one.")


# get the titles and links of all the articles on the guiding page
if df.empty:
    for page_id in range(1, 19):
        url = f"https://www.u-tokyo.ac.jp/focus/en/press/index.php?pageID={page_id}"
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            articles = soup.find_all("div", class_="p-news-list__press-releases-item")
            for article in articles:
                title = article.find(
                    "p", class_="p-news-list__press-releases-item-text"
                ).get_text(strip=True)
                link = article.find("a")["href"]
                date = article.find(
                    "p", class_="p-news-list__press-releases-item-date"
                ).get_text(strip=True)
                is_news = article.find("p", class_="c-icn-type").get_text(strip=True)
                full_link = f"https://www.u-tokyo.ac.jp{link}"
                article_dict = {
                    "title": title,
                    "link": full_link,
                    "date": date,
                    "is_news": is_news,
                    "content": None,
                }
                if article_dict["is_news"] == "Research news":
                    article_list.append(article_dict)
                    # print(article_dict)
        else:
            print(f"Failed to retrieve the page. Status code: {response.status_code}")
    df = pd.DataFrame(article_list)
    df.to_parquet("datasets/ppsci.parquet", engine="pyarrow", index=False)

for index, rows in tqdm(df.iterrows(), desc="Retrieving content", total=df.shape[0]):
    if rows["content"] is not None:
        article_url = rows["link"]
        response = requests.get(article_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            sentence_list = soup.find_all(tag_p_with_no_class)
            passage = ""
            for sentence in sentence_list:
                if "Giving to Utokyo" in sentence.get_text(strip=True):
                    continue
                sentence = sentence.get_text(strip=True) + "\n"
                passage += sentence
            df.at[index, "content"] = passage
            # print(passage)
        else:
            raise Exception(
                f"Failed to retrieve the page. Status code: {response.status_code}"
            )

df.to_parquet("datasets/popsci.parquet", engine="pyarrow", index=False)
