#!/usr/bin/env python3
"""
测试改进后的内容提取功能
"""

import sys
import os

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from frontiers_crawler import FrontiersCrawler
from bs4 import BeautifulSoup

def test_content_extraction():
    """测试内容提取功能"""
    print("🧪 测试改进后的内容提取功能...")

    # 读取示例HTML文件
    html_file = os.path.join(current_dir, '..', 'asset', 'frym.2025.1354853.html')

    if not os.path.exists(html_file):
        print(f"❌ HTML文件不存在: {html_file}")
        return False

    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 创建BeautifulSoup对象
        soup = BeautifulSoup(html_content, 'html.parser')

        # 创建爬虫实例
        crawler = FrontiersCrawler()

        # 测试内容提取
        print("\n📖 测试文章内容提取...")
        content = crawler.extract_article_content(soup)

        if content:
            print(f"✅ 成功提取内容，长度: {len(content)} 字符")
            print(f"📄 内容预览:\n{content[:500]}...")
        else:
            print("❌ 未能提取到内容")
            return False

        # 测试作者提取
        print("\n✍️ 测试作者信息提取...")
        authors = crawler.extract_authors_from_detail(soup)

        if authors:
            print(f"✅ 成功提取作者: {authors}")
        else:
            print("❌ 未能提取到作者信息")

        # 测试发布日期提取
        print("\n📅 测试发布日期提取...")
        published_date = crawler.extract_published_date(soup)

        if published_date:
            print(f"✅ 成功提取发布日期: {published_date}")
        else:
            print("❌ 未能提取到发布日期")

        # 测试标题提取
        print("\n📰 测试标题提取...")
        title_elem = soup.find('h1', class_='fulltext-heading')
        if title_elem:
            title = title_elem.get_text(strip=True)
            print(f"✅ 成功提取标题: {title}")
        else:
            print("❌ 未能提取到标题")

        # 测试元数据提取
        print("\n🏷️ 测试元数据提取...")
        article_data = {'url': 'https://kids.frontiersin.org/articles/10.3389/frym.2025.1354853'}
        metadata = crawler.extract_metadata(soup, article_data)

        if metadata:
            print(f"✅ 成功提取元数据: {metadata}")
        else:
            print("❌ 未能提取到元数据")

        print("\n✅ 内容提取测试完成")
        return True

    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

if __name__ == "__main__":
    success = test_content_extraction()
    if success:
        print("\n🎉 所有测试通过！")
    else:
        print("\n💥 测试失败！")