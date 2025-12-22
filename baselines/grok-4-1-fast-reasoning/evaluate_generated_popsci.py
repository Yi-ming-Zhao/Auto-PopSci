#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估生成的科普文章质量
使用 comprehensive_evaluation 接口进行综合评估
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from auto_popsci.evaluation.comprehensive_evaluation import ComprehensiveEvaluator
from auto_popsci.args import parse_args

# 输入和输出文件路径
INPUT_FILE = "/home/zym/Auto-Popsci/baselines/grok-4-1-fast-reasoning/output/generated_popsci_articles.json"
OUTPUT_DIR = "/home/zym/Auto-Popsci/baselines/grok-4-1-fast-reasoning/output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "evaluation_results.json")

# Keyfacts 文件目录（可选，如果不需要评估 keyfacts，可以设置为 None）
# 如果设置为 None，将跳过 keyfacts 评估
GROUND_TRUTH_KEYFACTS_DIR = None  # 例如: "auto_popsci/evaluation/output/dev_5/R1_ground_truth/with_priority/reference_keyfacts/"
GENERATED_KEYFACTS_DIR = None  # 例如: "auto_popsci/evaluation/output/dev_5/scinews_keyfacts/with_priority/reference_keyfacts/"

async def main():
    """主函数"""
    print("=" * 80)
    print("开始评估生成的科普文章质量")
    print("=" * 80)
    
    # 检查输入文件是否存在
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 错误: 输入文件 {INPUT_FILE} 不存在")
        return
    
    # 读取数据以检查格式
    print(f"\n📖 读取数据文件: {INPUT_FILE}")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data_list = json.load(f)
    
    print(f"✅ 成功加载 {len(data_list)} 条记录")
    
    # 检查第一条数据的结构
    if len(data_list) > 0:
        first_item = data_list[0]
        print("\n📋 数据结构检查:")
        print(f"  - original_data 存在: {'original_data' in first_item}")
        if 'original_data' in first_item:
            orig = first_item['original_data']
            print(f"  - original_data.wikipedia_article 存在: {'wikipedia_article' in orig.get('original_data', {})}")
            print(f"  - original_data.popsci_article 存在: {'popsci_article' in orig.get('original_data', {})}")
        
        # 检查模型字段
        model_fields = [k for k in first_item.keys() if k not in ['original_data', 'source_wikipedia', 'analysis']]
        print(f"  - 模型字段: {model_fields}")
        if model_fields:
            model_name = model_fields[0]
            print(f"  - 使用模型字段: {model_name}")
            if model_name in first_item:
                model_data = first_item[model_name]
                print(f"  - 模型数据包含 title: {'title' in model_data}")
                print(f"  - 模型数据包含 content: {'content' in model_data}")
    
    # 初始化评估器
    print("\n🔧 初始化评估器...")
    args = parse_args()
    
    # 配置 keyfacts 评估所需的 prompt template
    args.prompt_template = "keyfact_alignment"  # 用于 keyfacts 评估的 prompt template
    
    # 启用连贯性评估
    skip_coherence = False
    
    evaluator = ComprehensiveEvaluator(args=args, skip_coherence=skip_coherence)
    
    # 确定模型字段名
    if len(data_list) > 0:
        model_fields = [k for k in data_list[0].keys() if k not in ['original_data', 'source_wikipedia', 'analysis']]
        model_name = model_fields[0] if model_fields else "grok-4-1-fast-reasoning"
    else:
        model_name = "grok-4-1-fast-reasoning"
    
    print(f"📝 使用模型字段: {model_name}")
    
    # 构建字段路径
    popsci_field = f"{model_name}.content"  # 生成的科普文章内容
    original_field = "original_data.original_data.wikipedia_article.content"  # Wikipedia原文
    reference_field = "original_data.original_data.popsci_article.content"  # 参考科普文章（可选）
    
    print(f"\n📊 字段配置:")
    print(f"  - popsci_field: {popsci_field}")
    print(f"  - original_field: {original_field}")
    print(f"  - reference_field: {reference_field}")
    
    # Keyfacts 配置
    # 如果启用了自动生成 keyfacts，即使没有配置文件目录，也应该启用评估
    AUTO_GENERATE_KEYFACTS = True  # 启用自动生成 keyfacts
    
    # 检查是否从文件目录加载 keyfacts
    has_keyfacts_files = GROUND_TRUTH_KEYFACTS_DIR is not None and GENERATED_KEYFACTS_DIR is not None
    
    if has_keyfacts_files:
        print(f"\n🔑 Keyfacts 配置:")
        print(f"  - ground_truth_keyfacts_dir: {GROUND_TRUTH_KEYFACTS_DIR}")
        print(f"  - generated_keyfacts_dir: {GENERATED_KEYFACTS_DIR}")
        # 检查目录是否存在
        if not os.path.exists(GROUND_TRUTH_KEYFACTS_DIR):
            print(f"  ⚠️ 警告: ground_truth_keyfacts_dir 不存在，将使用自动生成")
            has_keyfacts_files = False
        if not os.path.exists(GENERATED_KEYFACTS_DIR):
            print(f"  ⚠️ 警告: generated_keyfacts_dir 不存在，将使用自动生成")
            has_keyfacts_files = False
    
    # 如果启用了自动生成，则启用 keyfacts 评估
    include_keyfacts = has_keyfacts_files or AUTO_GENERATE_KEYFACTS
    
    if AUTO_GENERATE_KEYFACTS:
        print(f"\n🔑 Keyfacts 配置: 启用自动生成 keyfacts")
        print(f"  - Wikipedia keyfacts: 使用 grok（从 original_text 生成）")
        print(f"  - 科普 keyfacts: 使用 grok（从 popsci_text 生成）")
        print(f"  - 并发数: 500")
    elif not include_keyfacts:
        print(f"\n🔑 Keyfacts 配置: 未配置，将跳过 keyfacts 评估")
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 执行评估
    print("\n" + "=" * 80)
    print("开始评估...")
    print("=" * 80)
    
    try:
        result = await evaluator.evaluate_dataset(
            dataset_path=INPUT_FILE,
            output_path=OUTPUT_FILE,
            dataset_format='json',
            popsci_field=popsci_field,
            original_field=original_field,
            reference_field=reference_field,  # 使用参考文章进行对比
            ground_truth_keyfacts_dir=GROUND_TRUTH_KEYFACTS_DIR if has_keyfacts_files else None,
            generated_keyfacts_dir=GENERATED_KEYFACTS_DIR if has_keyfacts_files else None,
            include_keyfacts=include_keyfacts,
            auto_generate_keyfacts=AUTO_GENERATE_KEYFACTS  # 启用自动生成 keyfacts
        )
        
        print("\n" + "=" * 80)
        print("✅ 评估完成！")
        print("=" * 80)
        print(f"\n📁 结果已保存到: {OUTPUT_FILE}")
        print(f"\n📈 评估统计:")
        print(f"  - 总文档数: {result.get('total_documents', 0)}")
        print(f"  - 已评估文档数: {result.get('evaluated_documents', 0)}")
        
        if 'statistics' in result:
            stats = result['statistics']
            print(f"\n📊 详细统计:")
            
            if 'coherence' in stats:
                coh = stats['coherence']
                print(f"  - 连贯性 (PPL):")
                mean_val = coh.get('mean', None)
                min_val = coh.get('min', None)
                max_val = coh.get('max', None)
                print(f"    * 平均值: {mean_val:.2f}" if mean_val is not None else "    * 平均值: N/A")
                print(f"    * 最小值: {min_val:.2f}" if min_val is not None else "    * 最小值: N/A")
                print(f"    * 最大值: {max_val:.2f}" if max_val is not None else "    * 最大值: N/A")
            
            if 'simplicity' in stats:
                sim = stats['simplicity']
                print(f"  - 简洁性 (FKGL):")
                mean_val = sim.get('mean', None)
                min_val = sim.get('min', None)
                max_val = sim.get('max', None)
                print(f"    * 平均值: {mean_val:.4f}" if mean_val is not None else "    * 平均值: N/A")
                print(f"    * 最小值: {min_val:.4f}" if min_val is not None else "    * 最小值: N/A")
                print(f"    * 最大值: {max_val:.4f}" if max_val is not None else "    * 最大值: N/A")
            
            if 'vividness' in stats:
                viv = stats['vividness']
                print(f"  - 生动性 (总体):")
                mean_val = viv.get('mean', None)
                min_val = viv.get('min', None)
                max_val = viv.get('max', None)
                print(f"    * 平均值: {mean_val:.4f}" if mean_val is not None else "    * 平均值: N/A")
                print(f"    * 最小值: {min_val:.4f}" if min_val is not None else "    * 最小值: N/A")
                print(f"    * 最大值: {max_val:.4f}" if max_val is not None else "    * 最大值: N/A")
            
            if 'figurativeness' in stats:
                fig = stats['figurativeness']
                print(f"  - 比喻性 (Figurativeness):")
                mean_val = fig.get('mean', None)
                min_val = fig.get('min', None)
                max_val = fig.get('max', None)
                print(f"    * 平均值: {mean_val:.4f}" if mean_val is not None else "    * 平均值: N/A")
                print(f"    * 最小值: {min_val:.4f}" if min_val is not None else "    * 最小值: N/A")
                print(f"    * 最大值: {max_val:.4f}" if max_val is not None else "    * 最大值: N/A")
            
            if 'emotionality' in stats:
                emo = stats['emotionality']
                print(f"  - 情感性 (Emotionality):")
                mean_val = emo.get('mean', None)
                min_val = emo.get('min', None)
                max_val = emo.get('max', None)
                print(f"    * 平均值: {mean_val:.4f}" if mean_val is not None else "    * 平均值: N/A")
                print(f"    * 最小值: {min_val:.4f}" if min_val is not None else "    * 最小值: N/A")
                print(f"    * 最大值: {max_val:.4f}" if max_val is not None else "    * 最大值: N/A")
            
            if 'decorativeness' in stats:
                dec = stats['decorativeness']
                print(f"  - 装饰性 (Decorativeness):")
                mean_val = dec.get('mean', None)
                min_val = dec.get('min', None)
                max_val = dec.get('max', None)
                print(f"    * 平均值: {mean_val:.4f}" if mean_val is not None else "    * 平均值: N/A")
                print(f"    * 最小值: {min_val:.4f}" if min_val is not None else "    * 最小值: N/A")
                print(f"    * 最大值: {max_val:.4f}" if max_val is not None else "    * 最大值: N/A")
            
            # Keyfacts 评估统计
            if 'keyfacts_precision' in stats:
                kf_prec = stats['keyfacts_precision']
                if kf_prec:  # 如果字典不为空
                    print(f"\n  - 关键事实精确率 (Keyfacts Precision):")
                    mean_val = kf_prec.get('mean', None)
                    min_val = kf_prec.get('min', None)
                    max_val = kf_prec.get('max', None)
                    count = kf_prec.get('count', 0)
                    print(f"    * 平均值: {mean_val:.4f}" if mean_val is not None else "    * 平均值: N/A")
                    print(f"    * 最小值: {min_val:.4f}" if min_val is not None else "    * 最小值: N/A")
                    print(f"    * 最大值: {max_val:.4f}" if max_val is not None else "    * 最大值: N/A")
                    print(f"    * 有效样本数: {count}")
            
            if 'keyfacts_recall' in stats:
                kf_rec = stats['keyfacts_recall']
                if kf_rec:  # 如果字典不为空
                    print(f"\n  - 关键事实召回率 (Keyfacts Recall):")
                    mean_val = kf_rec.get('mean', None)
                    min_val = kf_rec.get('min', None)
                    max_val = kf_rec.get('max', None)
                    count = kf_rec.get('count', 0)
                    print(f"    * 平均值: {mean_val:.4f}" if mean_val is not None else "    * 平均值: N/A")
                    print(f"    * 最小值: {min_val:.4f}" if min_val is not None else "    * 最小值: N/A")
                    print(f"    * 最大值: {max_val:.4f}" if max_val is not None else "    * 最大值: N/A")
                    print(f"    * 有效样本数: {count}")
            
            # 按优先级的统计信息
            if 'keyfacts_precision_by_priority' in stats:
                kf_prec_pri = stats['keyfacts_precision_by_priority']
                if kf_prec_pri:
                    print(f"\n  - 关键事实精确率 (按优先级):")
                    for priority in ['priority_1', 'priority_2', 'priority_3']:
                        if priority in kf_prec_pri and kf_prec_pri[priority]:
                            pri_stats = kf_prec_pri[priority]
                            mean_val = pri_stats.get('mean', None)
                            count = pri_stats.get('count', 0)
                            print(f"    * {priority}: 平均值={mean_val:.4f}, 样本数={count}" if mean_val is not None else f"    * {priority}: N/A")
            
            if 'keyfacts_recall_by_priority' in stats:
                kf_rec_pri = stats['keyfacts_recall_by_priority']
                if kf_rec_pri:
                    print(f"\n  - 关键事实召回率 (按优先级):")
                    for priority in ['priority_1', 'priority_2', 'priority_3']:
                        if priority in kf_rec_pri and kf_rec_pri[priority]:
                            pri_stats = kf_rec_pri[priority]
                            mean_val = pri_stats.get('mean', None)
                            count = pri_stats.get('count', 0)
                            print(f"    * {priority}: 平均值={mean_val:.4f}, 样本数={count}" if mean_val is not None else f"    * {priority}: N/A")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ 评估过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    asyncio.run(main())

