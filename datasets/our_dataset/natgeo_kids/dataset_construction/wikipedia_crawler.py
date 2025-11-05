import requests
import json
from bs4 import BeautifulSoup


def get_wikipedia_text(title):
    url = f"https://en.wikipedia.org/api/rest_v1/page/html/{title}"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.find("title").get_text()
        print(f"Title: {title}")
        note = soup.find("div", class_="hatnote navigation-not-searchable").get_text()
        print(f"Note: {note}")
        description = soup.find(
            "div", class_="shortdescription nomobile noexcerpt noprint searchaux"
        ).get_text()
        print(f"Description: {description}")
        # 移除标题和描述
        soup.find("title").decompose()
        soup.find(
            "div", class_="shortdescription nomobile noexcerpt noprint searchaux"
        ).decompose()
        soup.find("div", class_="hatnote navigation-not-searchable").decompose()
        # 移除不需要的元素（导航栏、引用、表格等）
        for element in soup(["sup", "table", "div.navbox", "span.reference"]):
            element.decompose()

        # 提取纯文本
        text = soup.get_text(separator="\n", strip=True)
        return text
    else:
        print(f"Error: Could not fetch page for '{title}'")
        return None


# 示例：获取 "Python (programming language)" 页面的文本
title = "Coronavirus"
text = get_wikipedia_text(title)
if text:
    text = text.replace("\n", " ")
print(text[:5000])  # 打印前500字符

with open("coronavirus_wikipedia.txt", "w", encoding="utf-8") as f:
    f.write(text)
