#!/usr/bin/env python3
"""
通用Selenium滚动翻页爬虫类
支持多种滚动策略和数据提取模式
"""

import time
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any, Set
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests


class ScrollStrategy(ABC):
    """滚动策略抽象基类"""

    @abstractmethod
    def scroll(self, driver, max_scrolls: int = 50) -> bool:
        """
        执行滚动策略

        Args:
            driver: WebDriver实例
            max_scrolls: 最大滚动次数

        Returns:
            bool: 是否成功加载新内容
        """
        pass


class InfiniteScrollStrategy(ScrollStrategy):
    """无限滚动策略 - 适用于动态加载内容的网站"""

    def __init__(self, scroll_pause_time: float = 2.0, incremental_scroll: bool = False):
        self.scroll_pause_time = scroll_pause_time
        self.incremental_scroll = incremental_scroll

    def scroll(self, driver, max_scrolls: int = 50) -> bool:
        """执行无限滚动"""
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        no_change_count = 0

        while scroll_count < max_scrolls:
            # 滚动到底部
            if self.incremental_scroll:
                # 渐进式滚动，看起来更像人类行为
                driver.execute_script("window.scrollBy(0, window.innerHeight);")
            else:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            time.sleep(self.scroll_pause_time)

            # 检查页面高度是否变化
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                no_change_count += 1
                if no_change_count >= 3:  # 连续3次没有变化就停止
                    break
            else:
                no_change_count = 0
                last_height = new_height

            scroll_count += 1

        return scroll_count > 0


class ButtonClickStrategy(ScrollStrategy):
    """点击按钮策略 - 适用于有"加载更多"按钮的网站"""

    def __init__(self, button_selector: str, max_clicks: int = 20, click_pause_time: float = 1.5):
        self.button_selector = button_selector
        self.max_clicks = max_clicks
        self.click_pause_time = click_pause_time

    def scroll(self, driver, max_scrolls: int = 50) -> bool:
        """点击"加载更多"按钮"""
        click_count = 0

        while click_count < self.max_clicks:
            try:
                # 查找按钮
                button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, self.button_selector))
                )

                # 滚动到按钮可见
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                time.sleep(0.5)

                # 点击按钮
                button.click()
                time.sleep(self.click_pause_time)
                click_count += 1

            except TimeoutException:
                # 找不到可点击的按钮，停止
                break
            except Exception as e:
                logging.warning(f"点击按钮时出错: {e}")
                break

        return click_count > 0


