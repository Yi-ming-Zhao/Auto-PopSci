#!/usr/bin/env python3
"""
滚动策略智能检测器
自动识别网站的滚动模式并选择最佳策略
"""

import re
import time
from typing import Dict, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

from selenium_scroll_crawler import (
    ScrollStrategy, InfiniteScrollStrategy, ButtonClickStrategy, MixedScrollStrategy
)


class WebsitePattern:
    """网站模式定义"""

    def __init__(
        self,
        name: str,
        url_patterns: List[str],
        scroll_strategy: str,
        button_selectors: List[str],
        item_selectors: List[str],
        content_indicators: List[str],
        scroll_indicators: List[str],
        wait_time: float = 2.0
    ):
        """
        初始化网站模式

        Args:
            name: 模式名称
            url_patterns: URL匹配模式
            scroll_strategy: 推荐的滚动策略
            button_selectors: 加载更多按钮选择器
            item_selectors: 内容项选择器
            content_indicators: 内容指示器
            scroll_indicators: 滚动指示器
            wait_time: 等待时间
        """
        self.name = name
        self.url_patterns = url_patterns
        self.scroll_strategy = scroll_strategy
        self.button_selectors = button_selectors
        self.item_selectors = item_selectors
        self.content_indicators = content_indicators
        self.scroll_indicators = scroll_indicators
        self.wait_time = wait_time


