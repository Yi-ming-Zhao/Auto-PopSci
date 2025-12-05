"""
Vividness Evaluation Example Usage
生动性评估使用示例

本文件展示了如何使用vividness评估模块来评估文本的生动性
"""

import sys
import os

# 添加父目录到路径以便导入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vividness import VividnessEvaluator, FigurativenessEvaluator, EmotionalityEvaluator, DecorativenessEvaluator


def example_individual_evaluators():
    """示例：单独使用各个评估器"""
    print("=" * 60)
    print("Individual Evaluator Examples")
    print("=" * 60)

    test_text = "The beautiful sunset painted the sky with golden colors like a masterpiece."

    # 1. 比喻丰富度评估
    print("\n1. Figurativeness Evaluation:")
    print("-" * 30)
    try:
        fig_evaluator = FigurativenessEvaluator()
        fig_score = fig_evaluator.evaluate_text(test_text)
        fig_interpretation = fig_evaluator.get_score_interpretation(fig_score)
        print(f"Text: {test_text}")
        print(f"Figurativeness Score: {fig_score:.3f}")
        print(f"Interpretation: {fig_interpretation}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. 情感丰富度评估
    print("\n2. Emotionality Evaluation:")
    print("-" * 30)
    try:
        emo_evaluator = EmotionalityEvaluator()
        emo_score = emo_evaluator.evaluate_text(test_text)
        emo_interpretation = emo_evaluator.get_score_interpretation(emo_score)
        emo_detailed = emo_evaluator.get_detailed_scores(test_text)
        print(f"Text: {test_text}")
        print(f"Emotionality Score: {emo_score:.3f}")
        print(f"Interpretation: {emo_interpretation}")
        print(f"VADER Compound: {emo_detailed['vader_scores']['compound']:.3f}")
    except Exception as e:
        print(f"Error: {e}")

    # 3. 修饰性丰富度评估
    print("\n3. Decorativeness Evaluation:")
    print("-" * 30)
    try:
        dec_evaluator = DecorativenessEvaluator()
        dec_score = dec_evaluator.evaluate_text(test_text)
        dec_interpretation = dec_evaluator.get_score_interpretation(dec_score)
        dec_detailed = dec_evaluator.get_detailed_scores(test_text)
        print(f"Text: {test_text}")
        print(f"Decorativeness Score: {dec_score:.3f}")
        print(f"Interpretation: {dec_interpretation}")
        print(f"Decorative Word Ratio: {dec_detailed['stats']['total_decorative_ratio']:.3f}")
    except Exception as e:
        print(f"Error: {e}")


def example_comprehensive_evaluation():
    """示例：综合生动性评估"""
    print("\n" + "=" * 60)
    print("Comprehensive Vividness Evaluation")
    print("=" * 60)

    # 创建综合评估器
    print("Initializing Vividness Evaluator...")
    evaluator = VividnessEvaluator()

    # 测试文本列表
    test_texts = [
        "The system processes data efficiently.",
        "The flowers are beautiful.",
        "Her voice was music to his ears, a sweet melody that brightened his darkest days.",
        "The algorithm shows remarkable performance improvement.",
        "An incredibly complex and sophisticated system processes massive datasets with extraordinary efficiency and remarkable accuracy."
    ]

    print(f"\nEvaluating {len(test_texts)} texts:")
    print("-" * 40)

    for i, text in enumerate(test_texts, 1):
        print(f"\n{i}. Text: {text}")

        # 获取详细分析
        analysis = evaluator.get_detailed_analysis(text)

        print(f"   Overall Vividness: {analysis['vividness_score']:.3f} ({analysis['interpretation']})")
        print("   Component Scores:")
        for component, score in analysis['component_scores'].items():
            weight = analysis['weights'][component]
            contribution = score * weight
            print(f"     - {component.capitalize()}: {score:.3f} (weight: {weight:.1f}, contribution: {contribution:.3f})")

    print("\n" + "=" * 60)


def example_batch_evaluation():
    """示例：批量评估"""
    print("\n" + "=" * 60)
    print("Batch Evaluation Example")
    print("=" * 60)

    # 创建评估器
    evaluator = VividnessEvaluator()

    # 文本列表
    texts = [
        "The computer processes information.",
        "The beautiful sunset was amazing.",
        "Her smile brightened the entire room.",
        "The results show significant improvement.",
        "A magnificent celebration of extraordinary achievements marked the joyous occasion."
    ]

    # 批量评估
    scores = evaluator.evaluate_texts(texts, return_components=True)

    print("Batch Results:")
    print("-" * 30)
    for i, (text, result) in enumerate(zip(texts, scores)):
        print(f"{i+1}. {text[:50]}...")
        print(f"   Score: {result['vividness_score']:.3f}")
        print(f"   Components: Fig={result['figurativeness']:.2f}, "
              f"Emo={result['emotionality']:.2f}, Dec={result['decorativeness']:.2f}")

    # 找出最生动的文本
    best_idx = max(range(len(scores)), key=lambda i: scores[i]['vividness_score'])
    worst_idx = min(range(len(scores)), key=lambda i: scores[i]['vividness_score'])

    print(f"\nMost Vivid: '{texts[best_idx]}' (Score: {scores[best_idx]['vividness_score']:.3f})")
    print(f"Least Vivid: '{texts[worst_idx]}' (Score: {scores[worst_idx]['vividness_score']:.3f})")


def example_text_comparison():
    """示例：文本比较"""
    print("\n" + "=" * 60)
    print("Text Comparison Example")
    print("=" * 60)

    # 创建评估器
    evaluator = VividnessEvaluator()

    # 比较的文本对
    comparisons = [
        ("The data shows growth.", "The remarkable data reveals extraordinary growth patterns."),
        ("The meeting was productive.", "The meeting was incredibly productive and generated brilliant ideas."),
        ("She spoke clearly.", "Her voice, clear as crystal, resonated beautifully throughout the hall.")
    ]

    for i, (text1, text2) in enumerate(comparisons, 1):
        print(f"\nComparison {i}:")
        print("-" * 30)
        print(f"Text 1: {text1}")
        print(f"Text 2: {text2}")

        comparison_result = evaluator.compare_texts(text1, text2)
        print(f"Result: {comparison_result['comparison']}")
        print(f"Text 1 Score: {comparison_result['text1_analysis']['vividness_score']:.3f}")
        print(f"Text 2 Score: {comparison_result['text2_analysis']['vividness_score']:.3f}")


def example_custom_weights():
    """示例：自定义权重"""
    print("\n" + "=" * 60)
    print("Custom Weights Example")
    print("=" * 60)

    # 测试文本
    text = "Her beautiful voice was like music, incredibly emotional and wonderfully descriptive."

    # 不同的权重配置
    weight_configs = [
        {"name": "Balanced", "weights": {'figurativeness': 0.33, 'emotionality': 0.33, 'decorativeness': 0.34}},
        {"name": "Figurative Focus", "weights": {'figurativeness': 0.6, 'emotionality': 0.2, 'decorativeness': 0.2}},
        {"name": "Emotional Focus", "weights": {'figurativeness': 0.2, 'emotionality': 0.6, 'decorativeness': 0.2}},
        {"name": "Decorative Focus", "weights": {'figurativeness': 0.2, 'emotionality': 0.2, 'decorativeness': 0.6}}
    ]

    print(f"Text: {text}")
    print("-" * 40)

    for config in weight_configs:
        evaluator = VividnessEvaluator(weights=config['weights'])
        result = evaluator.evaluate_text(text, return_components=True)

        print(f"\n{config['name']} Weights:")
        print(f"  Weights: {config['weights']}")
        print(f"  Overall Score: {result['vividness_score']:.3f}")
        print(f"  Components: Fig={result['figurativeness']:.3f}, "
              f"Emo={result['emotionality']:.3f}, Dec={result['decorativeness']:.3f}")


def main():
    """主函数"""
    print("Vividness Evaluation Examples")
    print("=" * 60)
    print("This script demonstrates various ways to use the vividness evaluation package.")
    print("\nChoose an example:")
    print("1. Individual evaluators")
    print("2. Comprehensive evaluation")
    print("3. Batch evaluation")
    print("4. Text comparison")
    print("5. Custom weights")
    print("6. Run all examples")

    try:
        choice = input("\nEnter your choice (1-6): ").strip()

        if choice == "1":
            example_individual_evaluators()
        elif choice == "2":
            example_comprehensive_evaluation()
        elif choice == "3":
            example_batch_evaluation()
        elif choice == "4":
            example_text_comparison()
        elif choice == "5":
            example_custom_weights()
        elif choice == "6":
            example_individual_evaluators()
            example_comprehensive_evaluation()
            example_batch_evaluation()
            example_text_comparison()
            example_custom_weights()
        else:
            print("Invalid choice. Running comprehensive evaluation example...")
            example_comprehensive_evaluation()

    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        print("Running basic example...")
        example_comprehensive_evaluation()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()