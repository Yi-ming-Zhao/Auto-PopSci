#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析科普文章和Wikipedia文章的关联性程序
使用deepseek-r1模型进行摘要和关联性分析
使用并发编程提高处理效率
"""

import json
import requests
import concurrent.futures
import time
import os
from typing import Dict, List, Tuple, Optional
import argparse


def call_deepseek_api(article_title: str, popsci_content: str, wiki_content: str) -> Tuple[str, str]:
    """
    调用deepseek-r1模型分析科普文章和Wikipedia文章的关联性
    
    Args:
        article_title: 文章标题
        popsci_content: 科普文章内容
        wiki_content: Wikipedia文章内容
    
    Returns:
        Tuple[str, str]: (popsci_summary, relevance_analysis)
    """
    # 构建第一个请求 - 为科普文章写摘要
    popsci_prompt = f"""请为以下科普文章写一个简洁的摘要，不超过200字：

标题：{article_title}

内容：
{popsci_content[:3000]}...

请直接返回摘要，不要添加其他解释。"""
    
    popsci_body = {
        "model": "deepseek-r1",
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的科学文章摘要助手，擅长提取关键信息并生成简洁的摘要。"
            },
            {
                "role": "user",
                "content": popsci_prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 200
    }
    
    # 构建第二个请求 - 分析关联性
    relevance_prompt = f"""请分析以下科普文章和Wikipedia文章之间的关联性：

科普文章：
标题：{article_title}
内容：
{popsci_content[:2000]}...

对应的Wikipedia文章：
标题：{wiki_content[:200]}...
内容：
{wiki_content[:2000]}...

请分析：
1. 科普文章介绍的主要内容是否在Wikipedia文章中有对应
2. 两篇文章的主题相关性如何（高/中/低）
3. 请给出简要的原因分析

