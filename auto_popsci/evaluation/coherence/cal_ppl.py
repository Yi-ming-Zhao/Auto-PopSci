#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用cal_ppl函数计算NatGeo Kids数据集的困惑度(Perplexity)
"""

import json
import sys
import os

# 直接实现PPL计算，避免依赖问题模块
USE_IMPORTED_PPL = False
print("Using simple PPL implementation to avoid module dependencies")


# 全局变量缓存模型和分词器
_cached_model = None
_cached_tokenizer = None

def simple_cal_ppl(text):
    """
    简单的困惑度计算实现
    使用transformers库的GPT2模型
    使用全局缓存避免重复加载模型
    """
    global _cached_model, _cached_tokenizer
    
    try:
        from transformers import GPT2LMHeadModel, GPT2Tokenizer
        import torch

        # 如果模型未缓存，则加载
        if _cached_model is None or _cached_tokenizer is None:
            try:
                print("正在加载 GPT-2 模型...")
                # 首先尝试使用本地缓存（避免网络问题）
                try:
                    _cached_tokenizer = GPT2Tokenizer.from_pretrained("gpt2", local_files_only=True)
                    _cached_model = GPT2LMHeadModel.from_pretrained("gpt2", local_files_only=True)
                    print("✅ 从本地缓存加载 GPT-2 模型成功")
                except Exception as local_error:
                    # 如果本地缓存不存在，尝试下载（可能会因网络问题失败）
                    print(f"⚠️ 本地缓存加载失败，尝试下载: {local_error}")
                    _cached_tokenizer = GPT2Tokenizer.from_pretrained("gpt2", local_files_only=False)
                    _cached_model = GPT2LMHeadModel.from_pretrained("gpt2", local_files_only=False)
                    print("✅ 下载并加载 GPT-2 模型成功")
                
                _cached_model.eval()  # 设为评估模式
            except Exception as e:
                print(f"⚠️ GPT-2 模型加载失败: {e}")
                print("将跳过连贯性评估，使用默认困惑度值")
                # 设置标记，避免后续重复尝试
                _cached_model = "FAILED"
                _cached_tokenizer = "FAILED"
                return 1000.0  # 返回一个默认的高值
        
        # 如果之前加载失败，直接返回默认值
        if _cached_model == "FAILED" or _cached_tokenizer == "FAILED":
            return 1000.0

        # 使用缓存的模型和分词器
        inputs = _cached_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        input_ids = inputs.input_ids

        with torch.no_grad():
            outputs = _cached_model(input_ids, labels=input_ids)
            logits = outputs.logits

        # 计算每个token的预测概率
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = input_ids[..., 1:].contiguous()

        # 计算交叉熵损失
        loss = torch.nn.functional.cross_entropy(
            shift_logits.view(-1, shift_logits.size(-1)),
            shift_labels.view(-1),
            reduction="mean",
        )

        nll = loss
        ppl = torch.exp(nll).item()
        return ppl
    except Exception as e:
        print(f"⚠️ 困惑度计算失败: {e}")
        return 1000.0  # 返回一个默认的高值


def load_natgeo_dataset(file_path):
    """加载NatGeo Kids数据集"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("JSON file format error: expected array")
            return None, None

        natgeo_texts = []
        wikipedia_texts = []

        valid_pairs = 0

        for item in data:
            natgeo_article = item.get('natgeo_article', {})
            wikipedia_content = item.get('wikipedia_content', '')

            if not natgeo_article or not wikipedia_content:
                continue

            natgeo_content = natgeo_article.get('content', '')

            if not natgeo_content:
                continue

            natgeo_texts.append(natgeo_content)
            wikipedia_texts.append(wikipedia_content)
            valid_pairs += 1

        print(f"Successfully loaded {valid_pairs} valid text pairs")
        return natgeo_texts, wikipedia_texts

    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None, None
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None


