#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 Grok-4-1-fast-reasoning 模型生成科普文章
基于 analyzed_articles_score_10.json 数据集中的 Wikipedia 文章生成科普文章
"""

import json
import openai
import concurrent.futures
import time
from typing import Dict, Any, Tuple, List
import os
import yaml
import re

# 配置文件路径
API_CONFIG_FILE = "/home/zym/Auto-Popsci/auth.yaml"
# 输入和输出文件路径
INPUT_FILE = "/home/zym/Auto-Popsci/datasets/our_dataset/analyzed_articles_score_10_test.json"
OUTPUT_DIR = "/home/zym/Auto-Popsci/baselines/grok-4-1-fast-reasoning/output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "generated_popsci_articles_test.json")

def load_api_config() -> Dict[str, str]:
    """加载 API 配置"""
    with open(API_CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config['grok']

def truncate_text(text: str, max_length: int = 8000) -> str:
    """截断文本以适应API限制"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "...[内容已截断]"

def call_grok_api(prompt: str, max_retries: int = 3) -> str:
    """调用Grok API生成科普文章"""
    config = load_api_config()
    openai.api_key = config['api_key']
    openai.base_url = config['base_url']
    model_name = config['model']
    
    for attempt in range(max_retries):
        try:
            response = openai.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in writing popular science articles for children aged 8-12. Your articles should be easy to understand, engaging, and avoid technical jargon and complex concepts."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"API调用异常: {str(e)}, 尝试: {attempt+1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    return "API调用失败，无法生成科普文章"

def generate_popsci_from_wikipedia(data: Dict[str, Any]) -> Dict[str, Any]:
    """基于Wikipedia文章生成科普文章"""
    
    original_data = data.get("original_data", {})
    wiki_article = original_data.get("wikipedia_article", {})
    
    wiki_title = wiki_article.get("title", "")
    wiki_content = wiki_article.get("content", "")
    
    # 不截断，使用全文
    # wiki_content = truncate_text(wiki_content)  # 移除截断
    
    # 构建提示词 - 使用英文
    prompt = f"""
You are an expert in writing popular science articles for children aged 8-12. Your task is to generate a popular science article based on the following Wikipedia article.

The article should:
1. Be easy to understand, avoiding technical jargon and complex concepts
2. Be vivid and interesting, using metaphors and personification
3. Be engaging and able to stimulate children's curiosity

Your output should be a dictionary in JSON format with the following keys:
- "title": article title
- "content": article content

Please ensure the output is valid JSON format, without ```json markers.

Wikipedia article title: {wiki_title}
Wikipedia article content: {wiki_content}
"""
    
    # 调用API
    response = call_grok_api(prompt)
    
    # 获取模型名称
    config = load_api_config()
    model_name = config['model']
    
    # 尝试解析JSON响应
    generated_popsci = None
    try:
        # 提取JSON部分（如果有额外的文本）
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            generated_popsci = json.loads(json_match.group())
        else:
            # 如果没有找到JSON，尝试整个解析
            generated_popsci = json.loads(response)
    except json.JSONDecodeError:
        # 如果JSON解析失败，创建一个基本的响应
        print(f"警告: 无法解析JSON响应，原始响应: {response[:200]}...")
        generated_popsci = {
            "title": wiki_title + " - Generated",
            "content": response  # 使用原始响应作为内容
        }
    
    # 确保所有必需的键都存在
    if "title" not in generated_popsci:
        generated_popsci["title"] = wiki_title + " - Generated"
    if "content" not in generated_popsci:
        generated_popsci["content"] = response
    
    return {
        "original_data": data,
        model_name: generated_popsci,  # 使用模型名称作为字段名
        "source_wikipedia": {
            "title": wiki_title,
            "content": wiki_content  # 保存完整内容
        }
    }

def process_article(data: Dict[str, Any], index: int, total: int) -> Tuple[int, Dict[str, Any]]:
    """处理单篇文章"""
    original_data = data.get("original_data", {})
    wiki_title = original_data.get("wikipedia_article", {}).get("title", "未知标题")
    print(f"处理文章 {index+1}/{total}: {wiki_title}")
    
    try:
        result = generate_popsci_from_wikipedia(data)
        return index, result
    except Exception as e:
        print(f"处理文章 {index+1} 时出错: {str(e)}")
        config = load_api_config()
        model_name = config['model']
        error_result = {
            "original_data": data,
            model_name: {
                "title": wiki_title + " - Generation Failed",
                "content": f"Generation failed: {str(e)}"
            },
            "source_wikipedia": {
                "title": wiki_title,
                "content": ""
            }
        }
        return index, error_result

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
    
    print(f"成功加载 {len(data_list)} 条文章记录")
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 使用线程池并发处理
    results = [None] * len(data_list)
    completed_count = 0
    
    print("开始生成科普文章...")
    start_time = time.time()
    
    # 使用高并发以提高处理速度
    max_workers = 500
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_index = {
            executor.submit(process_article, data, i, len(data_list)): i
            for i, data in enumerate(data_list)
        }
        
        # 处理完成的任务
        for future in concurrent.futures.as_completed(future_to_index):
            index, result = future.result()
            results[index] = result
            completed_count += 1
            
            elapsed = time.time() - start_time
            avg_time = elapsed / completed_count if completed_count > 0 else 0
            remaining = len(data_list) - completed_count
            eta = remaining * avg_time if avg_time > 0 else 0
            
            print(f"已完成 {completed_count}/{len(data_list)} ({completed_count/len(data_list)*100:.1f}%), "
                  f"预计剩余时间: {eta/60:.1f}分钟")
    
    # 确保所有结果都已处理（按原始顺序）
    config = load_api_config()
    model_name = config['model']
    for i, result in enumerate(results):
        if result is None:
            print(f"警告: 结果 {i} 未正确处理，使用占位符")
            results[i] = {
                "original_data": data_list[i],
                model_name: {
                    "title": "Generation Incomplete",
                    "content": "Generation Incomplete"
                },
                "source_wikipedia": {
                    "title": "",
                    "content": ""
                }
            }
    
    # 保存结果
    print(f"保存生成结果到 {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    total_time = time.time() - start_time
    print(f"生成完成! 总共处理 {len(results)} 篇文章，耗时 {total_time/60:.1f} 分钟")
    
    # 打印一些统计信息
    config = load_api_config()
    model_name = config['model']
    success_count = sum(1 for r in results 
                       if r.get(model_name, {}).get("content", "") 
                       and "Generation failed" not in r.get(model_name, {}).get("content", "")
                       and "生成失败" not in r.get(model_name, {}).get("content", "")
                       and "Generation Incomplete" not in r.get(model_name, {}).get("content", ""))
    print(f"成功生成文章数量: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")

if __name__ == "__main__":
    main()

