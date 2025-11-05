#!/usr/bin/env python3
"""
Frontiers for Young Minds 文章爬虫
爬取 https://kids.frontiersin.org/articles 下的所有文章
保存为与 NatGeo Kids 相同的 JSON 格式
"""

import requests
import json
import time
import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import re
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class FrontiersCrawler:
    def __init__(self):
        """初始化爬虫"""
        self.base_url = "https://kids.frontiersin.org"
        self.articles_url = "https://kids.frontiersin.org/articles"
        self.session = requests.Session()

        # 初始化requests会话
        self.init_session()

        # 检查Selenium是否可用
        self.selenium_available = self._check_selenium()
        if not self.selenium_available:
            print("⚠️  Selenium未安装，将使用传统爬取方法")
            print("   安装Selenium: pip install selenium")
            print("   并确保安装ChromeDriver")
            print("   或运行安装脚本: ./install_selenium.sh")
        else:
            print("✅ Selenium 可用，支持真正的无限滚动爬取")

    def _check_selenium(self) -> bool:
        """检查Selenium是否可用"""
        try:
            from selenium import webdriver

            return True
        except ImportError:
            return False

    def init_session(self):
        """初始化requests会话"""
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

    def get_article_list_from_page(self, page: int = 1) -> List[Dict]:
        """从指定页面获取文章列表"""
        try:
            if page == 1:
                url = self.articles_url
            else:
                url = f"{self.articles_url}?page={page}"

            print(f"正在获取第 {page} 页: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            articles = []

            # 查找所有文章卡片
            article_elements = soup.find_all("article", class_="article")

            if not article_elements:
                print(f"第 {page} 页没有找到文章元素")
                return []

            print(f"第 {page} 页找到 {len(article_elements)} 篇文章")

            for article_elem in article_elements:
                try:
                    article_data = self.extract_article_summary(article_elem)
                    if article_data:
                        articles.append(article_data)
                except Exception as e:
                    print(f"提取文章摘要时出错: {e}")
                    continue

            return articles

        except requests.RequestException as e:
            print(f"获取第 {page} 页时出错: {e}")
            return []
        except Exception as e:
            print(f"解析第 {page} 页时出错: {e}")
            return []

    def extract_article_summary(self, article_elem) -> Optional[Dict]:
        """从文章元素中提取摘要信息"""
        try:
            # 提取文章链接
            link_elem = article_elem.find("a", class_="article-link")
            if not link_elem:
                return None

            article_url = urljoin(self.base_url, link_elem.get("href", ""))

            # 提取标题
            title_elem = article_elem.find("h1", class_="article-heading")
            title = title_elem.get_text(strip=True) if title_elem else "No Title"

            # 提取摘要
            abstract_elem = article_elem.find("p", class_="article-abstract")
            description = abstract_elem.get_text(strip=True) if abstract_elem else ""

            # 提取日期
            date_elem = article_elem.find("div", class_="article-date")
            published_date = date_elem.get_text(strip=True) if date_elem else ""

            # 提取文章类型
            type_elem = article_elem.find("div", class_="article-type")
            article_type = type_elem.get_text(strip=True) if type_elem else ""

            # 提取作者
            authors_elem = article_elem.find("div", class_="article-authors-container")
            authors = authors_elem.get_text(strip=True) if authors_elem else ""
            if authors.startswith("Authors"):
                authors = authors.replace("Authors", "").strip()

            # 提取图片URL
            img_elem = article_elem.find("img", class_="lazy-loaded-image")
            image_url = ""
            if img_elem:
                # 优先使用 data-src，然后是 src
                image_url = img_elem.get("data-src") or img_elem.get("src", "")
                if image_url and not image_url.startswith("http"):
                    image_url = urljoin(self.base_url, image_url)

            # 提取文章ID
            article_id = article_elem.get("data-test-id", "").replace("article-", "")

            return {
                "url": article_url,
                "title": title,
                "description": description,
                "author": authors,
                "published_date": published_date,
                "article_type": article_type,
                "image_url": image_url,
                "article_id": article_id,
                "content": "",  # 将在详情页面获取
                "related_articles": [],  # 将在详情页面获取
                "meta_data": {},  # 将在详情页面获取
            }

        except Exception as e:
            print(f"提取文章摘要信息时出错: {e}")
            return None

    def get_article_detail(self, article_data: Dict) -> Dict:
        """获取文章详情"""
        try:
            # 安全获取标题，如果没有则使用URL
            title = article_data.get("title", article_data.get("url", "Unknown"))
            print(f"正在获取文章详情: {title}")

            response = self.session.get(article_data["url"], timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # 提取标题（如果还没有）
            if not article_data.get("title"):
                title_elem = soup.find("h1", class_="fulltext-heading")
                if title_elem:
                    article_data["title"] = title_elem.get_text(strip=True)

            # 提取作者信息（详情页面的作者更完整）
            authors = self.extract_authors_from_detail(soup)
            if authors:
                article_data["author"] = authors

            # 提取发布日期
            published_date = self.extract_published_date(soup)
            if published_date:
                article_data["published_date"] = published_date

            # 提取文章内容
            content = self.extract_article_content(soup)
            article_data["content"] = content

            # 提取相关文章
            related_articles = self.extract_related_articles(soup)
            article_data["related_articles"] = related_articles

            # 提取元数据
            meta_data = self.extract_metadata(soup, article_data)
            article_data["meta_data"] = meta_data

            print(f"完成获取文章详情: {article_data.get('title', title)}")
            return article_data

        except requests.RequestException as e:
            print(f"获取文章详情时出错 ({article_data['url']}): {e}")
            return article_data
        except Exception as e:
            print(f"解析文章详情时出错 ({article_data['url']}): {e}")
            return article_data

    async def crawl_articles_async_parallel(
        self, article_data_list: List[Dict], max_concurrent: int = 5
    ) -> List[Dict]:
        """异步并行获取多篇文章详情"""
        import aiohttp
        from bs4 import BeautifulSoup

        print(
            f"🚀 开始异步并行处理 {len(article_data_list)} 篇文章，并发数: {max_concurrent}"
        )

        # 创建连接器以限制并发数
        connector = aiohttp.TCPConnector(
            limit=max_concurrent, limit_per_host=max_concurrent
        )
        timeout = aiohttp.ClientTimeout(total=30, connect=10)

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        all_articles = []
        completed_count = 0

        async with aiohttp.ClientSession(
            connector=connector, timeout=timeout, headers=headers
        ) as session:
            # 创建任务列表
            tasks = []
            for i, article_data in enumerate(article_data_list):
                task = self.get_article_detail_async(
                    session, article_data, i + 1, len(article_data_list)
                )
                tasks.append(task)

            # 使用semaphore控制并发数
            semaphore = asyncio.Semaphore(max_concurrent)

            async def bounded_task(task):
                async with semaphore:
                    return await task

            # 执行所有任务
            bounded_tasks = [bounded_task(task) for task in tasks]

            # 使用as_completed来处理完成的任务
            for coro in asyncio.as_completed(bounded_tasks):
                try:
                    article_data = await coro
                    if article_data and article_data.get("title"):
                        all_articles.append(article_data)

                    completed_count += 1
                    if completed_count % 5 == 0 or completed_count == len(
                        article_data_list
                    ):
                        success_rate = (
                            len(all_articles) / completed_count * 100
                            if completed_count > 0
                            else 0
                        )
                        print(
                            f"📊 进度: {completed_count}/{len(article_data_list)} 篇文章, 成功率: {success_rate:.1f}%"
                        )

                except Exception as e:
                    print(f"❌ 异步任务处理出错: {e}")
                    completed_count += 1

        print(
            f"✅ 异步处理完成！成功获取 {len(all_articles)}/{len(article_data_list)} 篇文章"
        )
        return all_articles

    async def get_article_detail_async(
        self,
        session: aiohttp.ClientSession,
        article_data: Dict,
        current: int,
        total: int,
    ) -> Dict:
        """异步获取单篇文章详情"""
        try:
            url = article_data["url"]

            async with session.get(url) as response:
                if response.status == 200:
                    html_content = await response.text()
                    soup = BeautifulSoup(html_content, "html.parser")

                    # 提取标题
                    if not article_data.get("title"):
                        title_elem = soup.find("h1", class_="fulltext-heading")
                        if title_elem:
                            article_data["title"] = title_elem.get_text(strip=True)

                    # 提取作者信息
                    authors = self.extract_authors_from_detail(soup)
                    if authors:
                        article_data["author"] = authors

                    # 提取发布日期
                    published_date = self.extract_published_date(soup)
                    if published_date:
                        article_data["published_date"] = published_date

                    # 提取文章内容
                    content = self.extract_article_content(soup)
                    if content:
                        article_data["content"] = content

                    # 提取相关文章
                    related_articles = self.extract_related_articles(soup)
                    if related_articles:
                        article_data["related_articles"] = related_articles

                    # 提取元数据
                    meta_data = self.extract_metadata(soup, article_data)
                    if meta_data:
                        article_data["meta_data"] = meta_data

                    return article_data
                else:
                    print(f"⚠️ HTTP错误 {response.status} for {url}")
                    return article_data

        except asyncio.TimeoutError:
            print(f"⚠️ 请求超时: {url}")
            return article_data
        except Exception as e:
            print(f"❌ 异步获取文章详情出错 ({url}): {str(e)[:50]}...")
            return article_data

    def extract_authors_from_detail(self, soup: BeautifulSoup) -> str:
        """从详情页面提取作者信息"""
        try:
            authors = []

            # 基于HTML结构，作者信息在 fulltext-metadata 部分
            authors_container = soup.select_one("div.fulltext-metadata")

            if authors_container:
                # 查找作者链接
                author_links = authors_container.select("a.fulltext-person")

                for author_link in author_links:
                    # 获取作者名字
                    name_span = author_link.select_one("span.fulltext-person-name")
                    if name_span:
                        author_name = name_span.get_text(strip=True)
                        if author_name and author_name not in authors:
                            authors.append(author_name)

            # 备用方案：从元数据中提取
            if not authors:
                meta_author = soup.find("meta", attrs={"name": "citation_author"})
                if meta_author:
                    authors.append(meta_author.get("content", "").strip())

            return ", ".join(authors) if authors else ""

        except Exception as e:
            print(f"提取作者信息时出错: {e}")
            return ""

    def extract_published_date(self, soup: BeautifulSoup) -> str:
        """从详情页面提取发布日期"""
        try:
            # 基于HTML结构，发布日期在特定的容器中
            date_selectors = [
                ".fulltext-date",
                "span.fulltext-date",
                "div.fulltext-metadata .fulltext-date",
                'meta[name="citation_publication_date"]',
                'meta[property="article:published_time"]',
                'meta[name="DC.date"]',
            ]

            for selector in date_selectors:
                if selector.startswith("meta"):
                    # 处理meta标签
                    meta_elem = soup.select_one(selector)
                    if meta_elem:
                        date_content = meta_elem.get("content", "").strip()
                        if date_content:
                            return date_content
                else:
                    # 处理普通HTML元素
                    date_elem = soup.select_one(selector)
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                        if date_text and "Published:" in date_text:
                            # 提取日期部分
                            date_parts = date_text.split("Published:")
                            if len(date_parts) > 1:
                                return date_parts[1].strip()
                        elif date_text and len(date_text) > 6:
                            return date_text.strip()

            # 备用方案：从URL中提取日期（如果URL包含日期）
            url_date_match = re.search(
                r"/(\d{4})/(\d{1,2})/(\d{1,2})",
                (
                    soup.find("link", rel="canonical").get("href", "")
                    if soup.find("link", rel="canonical")
                    else ""
                ),
            )
            if url_date_match:
                year, month, day = url_date_match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

            return ""

        except Exception as e:
            print(f"提取发布日期时出错: {e}")
            return ""

    def extract_article_content(self, soup: BeautifulSoup) -> str:
        """提取文章内容（基于实际Frontiers HTML结构优化）"""
        try:
            content_sections = []

            # 基于HTML分析，文章主要内容在 div.size-small.fulltext-content 中
            main_content = soup.select_one("div.size-small.fulltext-content")

            if not main_content:
                # 尝试其他可能的选择器
                alternative_selectors = [
                    "div.fulltext-content",
                    "div.size-small.fulltext-content",
                    "div.size.small.fulltext-content",
                    "div.fulltext",
                ]
                for selector in alternative_selectors:
                    main_content = soup.select_one(selector)
                    if main_content:
                        break

            if main_content:
                # 移除不需要的元素
                for unwanted in main_content.select(
                    ".fulltext-image-container, .fulltext-badges-container, .fulltext-metadata, aside, .modal, .toast-container, footer, header, nav"
                ):
                    unwanted.decompose()

                # 按照HTML顺序处理内容
                for element in main_content.find_all(
                    [
                        "h1",
                        "h2",
                        "h3",
                        "h4",
                        "h5",
                        "h6",
                        "p",
                        "div",
                        "figure",
                        "section",
                    ]
                ):
                    try:
                        # 跳过空白元素和特定容器
                        if not element.get_text(strip=True):
                            continue

                        element_class = element.get("class", [])
                        element_id = element.get("id", "")

                        # 跳过特定的无关元素
                        skip_classes = [
                            "modal",
                            "toast",
                            "footer",
                            "header",
                            "nav",
                            "menu",
                            "fulltext-aside",
                            "fulltext-metadata",
                        ]
                        skip_ids = ["full-text-references"]

                        if any(cls in skip_classes for cls in element_class):
                            continue
                        if element_id in skip_ids:
                            continue

                        # 处理标题
                        if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                            heading_text = element.get_text(strip=True)
                            if heading_text and len(heading_text) > 3:
                                # 根据标题层级添加markdown格式
                                level = int(element.name[1])
                                content_sections.append(
                                    f"\n{'#' * (level + 1)} {heading_text}"
                                )
                            continue

                        # 处理摘要（特殊的div.abstract）
                        if element.name == "div" and "abstract" in element_class:
                            abstract_content = element.get_text(strip=True)
                            if abstract_content and len(abstract_content) > 20:
                                # 提取Abstract标题和内容
                                lines = abstract_content.split("\n")
                                clean_lines = [
                                    line.strip() for line in lines if line.strip()
                                ]
                                if clean_lines:
                                    content_sections.append("\n## Abstract")
                                    content_sections.append(
                                        clean_lines[-1]
                                    )  # 通常是摘要内容
                            continue

                        # 处理段落
                        if element.name == "p":
                            text = element.get_text(strip=True)

                            # 过滤掉太短或无意义的文本
                            if not text or len(text) < 20:
                                continue

                            # 过滤掉特定类型的段落
                            skip_phrases = [
                                "Copyright ©",
                                "All Rights Reserved",
                                "Creative Commons",
                                "doi:",
                                "DOI:",
                                "Received:",
                                "Accepted:",
                                "Published:",
                                "Correspondence:",
                                "E-mail:",
                                "Conflict of Interest",
                                "AI Tool Statement",
                                "Any alternative text",
                            ]

                            if any(phrase in text for phrase in skip_phrases):
                                continue

                            # 清理文本中的多余空格
                            clean_text = " ".join(text.split())
                            content_sections.append(clean_text)

                        # 处理div块（可能是特殊的内容块）
                        elif element.name == "div" and element_class:
                            # 检查是否是词汇表等特殊内容
                            if "fulltext-content" in " ".join(element_class):
                                text = element.get_text(strip=True)
                                if (
                                    text
                                    and len(text) > 50
                                    and not any(
                                        skip in text.lower()
                                        for skip in ["copyright", "license", "doi"]
                                    )
                                ):
                                    # 处理词汇表条目
                                    if "Glossary" in text:
                                        content_sections.append("\n## Glossary")
                                    else:
                                        content_sections.append(text)

                    except Exception as e:
                        # 忽略单个元素的处理错误
                        continue

            else:
                # 备用方案：如果没有找到主内容容器，尝试提取所有有意义的段落
                all_paragraphs = soup.find_all("p")
                for p in all_paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 100:  # 只取较长的段落
                        # 检查是否在主要内容区域
                        parent = p.parent
                        while parent:
                            parent_class = parent.get("class", [])
                            parent_id = parent.get("id", "")

                            # 如果在侧边栏或导航中，跳过
                            if any(
                                cls
                                in ["sidebar", "navigation", "menu", "footer", "header"]
                                for cls in parent_class
                            ):
                                break
                            if parent_id in ["footer", "header", "navigation"]:
                                break

                            # 如果找到了主内容区域，保留这个段落
                            if any(
                                cls in ["content", "article", "main", "fulltext"]
                                for cls in parent_class
                            ):
                                content_sections.append(text)
                                break

                            parent = parent.parent

            # 清理和组合内容
            cleaned_content = []
            for section in content_sections:
                # 清理HTML实体和特殊字符
                cleaned = (
                    section.replace("&#x02014;", "—")
                    .replace("&#x000B0;", "°")
                    .replace("&#x02019;", "'")
                )
                cleaned = cleaned.replace("&#x000B7;", "·").replace("&#x000B0;", "°")
                # 清理多余的空白
                cleaned = " ".join(cleaned.split())

                if cleaned and len(cleaned) > 10:
                    cleaned_content.append(cleaned)

            content = "\n\n".join(cleaned_content)
            return content

        except Exception as e:
            print(f"提取文章内容时出错: {e}")
            return ""

    def extract_related_articles(self, soup: BeautifulSoup) -> List[Dict]:
        """提取相关文章"""
        try:
            related_articles = []

            # 基于实际HTML结构查找相关文章
            # 查找相关文章区域
            related_section = soup.select_one("aside.articles-section")
            if related_section:
                # 查找相关文章链接
                article_links = related_section.select(
                    ".articles-container-slider .article-link"
                )
                for link in article_links:
                    title_elem = link.select_one(".article-heading")
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        href = link.get("href", "")
                        if href and title:
                            url = urljoin(self.base_url, href)
                            related_articles.append({"title": title, "url": url})

            # 如果没有找到，尝试其他选择器
            if not related_articles:
                fallback_selectors = [
                    ".related-articles a",
                    ".see-also a",
                    'div[class*="related"] a',
                    'section[class*="related"] a',
                ]

                for selector in fallback_selectors:
                    links = soup.select(selector)
                    for link in links:
                        title = link.get_text(strip=True)
                        href = link.get("href", "")
                        if href and title and len(title) > 5:  # 确保标题有意义
                            url = urljoin(self.base_url, href)
                            related_articles.append({"title": title, "url": url})

                    if related_articles:  # 如果找到了相关文章就停止
                        break

            return related_articles[:5]  # 最多返回5篇相关文章

        except Exception as e:
            print(f"提取相关文章时出错: {e}")
            return []

    def extract_metadata(self, soup: BeautifulSoup, article_data: Dict) -> Dict:
        """提取元数据"""
        try:
            meta_data = {}

            # 提取关键词
            keywords_elem = soup.find("meta", attrs={"name": "keywords"})
            if keywords_elem:
                meta_data["keywords"] = keywords_elem.get("content", "")

            # 提取主题信息
            subjects = []
            subject_selectors = [
                ".article-subjects",
                ".categories",
                ".tags",
                'div[class*="subject"]',
                'div[class*="category"]',
            ]

            for selector in subject_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text:
                        subjects.append(text)
                if subjects:
                    break

            if subjects:
                meta_data["subjects"] = subjects

            # 从URL中提取DOI
            article_url = article_data.get("url", "")
            doi_match = re.search(r"10\.3389/[\w.-]+", article_url)
            if doi_match:
                meta_data["doi"] = doi_match.group(0)

            # 添加已有的元数据
            if article_data.get("article_type"):
                meta_data["article_type"] = article_data["article_type"]

            if article_data.get("published_date"):
                meta_data["published_date"] = article_data["published_date"]

            return meta_data

        except Exception as e:
            print(f"提取元数据时出错: {e}")
            return {}

    def has_more_pages(self, soup: BeautifulSoup) -> bool:
        """检查是否还有更多页面"""
        try:
            # 检查是否有"下一页"或更多文章的指示器
            no_more_indicator = soup.find("p", class_="article-message")
            if no_more_indicator and "No more articles" in no_more_indicator.get_text():
                return False

            # 检查是否还有文章容器footer
            footer = soup.find("div", id="articles-container-footer")
            if footer:
                indicator = footer.find("p", class_="article-message")
                if indicator and "No more articles" in indicator.get_text():
                    return False

            return True

        except Exception:
            return True  # 默认认为还有更多页面

    def detect_infinite_scroll(self, soup: BeautifulSoup) -> bool:
        """检测页面是否使用无限滚动"""
        try:
            # 检查是否有无限滚动相关的JavaScript
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string:
                    script_content = script.string.lower()
                    if any(
                        keyword in script_content
                        for keyword in ["infinite", "scroll", "load", "ajax", "lazy"]
                    ):
                        return True

            # 检查是否有加载更多按钮或指示器
            load_more = soup.find(
                ["button", "a"],
                class_=lambda x: x and ("load" in x.lower() or "more" in x.lower()),
            )
            if load_more:
                return True

            # 检查是否有分页链接但隐藏了
            pagination = soup.find(
                ["nav", "div"], class_=lambda x: x and "pagination" in x.lower()
            )
            if (
                pagination
                and pagination.get("style")
                and "display:none" in pagination.get("style")
            ):
                return True

            return False

        except Exception:
            return False

    def setup_selenium_driver(self, headless: bool = True):
        """设置Selenium WebDriver（优化版）"""
        try:
            chrome_options = Options()

            # 基本设置
            if headless:
                chrome_options.add_argument("--headless")

            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

            # 性能优化和稳定性设置
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")  # 禁用图片加载以提高速度
            # 注意：不禁用JavaScript，因为现代网站需要它来动态加载内容
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--disable-sync")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")

            # 稳定性和超时设置
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-ipc-flooding-protection")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-dev-shm-usage")  # 防止共享内存问题
            chrome_options.add_argument("--remote-debugging-port=9222")  # 启用远程调试

            # 网络优化
            chrome_options.add_argument(
                "--disable-features=TranslateUI,BlinkGenPropertyTrees"
            )
            chrome_options.add_argument(
                "--enable-features=NetworkService,NetworkServiceInProcess"
            )
            chrome_options.add_argument("--max_old_space_size=4096")  # 增加内存限制

            # 用户代理
            user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            chrome_options.add_argument(f"--user-agent={user_agent}")

            # 反检测设置
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"]
            )
            chrome_options.add_experimental_option("useAutomationExtension", False)

            # 创建WebDriver
            driver = webdriver.Chrome(options=chrome_options)

            # 设置超时时间（更短的超时以快速失败）
            driver.set_page_load_timeout(30)  # 页面加载30秒超时
            driver.set_script_timeout(15)  # JavaScript执行15秒超时

            # 设置隐式等待
            driver.implicitly_wait(5)  # 元素查找5秒超时

            # 反检测脚本
            driver.execute_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                // 移除自动化标识
                window.navigator.chrome = {
                    runtime: {},
                };

                // 修改plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                // 修改languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            """
            )

            print("✅ WebDriver配置完成")
            return driver

        except Exception as e:
            print(f"❌ 设置Selenium WebDriver时出错: {e}")
            print("💡 请确保:")
            print("   1. 已安装Chrome浏览器")
            print("   2. 已安装对应版本的ChromeDriver")
            print("   3. ChromeDriver在PATH路径中")
            return None

    def scroll_to_load_all_articles(self, driver, max_scrolls: int = 50):
        """使用Selenium进行无限滚动加载所有文章（超稳定版本）"""
        try:
            print("🚀 开始无限滚动加载文章...")

            # 先快速获取页面，设置更短的超时
            driver.set_page_load_timeout(15)
            driver.set_script_timeout(10)

            try:
                driver.get(self.articles_url)
            except:
                # 如果页面加载超时，尝试停止并继续
                driver.execute_script("window.stop();")

            time.sleep(3)  # 等待基本加载

            articles = set()  # 存储文章URL
            scroll_count = 0
            no_new_content_count = 0
            previous_height = 0

            print("📜 开始稳定滚动...")

            # 先获取初始文章
            try:
                article_elements = driver.find_elements(
                    By.CSS_SELECTOR, 'a[href*="/articles/"]'
                )
                for elem in article_elements:
                    href = elem.get_attribute("href")
                    if href:
                        full_url = urljoin(self.base_url, href)
                        articles.add(full_url)
                print(f"📄 初始加载: 找到 {len(articles)} 篇文章")
            except Exception as e:
                print(f"⚠️ 初始加载出错: {str(e)[:30]}...")

            while scroll_count < max_scrolls and no_new_content_count < 10:  # 增加无新内容容忍次数，确保尽可能多地爬取
                try:
                    # 分步滚动，减少每次滚动的幅度
                    scroll_step = 800
                    for i in range(3):  # 分3步滚动
                        try:
                            driver.execute_script(f"window.scrollBy(0, {scroll_step});")
                            time.sleep(0.5)  # 短暂等待
                        except:
                            break

                    # 检查新文章
                    try:
                        article_elements = driver.find_elements(
                            By.CSS_SELECTOR, 'a[href*="/articles/"]'
                        )
                        current_articles = set()
                        for elem in article_elements:
                            href = elem.get_attribute("href")
                            if href:
                                full_url = urljoin(self.base_url, href)
                                current_articles.add(full_url)

                        new_articles = current_articles - articles
                        if new_articles:
                            articles.update(new_articles)
                            no_new_content_count = 0
                            print(
                                f"📄 滚动 {scroll_count + 1}: 新增 {len(new_articles)} 篇，总计 {len(articles)} 篇"
                            )
                        else:
                            no_new_content_count += 1
                            print(
                                f"📄 滚动 {scroll_count + 1}: 无新文章 (连续{no_new_content_count}次)"
                            )
                    except Exception as e:
                        print(f"⚠️ 查找文章出错: {str(e)[:30]}...")
                        no_new_content_count += 1

                    scroll_count += 1

                    # 如果连续无新内容，尝试更大的滚动
                    if no_new_content_count >= 2:
                        try:
                            driver.execute_script(
                                "window.scrollTo(0, document.body.scrollHeight);"
                            )
                            time.sleep(2)
                        except:
                            pass

                    # 页面高度检查
                    try:
                        current_height = driver.execute_script(
                            "return document.body.scrollHeight"
                        )
                        if (
                            current_height == previous_height
                            and no_new_content_count >= 8  # 增加页面高度不变的容忍次数
                        ):
                            print("🏁 页面高度连续不变，可能已到底部")
                            # 最后尝试一次强制滚动
                            try:
                                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                time.sleep(3)
                                final_height = driver.execute_script("return document.body.scrollHeight")
                                if final_height == current_height:
                                    print("🏁 确认已到达页面底部，停止滚动")
                                    break
                                else:
                                    print("🔄 页面高度发生变化，继续滚动...")
                                    previous_height = final_height
                                    no_new_content_count = 0
                            except:
                                pass
                        previous_height = current_height
                    except:
                        pass

                except Exception as e:
                    print(f"⚠️ 滚动步骤出错: {str(e)[:30]}...")
                    no_new_content_count += 1
                    if no_new_content_count >= 5:
                        break

            print(f"✅ 滚动完成，发现 {len(articles)} 篇文章")
            return list(articles)

        except Exception as e:
            print(f"❌ 无限滚动失败: {str(e)[:50]}...")
            return []

    def _safe_find_elements(self, driver, by, value, timeout=5):
        """安全的元素查找方法，带超时和异常处理"""
        try:
            wait = WebDriverWait(driver, timeout)
            return wait.until(EC.presence_of_all_elements_located((by, value)))
        except TimeoutException:
            # 超时返回空列表而不是抛出异常
            return []
        except Exception as e:
            print(f"⚠️ 元素查找出错: {str(e)[:50]}...")
            return []

    def _safe_find_element(self, parent_element, by, value):
        """在父元素内安全查找子元素"""
        try:
            return parent_element.find_element(by, value)
        except NoSuchElementException:
            return None
        except Exception as e:
            print(f"⚠️ 子元素查找出错: {str(e)[:50]}...")
            return None

    def _find_load_more_button(self, driver):
        """查找加载更多按钮"""
        try:
            # 尝试多种可能的按钮选择器
            button_selectors = [
                'button[class*="load"]',
                'a[class*="load"]',
                'button[class*="more"]',
                'a[class*="more"]',
                ".load-more",
                "#load-more",
                'button:contains("Load more")',
                'button:contains("加载更多")',
                'button:contains("More")',
                'a:contains("More")',
                '[data-testid*="load"]',
                '[data-testid*="more"]',
            ]

            for selector in button_selectors:
                try:
                    if ":contains(" in selector:
                        # 使用JavaScript查找包含特定文本的按钮
                        text = selector.split(':contains("')[1].rstrip('")')
                        buttons = driver.execute_script(
                            f"""
                            var buttons = document.querySelectorAll('button, a');
                            return Array.from(buttons).filter(btn =>
                                btn.textContent.toLowerCase().includes('{text.lower()}')
                            );
                        """
                        )
                        if buttons and buttons[0].is_displayed():
                            return buttons[0]
                    else:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.is_enabled():
                                return elem
                except:
                    continue

            return None
        except:
            return None

    def _click_load_more_to_load_articles(self, driver, button, max_clicks: int = 20):
        """通过点击加载更多按钮来加载文章"""
        try:
            print(f"🔘 开始点击'加载更多'按钮，最多点击{max_clicks}次")

            articles = set()
            click_count = 0
            no_new_articles_count = 0

            while click_count < max_clicks:
                # 获取当前文章
                article_elements = driver.find_elements(
                    By.CSS_SELECTOR, "article.article"
                )
                current_articles = set()

                for article_elem in article_elements:
                    try:
                        link_elem = article_elem.find_element(
                            By.CSS_SELECTOR, "a.article-link"
                        )
                        if link_elem:
                            href = link_elem.get_attribute("href")
                            if href:
                                full_url = urljoin(self.base_url, href)
                                current_articles.add(full_url)
                    except:
                        continue

                # 检查新文章
                new_articles = current_articles - articles
                if new_articles:
                    articles.update(new_articles)
                    no_new_articles_count = 0
                    print(
                        f"📄 点击 {click_count + 1}: 发现 {len(new_articles)} 篇新文章，总计 {len(articles)} 篇"
                    )
                else:
                    no_new_articles_count += 1
                    print(
                        f"📄 点击 {click_count + 1}: 没有新文章 (连续{no_new_articles_count}次)"
                    )

                # 如果连续多次没有新文章，停止
                if no_new_articles_count >= 3:
                    print("⏹️  连续多次点击无新内容，停止点击")
                    break

                # 检查按钮是否仍然可点击
                try:
                    if not button.is_displayed() or not button.is_enabled():
                        print("⏹️  按钮不再可用，停止点击")
                        break

                    # 滚动到按钮位置
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", button
                    )
                    time.sleep(0.5)

                    # 点击按钮
                    button.click()
                    click_count += 1

                    # 等待内容加载
                    time.sleep(2)

                    # 重新查找按钮（有时DOM会更新）
                    button = self._find_load_more_button(driver)
                    if not button:
                        print("⏹️  找不到'加载更多'按钮，停止点击")
                        break

                except Exception as e:
                    print(f"❌ 点击按钮时出错: {e}")
                    break

            print(f"✅ 点击完成，总共发现 {len(articles)} 篇文章")
            return list(articles)

        except Exception as e:
            print(f"❌ 按钮点击过程中出错: {e}")
            return []

    def get_article_urls_with_selenium(self) -> List[str]:
        """使用Selenium获取所有文章URL"""
        driver = None
        try:
            driver = self.setup_selenium_driver()
            if not driver:
                print("无法创建Selenium WebDriver")
                return []

            urls = self.scroll_to_load_all_articles(driver)
            return urls

        finally:
            if driver:
                driver.quit()

    def extract_article_summary_from_url(self, driver, url: str) -> Optional[Dict]:
        """从文章URL提取摘要信息"""
        try:
            driver.get(url)
            time.sleep(2)  # 等待页面加载

            # 使用BeautifulSoup解析页面
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # 提取标题
            title_elem = soup.find("h1") or soup.find("title")
            title = title_elem.get_text(strip=True) if title_elem else "No Title"

            # 提取描述
            description = ""
            desc_selectors = [
                'meta[name="description"]',
                'meta[property="og:description"]',
            ]
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get("content", "")
                    break

            # 如果没有找到描述，尝试从内容中提取
            if not description:
                content_p = soup.find("p")
                if content_p:
                    description = content_p.get_text(strip=True)[:200]

            return {
                "url": url,
                "title": title,
                "description": description,
                "content": "",  # 将在详情页面获取
                "author": "",
                "published_date": "",
                "article_type": "",
                "image_url": "",
                "article_id": "",
                "related_articles": [],
                "meta_data": {},
            }

        except Exception as e:
            print(f"从URL提取文章摘要时出错 ({url}): {e}")
            return None

    def get_max_pages_from_infinite_scroll(self, soup: BeautifulSoup) -> int:
        """从无限滚动页面中估算最大页数"""
        try:
            # 检查页面中的文章总数信息
            count_elements = soup.find_all(
                string=lambda text: text
                and ("articles" in text.lower() or "results" in text.lower())
            )

            for element in count_elements:
                import re

                match = re.search(r"(\d+).*?(?:articles|results)", element.lower())
                if match:
                    total_articles = int(match.group(1))
                    # 假设每页12篇文章
                    estimated_pages = (total_articles + 11) // 12
                    return min(estimated_pages, 50)  # 限制最大页数

            # 如果无法确定，返回合理的默认值
            return 3  # 对于重复文章的网站，只爬取3页进行测试

        except Exception:
            return 3  # 默认爬取3页

    async def get_article_list_with_scroll_detection(
        self, session: aiohttp.ClientSession, page: int = 1
    ) -> List[Dict]:
        """支持无限滚动的文章列表获取（异步版本）"""
        try:
            if page == 1:
                url = self.articles_url
            else:
                url = f"{self.articles_url}?page={page}"

            print(f"正在获取第 {page} 页: {url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    print(f"获取第 {page} 页失败: HTTP {response.status}")
                    return []

                content = await response.text()
                soup = BeautifulSoup(content, "html.parser")
                articles = []

                # 查找所有文章卡片
                article_elements = soup.find_all("article", class_="article")

                if not article_elements:
                    print(f"第 {page} 页没有找到文章元素")
                    return []

                print(f"第 {page} 页找到 {len(article_elements)} 篇文章")

                for article_elem in article_elements:
                    try:
                        article_data = self.extract_article_summary(article_elem)
                        if article_data:
                            articles.append(article_data)
                    except Exception as e:
                        print(f"提取文章摘要时出错: {e}")
                        continue

                return articles

        except asyncio.TimeoutError:
            print(f"获取第 {page} 页超时")
            return []
        except Exception as e:
            print(f"获取第 {page} 页时出错: {e}")
            return []

    async def get_article_detail_async(
        self, session: aiohttp.ClientSession, article_data: Dict
    ) -> Dict:
        """获取文章详情（异步版本）"""
        try:
            print(f"正在获取文章详情: {article_data['title']}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            async with session.get(
                article_data["url"],
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    print(
                        f"获取文章详情失败 ({article_data['url']}): HTTP {response.status}"
                    )
                    return article_data

                content = await response.text()
                soup = BeautifulSoup(content, "html.parser")

                # 提取文章内容
                article_data["content"] = self.extract_article_content(soup)

                # 提取相关文章
                article_data["related_articles"] = self.extract_related_articles(soup)

                # 提取元数据
                article_data["meta_data"] = self.extract_metadata(soup, article_data)

                print(f"完成获取文章详情: {article_data['title']}")
                return article_data

        except asyncio.TimeoutError:
            print(f"获取文章详情超时 ({article_data['url']})")
            return article_data
        except Exception as e:
            print(f"获取文章详情时出错 ({article_data['url']}): {e}")
            return article_data

    def crawl_all_articles_with_selenium(
        self,
        max_scrolls: int = 50,
        show_browser: bool = False,
        max_articles: int = None,
    ) -> List[Dict]:
        """使用Selenium爬取所有文章，支持真正的无限滚动（增强版）"""
        print("🚀 开始使用增强版Selenium爬取 Frontiers for Young Minds 文章...")

        driver = None
        try:
            # 设置WebDriver
            driver = self.setup_selenium_driver(headless=not show_browser)
            if not driver:
                print("❌ 无法创建Selenium WebDriver，使用传统爬取方法")
                return self._fallback_crawl()

            print("📜 第一步：使用智能滚动获取所有文章URL...")
            article_urls = self.scroll_to_load_all_articles(driver, max_scrolls)

            if not article_urls:
                print("❌ 未能获取到任何文章URL")
                return []

            print(f"✅ 总共发现 {len(article_urls)} 篇文章URL")

            # 如果设置了最大文章数量限制
            if max_articles and len(article_urls) > max_articles:
                article_urls = article_urls[:max_articles]
                print(f"📊 限制采集数量为 {max_articles} 篇文章")

            print("📖 第二步：开始获取文章详情...")
            all_articles = []

            # 使用异步并行处理获取详情（比同步快很多）
            print("🚀 使用异步并行处理获取文章详情...")

            # 将URL转换为article_data字典
            article_data_list = [{"url": url} for url in article_urls]

            # 使用asyncio.run运行异步函数
            try:
                import asyncio

                all_articles = asyncio.run(
                    self.crawl_articles_async_parallel(article_data_list)
                )
            except Exception as e:
                print(f"⚠️ 异步处理失败，回退到同步处理: {e}")
                # 回退到同步处理
                for i, article_data in enumerate(article_data_list):
                    try:
                        print(
                            f"📄 同步处理第 {i+1}/{len(article_data_list)} 篇文章 ({(i+1)/len(article_data_list)*100:.1f}%)"
                        )
                        detailed_article = self.get_article_detail(article_data)
                        if detailed_article and detailed_article.get("title"):
                            all_articles.append(detailed_article)
                        time.sleep(0.5)  # 减少延迟时间
                    except Exception as e:
                        print(f"  ❌ 处理文章 {article_data['url']} 时出错: {e}")
                        continue

        except Exception as e:
            print(f"❌ Selenium爬取过程中出现错误: {e}")
            # 返回已获取的文章
            if "all_articles" in locals():
                return all_articles
            else:
                return []
        finally:
            if driver:
                try:
                    driver.quit()
                    print("🔒 WebDriver已关闭")
                except:
                    pass

        print(f"🎉 Selenium爬取完成！总共获取 {len(all_articles)} 篇文章")
        return all_articles

    def _fallback_crawl(self):
        """备用爬取方法"""
        try:
            print("🔄 使用备用方法：异步爬取...")
            import asyncio

            return asyncio.run(self.crawl_all_articles_async(max_pages=10))
        except Exception as e:
            print(f"❌ 备用方法也失败: {e}")
            return []

    def crawl_with_smart_strategy(self, max_scrolls: int = 30) -> List[Dict]:
        """使用智能策略进行爬取"""
        print("🧠 使用智能策略进行爬取...")

        if not self.selenium_available:
            print("⚠️  Selenium不可用，使用传统方法")
            return self._fallback_crawl()

        # 先尝试智能滚动
        print("🔍 检测网站加载方式...")

        driver = None
        try:
            driver = self.setup_selenium_driver(headless=True)
            if not driver:
                return self._fallback_crawl()

            # 访问页面分析结构
            driver.get(self.articles_url)
            time.sleep(3)

            # 检测页面类型
            has_button = self._find_load_more_button(driver) is not None
            page_source = driver.page_source.lower()

            # 检测无限滚动指示器
            infinite_indicators = ["infinite", "scroll", "lazy", "loadmore", "autoload"]
            has_infinite = any(
                indicator in page_source for indicator in infinite_indicators
            )

            print(f"📊 分析结果:")
            print(f"   🔘 加载更多按钮: {'是' if has_button else '否'}")
            print(f"   📜 无限滚动: {'是' if has_infinite else '否'}")

            if has_button:
                print("🔘 检测到按钮模式，使用按钮点击策略")
                max_scrolls = min(max_scrolls, 20)  # 按钮模式通常需要较少的滚动
            elif has_infinite:
                print("📜 检测到无限滚动模式，使用滚动策略")
                max_scrolls = max_scrolls
            else:
                print("🤔 未检测到明确的加载模式，使用混合策略")

            driver.quit()
            driver = None

            # 执行爬取
            return self.crawl_all_articles_with_selenium(
                max_scrolls=max_scrolls, show_browser=False
            )

        except Exception as e:
            print(f"❌ 智能策略执行失败: {e}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            return self._fallback_crawl()

    async def crawl_all_articles_async(self, max_pages: int = None) -> List[Dict]:
        """异步爬取所有文章，支持无限滚动"""
        all_articles = []
        seen_urls = set()  # 用于去重

        # 创建aiohttp会话，优化网络配置
        connector = aiohttp.TCPConnector(
            limit=30,  # 总连接池大小
            limit_per_host=15,  # 每个主机的连接数
            ttl_dns_cache=300,  # DNS缓存5分钟
            use_dns_cache=True,  # 启用DNS缓存
            keepalive_timeout=60,  # 保持连接时间
            enable_cleanup_closed=True,  # 启用清理已关闭连接
        )
        timeout = aiohttp.ClientTimeout(
            total=120, connect=30, sock_read=30  # 总超时时间  # 连接超时  # 读取超时
        )

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers,
        ) as session:
            print("开始爬取 Frontiers for Young Minds 文章（异步版本）...")

            # 首先获取第一页来检测无限滚动
            first_page_articles = await self.get_article_list_with_scroll_detection(
                session, 1
            )

            if not first_page_articles:
                print("无法获取第一页文章，停止爬取")
                return all_articles

            # 过滤第一页的重复文章
            unique_first_page = []
            for article in first_page_articles:
                if article.get("url") and article["url"] not in seen_urls:
                    seen_urls.add(article["url"])
                    unique_first_page.append(article)
            first_page_articles = unique_first_page

            # 如果没有指定max_pages，尝试检测无限滚动
            if max_pages is None:
                try:
                    # 获取第一页的HTML来检测无限滚动
                    response = await session.get(self.articles_url)
                    if response.status == 200:
                        content = await response.text()
                        soup = BeautifulSoup(content, "html.parser")

                        if self.detect_infinite_scroll(soup):
                            print("检测到无限滚动，自动估算最大页数...")
                            max_pages = self.get_max_pages_from_infinite_scroll(soup)
                            print(f"估算最大页数: {max_pages}")
                        else:
                            max_pages = 10  # 默认页数
                            print("未检测到无限滚动，使用默认页数: 10")
                except Exception as e:
                    print(f"检测无限滚动时出错: {e}，使用默认页数 10")
                    max_pages = 10

            # 限制最大页数以避免过度爬取
            max_pages = min(max_pages, 100)  # 增加到100页
            print(f"将爬取最多 {max_pages} 页")

            page = 1
            consecutive_empty_pages = 0

            while page <= max_pages:
                if page == 1:
                    articles = first_page_articles
                else:
                    page_articles = await self.get_article_list_with_scroll_detection(
                        session, page
                    )
                    # 过滤重复文章
                    unique_articles = []
                    for article in page_articles:
                        if article.get("url") and article["url"] not in seen_urls:
                            seen_urls.add(article["url"])
                            unique_articles.append(article)

                    if len(unique_articles) < len(page_articles):
                        print(
                            f"第 {page} 页去重: {len(page_articles)} -> {len(unique_articles)} 篇文章"
                        )

                    articles = unique_articles

                if not articles:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= 3:  # 连续3页没有新文章就停止
                        print(f"连续 {consecutive_empty_pages} 页没有新文章，停止爬取")
                        break
                    print(f"第 {page} 页没有新文章，继续下一页")
                    page += 1
                    continue

                consecutive_empty_pages = 0  # 重置计数器

                # 使用异步并发处理文章详情，但限制并发数
                semaphore = asyncio.Semaphore(12)  # 限制并发数为12

                async def process_article_with_semaphore(article):
                    async with semaphore:
                        result = await self.get_article_detail_async(session, article)
                        # 添加延迟以遵守爬虫礼仪
                        await asyncio.sleep(1)
                        return result

                # 创建并发任务
                tasks = [
                    process_article_with_semaphore(article) for article in articles
                ]

                # 执行所有任务
                detailed_articles = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理结果
                for detailed_article in detailed_articles:
                    if isinstance(detailed_article, Exception):
                        print(f"处理文章时出现异常: {detailed_article}")
                        continue
                    elif detailed_article:
                        all_articles.append(detailed_article)

                print(f"已完成第 {page} 页，当前总共 {len(all_articles)} 篇文章")

                page += 1

                # 页面间延迟，避免请求过快
                await asyncio.sleep(2)

        return all_articles

    def crawl_all_articles(
        self, max_pages: int = 100, use_selenium: bool = True
    ) -> List[Dict]:
        """爬取所有文章（同步版本，保持向后兼容）"""
        if use_selenium:
            # 优先使用Selenium进行真正的无限滚动爬取
            return self.crawl_all_articles_with_selenium()
        else:
            # 使用传统的异步方法作为备用
            return asyncio.run(self.crawl_all_articles_async(max_pages))

    def save_to_json(self, articles: List[Dict], output_path: str):
        """保存数据到JSON文件"""
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)

            print(f"\n数据已保存到: {output_path}")
            print(f"总共保存了 {len(articles)} 篇文章")

        except Exception as e:
            print(f"保存文件时出错: {e}")


async def main():
    """主函数（异步版本）"""
    crawler = FrontiersCrawler()

    # 输出路径
    output_path = "/Users/yzxbb/Desktop/Auto-Popsci/datasets/our_dataset/frontiers_kids/original_frontiers/all_frontiers_kids_articles.json"

    # 爬取所有文章（支持无限滚动，不限制页数以获取所有文章）
    articles = await crawler.crawl_all_articles_async(
        max_pages=None
    )  # None表示自动检测并获取所有文章

    # 保存数据
    crawler.save_to_json(articles, output_path)

    print("\n=== 爬取完成 ===")
    print(f"总共爬取了 {len(articles)} 篇文章")

    # 显示几个示例
    if articles:
        print("\n=== 文章示例 ===")
        for i, article in enumerate(articles[:3]):
            print(f"\n示例 {i+1}:")
            print(f"标题: {article.get('title', 'N/A')}")
            print(f"URL: {article.get('url', 'N/A')}")
            print(f"作者: {article.get('author', 'N/A')}")
            print(f"发布日期: {article.get('published_date', 'N/A')}")
            print(f"描述: {article.get('description', 'N/A')[:100]}...")
            content_preview = article.get("content", "N/A")[:200]
            print(f"内容预览: {content_preview}...")


def main_sync():
    """主函数 - 直接使用无限滚动爬取"""
    crawler = FrontiersCrawler()

    # 输出路径
    output_path = "/Users/yzxbb/Desktop/Auto-Popsci/datasets/our_dataset/frontiers_kids/original_frontiers/all_frontiers_kids_articles.json"

    print("🚀 Frontiers for Young Minds 无限滚动爬虫启动")
    print("=" * 50)
    print("📜 直接使用无限滚动模式进行爬取...")
    print("=" * 50)

    # 直接使用无限滚动模式进行爬取
    try:
        print("\n📜 开始无限滚动爬取...")
        print("🔥 无限制模式：将爬取所有能找到的文章！")
        articles = crawler.crawl_all_articles_with_selenium(
            max_scrolls=999,  # 移除滚动次数限制
            show_browser=False,
            max_articles=None,  # 移除文章数量限制，爬取所有文章
        )

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断了爬取过程")
        return
    except Exception as e:
        print(f"\n❌ 无限滚动过程中出现错误: {e}")
        print("🔄 尝试使用备用方法...")
        try:
            articles = crawler._fallback_crawl()
        except Exception as fallback_error:
            print(f"❌ 备用方法也失败: {fallback_error}")
            return

    # 保存数据
    print(f"\n💾 正在保存数据到: {output_path}")
    crawler.save_to_json(articles, output_path)

    # 生成CSV格式
    csv_path = output_path.replace(".json", ".csv")
    try:
        import pandas as pd

        df = pd.DataFrame(articles)
        df.to_csv(csv_path, index=False, encoding="utf-8")
        print(f"📊 CSV文件也已保存到: {csv_path}")
    except Exception as e:
        print(f"⚠️  保存CSV文件时出错: {e}")

    # 显示统计信息
    print("\n" + "=" * 50)
    print("🎉 爬取完成！")
    print(f"📄 总共爬取了 {len(articles)} 篇文章")

    if articles:
        # 统计信息
        titles = [a.get("title", "") for a in articles if a.get("title")]
        authors = [a.get("author", "") for a in articles if a.get("author")]
        with_content = [a for a in articles if a.get("content", "").strip()]

        print(f"📊 统计信息:")
        print(f"   有标题的文章: {len(titles)}")
        print(f"   有作者的文章: {len(authors)}")
        print(f"   有内容的文章: {len(with_content)}")

        # 显示示例
        print("\n📖 文章示例 (前3篇):")
        for i, article in enumerate(articles[:3]):
            print(f"\n📄 示例 {i+1}:")
            print(f"   📝 标题: {article.get('title', 'N/A')}")
            print(f"   🔗 URL: {article.get('url', 'N/A')}")
            print(f"   ✍️  作者: {article.get('author', 'N/A')}")
            print(f"   📅 发布日期: {article.get('published_date', 'N/A')}")
            print(f"   📄 描述: {article.get('description', 'N/A')[:100]}...")

            content = article.get("content", "N/A")
            if content and content != "N/A":
                content_preview = content.replace("\n", " ")[:150]
                print(f"   📖 内容预览: {content_preview}...")

    print(f"\n💾 数据文件位置:")
    print(f"   📄 JSON: {output_path}")
    print(f"   📊 CSV: {csv_path if 'csv_path' in locals() else 'N/A'}")
    print("=" * 50)


if __name__ == "__main__":
    main_sync()  # 使用同步版本以避免直接运行asyncio
