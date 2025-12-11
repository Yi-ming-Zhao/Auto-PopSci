#!/usr/bin/env python3
"""
测试脚本：分析前几篇文章对的关联性
"""

import json
import openai
import time
from typing import Dict, Any
import os
import re

# API配置
API_KEY = "sk-F8sMUgSUkCgbd4eg43CaD6Ba99494dA4A776C5F8C05248F1"
BASE_URL = "https://api.ai-gaochao.cn/v1/"
MODEL_NAME = "grok-4-1-fast-reasoning"

# 输入和输出文件路径
INPUT_FILE = "/home/zym/Auto-Popsci/datasets/our_dataset/merged_popular_science_articles_with_wikipedia.json"
OUTPUT_FILE = "/home/zym/Auto-Popsci/datasets/our_dataset/test_analysis_results.json"

def truncate_text(text: str, max_length: int = 3000) -> str:
    """截断文本以适应API限制"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "...[内容已截断]"

def call_grok_api(prompt: str, max_retries: int = 3) -> str:
    """调用Grok API"""
    openai.api_key = API_KEY
    openai.base_url = BASE_URL
    
    for attempt in range(max_retries):
        try:
            response = openai.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的文本分析助手，能够准确地总结文章内容并分析文章间的关联性。请提供简洁、准确的分析结果。"
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"API调用异常: {str(e)}, 重试: {attempt+1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    return "API调用失败，无法获取分析结果"

def generate_summary_and_analyze_relevance(data: Dict[str, Any]) -> Dict[str, Any]:
    """为一对科普文章和Wikipedia文章生成摘要并分析关联性"""
    
    popsci_article = data.get("popsci_article", {})
    wiki_article = data.get("wikipedia_article", {})
    
    popsci_title = popsci_article.get("title", "")
    popsci_content = popsci_article.get("content", "")
    wiki_title = wiki_article.get("title", "")
    wiki_content = wiki_article.get("content", "")
    
    # 截断过长的内容
    popsci_content = truncate_text(popsci_content)
    wiki_content = truncate_text(wiki_content)
    
    # 构建提示词
    prompt = f"""
请分析以下科普文章和Wikipedia文章的关联性。

科普文章标题: {popsci_title}
科普文章内容: {popsci_content}

Wikipedia文章标题: {wiki_title}
Wikipedia文章内容: {wiki_content}

请提供以下分析（以JSON格式回复）:
1. 科普文章摘要: 用一句话概括科普文章的主要内容
2. Wikipedia文章摘要: 用一句话概括Wikipedia文章的主要内容
3. 内容关联性评分: 1-10分（1分表示无关联，10分表示高度相关）
4. 关联性分析: 解释科普文章介绍的内容是否出现在Wikipedia文章中，以及它们之间的关联程度
5. 关键共同点: 列出两篇文章共同讨论的2-3个关键概念或主题

请确保回复为有效的JSON格式。
"""
    
    # 调用API
    response = call_grok_api(prompt)
    print(f"API响应: {response[:200]}...")
    
    # 尝试解析JSON响应
    try:
        # 提取JSON部分（如果有额外的文本）
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            response_json = json.loads(json_match.group())
        else:
            # 如果没有找到JSON，尝试整个解析
            response_json = json.loads(response)
    except json.JSONDecodeError:
        # 如果JSON解析失败，创建一个基本的响应
        response_json = {
            "科普文章摘要": "无法生成摘要",
            "Wikipedia文章摘要": "无法生成摘要",
            "内容关联性评分": 0,
            "关联性分析": "无法分析关联性: " + response,
            "关键共同点": []
        }
    
    # 确保所有必需的键都存在
    for key in ["科普文章摘要", "Wikipedia文章摘要", "内容关联性评分", "关联性分析", "关键共同点"]:
        if key not in response_json:
            if key == "关键共同点":
                response_json[key] = []
            else:
                response_json[key] = "未提供"
    
    return {
        "original_data": data,
        "analysis": response_json
    }

def main():
    """主函数"""
    print("开始加载文章数据...")
    
    # 检查输入文件是否存在
    if not os.path.exists(INPUT_FILE):
        print(f"错误: 输入文件 {INPUT_FILE} 不存在")
        return
    
    # 加载数据
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data_list = json.load(f)
    
    print(f"成功加载 {len(data_list)} 条文章对")
    
    # 只处理前3个文章对作为测试
    test_count = min(3, len(data_list))
    results = []
    
    print(f"开始分析前 {test_count} 对文章的关联性...")
    start_time = time.time()
    
    for i in range(test_count):
        data = data_list[i]
        print(f"处理文章对 {i+1}/{test_count}: {data.get('popsci_article', {}).get('title', '未知标题')}")
        
        try:
            result = generate_summary_and_analyze_relevance(data)
            results.append(result)
            print(f"文章对 {i+1} 分析完成")
        except Exception as e:
            print(f"处理文章对 {i+1} 时出错: {str(e)}")
            error_result = {
                "original_data": data,
                "analysis": {
                    "科普文章摘要": "处理出错",
                    "Wikipedia文章摘要": "处理出错",
                    "内容关联性评分": 0,
                    "关联性分析": f"处理过程中出现错误: {str(e)}",
                    "关键共同点": []
                }
            }
            results.append(error_result)
    
    # 保存结果
    print(f"保存分析结果到 {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    total_time = time.time() - start_time
    print(f"分析完成! 总共处理 {len(results)} 条文章对，耗时 {total_time:.1f} 秒")
    
    # 打印一些统计信息
    scores = [r["analysis"]["内容关联性评分"] for r in results 
             if isinstance(r["analysis"]["内容关联性评分"], (int, float))]
    if scores:
        avg_score = sum(scores) / len(scores)
        high_score_count = sum(1 for s in scores if s >= 7)
        print(f"平均关联性评分: {avg_score:.2f}")
        print(f"高关联性(≥7分)文章对数量: {high_score_count}/{len(scores)} ({high_score_count/len(scores)*100:.1f}%)")

if __name__ == "__main__":
    main()
