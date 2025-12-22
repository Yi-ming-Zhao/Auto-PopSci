#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合评估接口使用示例
"""

import asyncio
import json
import os
from comprehensive_evaluation import (
    ComprehensiveEvaluator,
    evaluate_single_document_async,
    evaluate_document_pair_async,
    evaluate_dataset_async
)
from ..args import parse_args


async def example_single_document():
    """示例：评估单个文档"""
    print("=" * 80)
    print("示例 1: 评估单个文档")
    print("=" * 80)
    
    # 示例文本
    popsci_text = """
    The sun is like a giant ball of fire in the sky! It gives us light and warmth every day.
    Scientists have discovered that the sun is actually a star, just like the ones we see at night.
    It's very, very far away from Earth, but it's so big and bright that we can see it clearly.
    """
    
    original_text = """
    The Sun is the star at the center of the Solar System. It is a nearly perfect sphere of hot plasma,
    heated to incandescence by nuclear fusion reactions in its core, radiating the energy mainly as visible light
    and infrared radiation. It is by far the most important source of energy for life on Earth.
    """
    
    # 初始化评估器
    args = parse_args()
    evaluator = ComprehensiveEvaluator(args=args)
    
    # 评估
    result = await evaluator.evaluate_single_document(
        popsci_text=popsci_text,
        original_text=original_text,
        include_keyfacts=False  # 暂时不评估关键事实
    )
    
    print("\n评估结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    return result


async def example_document_pair():
    """示例：评估文档对"""
    print("\n" + "=" * 80)
    print("示例 2: 评估文档对（比较两个科普文章）")
    print("=" * 80)
    
    popsci_text_1 = """
    The sun is like a giant ball of fire in the sky! It gives us light and warmth every day.
    """
    
    popsci_text_2 = """
    The Sun is a star that provides light and heat to our planet. It is located at the center
    of our solar system and is essential for life on Earth.
    """
    
    original_text = """
    The Sun is the star at the center of the Solar System. It is a nearly perfect sphere of hot plasma.
    """
    
    # 初始化评估器
    args = parse_args()
    evaluator = ComprehensiveEvaluator(args=args)
    
    # 评估文档对
    result = await evaluator.evaluate_document_pair(
        popsci_text_1=popsci_text_1,
        popsci_text_2=popsci_text_2,
        original_text=original_text
    )
    
    print("\n评估结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    return result


async def example_dataset():
    """
    示例：评估数据集（使用 analyzed_articles_score_10.json 格式）
    
    数据集格式说明：
    analyzed_articles_score_10.json 是一个包含文章对的列表，每个元素格式如下：
    {
        "popsci_article": {
            "title": "科普文章标题",
            "content": "科普文章内容（待评估的文本）"
        },
        "wikipedia_article": {
            "title": "Wikipedia文章标题",
            "content": "Wikipedia文章内容（作为原始复杂文本，用于简洁性评估）"
        },
        "analysis": {...},  # 可选：分析结果
        "score": 10  # 可选：评分
    }
    """
    print("\n" + "=" * 80)
    print("示例 3: 评估数据集（analyzed_articles_score_10.json 格式）")
    print("=" * 80)
    
    # 数据集路径（使用 analyzed_articles_score_10.json 格式）
    dataset_path = 'datasets/our_dataset/analyzed_articles_score_10.json'
    
    # 检查文件是否存在
    if not os.path.exists(dataset_path):
        print(f"⚠️ 数据集文件不存在: {dataset_path}")
        print("请确保文件存在或使用正确的路径")
        print("\n提示：如果文件是 Git LFS 文件，请先使用 git lfs pull 下载")
        return None
    
    # 初始化评估器
    args = parse_args()
    evaluator = ComprehensiveEvaluator(args=args)
    
    # 评估数据集
    # 注意：评估器现在支持嵌套字段（使用点号分隔，如 'popsci_article.content'）
    output_path = 'output/analyzed_articles_score_10_evaluation_results.json'
    result = await evaluator.evaluate_dataset(
        dataset_path=dataset_path,
        output_path=output_path,
        dataset_format='json',
        popsci_field='popsci_article.content',  # 嵌套字段：科普文章内容（待评估）
        original_field='wikipedia_article.content',  # 嵌套字段：Wikipedia 作为原始复杂文本（用于简洁性评估）
        reference_field=None,  # 可选：如果有参考文本字段
        include_keyfacts=False  # 暂时不评估关键事实
    )
    
    print(f"\n✅ 评估完成！结果已保存到: {output_path}")
    print(f"📊 评估了 {result['evaluated_documents']} 个文档（共 {result['total_documents']} 个）")
    print("\n📈 统计信息:")
    print(json.dumps(result['statistics'], indent=2, ensure_ascii=False))
    
    return result


async def main():
    """主函数"""
    try:
        # 示例 1: 单个文档评估
        await example_single_document()
        
        # 示例 2: 文档对评估
        await example_document_pair()
        
        # 示例 3: 数据集评估
        await example_dataset()
        
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
