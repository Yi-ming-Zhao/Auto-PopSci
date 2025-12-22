"""
Decorativeness Evaluator
用于评估文本修饰性词汇丰富度的模块

本模块仅使用NLTK词性标注（POS tagging）来识别修饰性词汇（形容词和副词），
不使用预定义词表，确保评估结果更加客观和通用。

Usage:
    evaluator = DecorativenessEvaluator()
    score = evaluator.evaluate_text("Your text here")
    scores = evaluator.evaluate_texts(["text1", "text2", ...])
"""

import os
import re
import string
from tkinter import FALSE
import numpy as np
from collections import defaultdict
from tqdm import tqdm

def _check_nltk_data(nltk_module, data_name):
    """检查NLTK数据是否已下载"""
    try:
        nltk_module.data.find(data_name)
        return True
    except LookupError:
        return False

try:
    import nltk
    from nltk import pos_tag, word_tokenize
    from nltk.corpus import wordnet
    
    # 检查并下载punkt（分词器）
    if not _check_nltk_data(nltk, 'tokenizers/punkt'):
        nltk.download('punkt', quiet=False)
    
    # 检查并下载词性标注器
    if not _check_nltk_data(nltk, 'taggers/averaged_perceptron_tagger'):
        nltk.download('averaged_perceptron_tagger', quiet=False)
        nltk.download('averaged_perceptron_tagger_eng', quiet=False)
    
    # 检查并下载WordNet（虽然当前未使用，但保留以备将来使用）
    if not _check_nltk_data(nltk, 'corpora/wordnet'):
        nltk.download('wordnet', quiet=False)
    
    NLTK_AVAILABLE = True
except ImportError:
    print("Installing NLTK...")
    import subprocess
    subprocess.check_call(["pip", "install", "nltk"])
    try:
        import nltk
        from nltk import pos_tag, word_tokenize
        from nltk.corpus import wordnet
        
        # 检查并下载punkt（分词器）
        if not _check_nltk_data(nltk, 'tokenizers/punkt'):
            nltk.download('punkt', quiet=False)
        
        # 检查并下载词性标注器
        if not _check_nltk_data(nltk, 'taggers/averaged_perceptron_tagger'):
            nltk.download('averaged_perceptron_tagger', quiet=False)
            nltk.download('averaged_perceptron_tagger_eng', quiet=False)
        
        # 检查并下载WordNet
        if not _check_nltk_data(nltk, 'corpora/wordnet'):
            nltk.download('wordnet', quiet=False)
        
        NLTK_AVAILABLE = True
    except Exception as e:
        print(f"Warning: NLTK not available, using fallback methods: {e}")
        NLTK_AVAILABLE = False


