# Selenium滚动翻页数据采集框架

这个框架提供了强大的Selenium滚动翻页数据采集功能，支持多种滚动策略和智能检测。

## 功能特性

- **多种滚动策略**: 无限滚动、按钮点击、混合策略
- **智能策略检测**: 自动识别网站类型并推荐最佳策略
- **可配置性强**: 支持自定义选择器、等待时间等参数
- **错误处理**: 完善的异常处理和重试机制
- **进度跟踪**: 实时显示爬取进度
- **数据导出**: 支持JSON和CSV格式导出

## 核心组件

### 1. SeleniumScrollCrawler (通用滚动爬虫类)

基本的滚动爬虫类，提供核心功能。

```python
from selenium_scroll_crawler import SeleniumScrollCrawler

# 创建爬虫实例
crawler = SeleniumScrollCrawler(
    base_url="https://example.com",
    headless=True,
    scroll_pause_time=2.0
)

# 使用上下文管理器
with crawler:
    # 滚动并收集数据
    items = crawler.scroll_and_collect(
        url="https://example.com/articles",
        item_selector="article",
        max_scrolls=50
    )
```

### 2. ScrollStrategy (滚动策略)

支持三种主要滚动策略：

#### InfiniteScrollStrategy (无限滚动)
适用于动态加载内容的网站。

```python
from selenium_scroll_crawler import InfiniteScrollStrategy

strategy = InfiniteScrollStrategy(
    scroll_pause_time=2.0,  # 滚动间隔时间
    incremental_scroll=True  # 渐进式滚动，模拟人类行为
)
```

#### ButtonClickStrategy (按钮点击)
适用于有"加载更多"按钮的网站。

```python
from selenium_scroll_crawler import ButtonClickStrategy

strategy = ButtonClickStrategy(
    button_selector="button.load-more",  # 按钮选择器
    max_clicks=20,  # 最大点击次数
    click_pause_time=1.5  # 点击间隔时间
)
```

#### MixedScrollStrategy (混合策略)
结合无限滚动和按钮点击。

```python
from selenium_scroll_crawler import MixedScrollStrategy

strategy = MixedScrollStrategy(
    button_selector="button.load-more",  # 可选
    scroll_pause_time=2.0
)
```

### 3. ScrollStrategyDetector (智能检测器)

自动检测网站类型并推荐最佳策略。

```python
from scroll_strategy_detector import create_smart_crawler

# 创建智能爬虫配置
config = create_smart_crawler("https://example.com/articles")

print(f"推荐策略: {config['strategy_name']}")
print(f"推荐选择器: {config['item_selector']}")
```

## 使用示例

### 基础使用

```python
from selenium_scroll_crawler import SeleniumScrollCrawler

# 创建爬虫
crawler = SeleniumScrollCrawler(
    base_url="https://example.com",
    headless=False,  # 显示浏览器窗口
    scroll_pause_time=3.0  # 等待3秒
)

# 自定义内容提取函数
def extract_content(element):
    return {
        'title': element.find_element(By.TAG_NAME, 'h2').text,
        'link': element.find_element(By.TAG_NAME, 'a').get_attribute('href'),
        'description': element.find_element(By.TAG_NAME, 'p').text
    }

# 使用爬虫
with crawler:
    articles = crawler.scroll_and_collect(
        url="https://example.com/news",
        item_selector="article.news-item",
        content_extractor=extract_content,
        max_scrolls=30,
        progress_callback=lambda scroll, total, new: print(f"滚动{scroll}: {total}篇文章")
    )

    # 保存数据
    crawler.save_to_file(articles, "articles.json", "json")
```

### 智能检测使用

```python
from scroll_strategy_detector import ScrollStrategyDetector
from selenium_scroll_crawler import SeleniumScrollCrawler

# 检测器
detector = ScrollStrategyDetector()

# 创建爬虫
with SeleniumScrollCrawler() as crawler:
    # 获取推荐策略
    strategy_name, strategy, selectors = detector.recommend_strategy(
        "https://example.com", crawler.driver
    )

    # 获取最佳选择器
    item_selector = detector.get_best_item_selector(
        "https://example.com", crawler.driver
    )

    # 使用推荐策略
    items = crawler.scroll_and_collect(
        url="https://example.com",
        item_selector=item_selector,
        scroll_strategy=strategy
    )
```

### Frontiers爬虫使用

```python
from enhanced_frontiers_crawler import EnhancedFrontiersCrawler

# 创建Frontiers专用爬虫
crawler = EnhancedFrontiersCrawler()

# 测试不同策略
results = crawler.test_different_strategies()

# 使用最佳策略爬取
articles = crawler.crawl_with_strategy("auto")

# 保存数据
output_path = crawler.crawl_and_save("mixed", "frontiers_articles.json")
```

## 高级功能

### 自定义内容提取

