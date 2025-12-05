"""
Vividness Evaluation Package
用于评估文本生动性的综合模块

包含三个子模块：
- figurativeness: 比喻丰富度评估（基于MelBERT）
- emotionality: 情感丰富度评估（基于VADER Sentiment）
- decorativeness: 修饰性词汇丰富度评估
"""

# 安全导入各个评估器
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
    """文本生动性综合评估器"""

    def __init__(self, weights=None, melbert_path=None):
        """
        初始化生动性评估器

        Args:
            weights (dict): 各子模块权重，默认为等权重
            melbert_path (str): MelBERT模型路径
        """
        # 设置默认权重
        if weights is None:
            weights = {
                'figurativeness': 0.4,  # 比喻丰富度权重
                'emotionality': 0.3,     # 情感丰富度权重
                'decorativeness': 0.3    # 修饰性丰富度权重
            }

        # 验证权重
        if not all(0 <= w <= 1 for w in weights.values()):
            raise ValueError("Weights must be between 0 and 1")

        if abs(sum(weights.values()) - 1.0) > 0.001:
            raise ValueError("Weights must sum to 1.0")

        self.weights = weights

        # 初始化子评估器
        print("Initializing Vividness Evaluator...")

        print("- Loading Figurativeness Evaluator...")
        try:
            self.figurativeness_evaluator = FigurativenessEvaluator(melbert_path)
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
        评估单个文本的生动性

        Args:
            text (str): 输入文本
            return_components (bool): 是否返回各子模块分数

        Returns:
            float or dict: 生动性分数，或包含各子模块分数的字典
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

        # 计算各子模块分数
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

        # 计算加权总分
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
        批量评估文本的生动性

        Args:
            texts (list): 文本列表
            return_components (bool): 是否返回各子模块分数

        Returns:
            list: 生动性分数列表，或包含各子模块分数的字典列表
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
        获取详细的生动性分析

        Args:
            text (str): 输入文本

        Returns:
            dict: 详细分析结果
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

        # 获取各子模块详细分数
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

        # 计算总分
        component_scores = {k: v['score'] for k, v in component_details.items()}
        vividness_score = (
            component_scores['figurativeness'] * self.weights['figurativeness'] +
            component_scores['emotionality'] * self.weights['emotionality'] +
            component_scores['decorativeness'] * self.weights['decorativeness']
        )

        # 生成整体解释
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
        获取生动性分数的解释

        Args:
            score (float): 生动性分数

        Returns:
            str: 分数解释
        """
        if score >= 0.8:
            return "极高生动性"
        elif score >= 0.6:
            return "高生动性"
        elif score >= 0.4:
            return "中等生动性"
        elif score >= 0.2:
            return "低生动性"
        else:
            return "极少生动性"

    def compare_texts(self, text1, text2):
        """
        比较两个文本的生动性

        Args:
            text1 (str): 第一个文本
            text2 (str): 第二个文本

        Returns:
            dict: 比较结果
        """
        analysis1 = self.get_detailed_analysis(text1)
        analysis2 = self.get_detailed_analysis(text2)

        score_diff = analysis1['vividness_score'] - analysis2['vividness_score']

        if abs(score_diff) < 0.05:
            comparison = "两个文本的生动性相似"
        elif score_diff > 0:
            comparison = f"文本1的生动性高于文本2（差距: {score_diff:.3f}）"
        else:
            comparison = f"文本2的生动性高于文本1（差距: {abs(score_diff):.3f}）"

        return {
            'text1_analysis': analysis1,
            'text2_analysis': analysis2,
            'score_difference': score_diff,
            'comparison': comparison,
            'winner': 'text1' if score_diff > 0 else 'text2' if score_diff < 0 else 'tie'
        }


def main():
    """测试函数"""
    # 创建评估器
    evaluator = VividnessEvaluator()

    # 测试文本
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