class ScrollStrategyDetector:
    """滚动策略智能检测器"""

    def __init__(self):
        """初始化检测器"""
        self.logger = logging.getLogger(__name__)

        # 定义已知网站模式
        self.website_patterns = [
            # 新闻和博客类
            WebsitePattern(
                name="News/Blog Infinite Scroll",
                url_patterns=[r"news\.", r"blog\.", r"medium\.com", r"wordpress\.org"],
                scroll_strategy="infinite",
                button_selectors=[
                    'button[class*="load"]',
                    'button[class*="more"]',
                    'a[class*="load"]',
                    '.load-more',
                    '#load-more',
                    '.show-more',
                    'button:contains("Load more")',
                    'button:contains("加载更多")'
                ],
                item_selectors=[
                    'article',
                    '.post',
                    '.entry',
                    '.item',
                    '.card',
                    '.news-item'
                ],
                content_indicators=[
                    'article', 'post', 'blog', 'news', 'entry'
                ],
                scroll_indicators=[
                    'infinite', 'scroll', 'lazy', 'loadmore', 'autoload'
                ],
                wait_time=2.0
            ),

            # 电商类
            WebsitePattern(
                name="E-commerce",
                url_patterns=[r"amazon\.", r"ebay\.", r"shop\.", r"store\.", r".*shop.*"],
                scroll_strategy="mixed",
                button_selectors=[
                    '.pagination-next',
                    '.next-page',
                    'a[class*="next"]',
                    'button[class*="next"]',
                    '.load-more-products',
                    '.show-more-products'
                ],
                item_selectors=[
                    '.product',
                    '.item',
                    '.product-card',
                    '[data-component-type="s-search-result"]',
                    '.s-result-item'
                ],
                content_indicators=[
                    'product', 'price', 'cart', 'buy', 'shop'
                ],
                scroll_indicators=[
                    'pagination', 'page', 'next', 'previous'
                ],
                wait_time=1.5
            ),

            # 社交媒体类
            WebsitePattern(
                name="Social Media",
                url_patterns=[r"twitter\.", r"facebook\.", r"instagram\.", r"linkedin\."],
                scroll_strategy="infinite",
                button_selectors=[
                    '.show-more',
                    '.load-more',
                    'button[aria-label*="More"]',
                    '.see-more'
                ],
                item_selectors=[
                    '.tweet', '.post', '.story', '.update'
                ],
                content_indicators=[
                    'post', 'tweet', 'share', 'like', 'comment'
                ],
                scroll_indicators=[
                    'feed', 'timeline', 'stream', 'infinite'
                ],
                wait_time=1.0
            ),

            # 学术期刊类
            WebsitePattern(
                name="Academic/Journal",
                url_patterns=[r".*journal.*", r".*academic.*", r".*research.*", r"springer\.", r"elsevier\.", r"frontiersin\.org"],
                scroll_strategy="mixed",
                button_selectors=[
                    '.pagination-next',
                    '.next-page',
                    'a[class*="next"]',
                    'button[class*="next"]',
                    '.show-more-results',
                    '.load-more-articles'
                ],
                item_selectors=[
                    'article',
                    '.article-item',
                    '.paper',
                    '.publication',
                    '.search-result'
                ],
                content_indicators=[
                    'article', 'paper', 'journal', 'research', 'publication'
                ],
                scroll_indicators=[
                    'pagination', 'article', 'journal', 'search'
                ],
                wait_time=2.5
            ),

            # 图片/视频类
            WebsitePattern(
                name="Media/Gallery",
                url_patterns=[r".*gallery.*", r".*photo.*", r".*video.*", r"pinterest\.", r"unsplash\."],
                scroll_strategy="infinite",
                button_selectors=[
                    '.load-more',
                    '.show-more',
                    'button[class*="more"]',
                    '.more-items'
                ],
                item_selectors=[
                    '.photo',
                    '.image',
                    '.video',
                    '.media-item',
                    '.gallery-item'
                ],
                content_indicators=[
                    'image', 'photo', 'video', 'gallery', 'media'
                ],
                scroll_indicators=[
                    'masonry', 'grid', 'gallery', 'infinite'
                ],
                wait_time=1.5
            )
        ]

    def detect_website_pattern(self, url: str) -> Optional[WebsitePattern]:
        """
        根据URL检测网站模式

        Args:
            url: 目标URL

        Returns:
            WebsitePattern: 匹配的网站模式
        """
        for pattern in self.website_patterns:
            for url_pattern in pattern.url_patterns:
                if re.search(url_pattern, url, re.IGNORECASE):
                    self.logger.info(f"匹配到网站模式: {pattern.name}")
                    return pattern
        return None

    def analyze_page_structure(self, driver, url: str) -> Dict:
        """
        分析页面结构

        Args:
            driver: WebDriver实例
            url: 目标URL

        Returns:
            Dict: 页面结构分析结果
        """
        try:
            driver.get(url)
            time.sleep(3)

            page_source = driver.page_source.lower()
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # 检测按钮
            detected_buttons = []
            for selector in self._get_all_button_selectors():
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        detected_buttons.append({
                            'selector': selector,
                            'count': len(elements),
                            'visible': any(elem.is_displayed() for elem in elements)
                        })
                except:
                    continue

            # 检测内容项
            detected_items = []
            for selector in self._get_all_item_selectors():
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        detected_items.append({
                            'selector': selector,
                            'count': len(elements)
                        })
                except:
                    continue

            # 检测滚动指示器
            scroll_indicators_found = []
            for indicator in ['infinite', 'scroll', 'lazy', 'loadmore', 'autoload', 'pagination']:
                if indicator in page_source:
                    scroll_indicators_found.append(indicator)

            # 检测分页
            pagination_found = self._detect_pagination(driver)

            # 检测动态加载
            dynamic_loading = self._detect_dynamic_loading(driver)

            return {
                'detected_buttons': detected_buttons,
                'detected_items': detected_items,
                'scroll_indicators': scroll_indicators_found,
                'pagination_found': pagination_found,
                'dynamic_loading': dynamic_loading,
                'page_height': driver.execute_script("return document.body.scrollHeight"),
                'has_scroll': driver.execute_script("return document.body.scrollHeight > window.innerHeight")
            }

        except Exception as e:
            self.logger.error(f"分析页面结构失败: {e}")
            return {}

    def _get_all_button_selectors(self) -> List[str]:
        """获取所有可能的按钮选择器"""
        selectors = set()
        for pattern in self.website_patterns:
            selectors.update(pattern.button_selectors)
        return list(selectors)

    def _get_all_item_selectors(self) -> List[str]:
        """获取所有可能的内容项选择器"""
        selectors = set()
        for pattern in self.website_patterns:
            selectors.update(pattern.item_selectors)
        return list(selectors)

    def _detect_pagination(self, driver) -> bool:
        """检测是否有传统分页"""
        pagination_selectors = [
            '.pagination',
            '.pager',
            'nav[aria-label*="pagination"]',
            '.page-numbers',
            '.pagination-links'
        ]

        for selector in pagination_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    return True
            except:
                continue

        return False

    def _detect_dynamic_loading(self, driver) -> bool:
        """检测是否支持动态加载"""
        try:
            # 记录初始高度
            initial_height = driver.execute_script("return document.body.scrollHeight")

            # 滚动到底部
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # 检查高度是否变化
            new_height = driver.execute_script("return document.body.scrollHeight")

            return new_height > initial_height

        except:
            return False

    def recommend_strategy(self, url: str, driver) -> Tuple[str, ScrollStrategy, List[str]]:
        """
        推荐最佳滚动策略

        Args:
            url: 目标URL
            driver: WebDriver实例

        Returns:
            Tuple: (策略名称, 策略实例, 推荐的选择器)
        """
        # 首先尝试匹配已知模式
        pattern = self.detect_website_pattern(url)
        if pattern:
            self.logger.info(f"使用预定义模式: {pattern.name}")
            return self._create_strategy_from_pattern(pattern)

        # 分析页面结构
        self.logger.info("分析页面结构以确定最佳策略...")
        analysis = self.analyze_page_structure(driver, url)

        # 基于分析结果推荐策略
        strategy_name, button_selector = self._recommend_from_analysis(analysis)

        # 创建策略实例
        if strategy_name == "button" and button_selector:
            strategy = ButtonClickStrategy(button_selector, max_clicks=50, click_pause_time=2.0)
        elif strategy_name == "infinite":
            strategy = InfiniteScrollStrategy(scroll_pause_time=2.0, incremental_scroll=True)
        else:
            strategy = MixedScrollStrategy(button_selector=button_selector, scroll_pause_time=2.0)

        return strategy_name, strategy, [button_selector] if button_selector else []

    def _create_strategy_from_pattern(self, pattern: WebsitePattern) -> Tuple[str, ScrollStrategy, List[str]]:
        """从预定义模式创建策略"""
        if pattern.scroll_strategy == "infinite":
            return "infinite", InfiniteScrollStrategy(pattern.wait_time), []
        elif pattern.scroll_strategy == "button":
            # 选择第一个可用的按钮选择器
            button_selector = pattern.button_selectors[0] if pattern.button_selectors else None
            return "button", ButtonClickStrategy(button_selector, max_clicks=50, click_pause_time=pattern.wait_time), [button_selector]
        else:
            button_selector = pattern.button_selectors[0] if pattern.button_selectors else None
            return "mixed", MixedScrollStrategy(button_selector, scroll_pause_time=pattern.wait_time), [button_selector]

    def _recommend_from_analysis(self, analysis: Dict) -> Tuple[str, Optional[str]]:
        """基于分析结果推荐策略"""
        # 如果检测到可见的加载更多按钮
        visible_buttons = [btn for btn in analysis.get('detected_buttons', []) if btn.get('visible')]
        if visible_buttons:
            best_button = max(visible_buttons, key=lambda x: x['count'])
            return "button", best_button['selector']

        # 如果有动态加载但没有分页
        if analysis.get('dynamic_loading') and not analysis.get('pagination_found'):
            return "infinite", None

        # 如果有传统分页
        if analysis.get('pagination_found'):
            return "mixed", None

        # 默认使用无限滚动
        return "infinite", None

    def get_best_item_selector(self, url: str, driver) -> str:
        """
        获取最佳的内容项选择器

        Args:
            url: 目标URL
            driver: WebDriver实例

        Returns:
            str: 推荐的选择器
        """
        # 首先尝试匹配已知模式
        pattern = self.detect_website_pattern(url)
        if pattern:
            for selector in pattern.item_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.logger.info(f"使用预定义选择器: {selector} (找到 {len(elements)} 个元素)")
                        return selector
                except:
                    continue

        # 分析页面结构
        analysis = self.analyze_page_structure(driver, url)
        detected_items = analysis.get('detected_items', [])

        if detected_items:
            best_item = max(detected_items, key=lambda x: x['count'])
            self.logger.info(f"使用分析得出的选择器: {best_item['selector']} (找到 {best_item['count']} 个元素)")
            return best_item['selector']

        # 默认选择器
        default_selectors = ['article', '.item', '.card', '.post']
        for selector in default_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    self.logger.info(f"使用默认选择器: {selector} (找到 {len(elements)} 个元素)")
                    return selector
            except:
                continue

        return '*'  # 最后的备用选择器


