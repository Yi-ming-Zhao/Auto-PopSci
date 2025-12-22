# 综合评估接口使用说明

## 概述

`comprehensive_evaluation.py` 提供了综合评估科普文章的接口，包括以下评估指标：

- **coherence（连贯性）**: 使用困惑度（PPL）评估，值越低越好
- **simplicity（简洁性）**: 使用 SARI 分数评估
- **vividness（生动性）**: 使用 VividnessEvaluator 评估（包括比喻性、情感性、装饰性）
- **keyfacts precision（关键事实精确率）**: 评估生成的关键事实的精确率
- **keyfacts recall（关键事实召回率）**: 评估生成的关键事实的召回率

## 接口类型

### 1. 单个文档评估接口

评估单个科普文章文档。

```python
from auto_popsci.evaluation.comprehensive_evaluation import ComprehensiveEvaluator
from auto_popsci.args import parse_args
import asyncio

async def evaluate_single():
    args = parse_args()
    evaluator = ComprehensiveEvaluator(args=args)
    
    result = await evaluator.evaluate_single_document(
        popsci_text="科普文章文本",
        original_text="原始复杂文本（可选）",
        reference_text="参考文本（可选）",
        ground_truth_keyfacts="真实关键事实（可选）",
        generated_keyfacts="生成的关键事实（可选）",
        include_keyfacts=True  # 是否包含关键事实评估
    )
    
    return result

asyncio.run(evaluate_single())
```

### 2. 文档对评估接口

比较两个科普文章文档。

```python
async def evaluate_pair():
    args = parse_args()
    evaluator = ComprehensiveEvaluator(args=args)
    
    result = await evaluator.evaluate_document_pair(
        popsci_text_1="第一个科普文章",
        popsci_text_2="第二个科普文章",
        original_text="原始复杂文本（可选）",
        reference_text="参考文本（可选）"
    )
    
    return result
```

### 3. 数据集格式评估接口

批量评估数据集中的多个文档，结果会自动保存到 `output` 文件夹。

```python
async def evaluate_dataset_example():
    args = parse_args()
    evaluator = ComprehensiveEvaluator(args=args)
    
    result = await evaluator.evaluate_dataset(
        dataset_path="datasets/example.json",
        output_path="output/evaluation_results.json",  # 可选，默认保存到 output 文件夹
        dataset_format='json',
        popsci_field='popsci_text',  # 科普文章文本字段名
        original_field='original_text',  # 原始文本字段名
        reference_field='reference_text',  # 参考文本字段名（可选）
        include_keyfacts=True
    )
    
    return result
```

## 数据集格式

数据集应为 JSON 格式，包含文档列表。每个文档应包含以下字段：

```json
[
    {
        "id": "doc_1",
        "title": "文档标题",
        "popsci_text": "科普文章文本",
        "original_text": "原始复杂文本",
        "reference_text": "参考文本（可选）",
        "ground_truth_keyfacts": [...],  // 真实关键事实（可选）
        "generated_keyfacts": [...]      // 生成的关键事实（可选）
    },
    ...
]
```

## 输出格式

### 单个文档评估结果

```json
{
    "popsci_text": "科普文章文本（截断）",
    "coherence": {
        "ppl_score": 85.5,
        "interpretation": "相对流畅"
    },
    "simplicity": {
        "sari_score": 0.65,
        "interpretation": "相对简洁"
    },
    "vividness": {
        "vividness_score": 0.72,
        "figurativeness": 0.8,
        "emotionality": 0.7,
        "decorativeness": 0.65
    },
    "keyfacts": {
        "precision": 0.85,
        "recall": 0.78,
        "precision_by_priority": {
            "priority_1": 0.9,
            "priority_2": 0.8,
            "priority_3": 0.75
        },
        "recall_by_priority": {
            "priority_1": 0.85,
            "priority_2": 0.75,
            "priority_3": 0.7
        }
    }
}
```

### 数据集评估结果

```json
{
    "dataset_path": "datasets/example.json",
    "total_documents": 10,
    "evaluated_documents": 10,
    "results": [
        // 每个文档的评估结果
    ],
    "statistics": {
        "coherence": {
            "mean": 95.2,
            "min": 45.3,
            "max": 150.8,
            "count": 10
        },
        "simplicity": {
            "mean": 0.68,
            "min": 0.45,
            "max": 0.85,
            "count": 10
        },
        "vividness": {
            "mean": 0.71,
            "min": 0.52,
            "max": 0.89,
            "count": 10
        },
        "keyfacts_precision": {
            "mean": 0.82,
            "min": 0.65,
            "max": 0.95,
            "count": 10
        },
        "keyfacts_recall": {
            "mean": 0.75,
            "min": 0.58,
            "max": 0.88,
            "count": 10
        }
    }
}
```

## 便捷函数

还提供了便捷函数，可以直接使用：

```python
from auto_popsci.evaluation.comprehensive_evaluation import (
    evaluate_single_document_async,
    evaluate_document_pair_async,
    evaluate_dataset_async
)

# 评估单个文档
result = await evaluate_single_document_async(
    popsci_text="科普文章文本",
    original_text="原始文本",
    args=args
)

# 评估文档对
result = await evaluate_document_pair_async(
    popsci_text_1="第一个文本",
    popsci_text_2="第二个文本",
    original_text="原始文本",
    args=args
)

# 评估数据集
result = await evaluate_dataset_async(
    dataset_path="datasets/example.json",
    output_path="output/results.json",
    args=args
)
```

## 注意事项

1. **关键事实评估**: 需要提供 `args` 参数（包含 LLM 配置）才能进行关键事实评估
2. **生动性评估**: 需要正确配置 MelBERT 模型路径（如果使用）
3. **输出路径**: 数据集评估结果默认保存到 `output` 文件夹
4. **异步函数**: 所有评估函数都是异步的，需要使用 `asyncio.run()` 或 `await` 调用

## 示例

完整示例请参考 `example_usage.py` 文件。
