#!/usr/bin/env python3
"""
使用EASSE库计算NatGeo Kids数据集的SARI分数
"""

import json
import sys
import os

# 添加当前目录到Python路径，以便导入easse
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../easse'))

try:
    from easse.sari import corpus_sari
except ImportError:
    print("EASSE library not found. Please install it first: pip install easse")
    sys.exit(1)


def load_natgeo_dataset(file_path):
    """加载NatGeo Kids数据集"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("❌ JSON文件格式错误：预期是数组")
            return None, None, None

        orig_sents = []  # NatGeo文章内容作为原始句子
        sys_sents = []   # Wikipedia内容作为系统输出
        refs_sents = []  # 可以将NatGeo和Wikipedia互换作为参考

        valid_pairs = 0

        for item in data:
            natgeo_article = item.get('natgeo_article', {})
            wikipedia_content = item.get('wikipedia_content', '')

            if not natgeo_article or not wikipedia_content:
                continue

            natgeo_content = natgeo_article.get('content', '')

            if not natgeo_content:
                continue

            # 将长文本按句子分割，这里简单按句号分割
            # 实际应用中可能需要更复杂的句子分割
            natgeo_sentences = [s.strip() for s in natgeo_content.split('.') if s.strip()]
            wiki_sentences = [s.strip() for s in wikipedia_content.split('.') if s.strip()]

            # 取前几个句子作为样本，避免句子数量不匹配
            min_sentences = min(len(natgeo_sentences), len(wiki_sentences), 3)  # 最多取3句

            if min_sentences > 0:
                orig_sents.append('. '.join(natgeo_sentences[:min_sentences]))
                sys_sents.append('. '.join(wiki_sentences[:min_sentences]))
                refs_sents.append('. '.join(natgeo_sentences[:min_sentences]))  # 使用对应的NatGeo句子作为参考
                valid_pairs += 1

        print(f"📊 成功加载 {valid_pairs} 对有效句子对")
        return orig_sents, sys_sents, [refs_sents]

    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
        return None, None, None
    except Exception as e:
        print(f"❌ 加载数据时出错: {e}")
        return None, None, None


def main():
    """主函数"""
    print("🔧 使用EASSE库计算SARI分数...")

    # 检查EASSE是否可用
    try:
        from easse.sari import corpus_sari
        print("✅ EASSE库导入成功")
    except ImportError as e:
        print(f"❌ 无法导入EASSE库: {e}")
        print("请确保EASSE库已正确安装")
        return

    # 数据集路径
    dataset_path = 'datasets/our_dataset/natgeo_kids/natgeo_wikipedia_glm.json'

    # 加载数据
    orig_sents, sys_sents, refs_sents = load_natgeo_dataset(dataset_path)

    if orig_sents is None or sys_sents is None or refs_sents is None:
        print("❌ 数据加载失败")
        return

    if not orig_sents:
        print("❌ 没有有效的数据可以分析")
        return

    print(f"📈 开始计算SARI分数...")

    try:
        # 计算SARI分数
        # orig_sents: NatGeo Kids文章内容 (原始复杂文本)
        # sys_sents: Wikipedia内容 (简化文本)
        # refs_sents: 参考文本列表

        sari_score = corpus_sari(
            orig_sents=orig_sents,
            sys_sents=sys_sents,
            refs_sents=refs_sents,
            lowercase=True,
            tokenizer='13a',
            legacy=False,
            use_f1_for_deletion=True
        )

        print(f"\n🎯 SARI分析结果:")
        print(f"   分析的句子对数: {len(orig_sents)}")
        print(f"   平均SARI分数: {sari_score:.4f}")

        # 分别计算 NatGeo→Wikipedia 和 Wikipedia→NatGeo
        print(f"\n📊 计算双向SARI分数...")

        # NatGeo → Wikipedia (NatGeo作为原始，Wiki作为系统输出)
        sari_natgeo_to_wiki = corpus_sari(
            orig_sents=orig_sents,
            sys_sents=sys_sents,
            refs_sents=refs_sents,
            lowercase=True,
            tokenizer='13a'
        )

        # 为了简化，只计算主要方向的SARI分数
        print(f"   NatGeo → Wikipedia SARI: {sari_natgeo_to_wiki:.4f}")
        print(f"   总体SARI分数: {sari_score:.4f}")

        # 保存结果
        results = {
            'total_pairs': len(orig_sents),
            'sari_score': sari_score,
            'natgeo_to_wikipedia_sari': sari_natgeo_to_wiki,
            'method': 'EASSE_corpus_sari',
            'note': '主要计算NatGeo到Wikipedia的文本简化质量'
        }

        with open('easse_sari_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 结果已保存到: easse_sari_results.json")

    except Exception as e:
        print(f"❌ 计算SARI分数时出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()