请以以下格式返回结果：
关联性：[高/中/低]
原因分析：[简明扼要的分析]
"""
    
    relevance_body = {
        "model": "deepseek-r1",
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的文本分析助手，擅长分析不同文本之间的关联性和相关性。"
            },
            {
                "role": "user",
                "content": relevance_prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 300
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-dZgSCtrdDfFUny3NPwoXrAWU2Bq0cfSq9tUN005ZECsiOmKE"
    }
    
    url = "https://api.xianfeiglobal.com/v1/chat/completions"
    
    try:
        # 请求科普文章摘要
        popsci_response = requests.request("POST", url, json=popsci_body, headers=headers)
        if popsci_response.status_code == 200:
            popsci_summary = popsci_response.json().get("choices")[0].get("message").get("content").strip()
        else:
            popsci_summary = f"API请求失败，状态码: {popsci_response.status_code}"
            print(f"科普文章摘要请求失败: {popsci_response.status_code}, {popsci_response.text}")
        
        # 短暂休息，避免API频率限制
        time.sleep(1)
        
        # 请求关联性分析
        relevance_response = requests.request("POST", url, json=relevance_body, headers=headers)
        if relevance_response.status_code == 200:
            relevance_analysis = relevance_response.json().get("choices")[0].get("message").get("content").strip()
        else:
            relevance_analysis = f"API请求失败，状态码: {relevance_response.status_code}"
            print(f"关联性分析请求失败: {relevance_response.status_code}, {relevance_response.text}")
            
        return popsci_summary, relevance_analysis
        
    except Exception as e:
        error_msg = f"API调用异常: {str(e)}"
        print(error_msg)
        return error_msg, error_msg


def process_article_pair(article_data: Dict, index: int, total: int) -> Dict:
    """
    处理单个科普文章和Wikipedia文章对
    
    Args:
        article_data: 包含popsci_article和wikipedia_article的字典
        index: 当前处理的文章索引
        total: 总文章数量
    
    Returns:
        Dict: 包含处理结果的字典
    """
    popsci_title = article_data.get("popsci_article", {}).get("title", "无标题")
    popsci_content = article_data.get("popsci_article", {}).get("content", "")
    wiki_title = article_data.get("wikipedia_article", {}).get("title", "无标题")
    wiki_content = article_data.get("wikipedia_article", {}).get("content", "")
    source = article_data.get("source", "未知来源")
    
    print(f"处理文章 {index+1}/{total}: {popsci_title}")
    
    try:
        popsci_summary, relevance_analysis = call_deepseek_api(
            popsci_title, popsci_content, wiki_content
        )
        
        return {
            "index": index,
            "popsci_title": popsci_title,
            "wiki_title": wiki_title,
            "source": source,
            "popsci_summary": popsci_summary,
            "relevance_analysis": relevance_analysis
        }
    except Exception as e:
        error_msg = f"处理文章时出错: {str(e)}"
        print(error_msg)
        return {
            "index": index,
            "popsci_title": popsci_title,
            "wiki_title": wiki_title,
            "source": source,
            "error": error_msg
        }


def main():
    """
    主函数，加载JSON数据并处理文章对
    """
    parser = argparse.ArgumentParser(description='分析科普文章和Wikipedia文章的关联性')
    parser.add_argument('--input', default='datasets/our_dataset/merged_popular_science_articles_with_wikipedia.json',
                        help='输入JSON文件路径')
    parser.add_argument('--output', default='datasets/our_dataset/articles_analysis_results.json',
                        help='输出JSON文件路径')
    parser.add_argument('--limit', type=int, default=None,
                        help='处理文章数量限制，用于测试')
    parser.add_argument('--workers', type=int, default=3,
                        help='并发工作线程数量')
    
    args = parser.parse_args()
    
    # 加载JSON数据
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
        print(f"成功加载 {len(articles_data)} 条文章数据")
    except Exception as e:
        print(f"加载数据文件失败: {str(e)}")
        return
    
    # 如果指定了限制，则只处理部分文章
    if args.limit:
        articles_data = articles_data[:args.limit]
        print(f"限制处理数量为 {len(articles_data)} 条")
    
    # 使用线程池并发处理文章
    results = []
    total = len(articles_data)
    
    print(f"开始使用 {args.workers} 个并发工作线程处理文章...")
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        # 提交所有任务
        future_to_index = {
            executor.submit(process_article_pair, article, i, total): i 
            for i, article in enumerate(articles_data)
        }
        
        # 处理完成的任务
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result = future.result()
                results.append(result)
                print(f"完成文章 {index+1}/{total}")
            except Exception as e:
                print(f"处理文章 {index+1} 时出错: {str(e)}")
                # 添加错误记录
                if index < total:
                    article = articles_data[index]
                    error_result = {
                        "index": index,
                        "popsci_title": article.get("popsci_article", {}).get("title", "无标题"),
                        "wiki_title": article.get("wikipedia_article", {}).get("title", "无标题"),
                        "source": article.get("source", "未知来源"),
                        "error": str(e)
                    }
                    results.append(error_result)
    
    # 按原始索引排序结果
    results.sort(key=lambda x: x.get("index", 0))
    
    # 计算处理时间
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"处理完成，共 {len(results)} 条结果，耗时 {processing_time:.2f} 秒")
    
    # 保存结果
    try:
        # 创建输出目录（如果不存在）
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到 {args.output}")
    except Exception as e:
        print(f"保存结果失败: {str(e)}")
    
    # 输出统计信息
    successful = sum(1 for r in results if "error" not in r)
    errors = sum(1 for r in results if "error" in r)
    print(f"处理统计: 成功 {successful} 条，错误 {errors} 条")
    
    # 输出一些示例结果
    if successful > 0:
        print("\n示例结果:")
        for i, result in enumerate(results[:3]):
            if "error" not in result:
                print(f"\n文章 {i+1}:")
                print(f"标题: {result.get('popsci_title', '未知')}")
                print(f"摘要: {result.get('popsci_summary', '未知')}")
                print(f"关联性分析: {result.get('relevance_analysis', '未知')}")


if __name__ == "__main__":
    main()
