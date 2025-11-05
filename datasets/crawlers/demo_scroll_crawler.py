#!/usr/bin/env python3
"""
Selenium滚动翻页采集功能演示脚本
展示如何使用不同的滚动策略进行数据采集
"""

import os
import sys
import time

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from selenium_scroll_crawler import SeleniumScrollCrawler, InfiniteScrollStrategy, ButtonClickStrategy, MixedScrollStrategy
from scroll_strategy_detector import create_smart_crawler


def demo_infinite_scroll():
    """演示无限滚动策略"""
    print("\n=== 演示无限滚动策略 ===")

    # 创建一个简单的HTML文件用于演示
    demo_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Infinite Scroll Demo</title>
        <style>
            .item { height: 150px; border: 1px solid #ccc; margin: 10px; padding: 20px; background: #f9f9f9; }
            body { font-family: Arial, sans-serif; }
        </style>
    </head>
    <body>
        <h1>无限滚动演示页面</h1>
        <div id="container">
            <div class="item">项目 1 - 这是第一个项目</div>
            <div class="item">项目 2 - 这是第二个项目</div>
            <div class="item">项目 3 - 这是第三个项目</div>
        </div>

        <script>
            let counter = 4;

            // 模拟无限滚动
            function addMoreItems() {
                const container = document.getElementById('container');
                for(let i = 0; i < 3; i++) {
                    const item = document.createElement('div');
                    item.className = 'item';
                    item.textContent = '项目 ' + counter + ' - 这是动态加载的项目';
                    container.appendChild(item);
                    counter++;
                }
            }

            // 监听滚动事件
            window.addEventListener('scroll', function() {
                if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 100) {
                    setTimeout(addMoreItems, 1000); // 延迟1秒加载
                }
            });
        </script>
    </body>
    </html>
    """

    # 保存演示文件
    demo_file = os.path.join(current_dir, 'infinite_scroll_demo.html')
    with open(demo_file, 'w', encoding='utf-8') as f:
        f.write(demo_html)

    demo_url = f"file://{demo_file}"

    try:
        # 创建爬虫
        with SeleniumScrollCrawler(headless=False, scroll_pause_time=2.0) as crawler:
            # 使用无限滚动策略
            strategy = InfiniteScrollStrategy(
                scroll_pause_time=1.5,
                incremental_scroll=True
            )

            print("开始无限滚动采集...")

            # 定义内容提取函数
            def extract_item(element):
                return {
                    'text': element.text.strip(),
                    'item_number': element.text.strip().split(' ')[1] if element.text.strip().split(' ') else ''
                }

            # 执行采集
            items = crawler.scroll_and_collect(
                url=demo_url,
                item_selector='.item',
                scroll_strategy=strategy,
                max_scrolls=5,
                content_extractor=extract_item,
                progress_callback=lambda scroll, total, new: print(f"  滚动 {scroll}: 总计 {total} 项，新增 {new} 项")
            )

            print(f"\n采集完成！总共收集到 {len(items)} 个项目")

            # 显示前几个项目
            for i, item in enumerate(items[:5]):
                print(f"  {i+1}. {item['text']}")

            # 保存结果
            output_file = os.path.join(current_dir, 'infinite_scroll_results.json')
            crawler.save_to_file(items, output_file, 'json')
            print(f"结果已保存到: {output_file}")

    except Exception as e:
        print(f"❌ 无限滚动演示失败: {e}")

    finally:
        # 清理演示文件
        try:
            os.remove(demo_file)
        except:
            pass


def demo_button_click():
    """演示按钮点击策略"""
    print("\n=== 演示按钮点击策略 ===")

    # 创建带加载按钮的HTML文件
    demo_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Button Click Demo</title>
        <style>
            .item { height: 120px; border: 1px solid #ccc; margin: 10px; padding: 15px; background: #f0f8ff; }
            .load-more {
                background: #007bff; color: white; border: none; padding: 10px 20px;
                margin: 20px; cursor: pointer; border-radius: 5px; font-size: 16px;
            }
            .load-more:hover { background: #0056b3; }
            body { font-family: Arial, sans-serif; text-align: center; }
            .container { max-width: 600px; margin: 0 auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>按钮点击演示页面</h1>
            <div id="items-container">
                <div class="item">📚 书籍 1 - 《Python编程》</div>
                <div class="item">📚 书籍 2 - 《数据结构与算法》</div>
                <div class="item">📚 书籍 3 - 《机器学习实战》</div>
            </div>
            <button class="load-more" onclick="loadMoreBooks()">加载更多书籍</button>
        </div>

        <script>
            let bookCounter = 4;
            const bookTitles = [
                '《深度学习入门》', '《算法导论》', '《设计模式》',
                '《代码大全》', '《重构》', '《编程珠玑》'
            ];

            function loadMoreBooks() {
                const container = document.getElementById('items-container');
                const button = document.querySelector('.load-more');

                // 模拟加载延迟
                button.textContent = '加载中...';
                button.disabled = true;

                setTimeout(() => {
                    for(let i = 0; i < 2; i++) {
                        const item = document.createElement('div');
                        item.className = 'item';
                        const titleIndex = (bookCounter - 4) % bookTitles.length;
                        item.textContent = '📚 书籍 ' + bookCounter + ' - ' + bookTitles[titleIndex];
                        container.appendChild(item);
                        bookCounter++;
                    }

                    button.textContent = '加载更多书籍';
                    button.disabled = false;

                    // 最多加载10本书
                    if (bookCounter > 10) {
                        button.textContent = '已加载全部书籍';
                        button.disabled = true;
                    }
                }, 1000);
            }
        </script>
    </body>
    </html>
    """

    demo_file = os.path.join(current_dir, 'button_click_demo.html')
    with open(demo_file, 'w', encoding='utf-8') as f:
        f.write(demo_html)

    demo_url = f"file://{demo_file}"

    try:
        with SeleniumScrollCrawler(headless=False, scroll_pause_time=2.0) as crawler:
            # 使用按钮点击策略
            strategy = ButtonClickStrategy(
                button_selector='.load-more',
                max_clicks=6,
                click_pause_time=2.0
            )

            print("开始按钮点击采集...")

            def extract_book(element):
                return {
                    'title': element.text.strip(),
                    'number': element.text.strip().split(' ')[1] if ' ' in element.text.strip() else ''
                }

            items = crawler.scroll_and_collect(
                url=demo_url,
                item_selector='.item',
                scroll_strategy=strategy,
                content_extractor=extract_book,
                progress_callback=lambda scroll, total, new: print(f"  点击 {scroll}: 总计 {total} 本书，新增 {new} 本")
            )

            print(f"\n采集完成！总共收集到 {len(items)} 本书")

            for i, book in enumerate(items):
                print(f"  {i+1}. {book['title']}")

            # 保存结果
            output_file = os.path.join(current_dir, 'button_click_results.json')
            crawler.save_to_file(items, output_file, 'json')
            print(f"结果已保存到: {output_file}")

    except Exception as e:
        print(f"❌ 按钮点击演示失败: {e}")

    finally:
        try:
            os.remove(demo_file)
        except:
            pass