def calculate_text_ppl(text_list, text_type, max_samples=20):
    """计算文本列表的困惑度，限制样本数量以加快处理速度"""
    if not text_list:
        return 0.0

    print(f"Starting to calculate perplexity for {text_type}...")

    # 限制样本数量以提高处理速度
    if len(text_list) > max_samples:
        text_list = text_list[:max_samples]
        print(f"   Limited to first {max_samples} samples for faster processing")

    ppl_scores = []
    valid_texts = 0

    for i, text in enumerate(text_list):
        if len(text.strip()) < 50:  # 跳过太短的文本
            continue

        try:
            # 计算每个文本的困惑度
            ppl = simple_cal_ppl(text)
            if ppl > 0 and ppl < 10000:  # 过滤异常值
                ppl_scores.append(ppl)
                valid_texts += 1
                if (i + 1) % 5 == 0:  # 每5个文本输出一次进度
                    print(f"   Processed {i+1}/{len(text_list)} texts, {valid_texts} valid")
        except Exception as e:
            print(f"Error calculating PPL for text {i+1}: {e}")
            continue

    if not ppl_scores:
        return 0.0

    avg_ppl = sum(ppl_scores) / len(ppl_scores)
    print(f"Completed PPL calculation for {valid_texts} valid texts")

    return avg_ppl, ppl_scores, valid_texts


def interpret_ppl_score(ppl_score):
    """解释困惑度分数"""
    if ppl_score < 50:
        return "Very Fluent"
    elif ppl_score < 100:
        return "Relatively Fluent"
    elif ppl_score < 200:
        return "Moderately Fluent"
    elif ppl_score < 500:
        return "Less Fluent"
    else:
        return "Very Disfluent"


