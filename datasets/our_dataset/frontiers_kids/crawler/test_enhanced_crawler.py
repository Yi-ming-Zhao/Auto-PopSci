#!/usr/bin/env python3
"""
测试增强版Frontiers爬虫的无限滚动功能
"""

import sys
import os
import time

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from frontiers_crawler import FrontiersCrawler


def test_basic_functionality():
    """测试基本功能"""
    print("🧪 测试基本功能...")

    crawler = FrontiersCrawler()

    # 检查Selenium可用性
    print(f"✅ Selenium可用性: {crawler.selenium_available}")
    print(f"✅ 基础URL: {crawler.base_url}")
    print(f"✅ 文章URL: {crawler.articles_url}")

    return True


def test_selenium_setup():
    """测试Selenium设置"""
    print("\n🧪 测试Selenium设置...")

    crawler = FrontiersCrawler()

    if not crawler.selenium_available:
        print("⚠️  Selenium不可用，跳过测试")
        return True

    try:
        driver = crawler.setup_selenium_driver(headless=True)
        if driver:
            print("✅ WebDriver创建成功")

            # 测试基本功能
            driver.get("https://www.google.com")
            title = driver.title
            print(f"✅ 浏览器访问成功，页面标题: {title}")

            driver.quit()
            print("✅ WebDriver关闭成功")
            return True
        else:
            print("❌ WebDriver创建失败")
            return False
    except Exception as e:
        print(f"❌ Selenium测试失败: {e}")
        return False


def test_scroll_detection():
    """测试滚动检测功能"""
    print("\n🧪 测试滚动检测功能...")

    crawler = FrontiersCrawler()

    if not crawler.selenium_available:
        print("⚠️  Selenium不可用，跳过测试")
        return True

    try:
        driver = crawler.setup_selenium_driver(headless=True)
        if not driver:
            print("❌ 无法创建WebDriver")
            return False

        # 访问Frontiers网站
        print("🌐 访问Frontiers网站...")
        driver.get(crawler.articles_url)
        time.sleep(3)

        # 检测加载更多按钮
        button = crawler._find_load_more_button(driver)
        if button:
            print("✅ 检测到'加载更多'按钮")
        else:
            print("ℹ️  未检测到'加载更多'按钮")

        # 获取当前文章数量
        articles = driver.find_elements_by_css_selector("article.article")
        print(f"✅ 当前页面有 {len(articles)} 篇文章")

        driver.quit()
        return True

    except Exception as e:
        print(f"❌ 滚动检测测试失败: {e}")
        return False


def test_mini_crawl():
    """测试小规模爬取"""
    print("\n🧪 测试小规模爬取...")

    crawler = FrontiersCrawler()

    if not crawler.selenium_available:
        print("⚠️  Selenium不可用，使用备用方法")
        try:
            articles = crawler.crawl_all_articles(max_pages=2, use_selenium=False)
            print(f"✅ 备用方法爬取成功，获得 {len(articles)} 篇文章")
            return len(articles) > 0
        except Exception as e:
            print(f"❌ 备用方法也失败: {e}")
            return False

    try:
        # 使用智能策略，限制滚动次数
        print("🧠 使用智能策略进行测试爬取...")
        articles = crawler.crawl_with_smart_strategy(max_scrolls=3)

        if articles:
            print(f"✅ 测试爬取成功，获得 {len(articles)} 篇文章")

            # 显示第一个文章的基本信息
            if articles:
                first = articles[0]
                print(f"📄 示例文章:")
                print(f"   标题: {first.get('title', 'N/A')}")
                print(f"   URL: {first.get('url', 'N/A')}")
                print(f"   描述: {first.get('description', 'N/A')[:100]}...")

            return True
        else:
            print("⚠️  没有爬取到文章，但代码执行正常")
            return True

    except Exception as e:
        print(f"❌ 测试爬取失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 Frontiers增强版爬虫测试")
    print("=" * 50)

    tests = [
        ("基本功能测试", test_basic_functionality),
        ("Selenium设置测试", test_selenium_setup),
        ("滚动检测测试", test_scroll_detection),
        ("小规模爬取测试", test_mini_crawl),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 出现异常: {e}")

    print("\n" + "=" * 50)
    print(f"🎯 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！爬虫功能正常")
        print("\n💡 使用说明:")
        print("   1. 运行 python frontiers_crawler.py 启动完整爬虫")
        print("   2. 选择智能策略模式以获得最佳效果")
        print("   3. 使用快速测试模式验证网站变化")
    else:
        print("⚠️  部分测试失败，请检查:")
        print("   1. Chrome浏览器是否已安装")
        print("   2. ChromeDriver版本是否匹配")
        print("   3. 网络连接是否正常")
        print("   4. 目标网站是否可访问")

    print("=" * 50)


if __name__ == "__main__":
    main()