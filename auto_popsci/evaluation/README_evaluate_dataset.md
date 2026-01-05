# 通用数据集评测工具

这是一个通用的数据集评测工具，可以评测任何格式的科普文章生成结果，支持命令行参数配置。

## 功能特性

- ✅ 自动检测模型名称和字段路径
- ✅ 支持多种数据集格式（JSON、JSONL）
- ✅ 支持多种评估指标：
  - 连贯性（Coherence，使用PPL）
  - 简洁性（Simplicity，使用FKGL）
  - 生动性（Vividness）
    - 比喻性（Figurativeness）
    - 情感性（Emotionality）
    - 装饰性（Decorativeness）
  - 关键事实精确率和召回率（Keyfacts Precision/Recall）
- ✅ 支持自动生成keyfacts或使用已有的keyfacts文件
- ✅ 灵活的命令行参数配置

## 安装要求

确保已安装所有依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

### 方法1: 使用Shell脚本（推荐）

```bash
# 基本用法（自动检测所有字段）
./auto_popsci/evaluation/evaluate_dataset.sh \
    --input_file data.json \
    --output_file results.json

# 指定模型名称
./auto_popsci/evaluation/evaluate_dataset.sh \
    --input_file data.json \
    --output_file results.json \
    --model_name grok-4-1-fast-reasoning

# 指定字段路径
./auto_popsci/evaluation/evaluate_dataset.sh \
    --input_file data.json \
    --output_file results.json \
    --popsci_field "grok-4-1-fast-reasoning.content" \
    --original_field "original_data.wikipedia_article.content" \
    --reference_field "original_data.popsci_article.content"
```

### 方法2: 直接使用Python脚本

```bash
python auto_popsci/evaluation/evaluate_dataset.py \
    --input_file data.json \
    --output_file results.json
```

## 参数说明

### 必需参数

- `--input_file <路径>`: 输入数据文件路径（JSON格式）
- `--output_file <路径>`: 输出结果文件路径（JSON格式）

### 可选参数

- `--model_name <名称>`: 模型名称（如果不指定，将自动检测数据中的模型字段）
- `--popsci_field <路径>`: 生成的科普文章字段路径（如: `"model.content"`）
- `--original_field <路径>`: Wikipedia原文字段路径（如: `"original_data.wikipedia_article.content"`）
- `--reference_field <路径>`: 参考科普文章字段路径（可选，用于对比评估）
- `--skip_coherence`: 跳过连贯性评估（PPL）
- `--no_auto_generate_keyfacts`: 禁用自动生成keyfacts（默认启用）
- `--ground_truth_keyfacts_dir <路径>`: 参考keyfacts目录路径（如果提供，将使用文件中的keyfacts）
- `--generated_keyfacts_dir <路径>`: 生成的keyfacts目录路径（如果提供，将使用文件中的keyfacts）
- `--dataset_format <格式>`: 数据集格式（`json` 或 `jsonl`，默认: `json`）
- `--llm_type <类型>`: LLM类型（默认: `deepseek`）
- `--prompt_template <名称>`: Prompt模板名称（默认: `keyfact_alignment`）

## 数据格式要求

### 基本结构

输入数据应该是一个JSON数组，每个元素包含：

```json
{
  "model_name": {
    "content": "生成的科普文章内容...",
    "title": "文章标题"
  },
  "original_data": {
    "wikipedia_article": {
      "content": "Wikipedia原文内容...",
      "title": "Wikipedia标题"
    },
    "popsci_article": {
      "content": "参考科普文章内容...",
      "title": "参考文章标题"
    }
  }
}
```

### 字段路径说明

字段路径使用点号分隔，例如：
- `model_name.content` 表示 `data["model_name"]["content"]`
- `original_data.wikipedia_article.content` 表示 `data["original_data"]["wikipedia_article"]["content"]`

## 自动检测功能

脚本会自动检测以下内容：

1. **模型名称**: 从数据中排除标准字段（`original_data`, `source_wikipedia`, `analysis`等）后，自动识别模型字段
2. **字段路径**: 自动检测常见的字段路径模式：
   - `{model_name}.content` 或 `{model_name}.text` 作为生成的科普文章
   - `original_data.wikipedia_article.content` 作为Wikipedia原文
   - `original_data.popsci_article.content` 作为参考科普文章

如果自动检测失败，请使用命令行参数手动指定。

## 输出格式

评测结果会保存为JSON文件，包含：

```json
{
  "total_documents": 100,
  "evaluated_documents": 100,
  "statistics": {
    "coherence": {
      "mean": 15.23,
      "min": 10.5,
      "max": 25.6
    },
    "simplicity": {
      "mean": 8.5,
      "min": 5.2,
      "max": 12.3
    },
    "vividness": {
      "mean": 0.65,
      "min": 0.3,
      "max": 0.9
    },
    "keyfacts_precision": {
      "mean": 0.85,
      "count": 100
    },
    "keyfacts_recall": {
      "mean": 0.78,
      "count": 100
    }
  },
  "results": [
    {
      "document_id": 0,
      "coherence": 15.2,
      "simplicity": 8.5,
      "vividness": 0.65,
      "keyfacts_precision": 0.85,
      "keyfacts_recall": 0.78
    }
  ]
}
```

## 示例

### 示例1: 评测grok模型生成的文章

```bash
./auto_popsci/evaluation/evaluate_dataset.sh \
    --input_file baselines/grok-4-1-fast-reasoning/output/generated_popsci_articles.json \
    --output_file baselines/grok-4-1-fast-reasoning/output/evaluation_results.json \
    --model_name grok-4-1-fast-reasoning
```

### 示例2: 跳过连贯性评估

```bash
./auto_popsci/evaluation/evaluate_dataset.sh \
    --input_file data.json \
    --output_file results.json \
    --skip_coherence
```

### 示例3: 使用已有的keyfacts文件

```bash
./auto_popsci/evaluation/evaluate_dataset.sh \
    --input_file data.json \
    --output_file results.json \
    --ground_truth_keyfacts_dir "path/to/ground_truth_keyfacts" \
    --generated_keyfacts_dir "path/to/generated_keyfacts" \
    --no_auto_generate_keyfacts
```

## 常见问题

### Q: 如何知道数据中的字段路径？

A: 运行脚本时，如果自动检测失败，脚本会打印出数据中的所有字段名称，你可以根据这些信息手动指定字段路径。

### Q: 评测需要多长时间？

A: 评测时间取决于：
- 数据量大小
- 是否启用keyfacts自动生成（会增加时间）
- 是否启用连贯性评估（会增加时间）

对于100条数据，通常需要10-30分钟。

### Q: 如何只评测特定指标？

A: 目前不支持单独选择指标，但可以：
- 使用 `--skip_coherence` 跳过连贯性评估
- 使用 `--no_auto_generate_keyfacts` 跳过keyfacts评估

### Q: 支持哪些LLM类型？

A: 支持的LLM类型取决于 `auth.yaml` 中的配置。默认支持 `deepseek` 和 `grok`。

## 注意事项

1. 确保 `auth.yaml` 文件配置正确，包含所需的API密钥
2. 确保有足够的磁盘空间保存评测结果
3. 如果数据量很大，建议分批评测
4. 自动生成keyfacts会调用LLM API，请注意API使用限制和费用

## 更新日志

- v1.0.0: 初始版本，支持基本的评测功能