def main():
    """主函数"""
    print("Calculating perplexity for NatGeo Kids dataset using cal_ppl function...")

    # 数据集路径 - 使用项目根目录的相对路径
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 从 auto_popsci/evaluation/coherence/ 回到项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    dataset_path = os.path.join(project_root, 'datasets', 'our_dataset', 'natgeo_kids', 'natgeo_wikipedia_glm.json')
    print(f"Looking for dataset at: {dataset_path}")

    # 加载数据
    natgeo_texts, wiki_texts = load_natgeo_dataset(dataset_path)

    if natgeo_texts is None or wiki_texts is None:
        print("Data loading failed")
        return

    if not natgeo_texts or not wiki_texts:
        print("No valid data to analyze")
        return

    print(f"Starting perplexity calculation...")
    print(f"   NatGeo articles: {len(natgeo_texts)}")
    print(f"   Wikipedia articles: {len(wiki_texts)}")

    try:
        # 计算NatGeo文章的困惑度
        print(f"\nCalculating perplexity for NatGeo articles...")
        natgeo_avg_ppl, natgeo_ppl_scores, natgeo_valid = calculate_text_ppl(
            natgeo_texts, "NatGeo articles", max_samples=15
        )

        print(f"\nCalculating perplexity for Wikipedia content...")
        wiki_avg_ppl, wiki_ppl_scores, wiki_valid = calculate_text_ppl(
            wiki_texts, "Wikipedia content", max_samples=15
        )

        # 计算总体困惑度
        all_texts = natgeo_texts + wiki_texts
        print(f"\nCalculating perplexity for overall text...")
        overall_avg_ppl, overall_ppl_scores, overall_valid = calculate_text_ppl(
            all_texts, "overall text", max_samples=25
        )

        print(f"\nPerplexity (PPL) Analysis Results:")
        print(f"   Valid NatGeo articles: {natgeo_valid}/{len(natgeo_texts)}")
        print(f"   Valid Wikipedia articles: {wiki_valid}/{len(wiki_texts)}")
        print(f"   Overall valid articles: {overall_valid}/{len(all_texts)}")
        print(f"")
        print(f"   NatGeo average PPL: {natgeo_avg_ppl:.2f}")
        print(f"   Wikipedia average PPL: {wiki_avg_ppl:.2f}")
        print(f"   Overall average PPL: {overall_avg_ppl:.2f}")

        # PPL解释
        print(f"\nPPL Score Interpretation:")
        print(f"   <50: Very fluent")
        print(f"   50-100: Relatively fluent")
        print(f"   100-200: Moderately fluent")
        print(f"   200-500: Less fluent")
        print(f"   >500: Very disfluent")

        # 根据分数给出评估
        print(f"\nFluency Assessment:")
        print(f"   NatGeo Kids articles: {interpret_ppl_score(natgeo_avg_ppl)} (PPL: {natgeo_avg_ppl:.2f})")
        print(f"   Wikipedia content: {interpret_ppl_score(wiki_avg_ppl)} (PPL: {wiki_avg_ppl:.2f})")
        print(f"   Overall text: {interpret_ppl_score(overall_avg_ppl)} (PPL: {overall_avg_ppl:.2f})")

        # 比较分析
        print(f"\nComparative Analysis:")
        if natgeo_avg_ppl < wiki_avg_ppl:
            ppl_diff = wiki_avg_ppl - natgeo_avg_ppl
            print(f"   NatGeo articles are more fluent than Wikipedia content (difference: {ppl_diff:.2f})")
        elif natgeo_avg_ppl > wiki_avg_ppl:
            ppl_diff = natgeo_avg_ppl - wiki_avg_ppl
            print(f"   NatGeo articles are less fluent than Wikipedia content (difference: {ppl_diff:.2f})")
        else:
            print(f"   NatGeo articles and Wikipedia content have similar fluency")

        # 计算统计信息
        def calculate_stats(scores):
            if not scores:
                return {"min": 0, "max": 0, "median": 0, "std": 0}
            scores_sorted = sorted(scores)
            import math
            mean = sum(scores) / len(scores)
            variance = sum((x - mean) ** 2 for x in scores) / len(scores)
            std = math.sqrt(variance)
            return {
                "min": min(scores),
                "max": max(scores),
                "median": scores_sorted[len(scores_sorted) // 2],
                "std": std
            }

        natgeo_stats = calculate_stats(natgeo_ppl_scores)
        wiki_stats = calculate_stats(wiki_ppl_scores)

        print(f"\nStatistical Information:")
        print(f"   NatGeo PPL: min={natgeo_stats['min']:.2f}, max={natgeo_stats['max']:.2f}, "
              f"median={natgeo_stats['median']:.2f}, std={natgeo_stats['std']:.2f}")
        print(f"   Wikipedia PPL: min={wiki_stats['min']:.2f}, max={wiki_stats['max']:.2f}, "
              f"median={wiki_stats['median']:.2f}, std={wiki_stats['std']:.2f}")

        # 保存结果
        results = {
            'total_natgeo_texts': len(natgeo_texts),
            'total_wikipedia_texts': len(wiki_texts),
            'valid_natgeo_texts': natgeo_valid,
            'valid_wikipedia_texts': wiki_valid,
            'overall_valid_texts': overall_valid,
            'natgeo_avg_ppl': natgeo_avg_ppl,
            'wikipedia_avg_ppl': wiki_avg_ppl,
            'overall_avg_ppl': overall_avg_ppl,
            'natgeo_stats': natgeo_stats,
            'wikipedia_stats': wiki_stats,
            'fluency_assessment': {
                'natgeo_fluency': interpret_ppl_score(natgeo_avg_ppl),
                'wikipedia_fluency': interpret_ppl_score(wiki_avg_ppl),
                'overall_fluency': interpret_ppl_score(overall_avg_ppl)
            },
            'ppl_difference': abs(natgeo_avg_ppl - wiki_avg_ppl),
            'method': 'GPT-2_Perplexity',
            'model': 'gpt2',
            'note': f'Limited to first 15-25 samples for faster processing'
        }

        # 保存详细分数
        results['natgeo_ppl_scores'] = natgeo_ppl_scores
        results['wikipedia_ppl_scores'] = wiki_ppl_scores
        results['overall_ppl_scores'] = overall_ppl_scores

        with open('ppl_analysis_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\nDetailed results saved to: ppl_analysis_results.json")

    except Exception as e:
        print(f"Error calculating perplexity: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()