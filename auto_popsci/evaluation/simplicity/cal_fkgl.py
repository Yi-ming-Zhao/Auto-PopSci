#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用EASSE库计算NatGeo Kids数据集的FKGL (Flesch-Kincaid Grade Level) 平均值
"""

import json
import sys
import os

# 添加当前目录到Python路径，以便导入easse
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../easse'))

# 尝试导入EASSE FKGL
try:
    import sys
    sys.path.append('../../../easse')
    from easse.fkgl import corpus_fkgl
    EASSE_AVAILABLE = True
except ImportError:
    print("⚠️ EASSE FKGL库导入失败，将使用简单FKGL计算")
    EASSE_AVAILABLE = False


def simple_fkgl(sentences):
    """简单的FKGL计算实现"""
    if not sentences:
        return 0.0

    total_words = 0
    total_syllables = 0
    total_sentences = len(sentences)

    for sentence in sentences:
        words = sentence.split()
        total_words += len(words)
        for word in words:
            total_syllables += count_syllables(word)

    if total_sentences == 0 or total_words == 0:
        return 0.0

    # Flesch-Kincaid Grade Level formula
    fkgl = 0.39 * (total_words / total_sentences) + 11.8 * (total_syllables / total_words) - 15.59
    return max(0, fkgl)


def count_syllables(word):
    """简单的音节计数"""
    word = word.lower()
    vowels = "aeiouy"
    syllable_count = 0
    prev_char_was_vowel = False

    for char in word:
        if char in vowels:
            if not prev_char_was_vowel:
                syllable_count += 1
            prev_char_was_vowel = True
        else:
            prev_char_was_vowel = False

    if word.endswith('e') and syllable_count > 1:
        syllable_count -= 1

    return max(1, syllable_count)


def load_natgeo_dataset(file_path):
    """加载NatGeo Kids数据集"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("❌ JSON文件格式错误：预期是数组")
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

            # 将长文本按句子分割
            natgeo_text_sentences = [s.strip() for s in natgeo_content.split('.') if s.strip()]
            wiki_text_sentences = [s.strip() for s in wikipedia_content.split('.') if s.strip()]

            # 收集所有句子
            natgeo_sentences.extend(natgeo_text_sentences)
            wikipedia_sentences.extend(wiki_text_sentences)
            valid_pairs += 1

        print(f"📊 成功加载 {valid_pairs} 对有效文本对")
        print(f"   NatGeo句子数: {len(natgeo_sentences)}")
        print(f"   Wikipedia句子数: {len(wikipedia_sentences)}")

        return natgeo_sentences, wikipedia_sentences

    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
        return None, None
    except Exception as e:
        print(f"❌ 加载数据时出错: {e}")
        return None, None


