#!/usr/bin/env python3
"""
测试无限制爬虫
"""

import sys
import os

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append('datasets/our_dataset/frontiers_kids/crawler')

from frontiers_crawler import FrontiersCrawler

def test_unlimited_crawl():
    """测试无限制爬虫"""
    print("🚀 测试无限制爬虫...")

    # 设置更短的测试时间
    print("⚠️ 测试模式：限制10分钟运行时间")

    crawler = FrontiersCrawler()

    # 输出路径
    output_path = "/Users/yzxbb/Desktop/Auto-Popsci/datasets/our_dataset/frontiers_kids/original_frontiers/all_frontiers_kids_articles_unlimited.json"

    try:
        print("🔥 启动无限制爬虫模式...")

        # 调用爬虫的内部方法进行测试
        articles = crawler.crawl_all_articles_with_selenium(
            max_scrolls=999,  # 大数值限制
            show_browser=False,
            max_articles=None  # 无限制
        )

        print(f"\n✅ 爬取完成！获得 {len(articles)} 篇文章")

        # 保存到新文件
        crawler.save_to_json(articles, output_path)
        print(f"📄 数据已保存到: {output_path}")

        return len(articles)

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断了爬取")
        return 0
    except Exception as e:
        print(f"❌ 爬取出错: {e}")
        return 0

if __name__ == "__main__":
    count = test_unlimited_crawl()
    print(f"\n🎉 总共爬取了 {count} 篇文章")