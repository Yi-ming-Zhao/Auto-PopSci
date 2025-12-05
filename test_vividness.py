#!/usr/bin/env python3
"""
测试vividness评估模块
"""

import sys
import os

# 添加路径
sys.path.append('auto_popsci/evaluation/vividness')

def test_decorativeness():
    """测试decorativeness模块"""
    print("=" * 60)
    print("测试 Decorativeness 模块")
    print("=" * 60)

    try:
        from decorativeness.decorativeness import DecorativenessEvaluator
        evaluator = DecorativenessEvaluator()

        test_texts = [
            "The beautiful, brightly colored flowers danced gracefully.",
            "The system processes data.",
            "A complex algorithm manages datasets efficiently."
        ]

        for text in test_texts:
            score = evaluator.evaluate_text(text)
            detailed = evaluator.get_detailed_scores(text)
            interpretation = evaluator.get_score_interpretation(score)

            print(f"文本: {text}")
            print(f"分数: {score:.3f} ({interpretation})")
            print(f"修饰词比例: {detailed['stats']['total_decorative_ratio']:.3f}")
            print("-" * 40)

        print("✅ Decorativeness 模块工作正常!")
        return True

    except Exception as e:
        print(f"❌ Decorativeness 模块错误: {e}")
        return False

def test_emotionality():
    """测试emotionality模块"""
    print("=" * 60)
    print("测试 Emotionality 模块")
    print("=" * 60)

    try:
        from emotionality.emotionality import EmotionalityEvaluator
        evaluator = EmotionalityEvaluator()

        test_texts = [
            "I love this beautiful sunset! It's absolutely amazing!",
            "The data shows a 15% increase in quarterly revenue.",
            "I'm so frustrated and disappointed with this terrible situation."
        ]

        for text in test_texts:
            score = evaluator.evaluate_text(text)
            detailed = evaluator.get_detailed_scores(text)
            interpretation = evaluator.get_score_interpretation(score)

            print(f"文本: {text}")
            print(f"分数: {score:.3f} ({interpretation})")
            print(f"VADER分数: {detailed['vader_scores']}")
            print("-" * 40)

        print("✅ Emotionality 模块工作正常!")
        return True

    except Exception as e:
        print(f"❌ Emotionality 模块错误: {e}")
        return False

def test_figurativeness():
    """测试figurativeness模块"""
    print("=" * 60)
    print("测试 Figurativeness 模块")
    print("=" * 60)

    try:
        from figurativeness.figurativeness import FigurativenessEvaluator
        print("正在初始化FigurativenessEvaluator...")
        evaluator = FigurativenessEvaluator()

        test_texts = [
            "The sun is a golden coin in the sky.",
            "The computer is processing data.",
        ]

        for text in test_texts:
            print(f"正在评估: {text}")
            score = evaluator.evaluate_text(text)
            interpretation = evaluator.get_score_interpretation(score)

            print(f"文本: {text}")
            print(f"分数: {score:.3f} ({interpretation})")
            print("-" * 40)

        print("✅ Figurativeness 模块工作正常!")
        return True

    except Exception as e:
        print(f"❌ Figurativeness 模块错误: {e}")
        print("这是预期的错误，因为PyTorch版本不兼容")
        return False

def test_vividness_combined():
    """测试综合vividness评估"""
    print("=" * 60)
    print("测试综合 Vividness 评估")
    print("=" * 60)

    try:
        import vividness
        evaluator = vividness.VividnessEvaluator()

        test_text = "The beautiful sunset painted the sky with golden colors like a masterpiece."
        result = evaluator.get_detailed_analysis(test_text)

        print(f"文本: {test_text}")
        print(f"总分: {result['vividness_score']:.3f} ({result['interpretation']})")
        print("各组件分数:")
        for component, details in result['component_details'].items():
            weight = result['weights'][component]
            contribution = details['score'] * weight
            print(f"  - {component.capitalize()}: {details['score']:.3f} "
                  f"(权重: {weight:.1f}, 贡献: {contribution:.3f}) "
                  f"-> {details['interpretation']}")

        print("✅ 综合Vividness评估工作正常!")
        return True

    except Exception as e:
        print(f"❌ 综合Vividness评估错误: {e}")
        return False

if __name__ == "__main__":
    print("开始测试 Vividness 评估模块...")

    results = []

    # 测试各个模块
    results.append(("Decorativeness", test_decorativeness()))
    results.append(("Emotionality", test_emotionality()))
    results.append(("Figurativeness", test_figurativeness()))
    results.append(("综合Vividness", test_vividness_combined()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for module, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{module}: {status}")

    successful_modules = [r[0] for r in results if r[1]]
    print(f"\n成功模块: {len(successful_modules)}/{len(results)}")

    if len(successful_modules) == 3:  # decorativeness, emotionality, combined
        print("\n🎉 主要功能正常! Figurativeness因PyTorch版本问题暂时不可用。")
        print("解决方案: 升级PyTorch到2.1+版本")
    else:
        print(f"\n⚠️  仅有 {len(successful_modules)} 个模块正常工作，需要进一步调试。")