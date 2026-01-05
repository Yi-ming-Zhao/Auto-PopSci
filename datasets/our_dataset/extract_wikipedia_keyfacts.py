#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从wikids_final.json数据集中提取Wikipedia文章的keyfacts
并将结果保存回数据集的original_data.wikipedia_article字段下
"""

import asyncio
import json
import os
import sys
from typing import Dict, List, Optional
import time

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from auto_popsci.utils.utils import read_yaml_file
from auto_popsci.args import parse_args
from prompts.prompt_template import prompt
from openai import AsyncOpenAI


# 全局缓存auth配置，避免重复读取文件
_auth_config_cache = None

def get_auth_config():
    """获取auth配置（带缓存）"""
    global _auth_config_cache
    if _auth_config_cache is None:
        _auth_config_cache = read_yaml_file("auth.yaml")
    return _auth_config_cache


# 全局客户端缓存，避免重复创建
_client_cache = {}

def get_client(llm_type: str, auth_config: dict) -> AsyncOpenAI:
    """获取或创建AsyncOpenAI客户端（带缓存）"""
    if llm_type not in _client_cache:
        llm_config = auth_config.get(llm_type, {})
        if not llm_config:
            raise ValueError(f"auth.yaml中未找到 {llm_type} 配置")
        
        api_key = llm_config.get("api_key", "")
        base_url = llm_config.get("base_url", "")
        
        _client_cache[llm_type] = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
    return _client_cache[llm_type]


async def extract_keyfacts_for_wikipedia(
    content: str,
    title: str,
    args,
    llm_type: str = "gemini-3-pro-preview",
    auth_config: dict = None,
    client: AsyncOpenAI = None
) -> Optional[str]:
    """
    为Wikipedia内容提取keyfacts
    
    Args:
        content: Wikipedia文章内容
        title: 文章标题
        args: 参数对象
        llm_type: LLM类型，默认使用gemini-3-pro-preview
        auth_config: 认证配置（可选，如果不提供则从缓存读取）
        client: AsyncOpenAI客户端（可选，如果不提供则从缓存获取）
        
    Returns:
        keyfacts的JSON字符串，如果失败返回None
    """
    if not content or not content.strip():
        print(f"⚠️  跳过空内容: {title}")
        return None
    
    start_time = time.time()
    print(f"📝 提取keyfacts: {title}")
    
    try:
        # 使用传入的配置或从缓存读取
        if auth_config is None:
            auth_config = get_auth_config()
        
        # 使用传入的客户端或从缓存获取
        if client is None:
            client = get_client(llm_type, auth_config)
        
        # 使用gemini-3-pro-preview提取Wikipedia keyfacts
        llm_config = auth_config.get(llm_type, {})
        if not llm_config:
            print(f"❌ 错误: auth.yaml中未找到 {llm_type} 配置")
            return None
        
        model = llm_config.get("model", llm_type)
        
        # 使用带优先级的prompt template
        prompt_template_name = "key_fact_extraction_with_priority"
        prompt_text = prompt[prompt_template_name].format(paper=content)
        
        # 调用API
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt_text,
                }
            ],
        )
        
        if response and response.choices:
            result = response.choices[0].message.content
            end_time = time.time()
            print(f"✅ 成功提取keyfacts ({end_time - start_time:.2f}秒, 使用{llm_type}): {title}")
            return result
        else:
            print(f"❌ 未收到有效响应: {title}")
            return None
            
    except Exception as e:
        print(f"❌ 提取keyfacts失败: {title}, 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_json_in_chunks(file_path: str, chunk_size: int = 1000):
    """
    分块加载大型JSON文件
    
    Args:
        file_path: JSON文件路径
        chunk_size: 每次处理的记录数
        
    Yields:
        数据块（列表）
    """
    print(f"📂 加载JSON文件: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        data = [data]
    
    total = len(data)
    print(f"✅ 总共 {total} 条记录")
    
    # 分块处理
    for i in range(0, total, chunk_size):
        chunk = data[i:i + chunk_size]
        yield chunk, i, total


async def process_chunk(
    chunk: List[Dict],
    start_idx: int,
    args,
    max_concurrent: int = 300,
    auth_config: dict = None,
    client: AsyncOpenAI = None
) -> List[Dict]:
    """
    处理一个数据块，提取keyfacts
    
    Args:
        chunk: 数据块
        start_idx: 起始索引
        args: 参数对象
        max_concurrent: 最大并发数
        auth_config: 认证配置（可选，如果不提供则从缓存读取）
        client: AsyncOpenAI客户端（可选，如果不提供则从缓存获取）
        
    Returns:
        更新后的数据块
    """
    print(f"\n🔄 处理数据块 [{start_idx} - {start_idx + len(chunk) - 1}]")
    
    # 创建提取任务
    tasks = []
    for i, item in enumerate(chunk):
        original_data = item.get("original_data", {})
        wikipedia_article = original_data.get("wikipedia_article", {})
        
        content = wikipedia_article.get("content", "")
        title = wikipedia_article.get("title", f"item_{start_idx + i}")
        keyfacts = wikipedia_article.get("keyfacts", "")
        
        # 检查是否已经有有效的keyfacts
        if keyfacts and keyfacts.strip() and keyfacts.strip() != "[]":
            try:
                # 尝试解析JSON，确保是有效的keyfacts
                parsed = json.loads(keyfacts)
                if isinstance(parsed, list) and len(parsed) > 0:
                    print(f"⏭️  跳过已有有效keyfacts: {title}")
                    continue
                else:
                    # 空列表，需要重新提取
                    print(f"⚠️  发现空keyfacts，将重新提取: {title}")
            except:
                # keyfacts格式无效，需要重新提取
                print(f"⚠️  发现无效keyfacts，将重新提取: {title}")
        
        if content and content.strip():
            task = extract_keyfacts_for_wikipedia(
                content, title, args, 
                llm_type="gemini-3-pro-preview",
                auth_config=auth_config,
                client=client
            )
            tasks.append((i, task))
        else:
            print(f"⚠️  跳过空内容: {title}")
    
    if not tasks:
        print(f"✅ 数据块 [{start_idx} - {start_idx + len(chunk) - 1}] 无需处理")
        return chunk
    
    # 并发执行，限制并发数（用于API调用）
    semaphore = asyncio.Semaphore(max_concurrent)
    print(f"   使用并发数: {max_concurrent} 进行API调用")
    
    async def bounded_extract(idx, task):
        async with semaphore:
            return idx, await task
    
    bounded_tasks = [bounded_extract(idx, task) for idx, task in tasks]
    results = await asyncio.gather(*bounded_tasks)
    
    # 更新数据
    result_dict = {idx: keyfacts_result for idx, keyfacts_result in results}
    
    for item_idx, _ in tasks:
        if item_idx in result_dict and result_dict[item_idx]:
            original_data = chunk[item_idx].get("original_data", {})
            if not original_data:
                chunk[item_idx]["original_data"] = {}
                original_data = chunk[item_idx]["original_data"]
            
            wikipedia_article = original_data.get("wikipedia_article", {})
            if not wikipedia_article:
                original_data["wikipedia_article"] = {}
                wikipedia_article = original_data["wikipedia_article"]
            
            # 将keyfacts保存为字符串（JSON格式）
            wikipedia_article["keyfacts"] = result_dict[item_idx]
            print(f"✅ 已更新keyfacts: {wikipedia_article.get('title', f'item_{start_idx + item_idx}')}")
    
    return chunk


async def main():
    """主函数"""
    print("=" * 80)
    print("Wikipedia Keyfacts提取工具（续传模式）")
    print("=" * 80)
    
    # 文件路径
    input_file = "datasets/our_dataset/wikids_final.json"
    output_file = "datasets/our_dataset/wikids_final_with_keyfacts.json"
    backup_file = "datasets/our_dataset/wikids_final_backup.json"
    
    # 优先使用已有输出文件（续传模式）
    if os.path.exists(output_file):
        print(f"\n📂 检测到已有输出文件: {output_file}")
        print(f"   将使用续传模式，只处理缺少keyfacts的记录")
        input_file = output_file
    elif not os.path.exists(input_file):
        print(f"❌ 错误: 输入文件 {input_file} 不存在")
        return
    
    # 创建备份（如果输出文件存在，备份输出文件；否则备份输入文件）
    if os.path.exists(output_file):
        backup_file = output_file.replace(".json", "_backup.json")
        print(f"\n💾 创建备份文件: {backup_file}")
        import shutil
        shutil.copy2(output_file, backup_file)
        print(f"✅ 备份完成")
    elif os.path.exists(input_file):
        print(f"\n💾 创建备份文件: {backup_file}")
        import shutil
        shutil.copy2(input_file, backup_file)
        print(f"✅ 备份完成")
    
    # 初始化args
    args = parse_args()
    args.prompt_template = "key_fact_extraction_with_priority"
    
    # 预先加载auth配置（避免在高并发时重复读取文件）
    print(f"\n🔐 加载认证配置...")
    auth_config = get_auth_config()
    print(f"✅ 认证配置已加载")
    
    # 预先创建并缓存客户端（避免重复创建导致文件句柄泄漏）
    print(f"\n🔧 初始化API客户端...")
    llm_type = "gemini-3-pro-preview"
    client = get_client(llm_type, auth_config)
    print(f"✅ API客户端已初始化")
    
    # 加载完整数据
    print(f"\n📖 加载数据文件: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        data = [data]
    
    total = len(data)
    print(f"✅ 总共 {total} 条记录")
    
    # 统计需要处理的数量
    need_process = 0
    already_have = 0
    no_content = 0
    empty_keyfacts = 0
    
    for item in data:
        original_data = item.get("original_data", {})
        wikipedia_article = original_data.get("wikipedia_article", {})
        
        keyfacts = wikipedia_article.get("keyfacts", "")
        content = wikipedia_article.get("content", "")
        
        # 检查keyfacts是否存在且有效
        if keyfacts and keyfacts.strip() and keyfacts.strip() != "[]":
            # 尝试解析JSON，确保是有效的keyfacts
            try:
                parsed = json.loads(keyfacts)
                if isinstance(parsed, list) and len(parsed) > 0:
                    already_have += 1
                else:
                    empty_keyfacts += 1
                    if content:
                        need_process += 1
            except:
                # keyfacts格式无效，需要重新提取
                empty_keyfacts += 1
                if content:
                    need_process += 1
        elif content and content.strip():
            need_process += 1
        else:
            no_content += 1
    
    print(f"\n📊 统计信息:")
    print(f"  - 已有有效keyfacts: {already_have}")
    print(f"  - 需要提取: {need_process}")
    print(f"  - 无效/空keyfacts（需重新提取）: {empty_keyfacts}")
    print(f"  - 无内容: {no_content}")
    print(f"\n🔧 配置信息:")
    print(f"  - 使用LLM: gemini-3-pro-preview")
    print(f"  - 输入文件: {input_file}")
    print(f"  - 输出文件: {output_file}")
    
    if need_process == 0:
        print("\n✅ 所有记录都已包含有效的keyfacts，无需处理")
        return
    
    # 确认是否继续
    print(f"\n⚠️  将处理 {need_process} 条记录，使用 gemini-3-pro-preview 提取keyfacts")
    print(f"   这可能需要较长时间，请确保网络连接稳定")
    response = input("是否继续？(y/n): ")
    if response.lower() != 'y':
        print("已取消")
        return
    
    # 分块处理
    chunk_size = 100  # 每次处理100条
    max_concurrent = 300  # 最大并发300
    
    processed_count = 0
    start_time = time.time()
    
    for i in range(0, total, chunk_size):
        chunk = data[i:i + chunk_size]
        
        # 处理块
        updated_chunk = await process_chunk(chunk, i, args, max_concurrent, auth_config, client)
        
        # 更新数据
        data[i:i + chunk_size] = updated_chunk
        
        processed_count += len(chunk)
        elapsed = time.time() - start_time
        avg_time = elapsed / processed_count if processed_count > 0 else 0
        remaining = total - processed_count
        eta = remaining * avg_time if avg_time > 0 else 0
        
        print(f"\n📈 进度: {processed_count}/{total} ({processed_count/total*100:.1f}%)")
        print(f"   已用时间: {elapsed/60:.1f}分钟")
        print(f"   预计剩余: {eta/60:.1f}分钟")
        
        # 每处理一个块就保存一次（防止数据丢失）
        print(f"💾 保存中间结果...")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ 已保存到: {output_file}")
        except OSError as e:
            print(f"⚠️  保存文件时出错: {e}")
            print(f"   尝试强制刷新文件系统...")
            import gc
            gc.collect()
            # 稍等片刻再重试
            await asyncio.sleep(1)
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"✅ 重试成功，已保存到: {output_file}")
            except Exception as e2:
                print(f"❌ 重试失败: {e2}")
                raise
    
    # 最终保存
    print(f"\n💾 保存最终结果到: {output_file}")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"⚠️  保存文件时出错: {e}")
        print(f"   尝试强制刷新文件系统...")
        import gc
        gc.collect()
        await asyncio.sleep(1)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 清理客户端资源
    print(f"\n🧹 清理资源...")
    for llm_type_key in list(_client_cache.keys()):
        try:
            client_to_close = _client_cache.pop(llm_type_key)
            if hasattr(client_to_close, 'close'):
                await client_to_close.close()
        except Exception as e:
            print(f"⚠️  清理客户端时出错: {e}")
    print(f"✅ 资源清理完成")
    
    total_time = time.time() - start_time
    print(f"\n✅ 处理完成！")
    print(f"   总耗时: {total_time/60:.1f}分钟")
    print(f"   处理记录数: {processed_count}")
    print(f"   结果已保存到: {output_file}")
    print(f"   备份文件: {backup_file}")


if __name__ == "__main__":
    asyncio.run(main())

