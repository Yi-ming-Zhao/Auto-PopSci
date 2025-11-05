#!/usr/bin/env python3
"""
读取JSON文件并输出所有content字段
"""

import json

def output_all_contents():
    """输出所有文章的content字段"""
    try:
        # 读取JSON文件
        with open('datasets/our_dataset/frontiers_kids/original_frontiers/all_frontiers_kids_articles.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("❌ JSON文件格式错误：预期是数组")
            return

        print(f"📖 总共找到 {len(data)} 篇文章")
        print("=" * 80)

        for i, article in enumerate(data, 1):
            print(f"\n📄 文章 {i}/{len(data)}")
            print("-" * 60)

            # 输出标题（如果有）
            if article.get('title'):
                print(f"📰 标题: {article['title']}")

            # 输出作者（如果有）
            if article.get('author'):
                print(f"✍️  作者: {article['author']}")

            # 输出URL（如果有）
            if article.get('url'):
                print(f"🔗 URL: {article['url']}")

            # 输出content
            if article.get('content'):
                content = article['content']
                print(f"📖 内容 ({len(content)} 字符):")
                print("=" * 40)
                print(content)
                print("=" * 40)
            else:
                print("⚠️  没有内容字段")

            print("\n" + "=" * 80)

            # 每篇文章之间添加分隔
            if i < len(data):
                print("\n" + "=" * 80 + "\n")

    except FileNotFoundError:
        print("❌ 文件不存在: datasets/our_dataset/frontiers_kids/original_frontiers/all_frontiers_kids_articles.json")
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
    except Exception as e:
        print(f"❌ 读取文件时出错: {e}")

if __name__ == "__main__":
    output_all_contents()