def create_smart_crawler(url: str) -> Dict:
    """
    创建智能爬虫配置

    Args:
        url: 目标URL

    Returns:
        Dict: 包含推荐配置的字典
    """
    detector = ScrollStrategyDetector()

    # 创建临时driver用于分析
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = None
    try:
        driver = webdriver.Chrome(options=options)

        # 推荐策略
        strategy_name, strategy, selectors = detector.recommend_strategy(url, driver)

        # 获取最佳选择器
        item_selector = detector.get_best_item_selector(url, driver)

        return {
            'strategy_name': strategy_name,
            'strategy': strategy,
            'item_selector': item_selector,
            'button_selectors': selectors,
            'recommendations': {
                'scroll_pause_time': 2.0,
                'max_scrolls': 50,
                'request_delay': 1.5,
                'use_incremental_scroll': strategy_name == 'infinite'
            }
        }

    except Exception as e:
        logging.error(f"创建智能爬虫配置失败: {e}")
        return {
            'strategy_name': 'infinite',
            'strategy': InfiniteScrollStrategy(),
            'item_selector': 'article',
            'button_selectors': [],
            'recommendations': {
                'scroll_pause_time': 2.0,
                'max_scrolls': 30,
                'request_delay': 1.0
            }
        }

    finally:
        if driver:
            driver.quit()


# 使用示例
def example_usage():
    """使用示例"""
    url = "https://kids.frontiersin.org/articles"

    print(f"为网站创建智能爬虫配置: {url}")
    config = create_smart_crawler(url)

    print(f"推荐策略: {config['strategy_name']}")
    print(f"推荐选择器: {config['item_selector']}")
    print(f"按钮选择器: {config['button_selectors']}")
    print(f"配置建议: {config['recommendations']}")


if __name__ == "__main__":
    example_usage()