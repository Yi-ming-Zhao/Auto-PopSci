# Frontiers for Young Minds 增强版爬虫

这是一个专为 Frontiers for Young Minds 网站优化的智能爬虫，支持多种滚动策略和无限滚动功能。

## 🚀 新增功能

### 智能无限滚动
- **自动检测**: 自动识别网站的加载方式（无限滚动 vs 按钮点击）
- **智能策略**: 根据网站特点选择最佳爬取策略
- **错误恢复**: 智能处理网络错误和页面变化
- **性能优化**: 优化的Chrome配置和滚动算法

### 多种爬取模式
1. **🧠 智能策略** - 自动检测并选择最佳方式
2. **📜 无限滚动** - 适用于动态加载内容的网站
3. **🔘 按钮点击** - 适用于有"加载更多"按钮的网站
4. **⚡ 传统分页** - 使用传统的分页方式
5. **🎯 快速测试** - 小规模测试，验证网站变化

## 📦 依赖要求

```bash
pip install selenium beautifulsoup4 requests pandas aiohttp
```

确保已安装：
- Chrome浏览器
- ChromeDriver（版本与Chrome匹配）

## 🛠️ 使用方法

### 基本使用

```bash
cd datasets/our_dataset/frontiers_kids/crawler
python frontiers_crawler.py
```

### 选择爬取模式

运行后会看到选项菜单：
```
🚀 Frontiers for Young Minds 智能爬虫启动
==================================================
请选择爬取模式:
1. 🧠 智能策略（推荐）- 自动检测最佳爬取方式
2. 📜 无限滚动模式 - 适用于动态加载内容的网站
3. 🔘 按钮点击模式 - 适用于有'加载更多'按钮的网站
4. ⚡ 传统分页模式 - 使用传统分页方式
5. 🎯 快速测试模式 - 只爬取少量文章进行测试
```

### 编程方式使用

```python
from frontiers_crawler import FrontiersCrawler

# 创建爬虫实例
crawler = FrontiersCrawler()

# 使用智能策略
articles = crawler.crawl_with_smart_strategy(max_scrolls=30)

# 使用无限滚动
articles = crawler.crawl_all_articles_with_selenium(
    max_scrolls=40,
    show_browser=False,
    max_articles=100
)

# 保存数据
crawler.save_to_json(articles, "output.json")
```

## 🎯 功能特点

### 智能检测
- 自动检测"加载更多"按钮
- 识别无限滚动模式
- 分析页面结构
- 适应网站变化

### 优化配置
- 反检测机制
- 性能优化设置
- 错误自动恢复
- 进度实时显示

### 多格式输出
- JSON格式（完整数据）
- CSV格式（表格数据）
- 统计信息展示

## 📊 输出数据结构

每篇文章包含以下字段：
```json
{
  "url": "文章链接",
  "title": "文章标题",
  "description": "文章描述",
  "author": "作者信息",
  "published_date": "发布日期",
  "article_type": "文章类型",
  "image_url": "图片链接",
  "article_id": "文章ID",
  "content": "文章内容",
  "related_articles": [
    {
      "title": "相关文章标题",
      "url": "相关文章链接"
    }
  ],
  "meta_data": {
    "keywords": "关键词",
    "subjects": "主题分类",
    "doi": "DOI编号"
  }
}
```

## 🔧 配置选项

### Selenium配置
```python
# 显示浏览器窗口（调试用）
crawler.crawl_all_articles_with_selenium(show_browser=True)

# 限制爬取数量
crawler.crawl_all_articles_with_selenium(max_articles=50)

# 调整滚动次数
crawler.crawl_with_smart_strategy(max_scrolls=20)
```

### Chrome选项
- 无头模式（默认）
- 反检测设置
- 性能优化
- 自定义User-Agent

## 🧪 测试功能

运行测试脚本验证功能：
```bash
python test_enhanced_crawler.py
```

测试包括：
- 基本功能测试
- Selenium设置测试
- 滚动检测测试
- 小规模爬取测试

## ⚡ 性能优化

### 智能滚动算法
- 检测内容变化
- 自适应滚动速度
- 多种滚动策略
- 自动停止机制

### 资源管理
- 自动关闭浏览器
- 内存优化
- 异步处理
- 错误恢复

## 🛠️ 故障排除

### 常见问题

1. **ChromeDriver版本不匹配**
   ```bash
   # 更新ChromeDriver
   brew upgrade chromedriver  # macOS
   # 或下载对应版本：https://chromedriver.chromium.org/
   ```

2. **网站访问被拒绝**
   - 增加请求延迟
   - 使用代理设置
   - 检查User-Agent

3. **滚动不工作**
   - 检查网站结构变化
   - 尝试不同的爬取模式
   - 使用快速测试模式诊断

4. **内存不足**
   - 减少`max_scrolls`参数
   - 使用无头模式
   - 分批处理数据

### 调试模式

```python
# 显示浏览器窗口进行调试
articles = crawler.crawl_all_articles_with_selenium(
    show_browser=True,
    max_scrolls=5
)
```

## 📈 使用建议

### 最佳实践
1. **首次使用**: 选择快速测试模式验证网站
2. **大规模爬取**: 使用智能策略，设置合适的限制
3. **定期维护**: 监控网站结构变化
4. **数据质量**: 定期检查提取的内容质量

### 参数调优
- `max_scrolls`: 根据网站内容密度调整
- `max_articles`: 根据需求和系统资源设置
- `show_browser`: 调试时开启，生产环境关闭

## 🔄 版本历史

### v2.0 (当前版本)
- ✨ 新增智能无限滚动功能
- 🧠 自动检测网站加载方式
- 🔘 优化按钮点击策略
- ⚡ 改进性能和错误处理
- 📊 增强数据输出格式
- 🛠️ 添加测试和调试功能

### v1.0 (原版本)
- 基础爬取功能
- 异步处理支持
- JSON数据输出

## 📞 支持与反馈

如果遇到问题：
1. 查看测试脚本输出
2. 检查日志信息
3. 尝试不同的爬取模式
4. 确认依赖环境正确

## 📄 许可证

本项目遵循原项目的许可证条款。