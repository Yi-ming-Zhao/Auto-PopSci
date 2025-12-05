# Vividness Evaluation Module

这是一个用于评估文本生动性的综合模块，包含三个子评估器：

- **Figurativeness** (比喻丰富度): 使用MelBERT模型评估文本中的比喻性表达
- **Emotionality** (情感丰富度): 使用VADER Sentiment评估文本的情感表达
- **Decorativeness** (修饰性丰富度): 评估文本中形容词和副词等修饰性词汇的丰富度

## 文件结构

```
vividness/
├── __init__.py              # 主要的VividnessEvaluator类
├── example_usage.py         # 使用示例
├── README.md               # 本文件
├── figurativeness/          # 比喻丰富度评估模块
│   ├── __init__.py
│   ├── figurativeness.py    # FigurativenessEvaluator类
│   └── MelBERT/            # MelBERT模型文件
│       ├── melbert_ckpt/   # 预训练模型
│       ├── main.py
│       ├── modeling.py
│       └── ...
├── emotionality/            # 情感丰富度评估模块
│   ├── __init__.py
│   └── emotionality.py      # EmotionalityEvaluator类
└── decorativeness/          # 修饰性丰富度评估模块
    ├── __init__.py
    └── decorativeness.py    # DecorativenessEvaluator类
```

## 安装依赖

```bash
# VADER Sentiment
pip install vaderSentiment

# NLTK (用于修饰性评估)
pip install nltk

# PyTorch (用于MelBERT)
pip install torch transformers

# 如果遇到问题，也可以尝试：
pip install -r requirements.txt
```

## 快速开始

### 1. 综合评估

```python
from vividness import VividnessEvaluator

# 创建评估器
evaluator = VividnessEvaluator()

# 评估单个文本
text = "The beautiful sunset painted the sky with golden colors like a masterpiece."
score = evaluator.evaluate_text(text)
print(f"Vividness Score: {score:.3f}")

# 获取详细分析
analysis = evaluator.get_detailed_analysis(text)
print(f"Overall Score: {analysis['vividness_score']:.3f}")
print(f"Interpretation: {analysis['interpretation']}")

# 批量评估
texts = ["text1", "text2", "text3"]
scores = evaluator.evaluate_texts(texts)
```

### 2. 单独使用各评估器

```python
from vividness.figurativeness.figurativeness import FigurativenessEvaluator
from vividness.emotionality.emotionality import EmotionalityEvaluator
from vividness.decorativeness.decorativeness import DecorativenessEvaluator

# 比喻丰富度评估
fig_eval = FigurativenessEvaluator()
fig_score = fig_eval.evaluate_text(text)

# 情感丰富度评估
emo_eval = EmotionalityEvaluator()
emo_score = emo_eval.evaluate_text(text)

# 修饰性丰富度评估
dec_eval = DecorativenessEvaluator()
dec_score = dec_eval.evaluate_text(text)
```

### 3. 自定义权重

```python
# 自定义各子模块的权重
custom_weights = {
    'figurativeness': 0.5,   # 比喻权重
    'emotionality': 0.3,     # 情感权重
    'decorativeness': 0.2    # 修饰权重
}

evaluator = VividnessEvaluator(weights=custom_weights)
```

## 评估器详细说明

### Figurativeness (比喻丰富度)

使用预训练的MelBERT模型来检测文本中的比喻性表达。

**特点:**
- 基于VUA数据集训练
- 支持词级比喻检测
- 返回0-1的比喻性分数

**使用方法:**
```python
from vividness.figurativeness.figurativeness import FigurativenessEvaluator

evaluator = FigurativenessEvaluator()
score = evaluator.evaluate_text("The sun is a golden coin in the sky.")
# score: 比喻性分数 (0-1)
```

### Emotionality (情感丰富度)

使用VADER情感分析结合情感词汇密度来评估文本的情感丰富度。

**特点:**
- 基于VADER情感分析
- 考虑情感词汇密度和多样性
- 综合情感强度和分布

