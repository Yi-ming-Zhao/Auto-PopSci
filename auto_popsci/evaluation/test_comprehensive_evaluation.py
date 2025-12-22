#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试综合评估接口
"""

import asyncio
import json
import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from auto_popsci.evaluation.comprehensive_evaluation import ComprehensiveEvaluator
from auto_popsci.args import parse_args


async def test_single_document():
    """测试单个文档评估"""
    print("测试单个文档评估...")
    
    popsci_text = """
    The sun is like a giant ball of fire in the sky! It gives us light and warmth every day.
    Scientists have discovered that the sun is actually a star, just like the ones we see at night.
    """
    
    original_text = """
    The Sun is the star at the center of the Solar System. It is a nearly perfect sphere of hot plasma,
    heated to incandescence by nuclear fusion reactions in its core.
    """
    
    try:
        args = parse_args()
        evaluator = ComprehensiveEvaluator(args=args)
        
        result = await evaluator.evaluate_single_document(
            popsci_text=popsci_text,
            original_text=original_text,
            include_keyfacts=False
        )
        
        print("✅ 单个文档评估成功")
        print(f"连贯性 (PPL): {result['coherence']['ppl_score']:.2f}")
        print(f"简洁性 (SARI): {result['simplicity']['sari_score']:.4f}")
        print(f"生动性: {result['vividness'].get('vividness_score', 0.0):.4f}")
        
        return True
    except Exception as e:
        print(f"❌ 单个文档评估失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_document_pair():
    """测试文档对评估"""
    print("\n测试文档对评估...")
    
    popsci_text_1 = "The sun is like a giant ball of fire!"
    popsci_text_2 = "The Sun is a star that provides light and heat."
    original_text = "The Sun is the star at the center of the Solar System."
    
    try:
        args = parse_args()
        evaluator = ComprehensiveEvaluator(args=args)
        
        result = await evaluator.evaluate_document_pair(
            popsci_text_1=popsci_text_1,
            popsci_text_2=popsci_text_2,
            original_text=original_text
        )
        
        print("✅ 文档对评估成功")
        print(f"文档1 连贯性: {result['text_1']['coherence']['ppl_score']:.2f}")
        print(f"文档2 连贯性: {result['text_2']['coherence']['ppl_score']:.2f}")
        print(f"更好的文档（连贯性）: {result['comparison']['coherence']['better']}")
        
        return True
    except Exception as e:
        print(f"❌ 文档对评估失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_dataset():
    """测试数据集评估"""
    print("\n测试数据集评估...")
    
    # 创建示例数据集
    sample_dataset = [
        {
            'id': 'test_doc_1',
            'title': 'Test Document 1',
            'popsci_text': 'The sun is like a giant ball of fire!',
            'original_text': 'The Sun is the star at the center of the Solar System.'
        },
        {
            'id': 'test_doc_2',
            'title': 'Test Document 2',
            'popsci_text': 'The moon is our closest neighbor in space!',
            'original_text': 'The Moon is Earth\'s only natural satellite.'
        }
    ]
    
    # 保存示例数据集
    dataset_path = os.path.join(project_root, 'output', 'test_dataset.json')
    os.makedirs(os.path.dirname(dataset_path), exist_ok=True)
    with open(dataset_path, 'w', encoding='utf-8') as f:
        json.dump(sample_dataset, f, indent=2, ensure_ascii=False)
    
    try:
        args = parse_args()
        evaluator = ComprehensiveEvaluator(args=args)
        
        output_path = os.path.join(project_root, 'output', 'test_evaluation_results.json')
        result = await evaluator.evaluate_dataset(
            dataset_path=dataset_path,
            output_path=output_path,
            dataset_format='json',
            popsci_field='popsci_text',
            original_field='original_text',
            include_keyfacts=False
        )
        
        print("✅ 数据集评估成功")
        print(f"评估了 {result['evaluated_documents']} 个文档")
        print(f"结果已保存到: {output_path}")
        
        if result['statistics']:
            print("\n统计信息:")
            if 'coherence' in result['statistics']:
                print(f"  平均连贯性 (PPL): {result['statistics']['coherence'].get('mean', 0):.2f}")
            if 'simplicity' in result['statistics']:
                print(f"  平均简洁性 (SARI): {result['statistics']['simplicity'].get('mean', 0):.4f}")
            if 'vividness' in result['statistics']:
                print(f"  平均生动性: {result['statistics']['vividness'].get('mean', 0):.4f}")
        
        return True
    except Exception as e:
        print(f"❌ 数据集评估失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("=" * 80)
    print("综合评估接口测试")
    print("=" * 80)
    
    results = []
    
    # 测试单个文档评估
    results.append(await test_single_document())
    
    # 测试文档对评估
    results.append(await test_document_pair())
    
    # 测试数据集评估
    results.append(await test_dataset())
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"通过: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败")


if __name__ == "__main__":
    asyncio.run(main())