class DecorativenessEvaluator:
    """
    评估文本修饰性词汇丰富度的类
    
    仅基于NLTK词性标注识别修饰性词汇：
    - 形容词：JJ（原级）、JJR（比较级）、JJS（最高级）
    - 副词：RB（原级）、RBR（比较级）、RBS（最高级）
    """

    def __init__(self):
        """初始化修饰性评估器（仅使用NLTK词性标注，不使用预定义词表）"""
        # 修饰性词性标签（Penn Treebank POS tags）
        self.decorative_pos_tags = {
            'adjectives': {'JJ', 'JJR', 'JJS'},  # 形容词：原级、比较级、最高级
            'adverbs': {'RB', 'RBR', 'RBS'},    # 副词：原级、比较级、最高级
        }

    def _tokenize_text(self, text):
        """
        分词

        Args:
            text (str): 输入文本

        Returns:
            list: 词汇列表
        """
        if NLTK_AVAILABLE:
            return word_tokenize(text.lower())
        else:
            # 简单分词作为fallback
            return re.findall(r'\b\w+\b', text.lower())

    def _pos_tag_words(self, words):
        """
        词性标注

        Args:
            words (list): 词汇列表

        Returns:
            list: (词, 词性标签) 元组列表
        """
        if NLTK_AVAILABLE:
            return pos_tag(words)
        else:
            # 简单的词性标注作为fallback
            tagged = []
            for word in words:
                # 常见的形容词后缀
                if word.endswith(('ful', 'less', 'ous', 'ive', 'able', 'ible', 'al', 'ary', 'ed', 'ing')):
                    tagged.append((word, 'JJ'))
                # 常见的副词后缀
                elif word.endswith(('ly', 'wise', 'wards')):
                    tagged.append((word, 'RB'))
                else:
                    tagged.append((word, 'NN'))  # 默认为名词
            return tagged

    def _count_decorative_words(self, text):
        """
        统计修饰性词汇数量（仅基于NLTK词性标注）

        Args:
            text (str): 输入文本

        Returns:
            dict: 修饰性词汇统计
        """
        words = self._tokenize_text(text)
        if not words:
            return {
                'total_words': 0,
                'decorative_words': 0,
                'adjectives': 0,
                'adverbs': 0,
                'adjective_ratio': 0.0,
                'adverb_ratio': 0.0,
                'total_decorative_ratio': 0.0
            }

        tagged_words = self._pos_tag_words(words)
        total_words = len(words)

        # 统计词性（仅基于POS标签）
        pos_counts = defaultdict(int)

        for word, pos_tag in tagged_words:
            # 统计形容词
            if pos_tag in self.decorative_pos_tags['adjectives']:
                pos_counts['adjectives'] += 1
            # 统计副词
            elif pos_tag in self.decorative_pos_tags['adverbs']:
                pos_counts['adverbs'] += 1

        total_adjectives = pos_counts['adjectives']
        total_adverbs = pos_counts['adverbs']
        total_decorative = total_adjectives + total_adverbs

        # 计算比率
        ratios = {
            'adjective_ratio': total_adjectives / total_words if total_words > 0 else 0,
            'adverb_ratio': total_adverbs / total_words if total_words > 0 else 0,
            'total_decorative_ratio': total_decorative / total_words if total_words > 0 else 0
        }

        return {
            'total_words': total_words,
            'decorative_words': total_decorative,
            'adjectives': total_adjectives,
            'adverbs': total_adverbs,
            **ratios
        }

    def _calculate_decorative_diversity(self, text):
        """
        计算修饰性词汇多样性（仅基于NLTK词性标注）

        Args:
            text (str): 输入文本

        Returns:
            float: 多样性分数 (0-1)
        """
        words = self._tokenize_text(text)
        tagged_words = self._pos_tag_words(words)

        # 提取修饰性词汇（仅基于POS标签）
        decorative_words = []
        for word, pos_tag in tagged_words:
            if (pos_tag in self.decorative_pos_tags['adjectives'] or
                pos_tag in self.decorative_pos_tags['adverbs']):
                decorative_words.append(word)

        if len(decorative_words) == 0:
            return 0.0

        # 计算词汇多样性（不同词汇占总修饰词汇的比例）
        unique_decorative = len(set(decorative_words))
        diversity = unique_decorative / len(decorative_words)

        return diversity

    def _calculate_decorative_intensity(self, stats):
        """
        计算修饰性强度

        Args:
            stats (dict): 修饰性词汇统计

        Returns:
            float: 强度分数 (0-1)
        """
        total_ratio = stats['total_decorative_ratio']

        # 修饰性强度基于密度和分布
        if total_ratio <= 0.05:  # 5%以下为低强度
            intensity = total_ratio * 4  # 线性放大
        elif total_ratio <= 0.15:  # 5-15%为中等强度
            intensity = 0.2 + (total_ratio - 0.05) * 3
        elif total_ratio <= 0.30:  # 15-30%为高强度
            intensity = 0.5 + (total_ratio - 0.15) * 2
        else:  # 30%以上为极高强度
            intensity = min(0.8 + (total_ratio - 0.30), 1.0)

        return min(intensity, 1.0)

    def evaluate_text(self, text):
        """
        评估单个文本的修饰性词汇丰富度（仅基于NLTK词性标注）

        Args:
            text (str): 输入文本

        Returns:
            float: 修饰性丰富度分数 (0-1)，越高表示修饰越丰富
                   分数由强度（60%）和多样性（40%）加权计算
        """
        if not isinstance(text, str) or len(text.strip()) == 0:
            return 0.0

        # 统计修饰性词汇
        stats = self._count_decorative_words(text)

        # 计算多样性
        diversity = self._calculate_decorative_diversity(text)

        # 计算强度
        intensity = self._calculate_decorative_intensity(stats)

        # 综合修饰性丰富度分数
        decorativeness_score = 0.6 * intensity + 0.4 * diversity

        return min(decorativeness_score, 1.0)

    def evaluate_texts(self, texts):
        """
        批量评估文本的修饰性词汇丰富度

        Args:
            texts (list): 文本列表

        Returns:
            list: 修饰性丰富度分数列表
        """
        if not isinstance(texts, list):
            texts = [texts]

        scores = []
        for text in tqdm(texts, desc="Evaluating decorativeness"):
            score = self.evaluate_text(text)
            scores.append(score)

        return scores

    def get_detailed_scores(self, text):
        """
        获取详细的修饰性分析分数

        Args:
            text (str): 输入文本

        Returns:
            dict: 详细分数
        """
        if not isinstance(text, str) or len(text.strip()) == 0:
            return {
                'decorativeness_score': 0.0,
                'stats': {
                    'total_words': 0,
                    'decorative_words': 0,
                    'adjectives': 0,
                    'adverbs': 0,
                    'adjective_ratio': 0.0,
                    'adverb_ratio': 0.0,
                    'total_decorative_ratio': 0.0
                },
                'diversity': 0.0,
                'intensity': 0.0
            }

        stats = self._count_decorative_words(text)
        diversity = self._calculate_decorative_diversity(text)
        intensity = self._calculate_decorative_intensity(stats)
        decorativeness_score = 0.6 * intensity + 0.4 * diversity

        return {
            'decorativeness_score': decorativeness_score,
            'stats': stats,
            'diversity': diversity,
            'intensity': intensity
        }

    def get_score_interpretation(self, score):
        """
        获取分数的解释

        Args:
            score (float): 修饰性丰富度分数

        Returns:
            str: 分数解释
        """
        if score >= 0.7:
            return "高修饰性"
        elif score >= 0.4:
            return "中等修饰性"
        elif score >= 0.2:
            return "低修饰性"
        else:
            return "极少修饰"


def main():
    """测试函数"""
    # 创建评估器
    evaluator = DecorativenessEvaluator()

    # 测试文本
    test_texts = [
        "The beautiful, brightly colored flowers danced gracefully in the gentle, warm breeze.",
        "The system processes data.",
        "An incredibly complex and sophisticated algorithm efficiently manages massive datasets.",
        "The report is complete.",
        "A truly magnificent, extraordinarily beautiful, absolutely stunning sunset painted the sky in brilliant shades of orange, pink, and purple."
    ]

    print("Decorativeness Evaluation Results:")
    print("=" * 70)

    for text in test_texts:
        score = evaluator.evaluate_text(text)
        detailed = evaluator.get_detailed_scores(text)
        interpretation = evaluator.get_score_interpretation(score)

        print(f"Text: {text}")
        print(f"Score: {score:.3f} ({interpretation})")
        print(f"Decorative Ratio: {detailed['stats']['total_decorative_ratio']:.3f}")
        print(f"Diversity: {detailed['diversity']:.3f}")
        print("-" * 70)


if __name__ == "__main__":
    main()