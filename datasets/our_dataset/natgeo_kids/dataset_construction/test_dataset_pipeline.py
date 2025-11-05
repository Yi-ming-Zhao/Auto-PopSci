#!/usr/bin/env python3
"""
测试Wikipedia-NatGeo数据集构建管道（简化版，使用本地规则而非LLM）
"""

import json
import os
import requests
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re

# 配置参数
NATGEO_DATA_PATH = "/Users/yzxbb/Desktop/Auto-Popsci/datasets/our_dataset/natgeo_kids/all_natgeo_kids_articles.json"
OUTPUT_PATH = "/Users/yzxbb/Desktop/Auto-Popsci/datasets/our_dataset/wikipedia_natgeo_pairs_test.json"
SAMPLE_SIZE = 5  # 测试用，只处理5篇文章

@dataclass
class WikipediaNatgeoPair:
    """Wikipedia原文-NatGeo科普对数据结构"""
    natgeo_article: Dict
    wikipedia_search_keyword: str
    wikipedia_title: str
    wikipedia_content: str
    wikipedia_url: str

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "natgeo_article": {
                "title": self.natgeo_article.get("title", ""),
                "description": self.natgeo_article.get("description", ""),
                "content": self.natgeo_article.get("content", ""),
                "url": self.natgeo_article.get("url", ""),
                "category": self.natgeo_article.get("category", ""),
                "image_url": self.natgeo_article.get("image_url", "")
            },
            "wikipedia_search_keyword": self.wikipedia_search_keyword,
            "wikipedia_title": self.wikipedia_title,
            "wikipedia_content": self.wikipedia_content,
            "wikipedia_url": self.wikipedia_url
        }

def extract_keyword_simple(description: str) -> str:
    """使用简单规则提取Wikipedia搜索关键词

    Args:
        description: NatGeo文章描述

    Returns:
        Wikipedia搜索关键词
    """
    # 常见的科普主题关键词
    animal_keywords = ["shark", "whale", "dolphin", "turtle", "elephant", "lion", "tiger", "penguin", "bear", "wolf"]
    science_keywords = ["climate", "space", "planet", "star", "energy", "environment", "ocean", "forest", "volcano", "earthquake"]
    festival_keywords = ["festival", "celebration", "tradition", "culture"]

    description_lower = description.lower()

    # 检查动物关键词
    for animal in animal_keywords:
        if animal in description_lower:
            return animal.capitalize()

    # 检查科学关键词
    for science in science_keywords:
        if science in description_lower:
            return science.capitalize()

    # 检查节日关键词
    for festival in festival_keywords:
        if festival in description_lower:
            return festival.capitalize()

    # 如果没有匹配的关键词，提取描述中的第一个名词短语
    # 简单处理：取前3-4个词
    words = description.split()
    if len(words) >= 3:
        return " ".join(words[:3])
    else:
        return description

def search_wikipedia(keyword: str) -> Optional[Tuple[str, str, str]]:
    """在Wikipedia中搜索关键词

    Args:
        keyword: 搜索关键词

    Returns:
        (标题, 内容, URL) 的元组，如果搜索失败返回None
    """
    try:
        print(f"  正在搜索Wikipedia: {keyword}")

        # 使用Wikipedia API直接搜索
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": keyword,
            "format": "json",
            "srlimit": 1
        }

        search_response = requests.get(search_url, params=search_params)
        search_response.raise_for_status()
        search_data = search_response.json()

        # 检查搜索结果
        search_results = search_data.get("query", {}).get("search", [])
        if not search_results:
            print(f"  未找到关键词 '{keyword}' 的Wikipedia页面")
            return None

        # 获取第一个搜索结果的标题
        page_title = search_results[0]["title"]
        print(f"  找到Wikipedia页面: {page_title}")

        # 获取页面内容
        content_params = {
            "action": "query",
            "prop": "extracts",
            "explaintext": True,
            "exintro": False,
            "titles": page_title,
            "format": "json"
        }

        content_response = requests.get(search_url, params=content_params)
        content_response.raise_for_status()
        content_data = content_response.json()

        # 提取页面内容
        pages = content_data.get("query", {}).get("pages", {})
        page_content = ""
        for page_id, page_info in pages.items():
            if "extract" in page_info:
                page_content = page_info["extract"]
                break

        if not page_content:
            print(f"  无法获取页面内容")
            return None

        # 构建页面URL
        page_url = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"

        return page_title, page_content, page_url

    except Exception as e:
        print(f"  Wikipedia搜索 '{keyword}' 时出错: {e}")
        return None

def load_natgeo_articles(file_path: str, sample_size: Optional[int] = None) -> List[Dict]:
    """加载NatGeo Kids文章数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    if sample_size:
        articles = articles[:sample_size]

    print(f"加载了 {len(articles)} 篇NatGeo Kids文章")
    return articles

def build_test_dataset():
    """构建测试数据集"""
    print("开始构建测试数据集...")

    # 检查输入文件是否存在
    if not os.path.exists(NATGEO_DATA_PATH):
        print(f"错误：找不到NatGeo数据文件 {NATGEO_DATA_PATH}")
        return

    # 加载NatGeo文章
    articles = load_natgeo_articles(NATGEO_DATA_PATH, SAMPLE_SIZE)

    pairs = []
    failed_count = 0

    for i, article in enumerate(articles):
        print(f"\n处理第 {i+1}/{len(articles)} 篇文章...")
        print(f"标题: {article.get('title', 'N/A')}")
        print(f"描述: {article.get('description', 'N/A')}")

        try:
            # 提取Wikipedia搜索关键词
            description = article.get('description', '')
            if not description:
                print("跳过：没有描述内容")
                failed_count += 1
                continue

            search_keyword = extract_keyword_simple(description)
            print(f"提取的关键词: {search_keyword}")

            # 搜索Wikipedia
            wiki_result = search_wikipedia(search_keyword)
            if not wiki_result:
                print("跳过：Wikipedia搜索失败")
                failed_count += 1
                continue

            wiki_title, wiki_content, wiki_url = wiki_result
            print(f"Wikipedia页面: {wiki_title}")
            print(f"Wikipedia内容长度: {len(wiki_content)} 字符")

            # 创建数据对
            pair = WikipediaNatgeoPair(
                natgeo_article=article,
                wikipedia_search_keyword=search_keyword,
                wikipedia_title=wiki_title,
                wikipedia_content=wiki_content[:2000],  # 限制内容长度用于测试
                wikipedia_url=wiki_url
            )

            pairs.append(pair)

            # 添加延迟以避免API限制
            time.sleep(2)

        except Exception as e:
            print(f"处理文章时出错: {e}")
            failed_count += 1
            continue

    # 保存数据集
    dataset = [pair.to_dict() for pair in pairs]
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"\n=== 测试数据集构建完成 ===")
    print(f"成功处理: {len(pairs)} 篇文章")
    print(f"失败: {failed_count} 篇文章")
    print(f"数据已保存到: {OUTPUT_PATH}")

    # 显示统计信息
    if pairs:
        print(f"\n=== 示例数据对 ===")
        for i, pair in enumerate(pairs):
            print(f"\n示例 {i+1}:")
            print(f"NatGeo标题: {pair.natgeo_article.get('title', 'N/A')}")
            print(f"Wikipedia搜索关键词: {pair.wikipedia_search_keyword}")
            print(f"Wikipedia标题: {pair.wikipedia_title}")
            print(f"Wikipedia内容预览: {pair.wikipedia_content[:200]}...")

if __name__ == "__main__":
    build_test_dataset()