**使用方法:**
```python
from vividness.emotionality.emotionality import EmotionalityEvaluator

evaluator = EmotionalityEvaluator()
score = evaluator.evaluate_text("I'm so excited and happy about this wonderful news!")
# score: 情感丰富度分数 (0-1)

# 获取详细分析
details = evaluator.get_detailed_scores(text)
print(f"VADER Compound: {details['vader_scores']['compound']}")
print(f"Emotional Density: {sum(details['emotion_density'].values())}")
```

### Decorativeness (修饰性丰富度)

评估文本中形容词、副词等修饰性词汇的丰富度。

**特点:**
- 基于词性标注和词汇列表
- 考虑修饰词汇密度和多样性
- 支持NLTK和fallback分词

**使用方法:**
```python
from vividness.decorativeness.decorativeness import DecorativenessEvaluator

evaluator = DecorativenessEvaluator()
score = evaluator.evaluate_text("A beautifully designed, incredibly efficient system.")
# score: 修饰性丰富度分数 (0-1)

# 获取详细分析
details = evaluator.get_detailed_scores(text)
print(f"Decorative Word Ratio: {details['stats']['total_decorative_ratio']}")
print(f"Adjective Ratio: {details['stats']['adjective_ratio']}")
print(f"Adverb Ratio: {details['stats']['adverb_ratio']}")
```

## 分数解释

所有评估器都返回0-1的分数，解释如下：

| 分数范围 | 解释 |
|---------|------|
| 0.8-1.0 | 极高丰富度 |
| 0.6-0.8 | 高丰富度 |
| 0.4-0.6 | 中等丰富度 |
| 0.2-0.4 | 低丰富度 |
| 0.0-0.2 | 极少丰富度 |

## 高级功能

### 文本比较

```python
evaluator = VividnessEvaluator()
comparison = evaluator.compare_texts(text1, text2)
print(comparison['comparison'])
print(f"Winner: {comparison['winner']}")
```

### 批量处理

```python
texts = ["text1", "text2", "text3", "text4"]
results = evaluator.evaluate_texts(texts, return_components=True)

# 找出最生动的文本
best_idx = max(range(len(results)), key=lambda i: results[i]['vividness_score'])
print(f"Most vivid text: {texts[best_idx]}")
```

## 运行示例

```bash
cd auto_popsci/evaluation/vividness
python example_usage.py
```

这将运行多个示例，展示各种使用方式。

## 注意事项

1. **MelBERT模型**: figurativeness评估器需要预训练的MelBERT模型，确保模型文件位于正确路径
2. **NLTK数据**: 首次使用时会自动下载NLTK所需数据
3. **GPU支持**: 如果有GPU，MelBERT会自动使用GPU加速
4. **内存使用**: MelBERT模型较大，建议至少有4GB可用内存

## 故障排除

### 常见问题

1. **MelBERT导入错误**:
   ```
   确保auto_popsci/evaluation/figurativeness/MelBERT目录存在
   检查melbert_ckpt文件夹是否包含模型文件
   ```

2. **VADER安装问题**:
   ```bash
   pip install vaderSentiment
   ```

3. **NLTK数据下载问题**:
   ```python
   import nltk
   nltk.download('punkt')
   nltk.download('averaged_perceptron_tagger')
   nltk.download('wordnet')
   ```

### 性能优化

1. **批量评估**: 使用`evaluate_texts()`而不是循环调用`evaluate_text()`
2. **缓存结果**: 对于重复文本，考虑缓存评估结果
3. **GPU加速**: 如果有GPU，确保PyTorch支持CUDA

## 扩展

如需扩展此模块，可以考虑：

1. **添加新的评估维度**: 如意象性、节奏感等
2. **支持其他语言**: 添加多语言支持
3. **自定义词汇**: 允许用户自定义情感词或修饰词列表
4. **模型更新**: 使用更新的比喻检测模型

## 引用

如果使用此模块，请引用相关的原始论文：

- MelBERT: [MelBERT: Metaphor Detection via Contextualized Late Interaction using Metaphorical Identification Theories](https://www.aclweb.org/anthology/2021.naacl-main.141/)
- VADER: [VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text](https://www.aaai.org/ocs/index.php/ICWSM/ICWSM11/paper/view/2857/3259)