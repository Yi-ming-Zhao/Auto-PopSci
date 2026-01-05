# 评测脚本使用示例

## 基本用法

### 示例1: 评测grok模型生成的文章（自动检测）

```bash
# 使用Shell脚本
./auto_popsci/evaluation/evaluate_dataset.sh \
    --input_file baselines/grok-4-1-fast-reasoning/output/generated_popsci_articles.json \
    --output_file baselines/grok-4-1-fast-reasoning/output/evaluation_results.json

# 或使用Python脚本
python auto_popsci/evaluation/evaluate_dataset.py \
    --input_file baselines/grok-4-1-fast-reasoning/output/generated_popsci_articles.json \
    --output_file baselines/grok-4-1-fast-reasoning/output/evaluation_results.json
```

### 示例2: 指定模型名称

```bash
./auto_popsci/evaluation/evaluate_dataset.sh \
    --input_file data.json \
    --output_file results.json \
    --model_name grok-4-1-fast-reasoning
```

### 示例3: 手动指定字段路径

```bash
./auto_popsci/evaluation/evaluate_dataset.sh \
    --input_file data.json \
    --output_file results.json \
    --model_name grok-4-1-fast-reasoning \
    --popsci_field "grok-4-1-fast-reasoning.content" \
    --original_field "original_data.original_data.wikipedia_article.content" \
    --reference_field "original_data.original_data.popsci_article.content"
```

### 示例4: 跳过连贯性评估（加快速度）

```bash
./auto_popsci/evaluation/evaluate_dataset.sh \
    --input_file data.json \
    --output_file results.json \
    --skip_coherence
```

### 示例5: 使用已有的keyfacts文件

```bash
./auto_popsci/evaluation/evaluate_dataset.sh \
    --input_file data.json \
    --output_file results.json \
    --ground_truth_keyfacts_dir "auto_popsci/evaluation/output/dev_5/R1_ground_truth/with_priority/reference_keyfacts/" \
    --generated_keyfacts_dir "auto_popsci/evaluation/output/dev_5/scinews_keyfacts/with_priority/reference_keyfacts/" \
    --no_auto_generate_keyfacts
```

### 示例6: 评测JSONL格式的数据

```bash
./auto_popsci/evaluation/evaluate_dataset.sh \
    --input_file data.jsonl \
    --output_file results.json \
    --dataset_format jsonl
```

## 数据格式示例

### 格式1: 标准格式（推荐）

```json
[
  {
    "grok-4-1-fast-reasoning": {
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
]
```

### 格式2: 嵌套格式

```json
[
  {
    "grok-4-1-fast-reasoning": {
      "content": "生成的科普文章内容..."
    },
    "original_data": {
      "original_data": {
        "wikipedia_article": {
          "content": "Wikipedia原文内容..."
        },
        "popsci_article": {
          "content": "参考科普文章内容..."
        }
      }
    }
  }
]
```

## 输出结果示例

```json
{
  "total_documents": 100,
  "evaluated_documents": 100,
  "statistics": {
    "coherence": {
      "mean": 15.23,
      "min": 10.5,
      "max": 25.6,
      "stdev": 3.2
    },
    "simplicity": {
      "mean": 8.5,
      "min": 5.2,
      "max": 12.3,
      "stdev": 1.5
    },
    "vividness": {
      "mean": 0.65,
      "min": 0.3,
      "max": 0.9,
      "stdev": 0.15
    },
    "figurativeness": {
      "mean": 0.45,
      "min": 0.1,
      "max": 0.8
    },
    "emotionality": {
      "mean": 0.52,
      "min": 0.2,
      "max": 0.9
    },
    "decorativeness": {
      "mean": 0.38,
      "min": 0.1,
      "max": 0.7
    },
    "keyfacts_precision": {
      "mean": 0.85,
      "min": 0.6,
      "max": 1.0,
      "count": 100
    },
    "keyfacts_recall": {
      "mean": 0.78,
      "min": 0.5,
      "max": 1.0,
      "count": 100
    }
  },
  "results": [
    {
      "document_id": 0,
      "coherence": 15.2,
      "simplicity": 8.5,
      "vividness": 0.65,
      "figurativeness": 0.45,
      "emotionality": 0.52,
      "decorativeness": 0.38,
      "keyfacts_precision": 0.85,
      "keyfacts_recall": 0.78
    }
  ]
}
```

## 常见问题排查

### 问题1: 无法自动检测模型名称

**症状**: 脚本提示"无法自动检测模型名称"

**解决方案**: 
1. 检查数据格式是否正确
2. 使用 `--model_name` 参数手动指定模型名称

### 问题2: 字段路径错误

**症状**: 提示"无法确定popsci_field"或"无法确定original_field"

**解决方案**:
1. 检查数据结构
2. 使用 `--popsci_field` 和 `--original_field` 参数手动指定字段路径
3. 字段路径使用点号分隔，例如: `"model.content"`

### 问题3: Keyfacts生成失败

**症状**: 提示"生成keyfacts失败"

**解决方案**:
1. 检查 `auth.yaml` 文件中的API配置是否正确
2. 检查网络连接
3. 如果不需要keyfacts评估，使用 `--no_auto_generate_keyfacts` 跳过

### 问题4: 评测速度慢

**解决方案**:
1. 使用 `--skip_coherence` 跳过连贯性评估
2. 使用 `--no_auto_generate_keyfacts` 跳过keyfacts评估
3. 如果已有keyfacts文件，使用文件而不是自动生成

## 性能优化建议

1. **大批量数据**: 建议分批评测，每批100-500条
2. **快速预览**: 先评测少量数据（如10条）验证配置正确
3. **并行处理**: keyfacts生成使用并发处理（默认500并发）
4. **缓存结果**: 如果重复评测，考虑保存中间结果

## 注意事项

1. 确保 `auth.yaml` 文件配置正确
2. 确保有足够的磁盘空间
3. 注意API使用限制和费用
4. 评测时间取决于数据量和启用的评估指标

