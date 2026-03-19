#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compute CEFR (Common European Framework of Reference) levels using the cefrpy package.
"""

import json
import sys
import os
import re
from typing import List, Dict, Optional, Tuple

try:
    from cefrpy import CEFRAnalyzer
    CEFRPY_AVAILABLE = True
except ImportError:
    print("cefrpy is not installed; please run: pip install cefrpy")
    CEFRPY_AVAILABLE = False
    # Define a stub class to avoid type hints when cefrpy is unavailable.
    class CEFRAnalyzer:
        pass

try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.tag import pos_tag
    from auto_popsci.utils.utils import download_nltk_data
    NLTK_AVAILABLE = True
    # Download required NLTK data.
    download_nltk_data('punkt')
    download_nltk_data('averaged_perceptron_tagger')
except ImportError:
    print("NLTK is not installed; falling back to a simple tokenizer.")
    print("   Optional: pip install nltk")
    NLTK_AVAILABLE = False


def get_cefr_level_name(level: float) -> str:
    """Convert a numeric CEFR level to a descriptive label."""
    if level < 1.0:
        return "A1 (Beginner)"
    elif level < 2.0:
        return "A2 (Elementary)"
    elif level < 3.0:
        return "B1 (Intermediate)"
    elif level < 4.0:
        return "B2 (Upper Intermediate)"
    elif level < 5.0:
        return "C1 (Fluent)"
    else:
        return "C2 (Proficient)"


def simple_tokenize(text: str) -> List[str]:
    """Simple tokenizer used when NLTK is unavailable."""
    # Remove punctuation, lowercase, and split into words.
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.lower().split()
    return words


def get_pos_tag_simple(word: str) -> str:
    """Simple POS tagger fallback for when NLTK is unavailable."""
    # This is a highly simplified POS tagger; prefer NLTK when available.
    # Default to the most common POS tag.
    return "NN"  # Noun.


def tokenize_and_tag(text: str) -> List[Tuple[str, str]]:
    """
    Tokenize and POS tag the text.

    Returns:
        List of (word, tag) tuples.
    """
    if NLTK_AVAILABLE:
        try:
            words = word_tokenize(text)
            tagged = pos_tag(words)
            # Convert NLTK POS tags to the Penn Treebank format required by cefrpy.
            return [(word.lower(), tag) for word, tag in tagged if word.isalpha()]
        except Exception as e:
            print(f"NLTK processing failed; using fallback tokenizer: {e}")
            words = simple_tokenize(text)
            return [(word, get_pos_tag_simple(word)) for word in words]
    else:
        words = simple_tokenize(text)
        return [(word, get_pos_tag_simple(word)) for word in words]


def calculate_text_cefr(text: str, analyzer: CEFRAnalyzer) -> Dict:
    """
    Calculate the CEFR level for a single text.

    Args:
        text: The text to analyze.
        analyzer: CEFRAnalyzer instance.

    Returns:
        Dict containing CEFR level metadata.
    """
    if not text or not text.strip():
        return {
            'level': None,
            'level_name': 'N/A',
            'error': 'text is empty',
            'word_count': 0,
            'analyzed_words': 0
        }
    
    try:
        # Tokenize and POS tag the text.
        word_pos_pairs = tokenize_and_tag(text)
        
        if not word_pos_pairs:
            return {
                'level': None,
                'level_name': 'N/A',
                'error': 'unable to tokenize text',
                'word_count': 0,
                'analyzed_words': 0
            }
        
        # Compute the CEFR level for each word.
        levels = []
        analyzed_count = 0
        
        for word, pos_tag in word_pos_pairs:
            try:
                # Try to get the CEFR level for the word with this POS tag.
                level = analyzer.get_word_pos_level_float(word, pos_tag)
                if level is not None:
                    levels.append(level)
                    analyzed_count += 1
                else:
                    # If no match for the specific POS, try the average level.
                    avg_level = analyzer.get_average_word_level_float(word)
                    if avg_level is not None:
                        levels.append(avg_level)
                        analyzed_count += 1
            except Exception:
                continue
        
        if not levels:
            return {
                'level': None,
                'level_name': 'N/A',
                'error': 'no CEFR level found for any word',
                'word_count': len(word_pos_pairs),
                'analyzed_words': 0
            }
        
        # Compute the average CEFR level.
        avg_level = sum(levels) / len(levels)
        
        return {
            'level': avg_level,
            'level_name': get_cefr_level_name(avg_level),
            'error': None,
            'word_count': len(word_pos_pairs),
            'analyzed_words': analyzed_count,
            'min_word_level': min(levels),
            'max_word_level': max(levels)
        }
    except Exception as e:
        return {
            'level': None,
            'level_name': 'N/A',
            'error': str(e),
            'word_count': 0,
            'analyzed_words': 0
        }


def calculate_corpus_cefr(texts: List[str], analyzer: CEFRAnalyzer) -> Dict:
    """
    Calculate corpus-level CEFR statistics.

    Args:
        texts: List of texts.
        analyzer: CEFRAnalyzer instance.

    Returns:
        Dict containing summary statistics.
    """
    if not texts:
        return {
            'average_level': None,
            'average_level_name': 'N/A',
            'min_level': None,
            'max_level': None,
            'total_texts': 0,
            'valid_texts': 0
        }
    
    levels = []
    valid_count = 0
    
    for text in texts:
        result = calculate_text_cefr(text, analyzer)
        if result['level'] is not None:
            levels.append(result['level'])
            valid_count += 1
    
    if not levels:
        return {
            'average_level': None,
            'average_level_name': 'N/A',
            'min_level': None,
            'max_level': None,
            'total_texts': len(texts),
            'valid_texts': 0
        }
    
    avg_level = sum(levels) / len(levels)
    min_level = min(levels)
    max_level = max(levels)
    
    return {
        'average_level': avg_level,
        'average_level_name': get_cefr_level_name(avg_level),
        'min_level': min_level,
        'min_level_name': get_cefr_level_name(min_level),
        'max_level': max_level,
        'max_level_name': get_cefr_level_name(max_level),
        'total_texts': len(texts),
        'valid_texts': valid_count
    }


def load_articles_from_json(file_path: str, content_field: str = 'content') -> List[str]:
    """
    Load article contents from a JSON file.
    
    Args:
        file_path: Path to the JSON file.
        content_field: Field name containing the text (default 'content').
    
    Returns:
        List[str]: Extracted article texts.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        articles = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    content = item.get(content_field, '')
                    if content and content.strip():
                        articles.append(content.strip())
        elif isinstance(data, dict):
            content = data.get(content_field, '')
            if content and content.strip():
                articles.append(content.strip())
        
        return articles
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error loading articles: {e}")
        return []


