import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re
from urllib.parse import urljoin, urlparse
import pandas as pd
from tqdm import tqdm
from collections import deque


class NatGeoKidsScraper:
    def __init__(
        self,
        base_url="https://kids.nationalgeographic.com/",
        output_dir="datasets/our_dataset/natgeo_kids",
        delay=1,
        max_pages=500,  # 限制爬取的最大页面数
    ):
        """
        初始化爬虫

        Args:
            base_url: 要爬取的基本URL
            output_dir: 保存数据的目录
            delay: 请求之间的延迟时间(秒)
            max_pages: 爬取的最大页面数量
        """
        self.base_url = base_url
        self.output_dir = output_dir
        self.delay = delay
        self.max_pages = max_pages
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 创建存储文章链接的CSV文件
        self.articles_file = os.path.join(output_dir, "natgeo_kids_articles.csv")

        # 已访问的URL集合
        self.visited_urls = set()

        # 用于存储发现的文章URL
        self.article_links = []

        # 预定义的分类列表，用于辅助识别
        self.common_categories = [
            "animals",
            "science",
            "history",
            "space",
            "weird-but-true",
            "environment",
            "geography",
            "archaeology",
        ]

    def is_article_url(self, url):
        """
        判断URL是否是文章页面

        Args:
            url: 要检查的URL

        Returns:
            bool: 是否是文章页面
        """
        # 检查URL是否属于当前网站
        if not url.startswith(self.base_url):
            return False

        # 检查URL是否包含"/article/"路径
        if "/article/" in url:
            return True

        return False

    def crawl_site(self):
        """
        从主页开始爬行整个网站，寻找所有文章页面

        Returns:
            list: 发现的所有文章链接
        """
        # 如果已经保存了文章链接，直接加载
        # if os.path.exists(self.articles_file):
        #     df = pd.read_csv(self.articles_file)
        #     self.article_links = df["url"].tolist()
        #     print(f"从已保存文件中加载了 {len(self.article_links)} 个文章链接")
        #     return self.article_links

        # 首先尝试从sitemap获取文章链接
        try:
            sitemap_url = "https://kids.nationalgeographic.com/sitemap.xml"
            response = requests.get(sitemap_url, headers=self.headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "xml")
                for url in soup.find_all("loc"):
                    url_text = url.text
                    # 查找所有包含 "/article/" 的URL
                    if "/article/" in url_text:
                        self.article_links.append(url_text)
                        print(f"从sitemap找到文章: {url_text}")

                if len(self.article_links) > 0:
                    print(f"从sitemap找到 {len(self.article_links)} 篇文章")
                    # 保存文章链接
                    df = pd.DataFrame({"url": self.article_links})
                    df.to_csv(self.articles_file, index=False)
                    return self.article_links
        except Exception as e:
            print(f"获取sitemap时出错: {e}")

        # 如果sitemap方法失效，使用BFS爬行网站
        print("开始爬行网站...")

        # 使用队列进行BFS
        queue = deque([self.base_url])

        # 计数器
        pages_visited = 0

        while queue and pages_visited < self.max_pages:
            # 从队列中取出URL
            current_url = queue.popleft()

            # 跳过已访问的URL
            if current_url in self.visited_urls:
                continue

            print(f"正在访问: {current_url} ({pages_visited+1}/{self.max_pages})")

            try:
                # 发送请求
                response = requests.get(current_url, headers=self.headers)

                # 将URL添加到已访问集合
                self.visited_urls.add(current_url)
                pages_visited += 1

                # 检查响应状态
                if response.status_code != 200:
                    print(f"请求失败，状态码: {response.status_code}")
                    continue

                # 解析HTML
                soup = BeautifulSoup(response.text, "html.parser")

                # 检查当前URL是否是文章页面
                if self.is_article_url(current_url):
                    if current_url not in self.article_links:
                        self.article_links.append(current_url)
                        print(f"找到文章: {current_url}")

                # 提取所有链接
                for link in soup.find_all("a", href=True):
                    href = link["href"]

                    # 忽略空链接、锚点和JavaScript
                    if (
                        not href
                        or href.startswith("#")
                        or href.startswith("javascript:")
                    ):
                        continue

                    # 构建完整URL
                    full_url = urljoin(current_url, href)

                    # 只处理同一网站的URL
                    if not full_url.startswith(self.base_url):
                        continue

                    # 规范化URL，删除锚点和查询参数
                    parsed_url = urlparse(full_url)
                    normalized_url = (
                        f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                    )

                    # 忽略常见的非内容页面
                    if any(
                        x in normalized_url
                        for x in ["/search", "/games", "/photos", "/videos", "/login"]
                    ):
                        continue

                    # 检查是否是文章URL
                    if self.is_article_url(normalized_url):
                        if normalized_url not in self.article_links:
                            self.article_links.append(normalized_url)
                            print(f"找到文章: {normalized_url}")

                    # 将未访问的URL添加到队列
                    if (
                        normalized_url not in self.visited_urls
                        and normalized_url not in queue
                    ):
                        queue.append(normalized_url)

                # 保存当前进度
                if len(self.article_links) % 10 == 0 and len(self.article_links) > 0:
                    df = pd.DataFrame({"url": self.article_links})
                    df.to_csv(self.articles_file, index=False)
                    print(f"已保存 {len(self.article_links)} 篇文章链接")

                # 添加延迟
                time.sleep(self.delay)

            except Exception as e:
                print(f"处理 {current_url} 时出错: {e}")

        # 保存文章链接
        if self.article_links:
            df = pd.DataFrame({"url": self.article_links})
            df.to_csv(self.articles_file, index=False)
            print(f"共找到 {len(self.article_links)} 篇文章")
        else:
            print("未找到任何文章链接")

        return self.article_links

    def get_article_links(self):
        """
        获取所有分类下的文章链接

        Returns:
            list: 文章链接列表
        """
        # 使用新的爬行方法
        article_links = self.crawl_site()

        # 如果爬行方法失败，尝试使用旧的方法
        if not article_links:
            print("爬行方法未找到文章，尝试其他方法...")

            # 从sitemap获取所有文章链接
            try:
                sitemap_url = "https://kids.nationalgeographic.com/sitemap.xml"
                response = requests.get(sitemap_url, headers=self.headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "xml")
                    for url in soup.find_all("loc"):
                        url_text = url.text
                        # 查找所有包含 "/article/" 的URL
                        if "/article/" in url_text:
                            article_links.append(url_text)
                            print(f"从sitemap找到文章: {url_text}")
            except Exception as e:
                print(f"获取sitemap时出错: {e}")

            # 如果sitemap方法失效，尝试从主页获取文章链接
            if not article_links:
                try:
                    main_page = requests.get(self.base_url, headers=self.headers)
                    if main_page.status_code == 200:
                        main_soup = BeautifulSoup(main_page.text, "html.parser")

                        # 查找主页上的所有链接
                        for link in main_soup.find_all("a", href=True):
                            href = link["href"]
                            if "/article/" in href:
                                full_url = urljoin(self.base_url, href)
                                if full_url not in article_links:
                                    article_links.append(full_url)
                                    print(f"从主页找到文章: {full_url}")
                except Exception as e:
                    print(f"从主页获取文章时出错: {e}")

            # 如果依然没有找到文章，尝试搜索各个常见分类
            if not article_links:
                for category in self.common_categories:
                    try:
                        search_url = f"{self.base_url}search"
                        params = {"q": category}
                        response = requests.get(
                            search_url, params=params, headers=self.headers
                        )

                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, "html.parser")

                            for link in soup.find_all("a", href=True):
                                href = link["href"]
                                if "/article/" in href:
                                    full_url = urljoin(self.base_url, href)
                                    if full_url not in article_links:
                                        article_links.append(full_url)
                                        print(
                                            f"通过搜索 {category} 找到文章: {full_url}"
                                        )

                        time.sleep(self.delay)
                    except Exception as e:
                        print(f"搜索分类 {category} 时出错: {e}")

            # 如果仍然没有找到文章，使用手动指定的示例链接
            if not article_links:
                article_links = [
                    "https://kids.nationalgeographic.com/science/article/facts-about-coronavirus",
                    "https://kids.nationalgeographic.com/science/article/coronavirus-glossary",
                    "https://kids.nationalgeographic.com/space/article/what-is-a-planet",
                    "https://kids.nationalgeographic.com/animals/article/15-facts-about-sharks",
                    "https://kids.nationalgeographic.com/history/article/abraham-lincoln",
                ]
                print("使用手动指定的文章链接")

            # 保存文章链接到CSV文件
            df = pd.DataFrame({"url": article_links})
            df.to_csv(self.articles_file, index=False)

        print(f"共找到 {len(article_links)} 篇文章")
        return article_links

    def extract_category_from_url(self, url):
        """
        从URL中提取分类名称

        Args:
            url: 文章URL

        Returns:
            str: 分类名称
        """
        try:
            parsed_url = urlparse(url)
            path_parts = parsed_url.path.strip("/").split("/")

            # URL格式通常是 /{category}/article/{article-name}
            if len(path_parts) >= 2 and path_parts[1] == "article":
                return path_parts[0]
        except:
            pass

        return "unknown"

    def parse_article(self, url):
        """
        解析单个文章页面

        Args:
            url: 文章URL

        Returns:
            dict: 包含文章信息的字典
        """
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                print(f"获取文章失败: {url}, 状态码: {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # 从URL中提取分类
            category = self.extract_category_from_url(url)

            # 提取文章标题
            title = soup.find("h1", class_="Article__Headline__Title")
            if not title:
                title = soup.find("h1")
            title_text = title.text.strip() if title else "未找到标题"

            # 提取文章描述
            description = soup.find("p", class_="Article__Headline__Desc")
            description_text = description.text.strip() if description else ""

            # 提取作者信息
            author = soup.find("span", class_="Byline__Author")
            author_text = author.text.strip() if author else "Unknown"

            # 提取发布日期
            pub_date = soup.find("div", class_="Byline__Meta--publishDate")
            pub_date_text = (
                pub_date.text.replace("Published ", "").strip() if pub_date else ""
            )

            # 提取文章内容
            content_section = soup.find("section", class_="Article__Content")
            if content_section:
                paragraphs = content_section.find_all(["p", "h2", "h3", "ul", "ol"])
                content = []
                for p in paragraphs:
                    if p.name in ["h2", "h3"]:
                        content.append(f"\n## {p.text.strip()}\n")
                    elif p.name in ["ul", "ol"]:
                        list_items = p.find_all("li")
                        for item in list_items:
                            content.append(f"- {item.text.strip()}")
                    else:
                        content.append(p.text.strip())
                content_text = "\n".join(content)
            else:
                content_text = "未找到内容"

            # 提取主图片URL
            main_image = soup.find("figure", class_="Image")
            if main_image:
                img = main_image.find("img")
                image_url = img.get("src") if img else ""
            else:
                image_url = ""

            # 提取相关文章
            related_articles = []
            read_next_section = soup.find("section", class_="ReadThisNext")
            if read_next_section:
                for item in read_next_section.find_all(
                    "div", class_="ContentList__Item"
                ):
                    link = item.find("a")
                    if link:
                        headline = link.find("h2")
                        headline_text = headline.text.strip() if headline else ""
                        href = link.get("href", "")
                        if headline_text and href:
                            related_articles.append(
                                {
                                    "title": headline_text,
                                    "url": urljoin(self.base_url, href),
                                }
                            )

            # 尝试提取元数据
            meta_data = {}
            for meta in soup.find_all("meta"):
                if meta.get("name") in [
                    "tax:firstSubject",
                    "tax:otherSubjects",
                    "article:published_time",
                ]:
                    meta_data[meta.get("name")] = meta.get("content", "")

            # 构建返回的文章数据
            article_data = {
                "url": url,
                "category": category,
                "title": title_text,
                "description": description_text,
                "author": author_text,
                "published_date": pub_date_text,
                "content": content_text,
                "image_url": image_url,
                "related_articles": related_articles,
                "meta_data": meta_data,
            }

            return article_data

        except Exception as e:
            print(f"解析文章时出错 {url}: {e}")
            return None

    def scrape_all_articles(self):
        """
        爬取所有文章

        Returns:
            list: 包含所有文章数据的列表
        """
        article_links = self.get_article_links()
        all_articles = []

        # 按分类组织的文章
        category_articles = {}

        print(f"准备爬取 {len(article_links)} 篇文章")

        for i, url in enumerate(tqdm(article_links)):
            print(f"正在爬取文章 {i+1}/{len(article_links)}: {url}")
            article_data = self.parse_article(url)

            if article_data:
                all_articles.append(article_data)

                # 按分类组织文章
                category = article_data["category"]
                if category not in category_articles:
                    category_articles[category] = []
                category_articles[category].append(article_data)

                # 确保分类目录存在
                category_dir = os.path.join(self.output_dir, category)
                if not os.path.exists(category_dir):
                    os.makedirs(category_dir)

                # 保存单个文章为JSON文件
                article_filename = (
                    re.sub(r"[^\w]", "-", article_data["title"])[:50] + ".json"
                )
                article_path = os.path.join(category_dir, article_filename)

                with open(article_path, "w", encoding="utf-8") as f:
                    json.dump(article_data, f, ensure_ascii=False, indent=4)

                print(f"已保存文章到 {article_path}")

            # 添加延迟，避免请求过于频繁
            time.sleep(self.delay)

        # 保存所有文章为一个大的JSON文件
        all_articles_path = os.path.join(
            self.output_dir, "all_natgeo_kids_articles.json"
        )
        with open(all_articles_path, "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=4)

        # 为每个分类保存一个JSON文件
        for category, articles in category_articles.items():
            category_file = os.path.join(self.output_dir, f"{category}_articles.json")
            with open(category_file, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False, indent=4)
            print(f"已保存 {len(articles)} 篇 {category} 分类的文章到 {category_file}")

        print(f"已保存所有 {len(all_articles)} 篇文章到 {all_articles_path}")

        return all_articles

    def export_to_csv(self, articles):
        """
        将文章数据导出为CSV文件

        Args:
            articles: 文章数据列表
        """
        if not articles:
            print("没有文章可导出")
            return

        # 按分类组织文章
        category_articles = {}
        for article in articles:
            category = article.get("category", "unknown")
            if category not in category_articles:
                category_articles[category] = []
            category_articles[category].append(article)

        # 提取CSV所需的列
        csv_data = []
        for article in articles:
            csv_data.append(
                {
                    "url": article["url"],
                    "category": article.get("category", "unknown"),
                    "title": article["title"],
                    "description": article["description"],
                    "author": article["author"],
                    "published_date": article["published_date"],
                    "image_url": article["image_url"],
                    "content_length": len(article["content"]),
                    "subjects": article.get("meta_data", {}).get(
                        "tax:otherSubjects", ""
                    ),
                }
            )

        # 创建DataFrame并保存为CSV
        df = pd.DataFrame(csv_data)
        csv_path = os.path.join(self.output_dir, "natgeo_kids_articles_summary.csv")
        df.to_csv(csv_path, index=False)
        print(f"已导出所有 {len(csv_data)} 篇文章到 {csv_path}")

        # 为每个分类创建单独的CSV
        for category, cat_articles in category_articles.items():
            category_csv_data = []
            for article in cat_articles:
                category_csv_data.append(
                    {
                        "url": article["url"],
                        "title": article["title"],
                        "description": article["description"],
                        "author": article["author"],
                        "published_date": article["published_date"],
                        "image_url": article["image_url"],
                        "content_length": len(article["content"]),
                        "subjects": article.get("meta_data", {}).get(
                            "tax:otherSubjects", ""
                        ),
                    }
                )

            category_df = pd.DataFrame(category_csv_data)
            category_csv_path = os.path.join(
                self.output_dir, f"{category}_articles_summary.csv"
            )
            category_df.to_csv(category_csv_path, index=False)
            print(
                f"已导出 {len(category_csv_data)} 篇 {category} 分类的文章到 {category_csv_path}"
            )


if __name__ == "__main__":
    # 创建爬虫实例
    scraper = NatGeoKidsScraper(
        base_url="https://kids.nationalgeographic.com/",
        output_dir="datasets/our_dataset/natgeo_kids",
        delay=2,  # 2秒延迟，避免请求过于频繁
        max_pages=100000000,  # 最多爬取1000个页面
    )

    # 爬取所有文章
    articles = scraper.scrape_all_articles()

    # 导出为CSV
    scraper.export_to_csv(articles)

    print("爬取完成!")
