"""
Vividness Evaluation Package
A comprehensive suite for assessing textual vividness.

Includes three submodules:
- figurativeness: figurative richness evaluation (based on MelBERT)
- emotionality: emotional richness evaluation (based on VADER Sentiment)
- decorativeness: decorative vocabulary richness evaluation
"""

# Safely import each evaluator.
try:
    from .figurativeness.figurativeness import FigurativenessEvaluator
except ImportError as e:
    print(f"Warning: FigurativenessEvaluator not available: {e}")
    FigurativenessEvaluator = None

try:
    from .emotionality.emotionality import EmotionalityEvaluator
except ImportError as e:
    print(f"Warning: EmotionalityEvaluator not available: {e}")
    EmotionalityEvaluator = None

try:
    from .decorativeness.decorativeness import DecorativenessEvaluator
except ImportError as e:
    print(f"Warning: DecorativenessEvaluator not available: {e}")
    DecorativenessEvaluator = None


class VividnessEvaluator:
    """Composite vividness evaluator."""

    def __init__(self, weights=None, melbert_path=None, device=None):
        """
        Initialize the vividness evaluator.
        """
        # Set default weights.
        if weights is None:
            weights = {
                'figurativeness': 0.4,  # Weight for figurativeness.
                'emotionality': 0.3,     # Weight for emotionality.
                'decorativeness': 0.3    # Weight for decorativeness.
            }

        # Validate weight settings.
        if not all(0 <= w <= 1 for w in weights.values()):
            raise ValueError("Weights must be between 0 and 1")

        if abs(sum(weights.values()) - 1.0) > 0.001:
            raise ValueError("Weights must sum to 1.0")

        self.weights = weights
        self.device = device 

        # Initialize the sub-evaluators.
        print("Initializing Vividness Evaluator...")

        print("- Loading Figurativeness Evaluator...")
        try:
            self.figurativeness_evaluator = FigurativenessEvaluator(melbert_path, device=device)
        except TypeError:
            self.figurativeness_evaluator = FigurativenessEvaluator(melbert_path)
            if device: print(f"Warning: Device {device} passed but FigurativenessEvaluator didn't accept it.")
        except Exception as e:
            print(f"Warning: Failed to load Figurativeness Evaluator: {e}")
            self.figurativeness_evaluator = None

        print("- Loading Emotionality Evaluator...")
        try:
            self.emotionality_evaluator = EmotionalityEvaluator()
        except Exception as e:
            print(f"Warning: Failed to load Emotionality Evaluator: {e}")
            self.emotionality_evaluator = None

        print("- Loading Decorativeness Evaluator...")
        try:
            self.decorativeness_evaluator = DecorativenessEvaluator()
        except Exception as e:
            print(f"Warning: Failed to load Decorativeness Evaluator: {e}")
            self.decorativeness_evaluator = None

        print("Vividness Evaluator initialization complete.")

    def evaluate_text(self, text, return_components=False):
        """
        Evaluate the vividness of a single text.

        Args:
            text (str): Input text.
            return_components (bool): Whether to return each component score.

        Returns:
            float or dict: The vividness score or detailed component scores.
        """
        if not isinstance(text, str) or len(text.strip()) == 0:
            if return_components:
                return {
                    'vividness_score': 0.0,
                    'figurativeness': 0.0,
                    'emotionality': 0.0,
                    'decorativeness': 0.0
                }
            return 0.0

        # Compute each component's score.
        component_scores = {}

        if self.figurativeness_evaluator is not None:
            try:
                component_scores['figurativeness'] = self.figurativeness_evaluator.evaluate_text(text)
            except Exception as e:
                print(f"Warning: Figurativeness evaluation failed: {e}")
                component_scores['figurativeness'] = 0.0
        else:
            component_scores['figurativeness'] = 0.0

        if self.emotionality_evaluator is not None:
            try:
                component_scores['emotionality'] = self.emotionality_evaluator.evaluate_text(text)
            except Exception as e:
                print(f"Warning: Emotionality evaluation failed: {e}")
                component_scores['emotionality'] = 0.0
        else:
            component_scores['emotionality'] = 0.0

        if self.decorativeness_evaluator is not None:
            try:
                component_scores['decorativeness'] = self.decorativeness_evaluator.evaluate_text(text)
            except Exception as e:
                print(f"Warning: Decorativeness evaluation failed: {e}")
                component_scores['decorativeness'] = 0.0
        else:
            component_scores['decorativeness'] = 0.0

        # Compute the weighted total vividness score.
        vividness_score = (
            component_scores['figurativeness'] * self.weights['figurativeness'] +
            component_scores['emotionality'] * self.weights['emotionality'] +
            component_scores['decorativeness'] * self.weights['decorativeness']
        )

        if return_components:
            return {
                'vividness_score': vividness_score,
                **component_scores,
                'weights': self.weights.copy()
            }

        return vividness_score

    def evaluate_texts(self, texts, return_components=False):
        """
        Evaluate multiple texts' vividness scores.

        Args:
            texts (list): A list of texts.
            return_components (bool): Whether to return component-level scores.

        Returns:
            list: List of vividness scores or component dicts.
        """
        if not isinstance(texts, list):
            texts = [texts]

        results = []
        for text in texts:
            result = self.evaluate_text(text, return_components)
            results.append(result)

        return results

    def get_detailed_analysis(self, text):
        """
        Get a detailed vividness analysis for a text.

        Args:
            text (str): Input text.

        Returns:
            dict: Detailed analysis results.
        """
        if not isinstance(text, str) or len(text.strip()) == 0:
            return {
                'vividness_score': 0.0,
                'component_scores': {
                    'figurativeness': 0.0,
                    'emotionality': 0.0,
                    'decorativeness': 0.0
                },
                'component_details': {},
                'interpretation': 'Empty text',
                'weights': self.weights
            }

        # Gather detailed component scores.
        component_details = {}

        if self.figurativeness_evaluator is not None:
            try:
                fig_score = self.figurativeness_evaluator.evaluate_text(text)
                component_details['figurativeness'] = {
                    'score': fig_score,
                    'interpretation': self.figurativeness_evaluator.get_score_interpretation(fig_score)
                }
            except Exception as e:
                component_details['figurativeness'] = {
                    'score': 0.0,
                    'interpretation': 'Evaluation failed',
                    'error': str(e)
                }
        else:
            component_details['figurativeness'] = {
                'score': 0.0,
                'interpretation': 'Evaluator not available'
            }

        if self.emotionality_evaluator is not None:
            try:
                emo_score = self.emotionality_evaluator.evaluate_text(text)
                emo_details = self.emotionality_evaluator.get_detailed_scores(text)
                component_details['emotionality'] = {
                    'score': emo_score,
                    'interpretation': self.emotionality_evaluator.get_score_interpretation(emo_score),
                    'details': emo_details
                }
            except Exception as e:
                component_details['emotionality'] = {
                    'score': 0.0,
                    'interpretation': 'Evaluation failed',
                    'error': str(e)
                }
        else:
            component_details['emotionality'] = {
                'score': 0.0,
                'interpretation': 'Evaluator not available'
            }

        if self.decorativeness_evaluator is not None:
            try:
                dec_score = self.decorativeness_evaluator.evaluate_text(text)
                dec_details = self.decorativeness_evaluator.get_detailed_scores(text)
                component_details['decorativeness'] = {
                    'score': dec_score,
                    'interpretation': self.decorativeness_evaluator.get_score_interpretation(dec_score),
                    'details': dec_details
                }
            except Exception as e:
                component_details['decorativeness'] = {
                    'score': 0.0,
                    'interpretation': 'Evaluation failed',
                    'error': str(e)
                }
        else:
            component_details['decorativeness'] = {
                'score': 0.0,
                'interpretation': 'Evaluator not available'
            }

    # Calculate the total vividness score.
        component_scores = {k: v['score'] for k, v in component_details.items()}
        vividness_score = (
            component_scores['figurativeness'] * self.weights['figurativeness'] +
            component_scores['emotionality'] * self.weights['emotionality'] +
            component_scores['decorativeness'] * self.weights['decorativeness']
        )

    # Generate the overall interpretation.
        interpretation = self.get_score_interpretation(vividness_score)

        return {
            'vividness_score': vividness_score,
            'component_scores': component_scores,
            'component_details': component_details,
            'interpretation': interpretation,
            'weights': self.weights.copy()
        }

    def get_score_interpretation(self, score):
        """
        Translate a vividness score into an interpretation.

        Args:
            score (float): vividness score

        Returns:
            str: English description of the score
        """
        if score >= 0.8:
            return "Extremely vivid"
        elif score >= 0.6:
            return "High vividness"
        elif score >= 0.4:
            return "Moderate vividness"
        elif score >= 0.2:
            return "Low vividness"
        else:
            return "Minimal vividness"

    def compare_texts(self, text1, text2):
        """
        Compare the vividness of two texts.

        Args:
            text1 (str): first text
            text2 (str): second text

        Returns:
            dict: comparison results
        """
        analysis1 = self.get_detailed_analysis(text1)
        analysis2 = self.get_detailed_analysis(text2)

        score_diff = analysis1['vividness_score'] - analysis2['vividness_score']

        if abs(score_diff) < 0.05:
            comparison = "Both texts have similar vividness"
        elif score_diff > 0:
            comparison = f"Text 1 is more vivid than Text 2 (difference: {score_diff:.3f})"
        else:
            comparison = f"Text 2 is more vivid than Text 1 (difference: {abs(score_diff):.3f})"

        return {
            'text1_analysis': analysis1,
            'text2_analysis': analysis2,
            'score_difference': score_diff,
            'comparison': comparison,
            'winner': 'text1' if score_diff > 0 else 'text2' if score_diff < 0 else 'tie'
        }


def main():
    """Sample driver for the vividness evaluator."""
    # Create the evaluator.
    evaluator = VividnessEvaluator()

    # Test text.
    test_texts = [
        "The sun is a golden coin in the sky.",
        "The system processes data efficiently.",
        "Her beautiful smile lit up the room like a beacon of hope.",
        "The report indicates significant growth.",
        "An incredibly complex algorithm processes massive datasets with remarkable efficiency."
    ]

    print("Comprehensive Vividness Evaluation Results:")
    print("=" * 80)

    for text in test_texts:
        print(f"Text: {text}")
        result = evaluator.get_detailed_analysis(text)

        print(f"Overall Score: {result['vividness_score']:.3f} ({result['interpretation']})")
        print("Components:")
        for component, details in result['component_details'].items():
            weight = result['weights'][component]
            contribution = details['score'] * weight
            print(f"  - {component.capitalize()}: {details['score']:.3f} "
                  f"(weight: {weight:.1f}, contribution: {contribution:.3f}) "
                  f"-> {details['interpretation']}")
        print("-" * 80)


if __name__ == "__main__":
    main()