def demo_smart_detection():
    """演示智能检测功能"""
    print("\n=== 演示智能策略检测 ===")

    # 使用真实的网站URL进行演示
    test_urls = [
        ("Frontiers for Young Minds", "https://kids.frontiersin.org/articles"),
        # 可以添加更多测试URL
    ]

    for name, url in test_urls:
        print(f"\n检测网站: {name}")
        print(f"URL: {url}")

        try:
            # 获取智能推荐配置
            config = create_smart_crawler(url)

            print(f"  ✅ 检测成功!")
            print(f"  推荐策略: {config['strategy_name']}")
            print(f"  推荐选择器: {config['item_selector']}")
            print(f"  按钮选择器: {config['button_selectors']}")
            print(f"  配置建议:")
            for key, value in config['recommendations'].items():
                print(f"    {key}: {value}")

        except Exception as e:
            print(f"  ❌ 检测失败: {e}")


def main():
    """主演示函数"""
    print("🚀 Selenium滚动翻页采集功能演示")
    print("=" * 50)

    print("注意：此演示将打开Chrome浏览器窗口，请确保已安装Chrome和ChromeDriver")
    print("演示过程中请保持浏览器窗口不要关闭")

    # 等待用户确认
    input("\n按回车键开始演示...")

    try:
        # 演示无限滚动
        demo_infinite_scroll()

        time.sleep(2)

        # 演示按钮点击
        demo_button_click()

        time.sleep(2)

        # 演示智能检测（这会在后台运行，不显示浏览器）
        demo_smart_detection()

    except KeyboardInterrupt:
        print("\n\n演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")

    print("\n" + "=" * 50)
    print("✅ 演示完成！")
    print("\n要了解更多用法，请查看:")
    print("  - README_SeleniumScroll.md: 详细使用说明")
    print("  - test_scroll_crawler.py: 功能测试脚本")
    print("  - enhanced_frontiers_crawler.py: Frontiers专用爬虫")


if __name__ == "__main__":
    main()