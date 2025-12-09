#!/usr/bin/env python3
"""
Pitara 文章爬虫
爬取 https://www.pitara.com 下的所有文章
保存为与 NatGeo Kids 相同的 JSON 格式
"""

import requests
import json
import time
import os
import re
import asyncio
import aiohttp
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from typing import Dict, List, Optional, Set
import warnings

# 忽略XML警告
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class PitaraCrawler:
    def __init__(self):
        """初始化爬虫"""
        self.base_url = "https://www.pitara.com"
        self.session = requests.Session()
        
        # Pitara网站的正确分类URL结构
        self.categories = {
            # Science 类别
            "5ws-and-h": f"{self.base_url}/science-for-kids/5ws-and-h/",
            "planet-earth": f"{self.base_url}/science-for-kids/planet-earth-for-kids/",
            "living-world": f"{self.base_url}/science-for-kids/living-world-for-kids/",
            "science-news": f"{self.base_url}/science-for-kids/science-news-for-kids/",
            
            # Fiction 类别
            "stories": f"{self.base_url}/fiction-for-kids/stories-for-kids/",
            "poems": f"{self.base_url}/fiction-for-kids/poems-for-kids/",
            "folktales": f"{self.base_url}/fiction-for-kids/folktales/",
            "book-reviews": f"{self.base_url}/fiction-for-kids/childrens-books/",
            "hindi-stories": f"{self.base_url}/fiction-for-kids/hindi-stories-for-kids/",
            "hindi-poems": f"{self.base_url}/fiction-for-kids/hindi-poems-for-kids/",
            
            # Non-fiction 类别
            "features": f"{self.base_url}/non-fiction-for-kids/features-for-kids/",
            "biographies": f"{self.base_url}/non-fiction-for-kids/biographies-for-kids/",
            "festivals": f"{self.base_url}/non-fiction-for-kids/festivals-for-kids/",
            "did-you-know": f"{self.base_url}/non-fiction-for-kids/did-you-know-for-kids/",
            "quotes": f"{self.base_url}/non-fiction-for-kids/quotes-for-kids/",
            "proverbs": f"{self.base_url}/non-fiction-for-kids/proverbs-for-kids/",
            "news": f"{self.base_url}/news-for-kids/world-news/",
            
            # Activities 类别
            "quizzes": f"{self.base_url}/quizzes-for-kids/",
            "art-quizzes": f"{self.base_url}/quizzes-for-kids/art-quizzes-for-kids/",
            "geography-quizzes": f"{self.base_url}/quizzes-for-kids/geography-quizzes-for-kids/",
            "history-quizzes": f"{self.base_url}/quizzes-for-kids/history-quizzes-for-kids/",
            "science-quizzes": f"{self.base_url}/quizzes-for-kids/science-quizzes-for-kids/",
            "art-activities": f"{self.base_url}/art-craft-for-kids/art-for-kids/",
            "coloring-pages": f"{self.base_url}/art-craft-for-kids/coloring-pages/",
            "craft-activities": f"{self.base_url}/art-craft-for-kids/craft-activities-for-kids/",
            "puzzles": f"{self.base_url}/games-puzzles-for-kids/matching-puzzles/",
            
            # Wordplay 类别
            "jokes": f"{self.base_url}/fun-stuff-for-kids/jokes-for-kids/",
            "riddles": f"{self.base_url}/fun-stuff-for-kids/riddles-for-kids/",
            "tongue-twisters": f"{self.base_url}/fun-stuff-for-kids/tongue-twisters-for-kids/",
        }
        
        # 初始化requests会话
        self.init_session()
        
    def init_session(self):
        """初始化requests会话"""
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

    def get_category_from_url(self, url: str) -> str:
        """从URL中提取分类"""
        try:
            # 根据URL路径匹配分类
            if "/science-for-kids/5ws-and-h/" in url:
                return "5ws-and-h"
            elif "/science-for-kids/planet-earth-for-kids/" in url:
                return "planet-earth"
            elif "/science-for-kids/living-world-for-kids/" in url:
                return "living-world"
            elif "/science-for-kids/science-news-for-kids/" in url:
                return "science-news"
            elif "/fiction-for-kids/stories-for-kids/" in url:
                return "stories"
            elif "/fiction-for-kids/poems-for-kids/" in url:
                return "poems"
            elif "/fiction-for-kids/folktales/" in url:
                return "folktales"
            elif "/fiction-for-kids/childrens-books/" in url:
                return "book-reviews"
            elif "/fiction-for-kids/hindi-stories-for-kids/" in url:
                return "hindi-stories"
            elif "/fiction-for-kids/hindi-poems-for-kids/" in url:
                return "hindi-poems"
            elif "/non-fiction-for-kids/features-for-kids/" in url:
                return "features"
            elif "/non-fiction-for-kids/biographies-for-kids/" in url:
                return "biographies"
            elif "/non-fiction-for-kids/festivals-for-kids/" in url:
                return "festivals"
            elif "/non-fiction-for-kids/did-you-know-for-kids/" in url:
                return "did-you-know"
            elif "/non-fiction-for-kids/quotes-for-kids/" in url:
                return "quotes"
            elif "/non-fiction-for-kids/proverbs-for-kids/" in url:
                return "proverbs"
            elif "/quizzes-for-kids/" in url:
                return "quizzes"
            elif "/art-craft-for-kids/" in url:
                return "art-craft"
            elif "/fun-stuff-for-kids/" in url:
                return "wordplay"
            elif "/news-for-kids/" in url:
                return "news"
            else:
                # 从URL路径提取
                parsed = urlparse(url)
                path_parts = [p for p in parsed.path.strip('/').split('/') if p]
                if len(path_parts) >= 2:
                    return path_parts[1]
                elif len(path_parts) == 1:
                    return path_parts[0]
                return "unknown"
        except Exception:
            return "unknown"

    def is_article_url(self, url: str) -> bool:
        """判断URL是否是文章链接"""
        if not url:
            return False
            
        # 必须是pitara.com的链接
        if url.startswith("http") and "pitara.com" not in url:
            return False
        
        # 排除分类首页、标签页面、作者页面等
        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/wp-content/", "/wp-includes/", "/feed/",
            "#", "javascript:", "mailto:", 
            "/search/", "/login/", "/register/",
            "/corporate/", "/index.xml",
            "babynames.pitara.com",
        ]
        
        for pattern in exclude_patterns:
            if pattern in url.lower():
                return False
        
        # 排除纯图片链接
        if any(url.lower().endswith(ext) for ext in ['.jpg', '.png', '.gif', '.jpeg', '.webp', '.svg']):
            return False
        
        # 检查是否是分类列表页面（结尾是 -for-kids/ 或类似的）
        category_pages = [
            "/science-for-kids/$",
            "/fiction-for-kids/$",
            "/non-fiction-for-kids/$",
            "/art-craft-for-kids/$",
            "/quizzes-for-kids/$",
            "/fun-stuff-for-kids/$",
            "/games-puzzles-for-kids/$",
            "/news-for-kids/$",
        ]
        
        for pattern in category_pages:
            if re.search(pattern.replace('$', '/?$'), url):
                return False
        
        # 检查是否是子分类页面
        subcategory_pages = [
            "-for-kids/$",
            "/folktales/$",
            "/5ws-and-h/$",
        ]
        
        # 允许子分类页面下的具体文章
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]
        
        # 文章URL通常有3个或更多路径部分（如 /fiction-for-kids/stories-for-kids/article-name/）
        if len(path_parts) >= 3:
            return True
        
        # 对于某些特殊分类，允许2个路径部分
        if len(path_parts) == 2:
            # 检查第二部分是否看起来像文章slug（不以-for-kids结尾）
            if not path_parts[1].endswith("-for-kids") and not path_parts[1].endswith("-quizzes"):
                return True
        
        return False

    def get_article_links_from_category(self, category_url: str, category_name: str) -> List[Dict]:
        """从分类页面获取所有文章链接"""
        articles = []
        page = 1
        seen_urls = set()
        max_pages = 50  # 限制最大页数
        
        while page <= max_pages:
            try:
                if page == 1:
                    url = category_url
                else:
                    # Pitara使用 /page/N/ 格式分页
                    url = f"{category_url.rstrip('/')}/page/{page}/"
                
                print(f"   📄 正在获取第 {page} 页: {url}")
                response = self.session.get(url, timeout=30)
                
                # 如果页面不存在，停止
                if response.status_code == 404:
                    print(f"   📌 分类 [{category_name}] 没有更多页面（共{page-1}页）")
                    break
                    
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
                
                page_articles = 0
                
                # 查找所有文章卡片 - Pitara使用 uk-card 样式
                article_cards = soup.select("div.uk-card")
                
                for card in article_cards:
                    # 找到文章链接
                    link = card.find("a", href=True)
                    if not link:
                        continue
                    
                    href = link.get("href", "")
                    full_url = urljoin(self.base_url, href)
                    
                    if not self.is_article_url(full_url):
                        continue
                    
                    if full_url in seen_urls:
                        continue
                    
                    seen_urls.add(full_url)
                    
                    # 提取标题
                    title_elem = card.find(["h4", "h3", "h2", "a"])
                    title = title_elem.get_text(strip=True) if title_elem else "Unknown"
                    
                    # 提取描述
                    desc_elem = card.find("p")
                    description = desc_elem.get_text(strip=True) if desc_elem else ""
                    
                    # 提取图片
                    img_elem = card.find("img")
                    image_url = ""
                    if img_elem:
                        image_url = img_elem.get("data-src") or img_elem.get("src") or ""
                        if image_url and not image_url.startswith("http"):
                            image_url = urljoin(self.base_url, image_url)
                    
                    articles.append({
                        "url": full_url,
                        "title": title,
                        "description": description,
                        "category": category_name,
                        "image_url": image_url,
                    })
                    page_articles += 1
                
                # 如果没找到卡片，尝试其他选择器
                if page_articles == 0:
                    # 尝试查找所有文章链接
                    all_links = soup.find_all("a", href=True)
                    for link in all_links:
                        href = link.get("href", "")
                        full_url = urljoin(self.base_url, href)
                        
                        if not self.is_article_url(full_url):
                            continue
                        
                        if full_url in seen_urls:
                            continue
                        
                        # 检查链接是否在主内容区域
                        parent = link.find_parent(["article", "main", "div"], class_=re.compile(r"content|article|post|entry"))
                        if not parent:
                            continue
                        
                        seen_urls.add(full_url)
                        title = link.get_text(strip=True) or "Unknown"
                        
                        articles.append({
                            "url": full_url,
                            "title": title,
                            "description": "",
                            "category": category_name,
                            "image_url": "",
                        })
                        page_articles += 1
                
                print(f"      找到 {page_articles} 篇文章")
                
                if page_articles == 0:
                    print(f"   📌 分类 [{category_name}] 第 {page} 页没有新文章，停止")
                    break
                
                page += 1
                time.sleep(0.5)  # 请求间隔
                
            except requests.RequestException as e:
                print(f"   ❌ 获取分类页面时出错: {e}")
                break
            except Exception as e:
                print(f"   ❌ 解析分类页面时出错: {e}")
                break
        
        return articles

    def get_article_detail(self, article_data: Dict) -> Dict:
        """获取文章详情"""
        try:
            url = article_data["url"]
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # 提取标题
            title = article_data.get("title", "")
            if not title or title == "Unknown":
                title_elem = soup.find("h1")
                if title_elem:
                    title = title_elem.get_text(strip=True)
                else:
                    # 从<title>标签提取
                    title_tag = soup.find("title")
                    if title_tag:
                        title = title_tag.get_text(strip=True).split("|")[0].strip()
            article_data["title"] = title
            
            # 提取作者
            author = self.extract_author(soup)
            article_data["author"] = author
            
            # 提取发布日期
            published_date = self.extract_date(soup)
            article_data["published_date"] = published_date
            
            # 提取文章内容
            content = self.extract_content(soup)
            article_data["content"] = content
            
            # 提取描述
            if not article_data.get("description"):
                desc_elem = soup.find("meta", attrs={"name": "description"}) or \
                           soup.find("meta", attrs={"property": "og:description"})
                if desc_elem:
                    article_data["description"] = desc_elem.get("content", "")
                elif content:
                    # 使用内容的前200个字符作为描述
                    clean_content = re.sub(r'\s+', ' ', content).strip()
                    article_data["description"] = clean_content[:200] + "..." if len(clean_content) > 200 else clean_content
            
            # 提取图片URL
            if not article_data.get("image_url"):
                img_elem = soup.find("meta", attrs={"property": "og:image"})
                if img_elem:
                    article_data["image_url"] = img_elem.get("content", "")
            
            # 提取相关文章
            related_articles = self.extract_related_articles(soup)
            article_data["related_articles"] = related_articles
            
            # 提取元数据
            meta_data = self.extract_metadata(soup)
            article_data["meta_data"] = meta_data
            
            return article_data
            
        except requests.RequestException as e:
            print(f"   ❌ 获取文章详情时出错 ({article_data.get('url', 'unknown')}): {e}")
            return article_data
        except Exception as e:
            print(f"   ❌ 解析文章详情时出错 ({article_data.get('url', 'unknown')}): {e}")
            return article_data

    def extract_author(self, soup: BeautifulSoup) -> str:
        """提取作者信息"""
        try:
            # 尝试从meta标签获取
            meta_author = soup.find("meta", attrs={"name": "author"})
            if meta_author:
                author = meta_author.get("content", "").strip()
                if author:
                    return author
            
            # 尝试从页面内容获取
            author_selectors = [
                ("a", {"rel": "author"}),
                ("span", {"class": re.compile(r"author")}),
                ("div", {"class": re.compile(r"author")}),
                ("p", {"class": re.compile(r"author")}),
            ]
            
            for tag, attrs in author_selectors:
                elem = soup.find(tag, attrs)
                if elem:
                    author = elem.get_text(strip=True)
                    if author:
                        return author
            
            return "Unknown"
            
        except Exception:
            return "Unknown"

    def extract_date(self, soup: BeautifulSoup) -> str:
        """提取发布日期"""
        try:
            # 尝试从meta标签获取
            date_metas = [
                ("meta", {"property": "article:published_time"}),
                ("meta", {"name": "date"}),
                ("meta", {"name": "DC.date.issued"}),
            ]
            
            for tag, attrs in date_metas:
                elem = soup.find(tag, attrs)
                if elem:
                    date_str = elem.get("content", "").strip()
                    if date_str:
                        # 格式化日期
                        return date_str.split("T")[0] if "T" in date_str else date_str
            
            # 尝试从页面内容获取
            time_elem = soup.find("time")
            if time_elem:
                return time_elem.get("datetime", "") or time_elem.get_text(strip=True)
            
            # 尝试其他选择器
            date_selectors = [
                ("span", {"class": re.compile(r"date|time")}),
                ("div", {"class": re.compile(r"date|time")}),
            ]
            
            for tag, attrs in date_selectors:
                elem = soup.find(tag, attrs)
                if elem:
                    date_text = elem.get_text(strip=True)
                    if date_text:
                        return date_text
            
            return ""
            
        except Exception:
            return ""

    def clean_content(self, content: str) -> str:
        """清理内容，去除面包屑导航和元数据"""
        if not content:
            return ""
        
        # 如果内容已经是用 \n\n 分隔的段落，直接处理
        # 否则按段落分割
        if '\n\n' in content:
            lines = content.split('\n\n')
        else:
            # 如果没有双换行，尝试按单换行分割，但只分割明显的段落
            lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 跳过面包屑导航（包含 Home/ 开头的行）
            if line.startswith('Home/'):
                continue
            
            # 跳过元数据行（包含 words | minutes、Readability、Filed under、Tags 等）
            line_lower = line.lower()
            if re.search(r'\d+\s*words\s*\|', line_lower):
                continue
            if 'readability:' in line_lower or 'based on flesch' in line_lower:
                continue
            if 'filed under:' in line_lower or line_lower.startswith('filed under'):
                continue
            if line.strip().startswith('Tags:') or (line.strip().startswith('#') and len(line.strip()) < 50):
                continue
            if re.match(r'^#\w+(\s|$)', line.strip()):  # 以 # 开头的标签行
                continue
            
            # 跳过非常短的纯作者名（通常只有名字，没有标点，且长度很短）
            if len(line) < 25 and not re.search(r'[.!?;:]', line):
                # 可能是作者名，跳过
                continue
            
            # 保留所有其他内容（包括短段落，只要它们包含标点符号）
            cleaned_lines.append(line)
        
        result = '\n\n'.join(cleaned_lines)
        # 清理多余空白
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result.strip()

    def extract_content(self, soup: BeautifulSoup) -> str:
        """提取文章内容"""
        try:
            content_sections = []
            
            # Pitara的文章内容通常在 uk-article 或 article-body 类中
            # 首先找主要内容区域
            main_content = None
            
            # 尝试多种选择器 - 按优先级排列
            content_selectors = [
                "div.article-body",           # Pitara 主要使用这个
                "div.uk-article",             # UIKit 框架的文章类
                "div.uk-container-small",     # 小容器
                "article",
                "div.entry-content",
                "div.post-content",
                "div.article-content",
                "main",
            ]
            
            for selector in content_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    # 验证是否包含段落内容
                    if main_content.find("p"):
                        break
            
            if not main_content:
                # 尝试找包含文章内容的container
                main_content = soup.find("div", class_=re.compile(r"article|content"))
            
            if not main_content:
                main_content = soup.find("body")
            
            if main_content:
                # 直接提取所有 <p> 标签的文本内容（不创建副本，避免丢失内容）
                all_paragraphs = main_content.find_all("p")
                for p in all_paragraphs:
                    text = p.get_text(strip=True)
                    if not text:
                        continue
                    
                    # 跳过明显的导航和元数据
                    skip_phrases = [
                        "copyright", "all rights reserved", "privacy policy",
                        "terms of use", "contact us", "about us",
                        "pitara kids", "source:", "advertisement",
                        "you may also be interested in these",
                        "words |", "minutes", "readability:", "filed under:", "tags:"
                    ]
                    
                    # 跳过面包屑导航（以 Home/ 开头）
                    if text.startswith("Home/"):
                        continue
                    
                    # 跳过纯元数据行（包含字数统计、可读性等）
                    text_lower = text.lower()
                    if any(skip in text_lower for skip in skip_phrases):
                        continue
                    
                    # 跳过非常短的纯作者名（通常只有名字，没有标点）
                    if len(text) < 30 and not re.search(r'[.!?;:]', text):
                        # 可能是作者名，跳过
                        continue
                    
                    # 保留所有其他内容
                    content_sections.append(text)
                
                # 如果没有找到段落，尝试提取标题和其他元素
                if not content_sections:
                    for element in main_content.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol", "blockquote"]):
                        text = element.get_text(strip=True)
                        
                        if not text or len(text) < 5:
                            continue
                        
                        # 跳过导航和页脚文本
                        skip_phrases = [
                            "copyright", "all rights reserved", "privacy policy",
                            "terms of use", "contact us", "about us", "home",
                            "pitara kids", "source:", "advertisement"
                        ]
                        if any(skip in text.lower() for skip in skip_phrases):
                            continue
                    
                        # 为标题添加markdown格式
                        if element.name in ["h1", "h2", "h3", "h4"]:
                            level = int(element.name[1])
                            content_sections.append(f"\n{'#' * level} {text}\n")
                        elif element.name in ["ul", "ol"]:
                            # 处理列表
                            list_items = element.find_all("li")
                            for item in list_items:
                                item_text = item.get_text(strip=True)
                                if item_text and len(item_text) > 3:
                                    content_sections.append(f"• {item_text}")
                        elif element.name == "blockquote":
                            content_sections.append(f"> {text}")
                        else:
                            content_sections.append(text)
            
            raw_content = "\n\n".join(content_sections)
            # 清理多余空白
            raw_content = re.sub(r'\n{3,}', '\n\n', raw_content)
            # 清理面包屑导航和元数据
            cleaned_content = self.clean_content(raw_content)
            return cleaned_content
            
        except Exception as e:
            print(f"   ⚠️ 提取内容时出错: {e}")
            return ""

    def extract_related_articles(self, soup: BeautifulSoup) -> List[Dict]:
        """提取相关文章"""
        try:
            related = []
            
            # 查找相关文章区域
            related_section = soup.find(["div", "section", "aside"], class_=re.compile(r"related|similar"))
            
            if related_section:
                links = related_section.find_all("a", href=True)
                for link in links[:5]:  # 最多5篇相关文章
                    href = link.get("href", "")
                    title = link.get_text(strip=True)
                    if href and title and self.is_article_url(urljoin(self.base_url, href)):
                        full_url = urljoin(self.base_url, href)
                        related.append({
                            "title": title,
                            "url": full_url
                        })
            
            return related
            
        except Exception:
            return []

    def extract_metadata(self, soup: BeautifulSoup) -> Dict:
        """提取元数据"""
        try:
            meta_data = {}
            
            # 提取关键词
            keywords_elem = soup.find("meta", attrs={"name": "keywords"})
            if keywords_elem:
                keywords = keywords_elem.get("content", "").strip()
                if keywords:
                    meta_data["keywords"] = keywords
            
            # 提取标签
            tags = []
            tag_elements = soup.select(".tags a, .tag a, [rel='tag'], .uk-label a")
            for tag_elem in tag_elements:
                tag_text = tag_elem.get_text(strip=True)
                if tag_text and tag_text not in tags:
                    tags.append(tag_text)
            if tags:
                meta_data["tags"] = tags
            
            return meta_data
            
        except Exception:
            return {}

    async def get_article_detail_async(
        self,
        session: aiohttp.ClientSession,
        article_data: Dict,
        semaphore: asyncio.Semaphore,
        current: int,
        total: int
    ) -> Dict:
        """异步获取文章详情"""
        async with semaphore:
            try:
                url = article_data["url"]
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        print(f"   ⚠️ HTTP {response.status}: {url}")
                        return article_data
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # 提取标题
                    if not article_data.get("title") or article_data["title"] == "Unknown":
                        title_elem = soup.find("h1")
                        if title_elem:
                            article_data["title"] = title_elem.get_text(strip=True)
                        else:
                            title_tag = soup.find("title")
                            if title_tag:
                                article_data["title"] = title_tag.get_text(strip=True).split("|")[0].strip()
                    
                    # 提取作者
                    article_data["author"] = self.extract_author(soup)
                    
                    # 提取日期
                    article_data["published_date"] = self.extract_date(soup)
                    
                    # 提取内容
                    article_data["content"] = self.extract_content(soup)
                    
                    # 提取描述
                    if not article_data.get("description"):
                        desc_elem = soup.find("meta", attrs={"name": "description"}) or \
                                   soup.find("meta", attrs={"property": "og:description"})
                        if desc_elem:
                            article_data["description"] = desc_elem.get("content", "")
                        elif article_data.get("content"):
                            clean_content = re.sub(r'\s+', ' ', article_data["content"]).strip()
                            article_data["description"] = clean_content[:200] + "..." if len(clean_content) > 200 else clean_content
                    
                    # 提取图片
                    if not article_data.get("image_url"):
                        img_elem = soup.find("meta", attrs={"property": "og:image"})
                        if img_elem:
                            article_data["image_url"] = img_elem.get("content", "")
                    
                    # 提取相关文章
                    article_data["related_articles"] = self.extract_related_articles(soup)
                    
                    # 提取元数据
                    article_data["meta_data"] = self.extract_metadata(soup)
                    
                    if current % 20 == 0 or current == total:
                        print(f"   📊 进度: {current}/{total} ({current/total*100:.1f}%)")
                    
                    # 添加延迟以遵守爬虫礼仪
                    await asyncio.sleep(0.3)
                    
                    return article_data
                    
            except asyncio.TimeoutError:
                print(f"   ⚠️ 请求超时: {article_data.get('url', 'unknown')}")
                return article_data
            except Exception as e:
                print(f"   ❌ 获取文章详情出错: {e}")
                return article_data

    async def crawl_all_articles_async(self, max_concurrent: int = 10, urls_file_path: Optional[str] = None, use_saved_urls: bool = True) -> List[Dict]:
        """异步爬取所有文章
        
        Args:
            max_concurrent: 最大并发数
            urls_file_path: URL列表文件路径（如果为None，使用默认路径）
            use_saved_urls: 是否使用已保存的URL列表（如果存在）
        """
        print("🚀 开始爬取 Pitara 文章...")
        print(f"📂 共有 {len(self.categories)} 个分类需要处理\n")
        
        # 确定URL列表文件路径
        if urls_file_path is None:
            output_dir = os.path.dirname(os.path.abspath(__file__))
            urls_file_path = os.path.join(output_dir, "pitara_article_urls.json")
        
        # 第一步：获取所有分类的文章列表
        all_article_previews = []
        
        # 尝试加载已保存的URL列表
        if use_saved_urls:
            saved_urls = self.load_urls_from_json(urls_file_path)
            if saved_urls:
                all_article_previews = saved_urls
                print(f"📋 使用已保存的URL列表，共 {len(all_article_previews)} 个URL\n")
            else:
                print("📋 未找到已保存的URL列表，开始获取URL...\n")
        
        # 如果需要获取URL列表
        if not all_article_previews:
            seen_urls: Set[str] = set()
            
            for category_name, category_url in self.categories.items():
                print(f"📂 正在处理分类: {category_name}")
                articles = self.get_article_links_from_category(category_url, category_name)
                
                # 去重
                new_count = 0
                for article in articles:
                    url = article.get("url")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_article_previews.append(article)
                        new_count += 1
                
                print(f"   ✅ 分类 [{category_name}] 新增 {new_count} 篇文章（去重后）\n")
                time.sleep(0.5)  # 分类之间的延迟
            
            print(f"📊 总共找到 {len(all_article_previews)} 篇不重复的文章\n")
            
            # 保存URL列表
            if all_article_previews:
                self.save_urls_to_json(all_article_previews, urls_file_path)
                print()
        
        if not all_article_previews:
            print("❌ 未找到任何文章")
            return []
        
        # 第二步：异步获取所有文章详情
        print(f"📖 开始获取文章详情 (并发数: {max_concurrent})...")
        
        connector = aiohttp.TCPConnector(limit=max_concurrent, limit_per_host=max_concurrent)
        timeout = aiohttp.ClientTimeout(total=120)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            semaphore = asyncio.Semaphore(max_concurrent)
            total = len(all_article_previews)
            
            tasks = [
                self.get_article_detail_async(session, article, semaphore, i + 1, total)
                for i, article in enumerate(all_article_previews)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤有效结果 - 放宽条件，只要有标题就保存
        valid_articles = []
        for result in results:
            if isinstance(result, Exception):
                print(f"   ❌ 任务异常: {result}")
                continue
            if result and result.get("title"):
                # 确保有基本内容，即使很短也保留
                if not result.get("content"):
                    result["content"] = result.get("description", "")
                valid_articles.append(result)
        
        print(f"\n✅ 成功获取 {len(valid_articles)}/{len(all_article_previews)} 篇文章详情")
        
        return valid_articles

    def crawl_all_articles(self, use_saved_urls: bool = True) -> List[Dict]:
        """爬取所有文章（同步入口）
        
        Args:
            use_saved_urls: 是否使用已保存的URL列表（如果存在）
        """
        return asyncio.run(self.crawl_all_articles_async(use_saved_urls=use_saved_urls))

    def save_urls_to_json(self, article_previews: List[Dict], urls_file_path: str):
        """保存URL列表到JSON文件"""
        try:
            # 确保输出目录存在
            dir_path = os.path.dirname(urls_file_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            
            with open(urls_file_path, "w", encoding="utf-8") as f:
                json.dump(article_previews, f, ensure_ascii=False, indent=4)
            
            print(f"💾 URL列表已保存到: {urls_file_path}")
            print(f"📊 总共保存了 {len(article_previews)} 个URL")
            
        except Exception as e:
            print(f"❌ 保存URL列表时出错: {e}")

    def load_urls_from_json(self, urls_file_path: str) -> Optional[List[Dict]]:
        """从JSON文件加载URL列表"""
        try:
            if not os.path.exists(urls_file_path):
                return None
            
            with open(urls_file_path, "r", encoding="utf-8") as f:
                article_previews = json.load(f)
            
            print(f"✅ 从文件加载了 {len(article_previews)} 个URL: {urls_file_path}")
            return article_previews
            
        except Exception as e:
            print(f"⚠️ 加载URL列表时出错: {e}")
            return None

    def save_to_json(self, articles: List[Dict], output_path: str):
        """保存数据到JSON文件"""
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 格式化数据以匹配参考格式
            formatted_articles = []
            for article in articles:
                formatted_article = {
                    "url": article.get("url", ""),
                    "category": article.get("category", "unknown"),
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "author": article.get("author", "Unknown"),
                    "published_date": article.get("published_date", ""),
                    "content": article.get("content", ""),
                    "image_url": article.get("image_url", ""),
                    "related_articles": article.get("related_articles", []),
                    "meta_data": article.get("meta_data", {})
                }
                formatted_articles.append(formatted_article)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(formatted_articles, f, ensure_ascii=False, indent=4)
            
            print(f"\n💾 数据已保存到: {output_path}")
            print(f"📊 总共保存了 {len(formatted_articles)} 篇文章")
            
        except Exception as e:
            print(f"❌ 保存文件时出错: {e}")


def main():
    """主函数"""
    import sys
    
    crawler = PitaraCrawler()
    
    # 输出路径
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "all_pitara_articles.json")
    
    print("=" * 60)
    print("🌟 Pitara 文章爬虫")
    print("=" * 60)
    
    # 检查命令行参数，是否强制重新获取URL列表
    use_saved_urls = True
    if len(sys.argv) > 1 and sys.argv[1] in ["--fresh-urls", "-f"]:
        use_saved_urls = False
        print("🔄 强制重新获取URL列表\n")
    
    # 爬取所有文章
    articles = crawler.crawl_all_articles(use_saved_urls=use_saved_urls)
    
    # 保存数据
    if articles:
        crawler.save_to_json(articles, output_path)
        
        # 显示统计信息
        print("\n" + "=" * 60)
        print("📊 爬取统计")
        print("=" * 60)
        
        # 按分类统计
        categories = {}
        for article in articles:
            cat = article.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\n分类统计:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            print(f"   {cat}: {count} 篇")
        
        # 显示示例
        print("\n📖 文章示例 (前3篇):")
        for i, article in enumerate(articles[:3]):
            print(f"\n示例 {i+1}:")
            print(f"   标题: {article.get('title', 'N/A')}")
            print(f"   URL: {article.get('url', 'N/A')}")
            print(f"   分类: {article.get('category', 'N/A')}")
            print(f"   作者: {article.get('author', 'N/A')}")
            content = article.get("content", "")
            if content:
                print(f"   内容预览: {content[:100]}...")
    else:
        print("❌ 未能获取到任何文章")
    
    print("\n" + "=" * 60)
    print("🎉 爬取完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
