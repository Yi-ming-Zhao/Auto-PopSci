#!/usr/bin/env python3
"""
计算NatGeo Kids数据集中所有文章的SARI平均值
"""

import json
import re
from collections import defaultdict

def calculate_sari(reference, simplified):
    """
    计算SARI (Simple Agreement Ratio)
    SARI = (重合的n-gram数) / (简化文本中的n-gram总数)

    参数:
    reference: 参考文本 (原始的复杂文本)
    simplified: 简化文本

    返回:
        SARI分数 (0-1之间)
    """
    # 清理文本
    def clean_text(text):
        # 移除特殊字符，保留字母、数字和基本标点
        text = re.sub(r'[^\w\s.,!?;:-]', '', text)
        return text.lower()

    # 生成n-gram (这里使用单词级别)
    def get_ngrams(text, n=2):
        words = text.split()
        ngrams = []
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i+n])
            ngrams.append(ngram)
        return ngrams

    ref_clean = clean_text(reference)
    simp_clean = clean_text(simplified)

    # 获取参考文本和简化文本的n-gram
    ref_ngrams = get_ngrams(ref_clean)
    simp_ngrams = get_ngrams(simp_clean)

    if len(simp_ngrams) == 0:
        return 0.0

    # 计算重合的n-gram数量
    overlap_count = 0
    for ngram in simp_ngrams:
        if ngram in ref_ngrams:
            overlap_count += 1

    # 计算SARI
    sari = overlap_count / len(simp_ngrams)
    return sari

def calculate_sari_for_text_pairs(text1, text2):
    """
    计算两个文本之间的双向SARI
    """
    return (calculate_sari(text1, text2) + calculate_sari(text2, text1)) / 2

def main():
    """主函数"""
    try:
        # 读取JSON文件
        with open('datasets/our_dataset/natgeo_kids/natgeo_wikipedia_glm.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("❌ JSON文件格式错误：预期是数组")
            return

        print(f"📊 开始分析 {len(data)} 条文章记录...")

        natgeo_sari_scores = []
        wikipedia_sari_scores = []
        sari_scores = []

        valid_pairs = 0

        for i, item in enumerate(data, 1):
            try:
                natgeo_article = item.get('natgeo_article', {})
                wikipedia_content = item.get('wikipedia_content', '')

                if not natgeo_article or not wikipedia_content:
                    print(f"⚠️  第{i}条记录缺少必要字段，跳过")
                    continue

                natgeo_content = natgeo_article.get('content', '')

                if not natgeo_content:
                    print(f"⚠️  第{i}条记录缺少NatGeo内容，跳过")
                    continue

                # 计算SARI分数
                sari_score = calculate_sari_for_text_pairs(
                    natgeo_content,
                    wikipedia_content
                )

                sari_scores.append(sari_score)
                valid_pairs += 1

                # 分别存储以便后续分析
                natgeo_sari = calculate_sari(wikipedia_content, natgeo_content)
                wikipedia_sari = calculate_sari(natgeo_content, wikipedia_content)

                natgeo_sari_scores.append(natgeo_sari)
                wikipedia_sari_scores.append(wikipedia_sari)

                print(f"✅ 第{i}条: SARI = {sari_score:.4f} "
                      f"(NatGeo→Wiki: {natgeo_sari:.4f}, "
                      f"Wiki→NatGeo: {wikipedia_sari:.4f})")

            except Exception as e:
                print(f"❌ 处理第{i}条记录时出错: {e}")
                continue

        if not sari_scores:
            print("❌ 没有有效的数据")
            return

        # 计算平均值
        avg_sari = sum(sari_scores) / len(sari_scores)
        avg_natgeo_sari = sum(natgeo_sari_scores) / len(natgeo_sari_scores)
        avg_wikipedia_sari = sum(wikipedia_sari_scores) / len(wikipedia_sari_scores)

        print(f"\n📈 SARI统计结果:")
        print(f"   有效分析的文章对数: {valid_pairs}")
        print(f"   双向SARI平均值: {avg_sari:.4f}")
        print(f"   NatGeo→Wikipedia SARI平均值: {avg_natgeo_sari:.4f}")
        print(f"   Wikipedia→NatGeo SARI平均值: {avg_wikipedia_sari:.4f}")

        # 按范围分组统计
        high_sari = sum(1 for score in sari_scores if score > 0.5)
        medium_sari = sum(1 for score in sari_scores if 0.2 <= score <= 0.5)
        low_sari = sum(1 for score in sari_scores if score < 0.2)

        print(f"\n📊 SARI分布:")
        print(f"   高相似度 (>0.5): {high_sari} 对 ({high_sari/len(sari_scores)*100:.1f}%)")
        print(f"   中等相似度 (0.2-0.5): {medium_sari} 对 ({medium_sari/len(sari_scores)*100:.1f}%)")
        print(f"   低相似度 (<0.2): {low_sari} 对 ({low_sari/len(sari_scores)*100:.1f}%)")

        # 保存详细结果
        results = {
            'total_pairs': valid_pairs,
            'average_sari': avg_sari,
            'average_natgeo_sari': avg_natgeo_sari,
            'average_wikipedia_sari': avg_wikipedia_sari,
            'distribution': {
                'high_similarity': high_sari,
                'medium_similarity': medium_sari,
                'low_similarity': low_sari
            },
            'individual_scores': sari_scores,
            'natgeo_to_wikipedia_scores': natgeo_sari_scores,
            'wikipedia_to_natgeo_scores': wikipedia_sari_scores
        }

        # 保存到JSON文件
        with open('sari_analysis_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 详细结果已保存到: sari_analysis_results.json")

        # 保存到CSV文件方便查看
        import csv
        with open('sari_scores.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Article_Index', 'SARI_Score', 'NatGeo_to_Wikipedia_SARI', 'Wikipedia_to_NatGeo_SARI'])

            for i, (sari, natgeo_sari, wiki_sari) in enumerate(zip(sari_scores, natgeo_sari_scores, wikipedia_sari_scores), 1):
                writer.writerow([i, f"{sari:.4f}", f"{natgeo_sari:.4f}", f"{wiki_sari:.4f}"])

        print(f"📊 SARI分数已保存到: sari_scores.csv")

    except FileNotFoundError:
        print("❌ 文件不存在: datasets/our_dataset/natgeo_kids/natgeo_wikipedia_glm.json")
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
    except Exception as e:
        print(f"❌ 处理数据时出错: {e}")

if __name__ == "__main__":
    main()