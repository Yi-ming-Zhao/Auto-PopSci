#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用数据集评测脚本
可以评测任何格式的数据集，支持命令行参数配置
"""

import asyncio
import json
import os
import sys
import argparse
from pathlib import Path
from typing import Optional

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 延迟导入，避免在显示帮助信息时出错
# from auto_popsci.evaluation.comprehensive_evaluation import ComprehensiveEvaluator
# from auto_popsci.args import parse_args


def detect_model_name(data_list: list) -> Optional[str]:
    """
    自动检测数据中的模型名称
    排除已知的标准字段
    """
    if not data_list:
        return None
    
    standard_fields = ['original_data', 'source_wikipedia', 'analysis', 'wikipedia_article', 'popsci_article']
    
    first_item = data_list[0]
    model_fields = [k for k in first_item.keys() if k not in standard_fields]
    
    if model_fields:
        return model_fields[0]
    return None


def detect_field_paths(data_list: list, model_name: str) -> dict:
    """
    自动检测字段路径
    返回包含 popsci_field, original_field, reference_field 的字典
    """
    if not data_list:
        return {
            'popsci_field': None,
            'original_field': None,
            'reference_field': None
        }
    
    first_item = data_list[0]
    
    # 检测生成的科普文章字段
    popsci_field = None
    if model_name and model_name in first_item:
        model_data = first_item[model_name]
        if isinstance(model_data, dict):
            if 'content' in model_data:
                popsci_field = f"{model_name}.content"
            elif 'text' in model_data:
                popsci_field = f"{model_name}.text"
    
    # 检测Wikipedia原文字段
    original_field = None
    if 'original_data' in first_item:
        orig = first_item['original_data']
        if isinstance(orig, dict):
            # 尝试多种可能的路径
            if 'wikipedia_article' in orig:
                wiki = orig['wikipedia_article']
                if isinstance(wiki, dict) and 'content' in wiki:
                    original_field = "original_data.wikipedia_article.content"
            elif 'original_data' in orig:
                orig2 = orig['original_data']
                if isinstance(orig2, dict) and 'wikipedia_article' in orig2:
                    wiki = orig2['wikipedia_article']
                    if isinstance(wiki, dict) and 'content' in wiki:
                        original_field = "original_data.original_data.wikipedia_article.content"
    
    # 检测参考科普文章字段
    reference_field = None
    if 'original_data' in first_item:
        orig = first_item['original_data']
        if isinstance(orig, dict):
            if 'popsci_article' in orig:
                popsci = orig['popsci_article']
                if isinstance(popsci, dict) and 'content' in popsci:
                    reference_field = "original_data.popsci_article.content"
            elif 'original_data' in orig:
                orig2 = orig['original_data']
                if isinstance(orig2, dict) and 'popsci_article' in orig2:
                    popsci = orig2['popsci_article']
                    if isinstance(popsci, dict) and 'content' in popsci:
                        reference_field = "original_data.original_data.popsci_article.content"
    
    return {
        'popsci_field': popsci_field,
        'original_field': original_field,
        'reference_field': reference_field
    }


def parse_evaluation_args():
    """解析评测参数"""
    parser = argparse.ArgumentParser(
        description="通用数据集评测脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基本用法（自动检测模型名称和字段路径）
  python evaluate_dataset.py --input_file data.json --output_file results.json
  
  # 指定模型名称
  python evaluate_dataset.py --input_file data.json --output_file results.json --model_name grok-4-1-fast-reasoning
  
  # 指定字段路径
  python evaluate_dataset.py --input_file data.json --output_file results.json \\
    --popsci_field "grok-4-1-fast-reasoning.content" \\
    --original_field "original_data.wikipedia_article.content" \\
    --reference_field "original_data.popsci_article.content"
  
  # 跳过连贯性评估
  python evaluate_dataset.py --input_file data.json --output_file results.json --skip_coherence
  
  # 禁用自动生成keyfacts
  python evaluate_dataset.py --input_file data.json --output_file results.json --no_auto_generate_keyfacts
        """
    )
    
    # 必需参数
    parser.add_argument(
        '--input_file',
        type=str,
        required=True,
        help='输入数据文件路径（JSON格式）'
    )
    
    parser.add_argument(
        '--output_file',
        type=str,
        required=True,
        help='输出结果文件路径（JSON格式）'
    )
    
    # 可选参数
    parser.add_argument(
        '--model_name',
        type=str,
        default=None,
        help='模型名称（如果不指定，将自动检测）'
    )
    
    parser.add_argument(
        '--popsci_field',
        type=str,
        default=None,
        help='生成的科普文章字段路径（如果不指定，将自动检测）'
    )
    
    parser.add_argument(
        '--original_field',
        type=str,
        default=None,
        help='Wikipedia原文字段路径（如果不指定，将自动检测）'
    )
    
    parser.add_argument(
        '--reference_field',
        type=str,
        default=None,
        help='参考科普文章字段路径（可选，用于对比评估）'
    )
    
    parser.add_argument(
        '--skip_coherence',
        action='store_true',
        help='跳过连贯性评估（PPL）'
    )
    
    parser.add_argument(
        '--auto_generate_keyfacts',
        action='store_true',
        default=True,
        help='自动生成keyfacts进行评估（默认启用）'
    )
    
    parser.add_argument(
        '--no_auto_generate_keyfacts',
        dest='auto_generate_keyfacts',
        action='store_false',
        help='禁用自动生成keyfacts'
    )
    
    parser.add_argument(
        '--ground_truth_keyfacts_dir',
        type=str,
        default=None,
        help='参考keyfacts目录路径（如果提供，将使用文件中的keyfacts而不是自动生成）'
    )
    
    parser.add_argument(
        '--generated_keyfacts_dir',
        type=str,
        default=None,
        help='生成的keyfacts目录路径（如果提供，将使用文件中的keyfacts而不是自动生成）'
    )
    
    parser.add_argument(
        '--dataset_format',
        type=str,
        default='json',
        choices=['json', 'jsonl'],
        help='数据集格式（默认：json）'
    )
    
    parser.add_argument(
        '--llm_type',
        type=str,
        default='deepseek',
        help='LLM类型（用于keyfacts生成，默认：deepseek）'
    )
    
    parser.add_argument(
        '--prompt_template',
        type=str,
        default='keyfact_alignment',
        help='Prompt模板名称（用于keyfacts评估，默认：keyfact_alignment）'
    )
    
    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_evaluation_args()
    
    # 延迟导入，避免在显示帮助信息时出错
    from auto_popsci.evaluation.comprehensive_evaluation import ComprehensiveEvaluator
    from auto_popsci.args import parse_args
    
    print("=" * 80)
    print("通用数据集评测工具")
    print("=" * 80)
    
    # 检查输入文件
    if not os.path.exists(args.input_file):
        print(f"❌ 错误: 输入文件 {args.input_file} 不存在")
        return
    
    # 读取数据
    print(f"\n📖 读取数据文件: {args.input_file}")
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            if args.dataset_format == 'json':
                data_list = json.load(f)
                if not isinstance(data_list, list):
                    # 如果是单个对象，转换为列表
                    data_list = [data_list]
            else:  # jsonl
                data_list = []
                for line in f:
                    line = line.strip()
                    if line:
                        data_list.append(json.loads(line))
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"✅ 成功加载 {len(data_list)} 条记录")
    
    if len(data_list) == 0:
        print("❌ 错误: 数据文件为空")
        return
    
    # 检测或使用指定的模型名称
    model_name = args.model_name
    if not model_name:
        model_name = detect_model_name(data_list)
        if model_name:
            print(f"✅ 自动检测到模型名称: {model_name}")
        else:
            print("⚠️  警告: 无法自动检测模型名称，请使用 --model_name 参数指定")
            print("   数据字段:", list(data_list[0].keys()))
            return
    else:
        print(f"✅ 使用指定的模型名称: {model_name}")
    
    # 检测或使用指定的字段路径
    detected_fields = detect_field_paths(data_list, model_name)
    
    popsci_field = args.popsci_field or detected_fields['popsci_field']
    original_field = args.original_field or detected_fields['original_field']
    reference_field = args.reference_field or detected_fields['reference_field']
    
    print(f"\n📊 字段配置:")
    print(f"  - popsci_field: {popsci_field}")
    print(f"  - original_field: {original_field}")
    print(f"  - reference_field: {reference_field}")
    
    if not popsci_field:
        print("❌ 错误: 无法确定popsci_field，请使用 --popsci_field 参数指定")
        return
    
    if not original_field:
        print("❌ 错误: 无法确定original_field，请使用 --original_field 参数指定")
        return
    
    # Keyfacts配置
    has_keyfacts_files = (
        args.ground_truth_keyfacts_dir is not None and 
        args.generated_keyfacts_dir is not None and
        os.path.exists(args.ground_truth_keyfacts_dir) and
        os.path.exists(args.generated_keyfacts_dir)
    )
    
    include_keyfacts = has_keyfacts_files or args.auto_generate_keyfacts
    
    if has_keyfacts_files:
        print(f"\n🔑 Keyfacts 配置: 使用文件目录")
        print(f"  - ground_truth_keyfacts_dir: {args.ground_truth_keyfacts_dir}")
        print(f"  - generated_keyfacts_dir: {args.generated_keyfacts_dir}")
    elif args.auto_generate_keyfacts:
        print(f"\n🔑 Keyfacts 配置: 启用自动生成 keyfacts")
        print(f"  - Wikipedia keyfacts: 使用 {args.llm_type}（从 original_text 生成）")
        print(f"  - 科普 keyfacts: 使用 {args.llm_type}（从 popsci_text 生成）")
    else:
        print(f"\n🔑 Keyfacts 配置: 未启用，将跳过 keyfacts 评估")
    
    # 创建输出目录
    output_dir = os.path.dirname(args.output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # 初始化评估器
    print("\n🔧 初始化评估器...")
    eval_args = parse_args()
    eval_args.prompt_template = args.prompt_template
    eval_args.llm_type = args.llm_type
    
    evaluator = ComprehensiveEvaluator(
        args=eval_args,
        skip_coherence=args.skip_coherence
    )
    
    # 执行评估
    print("\n" + "=" * 80)
    print("开始评估...")
    print("=" * 80)
    
    try:
        result = await evaluator.evaluate_dataset(
            dataset_path=args.input_file,
            output_path=args.output_file,
            dataset_format=args.dataset_format,
            popsci_field=popsci_field,
            original_field=original_field,
            reference_field=reference_field,
            ground_truth_keyfacts_dir=args.ground_truth_keyfacts_dir if has_keyfacts_files else None,
            generated_keyfacts_dir=args.generated_keyfacts_dir if has_keyfacts_files else None,
            include_keyfacts=include_keyfacts,
            auto_generate_keyfacts=args.auto_generate_keyfacts
        )
        
        print("\n" + "=" * 80)
        print("✅ 评估完成！")
        print("=" * 80)
        print(f"\n📁 结果已保存到: {args.output_file}")
        print(f"\n📈 评估统计:")
        print(f"  - 总文档数: {result.get('total_documents', 0)}")
        print(f"  - 已评估文档数: {result.get('evaluated_documents', 0)}")
        
        if 'statistics' in result:
            stats = result['statistics']
            print(f"\n📊 详细统计:")
            
            # 连贯性
            if 'coherence' in stats:
                coh = stats['coherence']
                print(f"  - 连贯性 (PPL):")
                mean_val = coh.get('mean', None)
                min_val = coh.get('min', None)
                max_val = coh.get('max', None)
                if mean_val is not None:
                    print(f"    * 平均值: {mean_val:.2f}")
                    print(f"    * 最小值: {min_val:.2f}")
                    print(f"    * 最大值: {max_val:.2f}")
            
            # 简洁性
            if 'simplicity' in stats:
                sim = stats['simplicity']
                print(f"  - 简洁性 (FKGL):")
                mean_val = sim.get('mean', None)
                min_val = sim.get('min', None)
                max_val = sim.get('max', None)
                if mean_val is not None:
                    print(f"    * 平均值: {mean_val:.4f}")
                    print(f"    * 最小值: {min_val:.4f}")
                    print(f"    * 最大值: {max_val:.4f}")
            
            # 生动性
            if 'vividness' in stats:
                viv = stats['vividness']
                print(f"  - 生动性 (总体):")
                mean_val = viv.get('mean', None)
                min_val = viv.get('min', None)
                max_val = viv.get('max', None)
                if mean_val is not None:
                    print(f"    * 平均值: {mean_val:.4f}")
                    print(f"    * 最小值: {min_val:.4f}")
                    print(f"    * 最大值: {max_val:.4f}")
            
            # 比喻性
            if 'figurativeness' in stats:
                fig = stats['figurativeness']
                print(f"  - 比喻性 (Figurativeness):")
                mean_val = fig.get('mean', None)
                if mean_val is not None:
                    print(f"    * 平均值: {mean_val:.4f}")
            
            # 情感性
            if 'emotionality' in stats:
                emo = stats['emotionality']
                print(f"  - 情感性 (Emotionality):")
                mean_val = emo.get('mean', None)
                if mean_val is not None:
                    print(f"    * 平均值: {mean_val:.4f}")
            
            # 装饰性
            if 'decorativeness' in stats:
                dec = stats['decorativeness']
                print(f"  - 装饰性 (Decorativeness):")
                mean_val = dec.get('mean', None)
                if mean_val is not None:
                    print(f"    * 平均值: {mean_val:.4f}")
            
            # Keyfacts评估统计
            if 'keyfacts_precision' in stats:
                kf_prec = stats['keyfacts_precision']
                if kf_prec:
                    print(f"\n  - 关键事实精确率 (Keyfacts Precision):")
                    mean_val = kf_prec.get('mean', None)
                    count = kf_prec.get('count', 0)
                    if mean_val is not None:
                        print(f"    * 平均值: {mean_val:.4f}")
                        print(f"    * 有效样本数: {count}")
            
            if 'keyfacts_recall' in stats:
                kf_rec = stats['keyfacts_recall']
                if kf_rec:
                    print(f"\n  - 关键事实召回率 (Keyfacts Recall):")
                    mean_val = kf_rec.get('mean', None)
                    count = kf_rec.get('count', 0)
                    if mean_val is not None:
                        print(f"    * 平均值: {mean_val:.4f}")
                        print(f"    * 有效样本数: {count}")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ 评估过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    asyncio.run(main())