class MixedScrollStrategy(ScrollStrategy):
    """混合滚动策略 - 结合无限滚动和按钮点击"""

    def __init__(self, button_selector: str = None, scroll_pause_time: float = 2.0):
        self.infinite_scroll = InfiniteScrollStrategy(scroll_pause_time)
        self.button_click = ButtonClickStrategy(button_selector) if button_selector else None

    def scroll(self, driver, max_scrolls: int = 50) -> bool:
        """执行混合滚动策略"""
        result = False

        # 先尝试无限滚动
        result |= self.infinite_scroll.scroll(driver, max_scrolls // 2)

        # 再尝试点击按钮
        if self.button_click:
            result |= self.button_click.scroll(driver, max_scrolls // 2)

        return result


class SeleniumScrollCrawler:
    """通用Selenium滚动翻页爬虫"""

    def __init__(
        self,
        base_url: str,
        headless: bool = True,
        timeout: int = 30,
        scroll_pause_time: float = 2.0,
        request_delay: float = 1.0,
        user_agent: str = None
    ):
        """
        初始化爬虫

        Args:
            base_url: 目标网站基础URL
            headless: 是否使用无头模式
            timeout: 元素等待超时时间
            scroll_pause_time: 滚动暂停时间
            request_delay: 请求延迟
            user_agent: 用户代理字符串
        """
        self.base_url = base_url
        self.headless = headless
        self.timeout = timeout
        self.scroll_pause_time = scroll_pause_time
        self.request_delay = request_delay
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # 设置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # WebDriver实例
        self.driver = None

        # 配置选项
        self.chrome_options = self._setup_chrome_options()

    def _setup_chrome_options(self) -> Options:
        """配置Chrome选项"""
        options = Options()

        if self.headless:
            options.add_argument('--headless')

        # 性能优化选项
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-images')  # 禁用图片加载以提高速度
        options.add_argument('--disable-javascript')  # 注意：某些网站需要JS

        # 窗口大小
        options.add_argument('--window-size=1920,1080')

        # 用户代理
        options.add_argument(f'--user-agent={self.user_agent}')

        # 防检测选项
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        return options

    def setup_driver(self) -> bool:
        """初始化WebDriver"""
        try:
            self.driver = webdriver.Chrome(options=self.chrome_options)

            # 设置隐式等待
            self.driver.implicitly_wait(self.timeout)

            # 设置页面加载超时
            self.driver.set_page_load_timeout(60)

            # 反检测脚本
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)

            self.logger.info("WebDriver初始化成功")
            return True

        except Exception as e:
            self.logger.error(f"初始化WebDriver失败: {e}")
            return False

    def detect_scroll_type(self, url: str) -> ScrollStrategy:
        """检测网站的滚动类型并返回相应的策略"""
        try:
            self.driver.get(url)
            time.sleep(3)

            page_source = self.driver.page_source.lower()

            # 检测加载更多按钮
            load_more_selectors = [
                'button[class*="load"]',
                'button[class*="more"]',
                'a[class*="load"]',
                'a[class*="more"]',
                '[data-testid*="load"]',
                '[data-testid*="more"]',
                'button:contains("Load more")',
                'button:contains("加载更多")',
                'button:contains("More")',
                '.load-more',
                '#load-more'
            ]

            for selector in load_more_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.logger.info(f"检测到'加载更多'按钮，选择器: {selector}")
                        return ButtonClickStrategy(selector, max_clicks=50, click_pause_time=2.0)
                except:
                    continue

            # 检测无限滚动
            infinite_scroll_indicators = [
                'infinite',
                'scroll',
                'lazy',
                'loadmore',
                'autoload',
                'pagination'
            ]

            if any(indicator in page_source for indicator in infinite_scroll_indicators):
                self.logger.info("检测到无限滚动模式")
                return InfiniteScrollStrategy(self.scroll_pause_time, incremental_scroll=True)

            # 默认使用混合策略
            self.logger.info("使用混合滚动策略")
            return MixedScrollStrategy(scroll_pause_time=self.scroll_pause_time)

        except Exception as e:
            self.logger.error(f"检测滚动类型失败: {e}")
            return InfiniteScrollStrategy(self.scroll_pause_time)

    def scroll_and_collect(
        self,
        url: str,
        item_selector: str,
        scroll_strategy: ScrollStrategy = None,
        max_scrolls: int = 50,
        content_extractor: Callable = None,
        stop_when_no_new_items: bool = True,
        progress_callback: Callable = None
    ) -> List[Dict]:
        """
        滚动页面并收集数据

        Args:
            url: 目标URL
            item_selector: 数据项选择器
            scroll_strategy: 滚动策略
            max_scrolls: 最大滚动次数
            content_extractor: 内容提取函数
            stop_when_no_new_items: 当没有新数据时是否停止
            progress_callback: 进度回调函数

        Returns:
            List[Dict]: 收集的数据列表
        """
        if not self.driver:
            if not self.setup_driver():
                return []

        # 自动检测滚动策略
        if scroll_strategy is None:
            scroll_strategy = self.detect_scroll_type(url)

        try:
            self.driver.get(url)
            time.sleep(3)

            collected_items = []
            seen_items = set()  # 用于去重
            scroll_count = 0
            no_new_items_count = 0

            while scroll_count < max_scrolls:
                # 查找当前页面的所有元素
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, item_selector)
                    current_items = []

                    for element in elements:
                        try:
                            # 提取数据
                            if content_extractor:
                                item_data = content_extractor(element)
                            else:
                                # 默认提取方法
                                item_data = self.default_extractor(element)

                            # 去重
                            item_key = item_data.get('url') or item_data.get('title') or str(element)
                            if item_key not in seen_items:
                                seen_items.add(item_key)
                                current_items.append(item_data)

                        except Exception as e:
                            self.logger.warning(f"提取元素数据时出错: {e}")
                            continue

                    # 检查是否有新数据
                    new_items_count = len(current_items) - len(collected_items)
                    if new_items_count > 0:
                        collected_items = current_items  # 更新为最新数据
                        no_new_items_count = 0
                        self.logger.info(f"滚动 {scroll_count + 1}: 发现 {new_items_count} 个新项目，总计 {len(collected_items)} 个")

                        # 调用进度回调
                        if progress_callback:
                            progress_callback(scroll_count, len(collected_items), new_items_count)
                    else:
                        no_new_items_count += 1
                        self.logger.info(f"滚动 {scroll_count + 1}: 没有发现新项目")

                        if stop_when_no_new_items and no_new_items_count >= 3:
                            self.logger.info("连续3次没有新数据，停止滚动")
                            break

                except Exception as e:
                    self.logger.error(f"查找元素时出错: {e}")
                    break

                # 执行滚动
                if not scroll_strategy.scroll(self.driver, 1):
                    self.logger.info("滚动策略返回False，停止滚动")
                    break

                scroll_count += 1
                time.sleep(self.scroll_pause_time)

            self.logger.info(f"滚动完成，总共收集了 {len(collected_items)} 个项目")
            return collected_items

        except Exception as e:
            self.logger.error(f"滚动采集过程中出错: {e}")
            return collected_items

    def default_extractor(self, element) -> Dict:
        """默认的元素数据提取方法"""
        try:
            # 尝试提取链接
            link_elem = element.find_element(By.TAG_NAME, 'a')
            url = link_elem.get_attribute('href')

            # 尝试提取标题
            title = ""
            title_selectors = ['h1', 'h2', 'h3', 'h4', '.title', '.headline', '[title]']
            for selector in title_selectors:
                try:
                    title_elem = element.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip() or title_elem.get_attribute('title') or title_elem.get_attribute('alt')
                    if title:
                        break
                except:
                    continue

            # 如果没找到标题，使用链接文本
            if not title and link_elem:
                title = link_elem.text.strip()

            # 尝试提取描述
            description = ""
            desc_selectors = ['p', '.description', '.summary', '.excerpt']
            for selector in desc_selectors:
                try:
                    desc_elem = element.find_element(By.CSS_SELECTOR, selector)
                    description = desc_elem.text.strip()
                    if description:
                        break
                except:
                    continue

            # 尝试提取图片
            image_url = ""
            try:
                img_elem = element.find_element(By.TAG_NAME, 'img')
                image_url = img_elem.get_attribute('src') or img_elem.get_attribute('data-src')
            except:
                pass

            return {
                'url': url or "",
                'title': title or "",
                'description': description or "",
                'image_url': image_url or "",
                'element_text': element.text.strip()[:500]  # 保留元素文本作为备份
            }

        except Exception as e:
            self.logger.warning(f"默认提取器出错: {e}")
            return {
                'url': "",
                'title': "",
                'description': "",
                'image_url': "",
                'element_text': element.text.strip()[:500] if element else ""
            }

    def collect_details(self, items: List[Dict], detail_extractor: Callable = None) -> List[Dict]:
        """
        收集每个项目的详细信息

        Args:
            items: 项目列表
            detail_extractor: 详情提取函数

        Returns:
            List[Dict]: 包含详细信息的项目列表
        """
        detailed_items = []

        for i, item in enumerate(items):
            if not item.get('url'):
                detailed_items.append(item)
                continue

            try:
                self.logger.info(f"获取详情 {i+1}/{len(items)}: {item.get('title', 'N/A')}")

                if detail_extractor:
                    detailed_item = detail_extractor(self.driver, item['url'])
                else:
                    detailed_item = self.default_detail_extractor(item['url'])

                # 合并基本信息和详细信息
                if detailed_item:
                    item.update(detailed_item)

                detailed_items.append(item)

                # 添加延迟以遵守爬虫礼仪
                time.sleep(self.request_delay)

            except Exception as e:
                self.logger.error(f"获取详情失败 {item.get('url')}: {e}")
                detailed_items.append(item)  # 保留基本信息

        return detailed_items

    def default_detail_extractor(self, url: str) -> Dict:
        """默认的详情提取方法"""
        try:
            self.driver.get(url)
            time.sleep(2)

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # 提取标题
            title = ""
            title_selectors = ['h1', '.title', '.headline', 'title']
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break

            # 提取内容
            content = ""
            content_selectors = ['article', '.content', '.article-body', '.post-content', 'main']
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # 提取所有段落
                    paragraphs = content_elem.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    content_parts = []
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text and len(text) > 10:  # 过滤短文本
                            content_parts.append(text)
                    content = '\n\n'.join(content_parts)
                    break

            return {
                'title': title,
                'content': content,
                'content_length': len(content)
            }

        except Exception as e:
            self.logger.warning(f"详情提取失败 {url}: {e}")
            return {}

    def save_to_file(self, data: List[Dict], file_path: str, format: str = 'json'):
        """
        保存数据到文件

        Args:
            data: 要保存的数据
            file_path: 文件路径
            format: 文件格式 ('json' 或 'csv')
        """
        try:
            import os
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            if format.lower() == 'json':
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            elif format.lower() == 'csv':
                import pandas as pd
                df = pd.DataFrame(data)
                df.to_csv(file_path, index=False, encoding='utf-8')

            else:
                raise ValueError(f"不支持的格式: {format}")

            self.logger.info(f"数据已保存到: {file_path}")

        except Exception as e:
            self.logger.error(f"保存文件失败: {e}")

    def close(self):
        """关闭WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("WebDriver已关闭")
            except Exception as e:
                self.logger.error(f"关闭WebDriver时出错: {e}")
            finally:
                self.driver = None

    def __enter__(self):
        """上下文管理器入口"""
        self.setup_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()


# 示例使用方法
def example_usage():
    """使用示例"""

    # 创建爬虫实例
    crawler = SeleniumScrollCrawler(
        base_url="https://example.com",
        headless=True,
        scroll_pause_time=2.0
    )

    # 使用上下文管理器
    with crawler:
        # 定义内容提取函数
        def extract_article(element):
            return {
                'url': element.find_element(By.CSS_SELECTOR, 'a').get_attribute('href'),
                'title': element.find_element(By.CSS_SELECTOR, 'h2').text.strip(),
                'description': element.find_element(By.CSS_SELECTOR, 'p').text.strip() if element.find_elements(By.CSS_SELECTOR, 'p') else ""
            }

        # 定义进度回调
        def progress_callback(scroll_count, total_items, new_items):
            print(f"滚动 {scroll_count}: 总计 {total_items} 项，新增 {new_items} 项")

        # 滚动并收集数据
        articles = crawler.scroll_and_collect(
            url="https://example.com/articles",
            item_selector="article",
            content_extractor=extract_article,
            max_scrolls=30,
            progress_callback=progress_callback
        )

        # 收集详细信息
        detailed_articles = crawler.collect_details(articles)

        # 保存数据
        crawler.save_to_file(detailed_articles, "articles.json", "json")
        crawler.save_to_file(detailed_articles, "articles.csv", "csv")

        print(f"总共收集了 {len(detailed_articles)} 篇文章")


if __name__ == "__main__":
    example_usage()