#!/usr/bin/env python3
"""
合并三个数据集：natgeo, pitara, frontiers
统一格式为 natgeo 格式，使用 popsci_article 作为文章对象名称
"""

import json
import os
from typing import Dict, List, Any

def load_json(file_path: str) -> List[Dict]:
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def merge_natgeo_article(article: Dict) -> Dict:
    """转换 natgeo 文章格式"""
    natgeo_article = article.get("natgeo_article", {})
    
    merged = {
        "popsci_article": {
            "title": natgeo_article.get("title", ""),
            "description": natgeo_article.get("description", ""),
            "content": natgeo_article.get("content", ""),
            "url": natgeo_article.get("url", ""),
            "category": natgeo_article.get("category", ""),
            "image_url": natgeo_article.get("image_url", ""),
            "author": "",  # natgeo 没有 author 字段
            "published_date": "",  # natgeo 没有 published_date 字段
            "related_articles": []  # natgeo 没有 related_articles
        },
        "wikipedia_article": {
            "search_keyword": article.get("wikipedia_search_keyword", ""),
            "title": article.get("wikipedia_title", ""),
            "content": article.get("wikipedia_content", ""),
            "url": article.get("wikipedia_url", "")
        },
        "source": "natgeo"
    }
    return merged

def merge_pitara_article(article: Dict) -> Dict:
    """转换 pitara 文章格式"""
    merged = {
        "popsci_article": {
            "title": article.get("title", ""),
            "description": article.get("description", ""),
            "content": article.get("content", ""),
            "url": article.get("url", ""),
            "category": article.get("category", ""),
            "image_url": article.get("image_url", ""),
            "author": article.get("author", ""),
            "published_date": article.get("published_date", ""),
            "related_articles": article.get("related_articles", [])
        },
        "wikipedia_article": {
            "search_keyword": "",  # pitara 没有 wikipedia 数据
            "title": "",
            "content": "",
            "url": ""
        },
        "source": "pitara"
    }
    return merged

def merge_frontiers_article(article: Dict) -> Dict:
    """转换 frontiers 文章格式"""
    merged = {
        "popsci_article": {
            "title": article.get("title", ""),
            "description": "",  # frontiers 没有 description
            "content": article.get("content", ""),
            "url": article.get("url", ""),
            "category": "",  # frontiers 没有 category
            "image_url": "",  # frontiers 没有 image_url
            "author": article.get("author", ""),
            "published_date": article.get("published_date", ""),
            "related_articles": article.get("related_articles", [])
        },
        "wikipedia_article": {
            "search_keyword": "",  # frontiers 没有 wikipedia 数据
            "title": "",
            "content": "",
            "url": ""
        },
        "source": "frontiers"
    }
    return merged

def merge_all_datasets():
    """合并所有数据集"""
    base_dir = "datasets/our_dataset"
    
    # 文件路径
    natgeo_path = os.path.join(base_dir, "natgeo_kids/natgeo_wikipedia_glm.json")
    pitara_path = os.path.join(base_dir, "pitara/all_pitara_articles.json")
    frontiers_path = os.path.join(base_dir, "frontiers_kids/original_frontiers/all_frontiers_kids_articles.json")
    
    # 输出路径
    output_path = os.path.join(base_dir, "merged_popular_science_articles.json")
    
    print("📂 开始加载数据集...")
    
    # 加载数据
    natgeo_articles = load_json(natgeo_path)
    pitara_articles = load_json(pitara_path)
    frontiers_articles = load_json(frontiers_path)
    
    print(f"✅ 已加载:")
    print(f"   NatGeo: {len(natgeo_articles)} 篇文章")
    print(f"   Pitara: {len(pitara_articles)} 篇文章")
    print(f"   Frontiers: {len(frontiers_articles)} 篇文章")
    
    # 转换格式
    print("\n🔄 开始转换格式...")
    merged_articles = []
    
    # 转换 natgeo
    for article in natgeo_articles:
        merged_articles.append(merge_natgeo_article(article))
    
    # 转换 pitara
    for article in pitara_articles:
        merged_articles.append(merge_pitara_article(article))
    
    # 转换 frontiers
    for article in frontiers_articles:
        merged_articles.append(merge_frontiers_article(article))
    
    print(f"✅ 转换完成，共 {len(merged_articles)} 篇文章")
    
    # 保存合并后的数据
    print(f"\n💾 保存到: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged_articles, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 合并完成！")
    
    # 统计信息
    print("\n📊 统计信息:")
    sources = {}
    for article in merged_articles:
        source = article.get("source", "unknown")
        sources[source] = sources.get(source, 0) + 1
    
    for source, count in sources.items():
        print(f"   {source}: {count} 篇")
    
    # 显示示例
    print("\n📖 示例文章 (每个来源1篇):")
    for source in ["natgeo", "pitara", "frontiers"]:
        for article in merged_articles:
            if article.get("source") == source:
                popsci = article.get("popsci_article", {})
                print(f"\n[{source}]")
                print(f"  标题: {popsci.get('title', 'N/A')}")
                print(f"  URL: {popsci.get('url', 'N/A')}")
                print(f"  分类: {popsci.get('category', 'N/A')}")
                print(f"  作者: {popsci.get('author', 'N/A')}")
                print(f"  相关文章数: {len(popsci.get('related_articles', []))}")
                if source == "natgeo":
                    wiki = article.get("wikipedia_article", {})
                    print(f"  Wikipedia标题: {wiki.get('title', 'N/A')}")
                break

if __name__ == "__main__":
    merge_all_datasets()

