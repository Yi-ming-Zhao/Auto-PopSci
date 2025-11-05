#!/usr/bin/env python3
"""
提取JSON文件中所有文章的content并保存到文本文件
"""

import json

def extract_all_contents():
    """提取所有文章的content并保存到文件"""
    try:
        # 读取JSON文件
        with open('datasets/our_dataset/frontiers_kids/original_frontiers/all_frontiers_kids_articles.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("❌ JSON文件格式错误：预期是数组")
            return

        output_file = 'all_articles_contents.txt'

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"📖 Frontiers for Young Minds 文章内容汇总\n")
            f.write(f"总共 {len(data)} 篇文章\n")
            f.write("=" * 100 + "\n\n")

            for i, article in enumerate(data, 1):
                f.write(f"📄 文章 {i}/{len(data)}\n")
                f.write("-" * 60 + "\n")

                # 输出基本信息
                if article.get('title'):
                    f.write(f"📰 标题: {article['title']}\n")

                if article.get('author'):
                    f.write(f"✍️  作者: {article['author']}\n")

                if article.get('published_date'):
                    f.write(f"📅 发布日期: {article['published_date']}\n")

                if article.get('url'):
                    f.write(f"🔗 URL: {article['url']}\n")

                f.write("\n📖 内容:\n")
                f.write("=" * 40 + "\n")

                # 输出content
                if article.get('content'):
                    content = article['content']
                    f.write(content)
                else:
                    f.write("⚠️  没有内容字段")

                f.write("\n" + "=" * 100 + "\n\n")

        print(f"✅ 成功提取 {len(data)} 篇文章内容到文件: {output_file}")
        print(f"📄 文件大小: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")

    except FileNotFoundError:
        print("❌ 文件不存在: datasets/our_dataset/frontiers_kids/original_frontiers/all_frontiers_kids_articles.json")
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
    except Exception as e:
        print(f"❌ 读取文件时出错: {e}")

if __name__ == "__main__":
    import os
    extract_all_contents()