"""
Decorativeness Evaluator
Module for assessing decorative vocabulary richness leveraging only POS tagging.

This evaluator relies on NLTK POS tagging to detect adjectives and adverbs without
predefined lexicons, maintaining objectivity and broader applicability.

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
    """Check whether the required NLTK data package exists."""
    try:
        nltk_module.data.find(data_name)
        return True
    except LookupError:
        return False

try:
    import nltk
    from nltk import pos_tag, word_tokenize
    from nltk.corpus import wordnet
    from auto_popsci.utils.utils import download_nltk_data
    
    # Ensure required NLTK data is downloaded.
    download_nltk_data('punkt')
    download_nltk_data('averaged_perceptron_tagger')
    download_nltk_data('averaged_perceptron_tagger_eng')
    # download_nltk_data('wordnet') # User requested to skip wordnet
    
    NLTK_AVAILABLE = True
except ImportError:
    print("NLTK not found. Attempting to install...")
    try:
        import subprocess
        subprocess.check_call(["pip", "install", "nltk"])
        import nltk
        from nltk import pos_tag, word_tokenize
        # from nltk.corpus import wordnet # User requested to skip
        from auto_popsci.utils.utils import download_nltk_data
        
        # Ensure required NLTK data is downloaded.
        download_nltk_data('punkt')
        download_nltk_data('averaged_perceptron_tagger')
        download_nltk_data('averaged_perceptron_tagger_eng')
        # download_nltk_data('wordnet')
        
        NLTK_AVAILABLE = True
    except Exception as e:
        print(f"Warning: NLTK not available, using fallback methods: {e}")
        NLTK_AVAILABLE = False


class DecorativenessEvaluator:
    """
    Decorativeness evaluator using NLTK POS tagging.

    It detects decorative words via POS tags:
    - adjectives: JJ, JJR, JJS
    - adverbs: RB, RBR, RBS
    """

    def __init__(self):
        """Initialize the decorativeness evaluator using POS tagging only."""
        # Decorative POS tags (Penn Treebank).
        self.decorative_pos_tags = {
            'adjectives': {'JJ', 'JJR', 'JJS'},  # Adjectives: base, comparative, superlative.
            'adverbs': {'RB', 'RBR', 'RBS'},    # Adverbs: base, comparative, superlative.
        }

    def _tokenize_text(self, text):
        """
        Tokenize the input text.

        Args:
            text (str): Input text.

        Returns:
            list: List of tokens.
        """
        if NLTK_AVAILABLE:
            return word_tokenize(text.lower())
        else:
            # Simple tokenization fallback.
            return re.findall(r'\b\w+\b', text.lower())

    def _pos_tag_words(self, words):
        """
        Tag tokens with part-of-speech labels.

        Args:
            words (list): List of tokens.

        Returns:
            list: List of (word, tag) tuples.
        """
        if NLTK_AVAILABLE:
            return pos_tag(words)
        else:
            # Simple POS tagging fallback.
            tagged = []
            for word in words:
                # Common adjective suffixes.
                if word.endswith(('ful', 'less', 'ous', 'ive', 'able', 'ible', 'al', 'ary', 'ed', 'ing')):
                    tagged.append((word, 'JJ'))
                # Common adverb suffixes.
                elif word.endswith(('ly', 'wise', 'wards')):
                    tagged.append((word, 'RB'))
                else:
                    tagged.append((word, 'NN'))  # Default to noun.
            return tagged

    def _count_decorative_words(self, text):
        """
        Count decorative words using POS tagging.

        Args:
            text (str): Input text.

        Returns:
            dict: Decorative word statistics.
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

        # Count POS tags based on NLTK tagging.
        pos_counts = defaultdict(int)

        for word, pos_tag in tagged_words:
            # Count adjectives.
            if pos_tag in self.decorative_pos_tags['adjectives']:
                pos_counts['adjectives'] += 1
            # Count adverbs.
            elif pos_tag in self.decorative_pos_tags['adverbs']:
                pos_counts['adverbs'] += 1

        total_adjectives = pos_counts['adjectives']
        total_adverbs = pos_counts['adverbs']
        total_decorative = total_adjectives + total_adverbs

        # Compute ratios.
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
        Calculate diversity of decorative vocabulary.

        Args:
            text (str): Input text.

        Returns:
            float: Diversity score (0-1).
        """
        words = self._tokenize_text(text)
        tagged_words = self._pos_tag_words(words)

        # Extract decorative words via POS tagging.
        decorative_words = []
        for word, pos_tag in tagged_words:
            if (pos_tag in self.decorative_pos_tags['adjectives'] or
                pos_tag in self.decorative_pos_tags['adverbs']):
                decorative_words.append(word)

        if len(decorative_words) == 0:
            return 0.0

        # Compute vocabulary diversity (unique decorative words).
        unique_decorative = len(set(decorative_words))
        diversity = unique_decorative / len(decorative_words)

        return diversity

    def _calculate_decorative_intensity(self, stats):
        """
        Calculate decorative intensity based on decorative ratios.

        Args:
            stats (dict): Decorative word statistics.

        Returns:
            float: Intensity score (0-1).
        """
        total_ratio = stats['total_decorative_ratio']

        # Decorative intensity is based on density and distribution.
        if total_ratio <= 0.05:  # <=5% indicates low intensity.
            intensity = total_ratio * 4  # Scale linearly.
        elif total_ratio <= 0.15:  # 5-15% indicates moderate intensity.
            intensity = 0.2 + (total_ratio - 0.05) * 3
        elif total_ratio <= 0.30:  # 15-30% indicates high intensity.
            intensity = 0.5 + (total_ratio - 0.15) * 2
        else:  # Above 30% indicates very high intensity.
            intensity = min(0.8 + (total_ratio - 0.30), 1.0)

        return min(intensity, 1.0)

    def evaluate_text(self, text):
        """
        Evaluate the decorativeness of a single text.

        Args:
            text (str): Input text.

        Returns:
            float: Decorativeness score (0-1); higher values denote richer decoration.
        """
        if not isinstance(text, str) or len(text.strip()) == 0:
            return 0.0

        # Collect decorative word statistics.
        stats = self._count_decorative_words(text)

        # Compute diversity.
        diversity = self._calculate_decorative_diversity(text)

        # Compute intensity.
        intensity = self._calculate_decorative_intensity(stats)

        # Combine intensity and diversity into a decorativeness score.
        decorativeness_score = 0.6 * intensity + 0.4 * diversity

        return min(decorativeness_score, 1.0)

    def evaluate_texts(self, texts):
        """
        Evaluate multiple texts for decorativeness.

        Args:
            texts (list): List of text inputs.

        Returns:
            list: Decorativeness scores.
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
        Obtain detailed decorativeness analysis scores.

        Args:
            text (str): Input text.

        Returns:
            dict: Detailed scoring breakdown.
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
        Provide a textual interpretation of a decorativeness score.

        Args:
            score (float): Decorativeness score.

        Returns:
            str: Interpretation label.
        """
        if score >= 0.7:
            return "High decorativeness"
        elif score >= 0.4:
            return "Moderate decorativeness"
        elif score >= 0.2:
            return "Low decorativeness"
        else:
            return "Minimal decorativeness"


def main():
    """Demo runner for the decorativeness evaluator."""
    # Create the evaluator.
    evaluator = DecorativenessEvaluator()

    # Test texts.
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
