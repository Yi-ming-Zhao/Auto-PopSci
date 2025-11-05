#!/usr/bin/env python3
"""
Selenium滚动翻页采集功能测试脚本
测试不同的滚动策略和网站兼容性
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List

# 添加路径以便导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from selenium_scroll_crawler import SeleniumScrollCrawler, InfiniteScrollStrategy, ButtonClickStrategy, MixedScrollStrategy
from scroll_strategy_detector import create_smart_crawler, ScrollStrategyDetector
from enhanced_frontiers_crawler import EnhancedFrontiersCrawler


class ScrollCrawlerTester:
    """滚动爬虫测试器"""

    def __init__(self):
        """初始化测试器"""
        self.test_results = {}
        self.logger = logging.getLogger(__name__)

        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # 测试网站列表
        self.test_websites = [
            {
                'name': 'Frontiers for Young Minds',
                'url': 'https://kids.frontiersin.org/articles',
                'expected_strategy': 'mixed',
                'item_selector': 'article.article'
            },
            {
                'name': 'News Example (Infinite Scroll)',
                'url': 'https://news.ycombinator.com',  # Hacker News
                'expected_strategy': 'infinite',
                'item_selector': '.storylink'
            },
            {
                'name': 'Blog Example',
                'url': 'https://medium.com/topic/technology',
                'expected_strategy': 'infinite',
                'item_selector': 'article'
            }
        ]

    def test_strategy_detector(self):
        """测试策略检测器"""
        print("=== 测试策略检测器 ===")

        for website in self.test_websites:
            print(f"\n测试网站: {website['name']}")
            print(f"URL: {website['url']}")

            try:
                config = create_smart_crawler(website['url'])

                result = {
                    'detected_strategy': config['strategy_name'],
                    'expected_strategy': website['expected_strategy'],
                    'item_selector': config['item_selector'],
                    'button_selectors': config['button_selectors'],
                    'success': True
                }

                print(f"  检测到策略: {result['detected_strategy']}")
                print(f"  期望策略: {result['expected_strategy']}")
                print(f"  推荐选择器: {result['item_selector']}")
                print(f"  按钮选择器: {result['button_selectors']}")

                if result['detected_strategy'] == result['expected_strategy']:
                    print("  ✅ 策略检测正确")
                else:
                    print("  ⚠️  策略检测与预期不同")

            except Exception as e:
                result = {
                    'detected_strategy': 'error',
                    'expected_strategy': website['expected_strategy'],
                    'error': str(e),
                    'success': False
                }
                print(f"  ❌ 检测失败: {e}")

            self.test_results[f"detect_{website['name']}"] = result

    def test_basic_scroll_strategies(self):
        """测试基本滚动策略"""
        print("\n=== 测试基本滚动策略 ===")

        # 创建一个简单的测试页面
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Scroll Test Page</title>
            <style>
                .item { height: 200px; border: 1px solid #ccc; margin: 10px; padding: 20px; }
                .load-more { padding: 10px 20px; margin: 10px; cursor: pointer; }
            </style>
        </head>
        <body>
            <h1>Scroll Test</h1>
            <div id="items">
                <div class="item">Item 1</div>
                <div class="item">Item 2</div>
                <div class="item">Item 3</div>
            </div>
            <button class="load-more" onclick="addItems()">Load More</button>

            <script>
                let itemCounter = 4;
                function addItems() {
                    const container = document.getElementById('items');
                    for(let i = 0; i < 3; i++) {
                        const item = document.createElement('div');
                        item.className = 'item';
                        item.textContent = 'Item ' + itemCounter++;
                        container.appendChild(item);
                    }
                }

                // 模拟无限滚动
                window.addEventListener('scroll', function() {
                    if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100) {
                        addItems();
                    }
                });
            </script>
        </body>
        </html>
        """

        # 保存测试页面
        test_file = os.path.join(current_dir, 'test_scroll_page.html')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_html)

        test_url = f"file://{test_file}"

        # 测试不同策略
        strategies = [
            ('Infinite Scroll', InfiniteScrollStrategy(scroll_pause_time=1.0)),
            ('Button Click', ButtonClickStrategy('.load-more', max_clicks=3)),
            ('Mixed', MixedScrollStrategy(button_selector='.load-more', scroll_pause_time=1.0))
        ]

        for strategy_name, strategy in strategies:
            print(f"\n测试策略: {strategy_name}")

            try:
                with SeleniumScrollCrawler(base_url=test_url, headless=True) as crawler:
                    def simple_extractor(element):
                        return {
                            'text': element.text.strip(),
                            'tag': element.tag_name
                        }

                    items = crawler.scroll_and_collect(
                        url=test_url,
                        item_selector='.item',
                        scroll_strategy=strategy,
                        max_scrolls=5,
                        content_extractor=simple_extractor,
                        stop_when_no_new_items=True
                    )

                    result = {
                        'strategy': strategy_name,
                        'items_collected': len(items),
                        'success': True
                    }

                    print(f"  收集到 {len(items)} 个项目")
                    print("  ✅ 策略测试成功")

            except Exception as e:
                result = {
                    'strategy': strategy_name,
                    'items_collected': 0,
                    'error': str(e),
                    'success': False
                }
                print(f"  ❌ 策略测试失败: {e}")

            self.test_results[f"strategy_{strategy_name}"] = result

        # 清理测试文件
        try:
            os.remove(test_file)
        except:
            pass

    def test_enhanced_frontiers_crawler(self):
        """测试增强版Frontiers爬虫"""
        print("\n=== 测试增强版Frontiers爬虫 ===")

        try:
            crawler = EnhancedFrontiersCrawler()

            # 测试策略检测
            print("测试策略检测...")
            results = crawler.test_different_strategies()

            for strategy, articles in results.items():
                result = {
                    'strategy': strategy,
                    'articles_count': len(articles),
                    'success': True
                }
                self.test_results[f"frontiers_{strategy}"] = result
                print(f"  {strategy} 策略: {len(articles)} 篇文章 ✅")

        except Exception as e:
            result = {
                'strategy': 'enhanced_frontiers',
                'articles_count': 0,
                'error': str(e),
                'success': False
            }
            self.test_results['frontiers_enhanced'] = result
            print(f"  ❌ 增强版爬虫测试失败: {e}")

    def test_real_website_crawling(self):
        """测试真实网站爬取（限制数量以避免过度请求）"""
        print("\n=== 测试真实网站爬取 ===")

        # 选择一个相对安全的测试网站
        test_url = "https://kids.frontiersin.org/articles"

        try:
            with SeleniumScrollCrawler(
                base_url="https://kids.frontiersin.org",
                headless=True,
                scroll_pause_time=2.0,
                request_delay=2.0
            ) as crawler:

                # 使用智能检测
                config = create_smart_crawler(test_url)

                def progress_callback(scroll_count, total_items, new_items):
                    print(f"  滚动 {scroll_count}: 总计 {total_items} 项，新增 {new_items} 项")

                # 限制爬取数量
                articles = crawler.scroll_and_collect(
                    url=test_url,
                    item_selector=config['item_selector'],
                    scroll_strategy=config['strategy'],
                    max_scrolls=3,  # 限制滚动次数
                    progress_callback=progress_callback,
                    stop_when_no_new_items=True
                )

                result = {
                    'website': 'Frontiers for Young Minds',
                    'articles_count': len(articles),
                    'strategy_used': config['strategy_name'],
                    'success': True
                }

                print(f"  使用策略: {config['strategy_name']}")
                print(f"  收集到 {len(articles)} 篇文章 ✅")

                # 保存测试结果
                if articles:
                    test_output = os.path.join(current_dir, 'test_crawling_results.json')
                    crawler.save_to_file(articles[:5], test_output, 'json')
                    print(f"  保存测试结果到: {test_output}")

        except Exception as e:
            result = {
                'website': 'Frontiers for Young Minds',
                'articles_count': 0,
                'error': str(e),
                'success': False
            }
            print(f"  ❌ 真实网站爬取失败: {e}")

        self.test_results['real_website_crawling'] = result

    def run_all_tests(self):
        """运行所有测试"""
        print("开始运行Selenium滚动翻页采集功能测试...")
        print("=" * 50)

        # 运行各个测试
        self.test_strategy_detector()
        self.test_basic_scroll_strategies()
        self.test_enhanced_frontiers_crawler()
        self.test_real_website_crawling()

        # 生成测试报告
        self.generate_test_report()

    def generate_test_report(self):
        """生成测试报告"""
        print("\n" + "=" * 50)
        print("测试报告")
        print("=" * 50)

        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results.values() if result.get('success', False))

        print(f"总测试数: {total_tests}")
        print(f"成功测试: {successful_tests}")
        print(f"失败测试: {total_tests - successful_tests}")
        print(f"成功率: {successful_tests/total_tests*100:.1f}%")

        print("\n详细结果:")
        for test_name, result in self.test_results.items():
            status = "✅ 成功" if result.get('success', False) else "❌ 失败"
            print(f"  {test_name}: {status}")

            if not result.get('success', False) and 'error' in result:
                print(f"    错误: {result['error']}")

        # 保存测试报告
        report_file = os.path.join(current_dir, 'test_report.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

        print(f"\n详细报告已保存到: {report_file}")


def main():
    """主函数"""
    tester = ScrollCrawlerTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()