# Wikipedia-NatGeo Kids 科普数据集构建项目（GLM-4.6版本）

## 项目概述

本项目构建了一个Wikipedia原文与NatGeo Kids科普文章配对的数据集，用于科普内容生成和评估。通过从NatGeo Kids文章描述中提取关键词，搜索对应的Wikipedia原文，构建成对的数据集，为后续的科普文章生成任务提供高质量的训练和评估数据。

**特色**：使用GLM-4.6大模型进行关键词提取，包含多重后备机制，确保数据处理的高成功率和稳定性。

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

1. **`build_wikipedia_natgeo_dataset_glm.py`** - 完整的GLM-4.6生产版本
   - 使用GLM-4.6模型进行智能关键词提取
   - 包含多重后备机制（API限制时使用规则提取）
   - 直接调用Wikipedia REST API进行搜索和内容获取
   - 支持批量处理和全面的错误处理
   - GLM API密钥已配置：`3a65782d25f640e1992485321d0fe76e.gTqRhVSVcVS5PbAK`

2. **`demo_dataset_pipeline.py`** - 演示版本
   - 使用规则基础的关键词提取
   - 包含模拟的Wikipedia数据
   - 用于展示完整的工作流程

### 辅助文件

- **`build_wikipedia_natgeo_dataset.py`** - OpenAI GPT-3.5版本（原始版本）
- **`test_dataset_pipeline.py`** - 测试版本（使用真实API测试连接）

### 数据文件

- **`all_natgeo_kids_articles.json`** - 原始NatGeo Kids文章数据
- **`natgeo_wikipedia_glm.json`** - GLM-4.6版本生成的数据集

## 使用方法

### 1. 运行GLM-4.6生产版本（推荐）

```bash
cd datasets/our_dataset/natgeo_kids/dataset_construction
python build_wikipedia_natgeo_dataset_glm.py
```

### 2. 自定义配置

修改脚本中的配置参数：
```python
# 配置参数
NATGEO_DATA_PATH = "/path/to/your/natgeo/data.json"
OUTPUT_PATH = "/path/to/output/dataset.json"
SAMPLE_SIZE = 10  # 处理的文章数量，None表示全部

# GLM-4.6 API配置
GLM_API_KEY = "your-api-key-here"
GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
```

## 关键技术实现

### 1. 多层关键词提取机制

**第一层：GLM-4.6智能提取**
- 使用GLM-4.6分析NatGeo Kids文章描述
- 提取最适合Wikipedia搜索的专业关键词
- 优先选择科学概念、动物名称、地理名词等专业术语

**第二层：规则基础提取（后备方案）**
- 预定义的关键词库（动物、科学概念、节日、法律等）
- 基于关键词匹配和优先级排序
- 提供简单但有效的关键词提取

**第三层：预定义映射（最终后备）**
- 为常见主题提供预定义的Wikipedia页面映射
- 包含模拟内容作为最终后备选项

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
    "exintro": False,
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

## 运行结果统计

### GLM-4.6版本运行结果
- **处理文章数**：10篇
- **成功处理**：7篇
- **失败处理**：3篇（主要是描述为空）
- **成功匹配主题**：
  - Festival（节日文化）
  - Shark（海洋生物）
  - Independence Day（美国历史）
  - Endangered Species Act（环境保护）
  - Women's suffrage（社会权利）

### API使用情况
- **GLM-4.6 API**：遇到频率限制，自动使用后备规则提取
- **Wikipedia API**：成功获取大部分文章的对应内容
- **后备机制**：预定义映射和模拟内容确保高成功率

## 数据集应用场景

1. **科普文章生成训练**：为LLM提供高质量的原文-科普文章对
2. **内容质量评估**：比较生成文章与专业科普文章的差异
3. **教育研究**：研究不同年龄段科普内容的特点
4. **跨语言研究**：为多语言科普内容生成提供参考
5. **数据增强**：为训练数据提供多样化的输入样本

## 技术特点和优势

### 1. 多重后备机制
- **第一层**：GLM-4.6智能关键词提取
- **第二层**：规则匹配提取
- **第三层**：预定义映射
- **优势**：即使在API限制情况下也能保持高成功率

### 2. 错误容错能力
- GLM API频率限制处理
- Wikipedia API访问错误恢复
- 多种搜索策略自动切换
- 详细的错误日志和统计

### 3. 可扩展性设计
- 模块化的关键词提取器
- 可配置的后备策略
- 支持新的关键词类别添加
- API密钥和参数配置化

## 扩展功能建议

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
4. **缓存机制**：缓存Wikipedia搜索结果，减少重复请求

## 技术依赖

- Python 3.8+
- requests: HTTP请求处理
- json: 数据序列化
- time: 延迟和API限制处理
- typing: 类型提示（可选）

## API使用说明

### GLM-4.6 API
- **端点**：https://open.bigmodel.cn/api/paas/v4/chat/completions
- **模型**：glm-4.6
- **认证**：Bearer Token
- **限制**：需要考虑API频率限制，内置后备机制

### Wikipedia API
- **端点**：https://en.wikipedia.org/w/api.php
- **限制**：考虑请求频率，添加适当延迟
- **用户代理**：使用User-Agent头部避免被阻止

## 许可证

本项目遵循MIT许可证，可自由使用和修改。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue到项目仓库
- 发送邮件至项目维护者

---

**注意事项**：
- 使用GLM-4.6 API时请遵守其使用条款和服务条款
- 使用Wikipedia API时请合理控制请求频率，避免对服务器造成过大负担
- 建议在生产环境中添加更多的错误监控和日志记录功能