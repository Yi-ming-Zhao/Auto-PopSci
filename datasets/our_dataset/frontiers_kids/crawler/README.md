# Frontiers for Young Minds 文章爬虫

这个爬虫用于从 Frontiers for Young Minds 网站爬取所有文章，并保存为与 NatGeo Kids 相同的 JSON 格式。

## 功能特性

- 🕷️ 爬取 Frontiers for Young Minds 网站的所有文章
- 📄 提取文章的完整内容、元数据和相关文章
- 🔄 **支持真正的无限滚动**（使用Selenium）
- 📝 保存为标准 JSON 格式，与 NatGeo Kids 数据格式一致
- 🛡️ 包含错误处理和请求延迟
- 📊 支持断点续爬（通过修改 max_pages 参数）
- 🚀 使用异步IO提升爬取效率，同时遵守爬虫礼仪
- 🔍 **Selenium动态渲染**，确保获取JavaScript生成的内容
- 🌐 **混合爬取模式**：Selenium + aiohttp，兼顾速度和完整性

## 依赖包

```bash
pip install requests beautifulsoup4 lxml aiohttp selenium
```

**注意：** Selenium需要Chrome浏览器和对应的ChromeDriver。请确保：
1. 已安装Chrome浏览器
2. 已下载与Chrome版本匹配的ChromeDriver
3. ChromeDriver已添加到系统PATH中

## 使用方法

### 基本使用

```bash
cd datasets/our_dataset/frontiers_kids/crawler/
python3 frontiers_crawler.py
```

### 自定义参数

可以在 `main_sync()` 函数中修改以下参数：

```python
# 输出路径
output_path = "/path/to/your/output.json"

# 最大爬取页数（设为None自动检测无限滚动）
max_pages = None  # 自动获取所有文章
# max_pages = 100  # 限制100页

# 创建爬虫实例
crawler = FrontiersCrawler()
articles = crawler.crawl_all_articles(max_pages=max_pages)
```

### 异步版本

如果需要更精细的控制，可以直接使用异步版本：

```python
import asyncio
from frontiers_crawler import FrontiersCrawler

async def async_crawl():
    crawler = FrontiersCrawler()
    articles = await crawler.crawl_all_articles_async(max_pages=None)
    return articles

# 运行异步爬虫
articles = asyncio.run(async_crawl())
```

### Selenium版本

使用Selenium进行真正的无限滚动爬取：

```python
from frontiers_crawler import FrontiersCrawler

# 创建爬虫实例
crawler = FrontiersCrawler()

# 使用Selenium爬取（推荐）
articles = crawler.crawl_all_articles(use_selenium=True)
```

### 混合模式

手动控制爬取模式：

```python
# 使用Selenium进行URL发现，异步获取详情
crawler = FrontiersCrawler()
article_urls = crawler.get_article_urls_with_selenium()
# 然后使用其他方法处理...
```

## 数据格式

生成的 JSON 文件包含以下字段：

```json
{
  "url": "文章链接",
  "title": "文章标题",
  "description": "文章摘要",
  "author": "作者列表",
  "published_date": "发布日期",
  "article_type": "文章类型 (Core Concept/New Discovery)",
  "image_url": "图片链接",
  "article_id": "文章ID",
  "content": "完整文章内容",
  "related_articles": "相关文章列表",
  "meta_data": {
    "doi": "DOI编号",
    "article_type": "文章类型",
    "published_date": "发布日期"
  }
}
```

## 爬虫特性

### 智能内容提取
- 多种选择器策略提取文章内容
- 过滤短文本，保留有意义的内容
- 支持异步加载和分页检测
- 保持文章的原始结构和格式
- 保留完整文章内容，包括Glossary等所有部分

### 无限滚动支持
- **自动检测无限滚动**机制，无需手动设置页数
- 智能估算文章总数，确保获取所有内容
- 连续空页面检测，避免无效爬取

### 异步并发处理
- **使用aiohttp实现异步IO**，大幅提升爬取效率
- **智能并发控制**：最多12个并发请求，平衡效率与服务器负载
- **遵守爬虫礼仪**：保持请求间隔，维护网站友好性
- 连接池优化，减少网络开销

### 错误处理
- 网络请求超时处理
- HTML解析错误处理
- 单篇文章失败不影响整体爬取
- 详细的错误日志和状态报告

### 礼仪爬取
- 设置合理的请求延迟（1-2秒）
- 包含适当的 User-Agent
- 遵循网站的爬虫协议
- **并发数量限制**，避免对服务器造成压力

## 注意事项

1. **请求频率控制**：爬虫内置了延迟机制，避免对网站造成过大压力
2. **网络环境**：确保网络连接稳定，某些地区可能需要代理
3. **数据完整性**：如果爬取过程中断，可以修改 max_pages 从指定页面继续
4. **存储空间**：完整爬取可能产生大量数据，确保有足够存储空间

## 输出文件

默认输出文件路径：
```
/Users/yzxbb/Desktop/Auto-Popsci/datasets/our_dataset/frontiers_kids/original_frontiers/all_frontiers_kids_articles.json
```

## 示例输出

```
使用Selenium进行动态网页爬取...
开始使用Selenium加载所有文章...
滚动 1: 发现 12 篇新文章，总计 12 篇
滚动 2: 发现 24 篇新文章，总计 36 篇
滚动 3: 发现 12 篇新文章，总计 48 篇
滚动 4: 发现 18 篇新文章，总计 66 篇
滚动 5: 发现 15 篇新文章，总计 81 篇
滚动 6: 没有发现新文章
页面高度没有变化，停止滚动
滚动完成，总共发现 81 篇文章URL，开始获取详情...

总共发现 81 篇文章URL，开始获取详情...
处理第 1/81 篇文章: https://kids.frontiersin.org/articles/10.3389/frym.2025.1354853
  完成: The Money Challenge of Climate Change
处理第 2/81 篇文章: https://kids.frontiersin.org/articles/10.3389/frym.2025.1632173
  完成: The Wonderful World of Wasps
...

Selenium爬取完成，总共获取 81 篇文章

数据已保存到: /path/to/output.json
总共保存了 81 篇文章

=== 爬取完成 ===
总共爬取了 81 篇文章
```

## 故障排除

### 常见问题

1. **SSL证书错误**：
   ```python
   # 在 session 创建后添加
   from requests.packages.urllib3.exceptions import InsecureRequestWarning
   requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
   ```

2. **超时错误**：
   - 检查网络连接
   - 增加 timeout 参数

3. **解析错误**：
   - 网站结构可能发生变化
   - 需要更新 CSS 选择器

4. **Selenium相关问题**：
   ```python
   # ChromeDriver 未找到
   # 解决方案：
   # 1. 下载对应版本的ChromeDriver
   # 2. 将ChromeDriver添加到系统PATH
   # 3. 或者指定ChromeDriver路径
   chrome_options = Options()
   chrome_options.binary_location = "/path/to/chromedriver"
   ```

5. **Chrome浏览器未找到**：
   - 安装Chrome浏览器
   - 确保Chrome可从命令行访问
   - 检查Chrome版本与ChromeDriver版本匹配

## 扩展功能

可以根据需要添加以下功能：

- 支持多线程/异步爬取
- 添加代理支持
- 实现断点续爬的持久化
- 添加数据去重功能
- 支持更多字段提取

## 许可证

本项目仅用于学术研究目的，请遵守目标网站的 robots.txt 和使用条款。