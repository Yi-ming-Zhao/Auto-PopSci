#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compute FKGL (Flesch-Kincaid Grade Level) averages for the NatGeo Kids dataset using the EASSE library.
"""

import json
import sys
import os

# Add the current directory to Python path to import easse.
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../easse'))

# Attempt to import EASSE FKGL (strong dependency; no simplified implementation available).
import sys
sys.path.append('../../../easse')
from easse.fkgl import corpus_fkgl


def load_natgeo_dataset(file_path):
    """Load the NatGeo Kids dataset."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("JSON file format error: expected a list.")
            return None, None

        natgeo_sentences = []
        wikipedia_sentences = []

        valid_pairs = 0

        for item in data:
            natgeo_article = item.get('natgeo_article', {})
            wikipedia_content = item.get('wikipedia_content', '')

            if not natgeo_article or not wikipedia_content:
                continue

            natgeo_content = natgeo_article.get('content', '')

            if not natgeo_content:
                continue

            # Split long text into sentences.
            natgeo_text_sentences = [s.strip() for s in natgeo_content.split('.') if s.strip()]
            wiki_text_sentences = [s.strip() for s in wikipedia_content.split('.') if s.strip()]

            # Collect all sentences.
            natgeo_sentences.extend(natgeo_text_sentences)
            wikipedia_sentences.extend(wiki_text_sentences)
            valid_pairs += 1

        print(f"Loaded {valid_pairs} valid sentence pairs.")
        print(f"  NatGeo sentences: {len(natgeo_sentences)}")
        print(f"  Wikipedia sentences: {len(wikipedia_sentences)}")

        return natgeo_sentences, wikipedia_sentences

    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None, None
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None


def main():
    """Main entry point."""
    print("Computing FKGL scores with the EASSE library...")
    print("Using the EASSE FKGL implementation for calculation.")
    fkgl_func = corpus_fkgl
    method_name = "EASSE_corpus_fkgl"

    # Dataset path.
    dataset_path = 'datasets/our_dataset/natgeo_kids/natgeo_wikipedia_glm.json'

    # Load the dataset.
    natgeo_sentences, wiki_sentences = load_natgeo_dataset(dataset_path)

    if natgeo_sentences is None or wiki_sentences is None:
        print("Failed to load dataset.")
        return

    if not natgeo_sentences or not wiki_sentences:
        print("No valid data available for analysis.")
        return

    print("Starting FKGL computation...")

    try:
        # Calculate FKGL scores.
        print("Computing FKGL score for NatGeo sentences...")
        natgeo_fkgl = fkgl_func(
            sentences=natgeo_sentences,
            tokenizer='13a'
        )

        print("Computing FKGL score for Wikipedia sentences...")
        wiki_fkgl = fkgl_func(
            sentences=wiki_sentences,
            tokenizer='13a'
        )

        # Calculate the overall FKGL score.
        all_sentences = natgeo_sentences + wiki_sentences
        overall_fkgl = fkgl_func(
            sentences=all_sentences,
            tokenizer='13a'
        )

        print("\nFKGL analysis results:")
        print(f"   NatGeo sentences: {len(natgeo_sentences)}")
        print(f"   Wikipedia sentences: {len(wiki_sentences)}")
        print(f"   Total sentences: {len(all_sentences)}")
        print()
        print(f"   NatGeo FKGL score: {natgeo_fkgl:.4f}")
        print(f"   Wikipedia FKGL score: {wiki_fkgl:.4f}")
        print(f"   Combined FKGL score: {overall_fkgl:.4f}")
        print(f"   Average FKGL score: {(natgeo_fkgl + wiki_fkgl) / 2:.4f}")

        # Explain the FKGL ranges.
        print("\nFKGL score interpretation:")
        print("   1-8: Elementary level")
        print("   9-12: Middle School level")
        print("   13-16: High School level")
        print("   17+: College level or above")

        # Provide readability assessments based on the scores.
        print("\nReadability evaluation:")
        if natgeo_fkgl <= 8:
            print("   NatGeo Kids article: Suitable for children (Elementary level).")
        elif natgeo_fkgl <= 12:
            print("   NatGeo Kids article: Requires moderate reading ability (Middle School level).")
        else:
            print("   NatGeo Kids article: Too complex for children (High School level or above).")

        if wiki_fkgl <= 12:
            print("   Wikipedia content: Relatively easy to read (Middle School level or below).")
        elif wiki_fkgl <= 16:
            print("   Wikipedia content: Requires strong reading skills (High School level).")
        else:
            print("   Wikipedia content: Complex (College level or above).")

        # Analyze simplification level.
        fkgl_difference = abs(natgeo_fkgl - wiki_fkgl)
        print("\nSimplification analysis:")
        print(f"   FKGL difference: {fkgl_difference:.4f}")
        if fkgl_difference < 2:
            print("   Readability is similar for both texts.")
        elif fkgl_difference < 5:
            print("   Moderate readability gap detected.")
        else:
            print("   Significant readability gap detected.")

        # Save the results.
        results = {
            'total_natgeo_sentences': len(natgeo_sentences),
            'total_wikipedia_sentences': len(wiki_sentences),
            'total_sentences': len(all_sentences),
            'natgeo_fkgl': natgeo_fkgl,
            'wikipedia_fkgl': wiki_fkgl,
            'overall_fkgl': overall_fkgl,
            'average_fkgl': (natgeo_fkgl + wiki_fkgl) / 2,
            'fkgl_difference': fkgl_difference,
            'readability_assessment': {
                'natgeo_level': get_readability_level(natgeo_fkgl),
                'wikipedia_level': get_readability_level(wiki_fkgl),
                'simplification_difficulty': get_simplification_assessment(fkgl_difference)
            },
            'method': method_name
        }

        with open('easse_fkgl_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print("\nDetailed results saved to: easse_fkgl_results.json")

    except Exception as e:
        print(f"Error computing FKGL scores: {e}")
        import traceback
        traceback.print_exc()


def get_readability_level(fkgl_score):
    """Return a readability level label for an FKGL score."""
    if fkgl_score <= 8:
        return "Elementary level"
    elif fkgl_score <= 12:
        return "Middle School level"
    elif fkgl_score <= 16:
        return "High School level"
    else:
        return "College level or above"


def get_simplification_assessment(difference):
    """Assess the simplification level based on FKGL difference."""
    if difference < 2:
        return "Similar readability"
    elif difference < 5:
        return "Moderate simplification gap"
    else:
        return "Significant simplification gap"


if __name__ == "__main__":
    main()