def main():
    """主函数"""
    print("🔧 使用EASSE库计算FKGL分数...")

    # 检查EASSE是否可用
    if EASSE_AVAILABLE:
        print("✅ 使用EASSE FKGL库进行计算")
        fkgl_func = corpus_fkgl
        method_name = "EASSE_corpus_fkgl"
    else:
        print("✅ 使用简单FKGL计算实现")
        fkgl_func = simple_fkgl
        method_name = "Simple_FKGL"

    # 数据集路径
    dataset_path = 'datasets/our_dataset/natgeo_kids/natgeo_wikipedia_glm.json'

    # 加载数据
    natgeo_sentences, wiki_sentences = load_natgeo_dataset(dataset_path)

    if natgeo_sentences is None or wiki_sentences is None:
        print("❌ 数据加载失败")
        return

    if not natgeo_sentences or not wiki_sentences:
        print("❌ 没有有效的数据可以分析")
        return

    print(f"📈 开始计算FKGL分数...")

    try:
        # 计算FKGL分数
        print("🔍 计算NatGeo文章的FKGL分数...")
        if EASSE_AVAILABLE:
            natgeo_fkgl = fkgl_func(
                sentences=natgeo_sentences,
                tokenizer='13a'
            )
        else:
            natgeo_fkgl = fkgl_func(natgeo_sentences)

        print("🔍 计算Wikipedia内容的FKGL分数...")
        if EASSE_AVAILABLE:
            wiki_fkgl = fkgl_func(
                sentences=wiki_sentences,
                tokenizer='13a'
            )
        else:
            wiki_fkgl = fkgl_func(wiki_sentences)

        # 计算总体的FKGL分数
        all_sentences = natgeo_sentences + wiki_sentences
        if EASSE_AVAILABLE:
            overall_fkgl = fkgl_func(
                sentences=all_sentences,
                tokenizer='13a'
            )
        else:
            overall_fkgl = fkgl_func(all_sentences)

        print(f"\n🎯 FKGL分析结果:")
        print(f"   NatGeo句子数: {len(natgeo_sentences)}")
        print(f"   Wikipedia句子数: {len(wiki_sentences)}")
        print(f"   总句子数: {len(all_sentences)}")
        print(f"")
        print(f"   NatGeo FKGL分数: {natgeo_fkgl:.4f}")
        print(f"   Wikipedia FKGL分数: {wiki_fkgl:.4f}")
        print(f"   总体FKGL分数: {overall_fkgl:.4f}")
        print(f"   平均FKGL分数: {(natgeo_fkgl + wiki_fkgl) / 2:.4f}")

        # FKGL解释
        print(f"\n📖 FKGL分数解释:")
        print(f"   1-8分: 小学水平")
        print(f"   9-12分: 中学水平")
        print(f"   13-16分: 高中水平")
        print(f"   17+分: 大学及以上水平")

        # 根据分数给出评估
        print(f"\n📝 可读性评估:")
        if natgeo_fkgl <= 8:
            print(f"   NatGeo Kids文章: ✅ 适合儿童阅读 (小学水平)")
        elif natgeo_fkgl <= 12:
            print(f"   NatGeo Kids文章: ⚠️  需要一定的阅读能力 (中学水平)")
        else:
            print(f"   NatGeo Kids文章: ❌ 对儿童来说过于复杂 (高中以上水平)")

        if wiki_fkgl <= 12:
            print(f"   Wikipedia内容: ✅ 相对易读 (中学及以下水平)")
        elif wiki_fkgl <= 16:
            print(f"   Wikipedia内容: ⚠️  需要较好的阅读能力 (高中水平)")
        else:
            print(f"   Wikipedia内容: ❌ 比较复杂 (大学及以上水平)")

        # 简化程度分析
        fkgl_difference = abs(natgeo_fkgl - wiki_fkgl)
        print(f"\n📊 简化程度分析:")
        print(f"   FKGL差异: {fkgl_difference:.4f}")
        if fkgl_difference < 2:
            print(f"   ✅ 两种文本的可读性相近")
        elif fkgl_difference < 5:
            print(f"   ⚠️  两种文本的可读性有中等差异")
        else:
            print(f"   ❌ 两种文本的可读性差异较大")

        # 保存结果
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

        print(f"\n💾 详细结果已保存到: easse_fkgl_results.json")

    except Exception as e:
        print(f"❌ 计算FKGL分数时出错: {e}")
        import traceback
        traceback.print_exc()


def get_readability_level(fkgl_score):
    """根据FKGL分数获取可读性等级"""
    if fkgl_score <= 8:
        return "小学水平 (Elementary)"
    elif fkgl_score <= 12:
        return "中学水平 (Middle School)"
    elif fkgl_score <= 16:
        return "高中水平 (High School)"
    else:
        return "大学及以上水平 (College)"


def get_simplification_assessment(difference):
    """根据FKGL差异评估简化程度"""
    if difference < 2:
        return "可读性相近 (Similar Readability)"
    elif difference < 5:
        return "中等简化程度 (Moderate Simplification)"
    else:
        return "显著简化程度 (Significant Simplification)"


if __name__ == "__main__":
    main()