def main():
    """Main entry point."""
    if not CEFRPY_AVAILABLE:
        print("cefrpy is not installed; cannot continue.")
        print("   Please run: pip install cefrpy")
        return
    
    print("Computing CEFR levels using cefrpy...")
    
    # Initialize the CEFR analyzer.
    try:
        analyzer = CEFRAnalyzer()
        print("CEFR analyzer initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize CEFR analyzer: {e}")
        return
    
    # Example 1: analyze a single text.
    print("\n" + "="*60)
    print("Example 1: Analyze a single text sample")
    print("="*60)
    
    sample_text = "The sun is very bright today. It makes me happy."
    print(f"Text: {sample_text}")
    result = calculate_text_cefr(sample_text, analyzer)
    print(f"CEFR level: {result['level']:.2f}")
    print(f"CEFR level name: {result['level_name']}")
    
    # Example 2: load and analyze from a JSON file.
    print("\n" + "="*60)
    print("Example 2: Analyze articles from a JSON file")
    print("="*60)
    
    # Check for CLI-specified file paths.
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = 'datasets/our_dataset/nasa_kids_articles.json'
    
    if os.path.exists(json_file):
        print(f"Loading file: {json_file}")
        articles = load_articles_from_json(json_file)
        
        if articles:
            print(f"Successfully loaded {len(articles)} articles.")
            
            # Calculate each article's CEFR level.
            print("\nStarting CEFR level computation...")
            results = []
            for i, article in enumerate(articles[:10], 1):
                result = calculate_text_cefr(article, analyzer)
                results.append({
                    'article_index': i,
                    'text_length': len(article),
                    **result
                })
                level_display = result['level'] if result['level'] is not None else float('nan')
                print(f"Article {i}: CEFR level = {level_display:.2f} ({result['level_name']})")
            
            # Compute overall statistics.
            print("\n" + "="*60)
            print("Corpus statistics")
            print("="*60)
            corpus_stats = calculate_corpus_cefr(articles, analyzer)
            print(f"Total articles: {corpus_stats['total_texts']}")
            print(f"Valid articles: {corpus_stats['valid_texts']}")
            print(f"Average CEFR level: {corpus_stats['average_level']:.2f}")
            print(f"Average CEFR level name: {corpus_stats['average_level_name']}")
            print(f"Minimum CEFR level: {corpus_stats['min_level']:.2f} ({corpus_stats['min_level_name']})")
            print(f"Maximum CEFR level: {corpus_stats['max_level']:.2f} ({corpus_stats['max_level_name']})")
            
            # Save the results.
            output_file = 'cefr_results.json'
            output_data = {
                'file_analyzed': json_file,
                'corpus_statistics': corpus_stats,
                'sample_results': results[:10]
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\nDetailed results saved to: {output_file}")
        else:
            print("No valid articles found in the file.")
    else:
        print(f"File not found: {json_file}")
        print("   Usage: python cal_cefr.py <json_file_path>")
        print("   Running without arguments will use the default file path.")


if __name__ == "__main__":
    main()
