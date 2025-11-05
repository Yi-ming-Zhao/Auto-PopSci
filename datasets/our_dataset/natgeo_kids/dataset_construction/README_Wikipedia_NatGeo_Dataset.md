# Wikipedia-NatGeo Kids 科普数据集构建项目

## 项目概述

本项目构建了一个Wikipedia原文与NatGeo Kids科普文章配对的数据集，用于科普内容生成和评估。通过从NatGeo Kids文章描述中提取关键词，搜索对应的Wikipedia原文，构建成对的数据集，为后续的科普文章生成任务提供高质量的训练和评估数据。

## 数据集结构

每个数据对包含以下信息：

```json
{
  "natgeo_article": {
    "title": "NatGeo Kids文章标题",
    "description": "NatGeo Kids文章描述",
    "content": "NatGeo Kids文章正文",
    "url": "文章链接",
    "category": "文章分类",
    "image_url": "配图链接"
  },
  "wikipedia_search_keyword": "用于搜索Wikipedia的关键词",
  "wikipedia_title": "Wikipedia页面标题",
  "wikipedia_content": "Wikipedia页面内容",
  "wikipedia_url": "Wikipedia页面链接"
}
```

## 项目文件

### 核心文件

1. **`build_wikipedia_natgeo_dataset.py`** - 完整的生产版本
   - 使用OpenAI GPT-3.5模型提取关键词
   - 调用Wikipedia API获取原文
   - 支持批量处理和错误处理
   - 需要设置OpenAI API密钥

2. **`demo_dataset_pipeline.py`** - 演示版本
   - 使用规则基础的关键词提取
   - 包含模拟的Wikipedia数据
   - 用于展示完整的工作流程
   - 不需要API密钥，可立即运行

3. **`test_dataset_pipeline.py`** - 测试版本
   - 使用简化的关键词提取规则
   - 调用真实的Wikipedia API
   - 用于测试API连接和网络环境

### 数据文件

- **`all_natgeo_kids_articles.json`** - 原始NatGeo Kids文章数据
- **`wikipedia_natgeo_pairs_demo.json`** - 演示版生成的数据集
- **`wikipedia_natgeo_pairs_test.json`** - 测试版生成的数据集

## 使用方法

### 1. 运行演示版本（推荐）

```bash
cd datasets/our_dataset/natgeo_kids
python demo_dataset_pipeline.py
```

这将使用模拟数据处理前5篇文章，展示完整的数据处理流程。

### 2. 运行完整生产版本

首先设置OpenAI API密钥：
```bash
export OPENAI_API_KEY="your-api-key-here"
```

然后运行：
```bash
python build_wikipedia_natgeo_dataset.py
```

### 3. 自定义配置

修改脚本中的配置参数：
```python
NATGEO_DATA_PATH = "path/to/your/natgeo/data.json"
OUTPUT_PATH = "path/to/output/dataset.json"
SAMPLE_SIZE = 10  # 处理的文章数量，None表示全部
```

## 关键技术实现

### 1. 关键词提取

**LLM方法（生产版本）**：
- 使用OpenAI GPT-3.5模型分析NatGeo Kids文章描述
- 提取最适合Wikipedia搜索的关键词
- 优先选择科学概念、动物名称等专业术语

**规则方法（演示版本）**：
- 预定义的关键词库（动物、科学概念、节日、法律等）
- 基于关键词匹配和优先级排序
- 提供简单但有效的关键词提取

### 2. Wikipedia API集成

**直接API调用**：
```python
# 搜索API
search_params = {
    "action": "query",
    "list": "search",
    "srsearch": keyword,
    "format": "json",
    "srlimit": 1
}

# 内容获取API
content_params = {
    "action": "query",
    "prop": "extracts",
    "explaintext": True,
    "titles": page_title,
    "format": "json"
}
```

**错误处理和重试机制**：
- 网络连接错误处理
- API限制和延迟机制
- 多种搜索策略回退

### 3. 数据质量控制

**输入验证**：
- 检查NatGeo文章是否有描述内容
- 验证数据格式和完整性

**搜索验证**：
- 验证Wikipedia搜索结果的有效性
- 检查页面内容是否为空
- 记录失败案例和错误信息

**输出标准化**：
- 统一的数据格式
- 内容长度限制（如需要）
- 编码和格式标准化

## 示例结果

演示生成的数据集包含以下示例对：

1. **节日主题**
   - NatGeo: "5 reasons why festivals are fantastic"
   - Wikipedia: "Festival"（关于节日的历史、文化意义等）

2. **海洋生物**
   - NatGeo: "Check out the issue!"（关于鲨鱼的文章）
   - Wikipedia: "Shark"（鲨鱼的生物学特征、分类等）

3. **美国历史**
   - NatGeo: "Independence Day"
   - Wikipedia: "Independence Day (United States)"（独立日的历史和庆祝方式）

4. **环境保护**
   - NatGeo: "Endangered Species Act"
   - Wikipedia: "Endangered Species Act of 1973"（法律的详细内容和影响）

## 数据集统计信息

演示数据集（4对）：
- 平均Wikipedia内容长度：约1,100字符
- 关键词提取成功率：80%（4/5）
- 搜索匹配成功率：100%

## 应用场景

1. **科普文章生成训练**：为LLM提供高质量的原文-科普文章对
2. **内容质量评估**：比较生成文章与专业科普文章的差异
3. **教育研究**：研究不同年龄段科普内容的特点
4. **跨语言研究**：为多语言科普内容生成提供参考

## 扩展功能

### 可能的改进方向：

1. **多关键词搜索**：提取多个关键词进行搜索，提高匹配率
2. **语义相似度评估**：计算NatGeo内容与Wikipedia内容的相似度
3. **多语言支持**：支持中文和其他语言的Wikipedia版本
4. **内容分级**：根据难度对Wikipedia内容进行分级处理
5. **批量处理优化**：支持大规模并行处理

### 集成建议：

1. **与现有pipeline集成**：可以集成到科普文章生成流程中
2. **自动更新机制**：定期更新NatGeo和Wikipedia数据
3. **质量监控**：建立数据质量评估和监控机制

## 技术依赖

- Python 3.8+
- requests: HTTP请求处理
- json: 数据序列化
- openai: GPT API调用（生产版本）
- wikipedia: Wikipedia API库（可选）

## 许可证

本项目遵循MIT许可证，可自由使用和修改。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue到项目仓库
- 发送邮件至项目维护者

---

**注意**：使用Wikipedia API时请遵守其使用条款和服务条款，合理控制请求频率，避免对服务器造成过大负担。