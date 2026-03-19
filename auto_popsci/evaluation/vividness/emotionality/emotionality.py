"""
Emotionality Evaluator using VADER Sentiment
Module for assessing textual emotional richness.

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
    """Evaluate a text's emotional richness using VADER Sentiment."""

    def __init__(self):
        """Initialize the emotionality evaluator."""
        self.analyzer = SentimentIntensityAnalyzer()

    def _calculate_emotionality_score(self, text):
        """
        Compute the emotionality score.

        Args:
            text (str): Input text.

        Returns:
            float: Emotionality score (0-1).
        """
        # Use VADER to analyze sentiment.
        scores = self.analyzer.polarity_scores(text)

        # Use pos + neg as the combined emotionality score.
        emotionality_score = scores['pos'] + scores['neg']

        return emotionality_score

    def evaluate_text(self, text):
        """
        Evaluate the emotionality of a single text.

        Args:
            text (str): Input text.

        Returns:
            float: Emotionality score (0-1); higher equals richer emotion.
        """
        if not isinstance(text, str) or len(text.strip()) == 0:
            return 0.0

        return self._calculate_emotionality_score(text.strip())

    def evaluate_texts(self, texts):
        """
        Evaluate multiple texts for emotionality.

        Args:
            texts (list): List of texts.

        Returns:
            list: Emotionality scores.
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
        Get detailed emotionality scores.

        Args:
            text (str): Input text.

        Returns:
            dict: Detailed score breakdown.
        """
        if not isinstance(text, str) or len(text.strip()) == 0:
            return {
                'emotionality_score': 0.0,
                'vader_scores': {'compound': 0.0, 'pos': 0.0, 'neg': 0.0, 'neu': 1.0}
            }

        # Retrieve VADER scores.
        vader_scores = self.analyzer.polarity_scores(text)

        # Emotionality score = pos + neg.
        emotionality_score = vader_scores['pos'] + vader_scores['neg']

        return {
            'emotionality_score': emotionality_score,
            'vader_scores': vader_scores
        }

    def get_score_interpretation(self, score):
        """
        Interpret an emotionality score.

        Args:
            score (float): Emotionality score.

        Returns:
            str: Textual interpretation.
        """
        if score >= 0.7:
            return "High emotional richness"
        elif score >= 0.4:
            return "Moderate emotional richness"
        elif score >= 0.2:
            return "Mild emotional richness"
        else:
            return "Minimal emotional expression"


def main():
    """Demo runner for the emotionality evaluator."""
    # Create the evaluator.
    evaluator = EmotionalityEvaluator()

    # Test texts.
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