```python
def custom_extractor(element):
    # 使用JavaScript提取更可靠的数据
    data = crawler.driver.execute_script("""
        var element = arguments[0];
        return {
            title: element.querySelector('h2').textContent.trim(),
            link: element.querySelector('a').href,
            image: element.querySelector('img').src,
            date: element.querySelector('.date').textContent
        };
    """, element)

    return data
```

### 详情页面采集

```python
def extract_detail(driver, url):
    driver.get(url)
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    return {
        'content': soup.select_one('.article-content').get_text(),
        'author': soup.select_one('.author').get_text(),
        'publish_date': soup.select_one('.date').get_text()
    }

# 采集基本信息后收集详情
items = crawler.scroll_and_collect(url, item_selector)
detailed_items = crawler.collect_details(items, extract_detail)
```

### 进度监控

```python
def progress_monitor(scroll_count, total_items, new_items):
    print(f"进度: 滚动{scroll_count}次, 总计{total_items}项, 新增{new_items}项")

    # 可以在这里添加更复杂的逻辑
    if total_items > 1000:
        print("已收集足够数据，可以考虑停止")
        return False  # 返回False可以停止爬取

items = crawler.scroll_and_collect(
    url, item_selector,
    progress_callback=progress_monitor
)
```

## 配置选项

### Chrome选项

```python
chrome_options = Options()
chrome_options.add_argument('--headless')  # 无头模式
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-images')  # 禁用图片加载
chrome_options.add_argument('--window-size=1920,1080')
```

### 性能优化

```python
crawler = SeleniumScrollCrawler(
    headless=True,  # 无头模式提高性能
    scroll_pause_time=1.0,  # 减少等待时间
    request_delay=0.5,  # 减少请求间隔
    user_agent="自定义User-Agent"
)
```

## 错误处理

框架包含完善的错误处理机制：

- **超时处理**: 自动重试和超时控制
- **元素查找错误**: 多种选择器备选方案
- **网络错误**: 自动重试机制
- **内存优化**: 及时清理资源

## 测试

运行测试脚本验证功能：

```bash
cd datasets/crawlers
python test_scroll_crawler.py
```

测试包括：
- 策略检测测试
- 基本滚动策略测试
- 增强版爬虫测试
- 真实网站爬取测试

## 注意事项

1. **遵守robots.txt**: 始终检查目标网站的robots.txt文件
2. **合理延迟**: 设置适当的请求延迟，避免对服务器造成压力
3. **错误处理**: 始终使用try-catch处理异常
4. **资源管理**: 使用上下文管理器或手动关闭WebDriver
5. **法律合规**: 确保爬取行为符合相关法律法规

## 依赖安装

```bash
pip install selenium beautifulsoup4 requests pandas lxml
```

还需要安装ChromeDriver：
```bash
# macOS
brew install chromedriver

# 或使用webdriver-manager自动管理
pip install webdriver-manager
```

## 扩展开发

### 自定义滚动策略

```python
from selenium_scroll_crawler import ScrollStrategy

class CustomScrollStrategy(ScrollStrategy):
    def scroll(self, driver, max_scrolls=50):
        # 实现自定义滚动逻辑
        for i in range(max_scrolls):
            # 自定义滚动行为
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(2)

        return True
```

### 自定义网站模式

```python
from scroll_strategy_detector import WebsitePattern

custom_pattern = WebsitePattern(
    name="Custom Website",
    url_patterns=[r"custom\.com"],
    scroll_strategy="infinite",
    button_selectors=['.custom-load-more'],
    item_selectors=['.custom-item'],
    content_indicators=['custom'],
    scroll_indicators=['custom-scroll']
)

detector = ScrollStrategyDetector()
detector.website_patterns.append(custom_pattern)
```

## 性能调优

1. **减少不必要的等待**: 使用显式等待而非固定延迟
2. **禁用图片和CSS**: 在不需要视觉元素时禁用
3. **并发处理**: 使用多个浏览器实例
4. **缓存机制**: 缓存已访问的URL
5. **增量更新**: 只爬取新增内容

## 故障排除

### 常见问题

1. **ChromeDriver版本不匹配**
   ```bash
   # 更新ChromeDriver
   brew upgrade chromedriver
   ```

2. **元素查找失败**
   - 检查选择器是否正确
   - 确认页面是否完全加载
   - 使用显式等待

3. **内存泄漏**
   - 及时关闭WebDriver
   - 清理不需要的变量
   - 使用上下文管理器

4. **被反爬虫机制阻止**
   - 增加请求延迟
   - 使用真实的User-Agent
   - 考虑使用代理

## 更新日志

- v1.0.0: 初始版本，支持基本滚动策略
- v1.1.0: 添加智能策略检测
- v1.2.0: 增强错误处理和性能优化
- v1.3.0: 添加更多网站模式支持