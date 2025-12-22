#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：只处理一篇文章进行生成测试
"""

import json
import openai
import time
from typing import Dict, Any
import os
import yaml
import re

# 配置文件路径
API_CONFIG_FILE = "/home/zym/Auto-Popsci/auth.yaml"
# 输入和输出文件路径
INPUT_FILE = "/home/zym/Auto-Popsci/datasets/our_dataset/analyzed_articles_score_10_test.json"
OUTPUT_DIR = "/home/zym/Auto-Popsci/baselines/grok-4-1-fast-reasoning/output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "test_single_article.json")

def load_api_config() -> Dict[str, str]:
    """加载 API 配置"""
    with open(API_CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config['grok']

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

def generate_popsci_from_article(data: Dict[str, Any]) -> Dict[str, Any]:
    """基于Wikipedia文章生成科普文章"""
    
    original_data = data.get("original_data", {})
    wiki_article = original_data.get("wikipedia_article", {})
    
    wiki_title = wiki_article.get("title", "")
    wiki_content = wiki_article.get("content", "")
    
    print(f"\n原文标题: {wiki_title}")
    print(f"原文长度: {len(wiki_content)} 字符")
    print(f"原文前200字符: {wiki_content[:200]}...")
    
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
    
    print("\n开始调用API生成...")
    start_time = time.time()
    
    # 调用API
    response = call_grok_api(prompt)
    
    elapsed_time = time.time() - start_time
    print(f"API调用完成，耗时: {elapsed_time:.2f} 秒")
    print(f"\nAPI响应前500字符: {response[:500]}...")
    
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
        print("\n✅ JSON解析成功")
    except json.JSONDecodeError as e:
        # 如果JSON解析失败，创建一个基本的响应
        print(f"\n⚠️ 警告: 无法解析JSON响应")
        print(f"错误信息: {str(e)}")
        print(f"原始响应: {response[:500]}...")
        generated_popsci = {
            "title": wiki_title + " - Generated",
            "content": response  # 使用原始响应作为内容
        }
    
    # 获取模型名称
    config = load_api_config()
    model_name = config['model']
    
    # 确保所有必需的键都存在
    if "title" not in generated_popsci:
        generated_popsci["title"] = wiki_title + " - Generated"
    if "content" not in generated_popsci:
        generated_popsci["content"] = response
    
    print(f"\n生成的文章标题: {generated_popsci.get('title', 'N/A')}")
    print(f"生成的文章内容长度: {len(generated_popsci.get('content', ''))} 字符")
    print(f"生成的文章内容前300字符: {generated_popsci.get('content', '')[:300]}...")
    
    return {
        "original_data": data,
        model_name: generated_popsci,  # 使用模型名称作为字段名
        "source_wikipedia": {
            "title": wiki_title,
            "content": wiki_content  # 保存完整内容
        }
    }

def main():
    """主函数"""
    print("=" * 80)
    print("测试脚本：单篇文章生成测试")
    print("=" * 80)
    
    # 检查输入文件是否存在
    if not os.path.exists(INPUT_FILE):
        print(f"错误: 输入文件 {INPUT_FILE} 不存在")
        return
    
    # 加载数据
    print(f"\n加载数据文件: {INPUT_FILE}")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data_list = json.load(f)
    
    print(f"总共有 {len(data_list)} 篇文章")
    
    # 只处理第一篇文章
    if len(data_list) == 0:
        print("错误: 数据文件为空")
        return
    
    test_data = data_list[0]
    print(f"\n选择第一篇文章进行测试:")
    original_data = test_data.get('original_data', {})
    wiki_title = original_data.get('wikipedia_article', {}).get('title', 'N/A')
    print(f"Wikipedia标题: {wiki_title}")
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 生成科普文章
    print("\n" + "=" * 80)
    result = generate_popsci_from_article(test_data)
    
    # 保存结果
    print("\n" + "=" * 80)
    print(f"保存结果到 {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 测试完成！结果已保存到: {OUTPUT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()

