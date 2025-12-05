"""
Emotionality Evaluator using VADER Sentiment
用于评估文本情感丰富度的模块

Usage:
    evaluator = EmotionalityEvaluator()
    score = evaluator.evaluate_text("Your text here")
    scores = evaluator.evaluate_texts(["text1", "text2", ...])
"""

import os
import re
import numpy as np
from collections import defaultdict
from tqdm import tqdm

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    print("Installing vaderSentiment...")
    import subprocess
    subprocess.check_call(["pip", "install", "vaderSentiment"])
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class EmotionalityEvaluator:
    """使用VADER Sentiment评估文本情感丰富度的类"""

    def __init__(self):
        """初始化情感性评估器"""
        self.analyzer = SentimentIntensityAnalyzer()

    def _calculate_emotionality_score(self, text):
        """
        计算情感丰富度分数

        Args:
            text (str): 输入文本

        Returns:
            float: 情感丰富度分数 (0-1)
        """
        # 使用VADER分析情感
        scores = self.analyzer.polarity_scores(text)

        # 直接使用pos + neg作为情感综合得分
        emotionality_score = scores['pos'] + scores['neg']

        return emotionality_score

    def evaluate_text(self, text):
        """
        评估单个文本的情感丰富度

        Args:
            text (str): 输入文本

        Returns:
            float: 情感丰富度分数 (0-1)，越高表示情感越丰富
        """
        if not isinstance(text, str) or len(text.strip()) == 0:
            return 0.0

        return self._calculate_emotionality_score(text.strip())

    def evaluate_texts(self, texts):
        """
        批量评估文本的情感丰富度

        Args:
            texts (list): 文本列表

        Returns:
            list: 情感丰富度分数列表
        """
        if not isinstance(texts, list):
            texts = [texts]

        scores = []
        for text in tqdm(texts, desc="Evaluating emotionality"):
            score = self.evaluate_text(text)
            scores.append(score)

        return scores

    def get_detailed_scores(self, text):
        """
        获取详细的情感分析分数

        Args:
            text (str): 输入文本

        Returns:
            dict: 详细分数
        """
        if not isinstance(text, str) or len(text.strip()) == 0:
            return {
                'emotionality_score': 0.0,
                'vader_scores': {'compound': 0.0, 'pos': 0.0, 'neg': 0.0, 'neu': 1.0}
            }

        # 获取VADER分数
        vader_scores = self.analyzer.polarity_scores(text)

        # 情感丰富度分数 = pos + neg
        emotionality_score = vader_scores['pos'] + vader_scores['neg']

        return {
            'emotionality_score': emotionality_score,
            'vader_scores': vader_scores
        }

    def get_score_interpretation(self, score):
        """
        获取分数的解释

        Args:
            score (float): 情感丰富度分数

        Returns:
            str: 分数解释
        """
        if score >= 0.7:
            return "高情感丰富度"
        elif score >= 0.4:
            return "中等情感丰富度"
        elif score >= 0.2:
            return "低情感丰富度"
        else:
            return "极少情感表达"


def main():
    """测试函数"""
    # 创建评估器
    evaluator = EmotionalityEvaluator()

    # 测试文本
    test_texts = [
        "I love this beautiful sunset! It's absolutely amazing and makes me feel incredibly happy.",
        "The data shows a 15% increase in quarterly revenue.",
        "I'm so frustrated and disappointed with this terrible situation.",
        "The system processes information efficiently.",
        "Wow! This is absolutely fantastic! I'm thrilled, excited, and completely delighted!"
    ]

    print("Emotionality Evaluation Results:")
    print("=" * 60)

    for text in test_texts:
        score = evaluator.evaluate_text(text)
        detailed = evaluator.get_detailed_scores(text)
        interpretation = evaluator.get_score_interpretation(score)

        print(f"Text: {text}")
        print(f"Score: {score:.3f} ({interpretation})")
        print(f"VADER Compound: {detailed['vader_scores']['compound']:.3f}")
        print(f"Positive Score: {detailed['vader_scores']['pos']:.3f}")
        print(f"Negative Score: {detailed['vader_scores']['neg']:.3f}")
        print(f"Positive + Negative: {detailed['emotionality_score']:.3f}")
        print("-" * 60)


if __name__ == "__main__":
    main()