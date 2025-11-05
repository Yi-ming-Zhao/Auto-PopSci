#!/usr/bin/env python3
"""
增强版 Frontiers for Young Minds 文章爬虫
使用通用Selenium滚动翻页框架，支持多种滚动策略
"""

import json
import time
import os
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Callable
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 导入通用滚动爬虫框架
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../crawlers'))
from selenium_scroll_crawler import SeleniumScrollCrawler, InfiniteScrollStrategy, ButtonClickStrategy, MixedScrollStrategy


class EnhancedFrontiersCrawler:
    """增强版Frontiers爬虫，使用通用滚动框架"""

    def __init__(self, output_dir: str = None):
        """初始化爬虫"""
        self.base_url = "https://kids.frontiersin.org"
        self.articles_url = "https://kids.frontiersin.org/articles"
        self.output_dir = output_dir or "/Users/yzxbb/Desktop/Auto-Popsci/datasets/our_dataset/frontiers_kids/original_frontiers"

        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

        # 初始化通用滚动爬虫
        self.crawler = SeleniumScrollCrawler(
            base_url=self.base_url,
            headless=True,
            scroll_pause_time=2.0,
            request_delay=1.5,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    def extract_frontiers_article(self, element) -> Optional[Dict]:
        """提取Frontiers文章信息"""
        try:
            # 使用JavaScript提取数据，更可靠
            article_data = self.crawler.driver.execute_script("""
                var element = arguments[0];
                var result = {
                    url: '',
                    title: '',
                    description: '',
                    author: '',
                    published_date: '',
                    article_type: '',
                    image_url: '',
                    article_id: ''
                };

                // 提取文章链接
                var link = element.querySelector('a.article-link');
                if (link) {
                    result.url = link.href;
                }

                // 提取标题
                var title = element.querySelector('h1.article-heading, .article-heading, h1, h2, h3');
                if (title) {
                    result.title = title.textContent.trim();
                }

                // 提取描述
                var desc = element.querySelector('p.article-abstract, .article-abstract, p');
                if (desc) {
                    result.description = desc.textContent.trim();
                }

                // 提取作者
                var authors = element.querySelector('.article-authors-container, .authors');
                if (authors) {
                    result.author = authors.textContent.trim().replace(/^Authors\s*:?\s*/i, '');
                }

                // 提取日期
                var date = element.querySelector('.article-date, .date, [datetime]');
                if (date) {
                    result.published_date = date.textContent.trim() || date.getAttribute('datetime');
                }

                // 提取文章类型
                var type = element.querySelector('.article-type, .type, .category');
                if (type) {
                    result.article_type = type.textContent.trim();
                }

                // 提取图片
                var img = element.querySelector('img.lazy-loaded-image, img');
                if (img) {
                    result.image_url = img.getAttribute('data-src') || img.getAttribute('src');
                }

                // 提取文章ID
                var id = element.getAttribute('data-test-id') || element.getAttribute('data-article-id');
                if (id) {
                    result.article_id = id.replace('article-', '').replace('test-id-', '');
                }

                return result;
            """, element)

            # 规范化图片URL
            if article_data['image_url'] and not article_data['image_url'].startswith('http'):
                article_data['image_url'] = urljoin(self.base_url, article_data['image_url'])

            # 添加默认值
            article_data.update({
                'content': '',
                'related_articles': [],
                'meta_data': {}
            })

            return article_data

        except Exception as e:
            self.logger.warning(f"提取文章信息时出错: {e}")
            return None

    def extract_article_detail(self, driver, url: str) -> Dict:
        """提取文章详情"""
        try:
            driver.get(url)
            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # 提取内容
            content = self.extract_article_content(soup)

            # 提取相关文章
            related_articles = self.extract_related_articles(soup)

            # 提取元数据
            meta_data = self.extract_metadata(soup, {'url': url})

            return {
                'content': content,
                'related_articles': related_articles,
                'meta_data': meta_data
            }

        except Exception as e:
            self.logger.error(f"提取文章详情失败 {url}: {e}")
            return {
                'content': '',
                'related_articles': [],
                'meta_data': {}
            }

    def extract_article_content(self, soup: BeautifulSoup) -> str:
        """提取文章内容"""
        try:
            content_sections = []

            # 查找主要内容区域
            main_content_selectors = [
                'div.fulltext-content',
                'div.size-small.fulltext-content',
                'div.size.small.fulltext-content',
                'article .content',
                'main .content'
            ]

            main_content = None
            for selector in main_content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    main_content = content_div
                    break

            if main_content:
                # 提取标题和段落
                elements = main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div'])

                for element in elements:
                    if element.name == 'div' and 'abstract' in element.get('class', []):
                        abstract_p = element.find('p')
                        if abstract_p:
                            abstract_text = abstract_p.get_text(strip=True)
                            if abstract_text:
                                content_sections.append(f"Abstract: {abstract_text}")
                        continue

                    if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        heading_text = element.get_text(strip=True)
                        if heading_text:
                            level = int(element.name[1])
                            prefix = '#' * level
                            content_sections.append(f"\n{prefix} {heading_text}")
                        continue

                    if element.name == 'p':
                        # 跳过引用和作者简介
                        if element.find_parent('section') and element.find_parent('section').get('id') == 'full-text-references':
                            continue
                        if 'person-bio' in element.get('class', []):
                            continue

                        text = element.get_text(strip=True)
                        if text and len(text) > 30:
                            content_sections.append(text)

            # 如果没有找到内容，使用备用方案
            if not content_sections:
                paragraphs = soup.find_all('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 50:
                        content_sections.append(text)

            # 清理内容
            cleaned_content = []
            for section in content_sections:
                # 清理HTML实体
                cleaned = section.replace('&#x02014;', '—').replace('&#x000B0;', '°').replace('&#x02019;', "'")
                cleaned = cleaned.replace('&#x000B7;', '·')
                cleaned = ' '.join(cleaned.split())

                if cleaned and len(cleaned) > 10:
                    cleaned_content.append(cleaned)

            return '\n\n'.join(cleaned_content)

        except Exception as e:
            self.logger.error(f"提取文章内容时出错: {e}")
            return ""

    def extract_related_articles(self, soup: BeautifulSoup) -> List[Dict]:
        """提取相关文章"""
        try:
            related_articles = []

            # 查找相关文章区域
            related_selectors = [
                'aside.articles-section .articles-container-slider .article-link',
                '.related-articles a',
                '.see-also a',
                'div[class*="related"] a',
                'section[class*="related"] a'
            ]

            for selector in related_selectors:
                links = soup.select(selector)
                for link in links:
                    title_elem = link.select_one('.article-heading, h1, h2, h3, h4, h5, h6') or link
                    title = title_elem.get_text(strip=True)
                    href = link.get('href', '')

                    if href and title and len(title) > 5:
                        url = urljoin(self.base_url, href)
                        related_articles.append({
                            'title': title,
                            'url': url
                        })

                if related_articles:
                    break

            return related_articles[:5]

        except Exception as e:
            self.logger.error(f"提取相关文章时出错: {e}")
            return []

    def extract_metadata(self, soup: BeautifulSoup, article_data: Dict) -> Dict:
        """提取元数据"""
        try:
            meta_data = {}

            # 提取关键词
            keywords_elem = soup.find('meta', attrs={'name': 'keywords'})
            if keywords_elem:
                meta_data['keywords'] = keywords_elem.get('content', '')

            # 提取主题信息
            subjects = []
            subject_selectors = [
                '.article-subjects',
                '.categories',
                '.tags',
                'div[class*="subject"]',
                'div[class*="category"]'
            ]

            for selector in subject_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text:
                        subjects.append(text)
                if subjects:
                    break

            if subjects:
                meta_data['subjects'] = subjects

            # 从URL中提取DOI
            article_url = article_data.get('url', '')
            doi_match = re.search(r'10\.3389/[\w.-]+', article_url)
            if doi_match:
                meta_data['doi'] = doi_match.group(0)

            return meta_data

        except Exception as e:
            self.logger.error(f"提取元数据时出错: {e}")
            return {}

    def crawl_with_strategy(self, strategy_name: str = "auto") -> List[Dict]:
        """
        使用指定策略爬取文章

        Args:
            strategy_name: 策略名称 ('auto', 'infinite', 'button', 'mixed')

        Returns:
            List[Dict]: 文章列表
        """
        with self.crawler as crawler:
            # 选择滚动策略
            if strategy_name == "infinite":
                scroll_strategy = InfiniteScrollStrategy(scroll_pause_time=2.0, incremental_scroll=True)
            elif strategy_name == "button":
                # Frontiers常见的加载更多按钮选择器
                button_selectors = [
                    'button[class*="load"]',
                    'a[class*="load"]',
                    '.load-more',
                    '#load-more'
                ]
                scroll_strategy = None  # 让系统自动检测
            elif strategy_name == "mixed":
                scroll_strategy = MixedScrollStrategy(scroll_pause_time=2.0)
            else:
                scroll_strategy = None  # 自动检测

            # 定义进度回调
            def progress_callback(scroll_count, total_items, new_items):
                self.logger.info(f"滚动 {scroll_count}: 总计 {total_items} 篇文章，新增 {new_items} 篇")

            # 滚动并收集文章
            self.logger.info(f"开始使用 {strategy_name} 策略爬取Frontiers文章...")

            articles = crawler.scroll_and_collect(
                url=self.articles_url,
                item_selector="article.article",
                scroll_strategy=scroll_strategy,
                max_scrolls=50,
                content_extractor=self.extract_frontiers_article,
                progress_callback=progress_callback,
                stop_when_no_new_items=True
            )

            self.logger.info(f"收集到 {len(articles)} 篇文章的基本信息")

            # 收集详细信息
            if articles:
                self.logger.info("开始收集文章详细信息...")
                detailed_articles = crawler.collect_details(
                    articles[:10],  # 限制数量以避免过度请求
                    detail_extractor=self.extract_article_detail
                )
                articles = detailed_articles

            return articles

    def crawl_and_save(self, strategy_name: str = "auto", output_filename: str = None) -> str:
        """
        爬取并保存文章

        Args:
            strategy_name: 策略名称
            output_filename: 输出文件名

        Returns:
            str: 保存的文件路径
        """
        # 爬取文章
        articles = self.crawl_with_strategy(strategy_name)

        if not articles:
            self.logger.warning("没有爬取到任何文章")
            return ""

        # 生成输出文件路径
        if not output_filename:
            timestamp = int(time.time())
            output_filename = f"frontiers_articles_{timestamp}.json"

        output_path = os.path.join(self.output_dir, output_filename)

        # 保存数据
        self.crawler.save_to_file(articles, output_path, "json")

        # 同时保存CSV格式
        csv_path = output_path.replace('.json', '.csv')
        self.crawler.save_to_file(articles, csv_path, "csv")

        self.logger.info(f"爬取完成，保存了 {len(articles)} 篇文章")
        return output_path

    def test_different_strategies(self) -> Dict[str, List[Dict]]:
        """测试不同的滚动策略"""
        results = {}
        strategies = ["auto", "infinite", "mixed"]

        for strategy in strategies:
            try:
                self.logger.info(f"测试策略: {strategy}")
                articles = self.crawl_with_strategy(strategy)
                results[strategy] = articles

                # 保存测试结果
                test_output = os.path.join(self.output_dir, f"test_{strategy}_results.json")
                self.crawler.save_to_file(articles, test_output, "json")

                self.logger.info(f"策略 {strategy} 获取到 {len(articles)} 篇文章")

                # 添加延迟避免被限制
                time.sleep(5)

            except Exception as e:
                self.logger.error(f"测试策略 {strategy} 时出错: {e}")
                results[strategy] = []

        return results


def main():
    """主函数"""
    crawler = EnhancedFrontiersCrawler()

    # 测试不同策略
    print("=== 测试不同的滚动策略 ===")
    results = crawler.test_different_strategies()

    # 显示结果统计
    for strategy, articles in results.items():
        print(f"{strategy} 策略: {len(articles)} 篇文章")

    # 使用最佳策略进行完整爬取
    best_strategy = max(results.keys(), key=lambda k: len(results[k]))
    print(f"\n=== 使用最佳策略 ({best_strategy}) 进行完整爬取 ===")

    output_path = crawler.crawl_and_save(best_strategy, "frontiers_all_articles.json")
    print(f"完整爬取结果已保存到: {output_path}")


if __name__ == "__main__":
    main()