#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模型科普文章生成评测脚本（异步版本）
支持5个模型：GPT-5.2、Claude Opus、Gemini、Grok、DeepSeek
按顺序处理每个模型，每个模型内部使用200并发
"""

import json
import asyncio
from openai import AsyncOpenAI
import time
from typing import Dict, Any, List, Optional, Tuple
import os
import yaml
import re
import signal
import sys

# ==================== 配置区域 ====================
# 设置 sample 变量，如果设置则只处理前 sample 条数据
sample = None  # 例如: sample = 10 表示只处理前10条数据

# 配置文件路径
API_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "auth.yaml")
# 输入和输出文件路径
INPUT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "datasets/our_dataset/wikids_final_with_keyfacts.json",
)
OUTPUT_FILE = os.path.join(
    os.path.dirname(__file__), "multi_model_generation_output.json"
)

# 模型配置映射（auth.yaml 中的键名 -> (子键名, 显示名称)）
MODEL_CONFIGS = {
    "openai": ("gpt-5.2", "gpt-5.2"),
    "anthropic": (
        "claude-opus-4-5-20251101-thinking",
        "claude-opus-4-5-20251101-thinking",
    ),
    "google": ("gemini-3-pro-preview", "gemini-3-pro-preview"),
    "xai": ("grok-4-1-fast-reasoning", "grok-4-1-fast-reasoning"),
    # "qwen": ("qwen3-235b-a22b-thinking-2507", "qwen3-235b-a22b-thinking-2507"),  # 暂时不使用
    "deepseek": ("deepseek-r1", "deepseek-r1"),
}

# 并发数
MAX_CONCURRENT = 200

# 全局中断标志
interrupt_flag = False

# API 调用超时时间（秒）
API_TIMEOUT = 300  # 5分钟超时

# 特定模型的超时配置
MODEL_TIMEOUTS = {
    "claude-opus-4-5-20251101-thinking": 300,  # 10分钟
    "gpt-5.2": 300,
    "gemini-3-pro-preview": 300,
    "grok-4-1-fast-reasoning": 300,
    "deepseek-r1": 300,
}


# ==================== 工具函数 ====================


def save_results(
    article_model_results: Dict[int, Dict[str, Dict[str, str]]],
    data_list: List[Dict[str, Any]],
    model_configs: Dict[str, Dict[str, str]],
) -> None:
    """保存当前已生成的结果到输出文件"""
    try:
        # 合并结果
        results = []
        for i, data in enumerate(data_list):
            models_dict = {}
            for model_name in model_configs.keys():
                if (
                    i in article_model_results
                    and model_name in article_model_results[i]
                ):
                    models_dict[model_name] = article_model_results[i][model_name]
                else:
                    original_data = data.get("original_data", {})
                    wiki_title = original_data.get("wikipedia_article", {}).get(
                        "title", ""
                    )
                    models_dict[model_name] = {
                        "title": wiki_title + " - Generation Incomplete",
                        "content": "Generation Incomplete",
                    }

            results.append(
                {
                    "original_data": data,
                    "models": models_dict,
                }
            )

        # 保存到文件
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存结果时出错: {str(e)}")


def load_all_model_configs() -> Dict[str, Dict[str, str]]:
    """加载所有模型的配置"""
    configs = {}
    with open(API_CONFIG_FILE, "r", encoding="utf-8") as f:
        all_configs = yaml.safe_load(f)

    for model_key, (sub_key, display_name) in MODEL_CONFIGS.items():
        if model_key in all_configs:
            if sub_key in all_configs[model_key]:
                configs[display_name] = all_configs[model_key][sub_key]

    return configs


def parse_json_response(response: str, wiki_title: str) -> Dict[str, str]:
    """解析模型返回的JSON响应"""
    cleaned_response = response.strip()

    # 移除可能的 ```json 和 ``` 标记
    if cleaned_response.startswith("```"):
        lines = cleaned_response.split("\n")
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned_response = "\n".join(lines).strip()

    # 策略1: 直接解析整个响应
    try:
        generated_popsci = json.loads(cleaned_response)
        if isinstance(generated_popsci, dict):
            if "title" in generated_popsci and "content" in generated_popsci:
                return generated_popsci
    except json.JSONDecodeError:
        pass

    # 策略2: 查找第一个 { 到最后一个 } 之间的内容
    try:
        start_idx = cleaned_response.find("{")
        end_idx = cleaned_response.rfind("}")
        if start_idx >= 0 and end_idx > start_idx:
            json_str = cleaned_response[start_idx : end_idx + 1]
            generated_popsci = json.loads(json_str)
            if isinstance(generated_popsci, dict):
                if "title" in generated_popsci and "content" in generated_popsci:
                    return generated_popsci
    except json.JSONDecodeError:
        pass

    # 策略3: 手动提取title和content字段
    try:
        title_match = re.search(
            r'"title"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', cleaned_response
        )
        content_match = re.search(
            r'"content"\s*:\s*"((?:[^"\\]|\\.|\\n|\\r|\\t)*)"',
            cleaned_response,
            re.DOTALL,
        )

        title = None
        content = None

        if title_match:
            title = (
                title_match.group(1)
                .replace('\\"', '"')
                .replace("\\n", "\n")
                .replace("\\r", "\r")
                .replace("\\t", "\t")
            )

        if content_match:
            content = (
                content_match.group(1)
                .replace('\\"', '"')
                .replace("\\n", "\n")
                .replace("\\r", "\r")
                .replace("\\t", "\t")
            )

        if title or content:
            generated_popsci = {
                "title": title if title else wiki_title + " - Generated",
                "content": content if content else cleaned_response,
            }
            return generated_popsci
    except Exception:
        pass

    # 如果所有策略都失败，创建基本响应
    print(f"警告: 无法解析JSON响应，原始响应前500字符: {cleaned_response[:500]}...")
    generated_popsci = {
        "title": wiki_title + " - Generated",
        "content": cleaned_response,
    }

    if "title" not in generated_popsci:
        generated_popsci["title"] = wiki_title + " - Generated"
    if "content" not in generated_popsci:
        generated_popsci["content"] = cleaned_response

    return generated_popsci


def build_prompt(wiki_title: str, wiki_content: str) -> str:
    """构建提示词"""
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
    return prompt


# ==================== 异步函数 ====================


async def call_model_api(
    prompt: str, client: AsyncOpenAI, model_name: str, max_retries: int = 2
) -> str:
    """异步调用模型API"""
    global interrupt_flag
    if interrupt_flag:
        return "API调用被中断"

    model_timeout = MODEL_TIMEOUTS.get(model_name, API_TIMEOUT)

    for attempt in range(max_retries):
        if interrupt_flag:
            return "API调用被中断"

        try:
            start_time = time.time()
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert in writing popular science articles for children aged 8-12. Your articles should be easy to understand, engaging, and avoid technical jargon and complex concepts.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                ),
                timeout=model_timeout,
            )

            elapsed_time = time.time() - start_time
            if elapsed_time > 60:
                print(f"[{model_name}] API调用耗时 {elapsed_time:.1f}秒")

            return response.choices[0].message.content

        except asyncio.TimeoutError:
            error_msg = f"超时（{model_timeout}秒）"
            print(f"API调用超时 (模型: {model_name}, 尝试: {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(min(5 * (attempt + 1), 15))
            else:
                return f"API调用超时失败（模型: {model_name}）"
        except Exception as e:
            error_msg = str(e)
            print(
                f"API调用异常 (模型: {model_name}, 尝试: {attempt+1}/{max_retries}): {error_msg[:200]}"
            )
            if attempt < max_retries - 1:
                if interrupt_flag:
                    return "API调用被中断"
                await asyncio.sleep(min(2**attempt, 10))
            else:
                return f"API调用失败（模型: {model_name}, 错误: {error_msg[:100]}）"

    return f"API调用失败，无法生成科普文章（模型: {model_name}）"


async def generate_popsci_for_model(
    data: Dict[str, Any], model_name: str, client: AsyncOpenAI
) -> Dict[str, str]:
    """为单个模型生成科普文章"""
    original_data = data.get("original_data", {})
    wiki_article = original_data.get("wikipedia_article", {})

    wiki_title = wiki_article.get("title", "")
    wiki_content = wiki_article.get("content", "")

    prompt = build_prompt(wiki_title, wiki_content)
    response = await call_model_api(prompt, client, model_name)
    generated_popsci = parse_json_response(response, wiki_title)

    return generated_popsci


async def process_article_for_model(
    data: Dict[str, Any],
    model_name: str,
    client: AsyncOpenAI,
    index: int,
    total: int,
    article_model_results: Dict[int, Dict[str, Dict[str, str]]],
    progress_counter: Dict[str, int],
) -> Tuple[int, str, Dict[str, str]]:
    """处理单篇文章和单个模型"""
    global interrupt_flag
    if interrupt_flag:
        raise asyncio.CancelledError("处理被中断")

    original_data = data.get("original_data", {})
    wiki_title = original_data.get("wikipedia_article", {}).get("title", "未知标题")
    task_start_time = time.time()

    try:
        result = await generate_popsci_for_model(data, model_name, client)

        elapsed = time.time() - task_start_time
        progress_counter[model_name] = progress_counter.get(model_name, 0) + 1
        current_progress = progress_counter[model_name]

        # 更新结果
        if index not in article_model_results:
            article_model_results[index] = {}
        article_model_results[index][model_name] = result

        # 打印进度
        if elapsed > 120:
            print(
                f"[{model_name}] 文章 {index+1} ({wiki_title[:50]}) 处理耗时 {elapsed:.1f}秒"
            )
        print(f"[{model_name}] 处理文章 {current_progress}/{total}: {wiki_title[:50]}")

        return index, model_name, result

    except asyncio.CancelledError:
        raise
    except Exception as e:
        elapsed = time.time() - task_start_time
        error_msg = str(e)
        error_result = {
            "title": wiki_title + " - Generation Failed",
            "content": f"Generation failed after {elapsed:.1f}s: {error_msg[:500]}",
        }

        progress_counter[model_name] = progress_counter.get(model_name, 0) + 1

        if index not in article_model_results:
            article_model_results[index] = {}
        article_model_results[index][model_name] = error_result

        print(
            f"[{model_name}] 处理文章 {index+1} ({wiki_title[:50]}) 时出错 (耗时 {elapsed:.1f}秒): {error_msg[:100]}"
        )

        return index, model_name, error_result


async def process_model(
    model_name: str,
    model_config: Dict[str, str],
    data_list: List[Dict[str, Any]],
    article_model_results: Dict[int, Dict[str, Dict[str, str]]],
    progress_counter: Dict[str, int],
    model_configs: Dict[str, Dict[str, str]],
    save_interval: int = 50,
) -> None:
    """处理单个模型的所有文章"""
    global interrupt_flag

    print(f"\n{'='*60}")
    print(f"开始处理模型: {model_name}")
    print(f"{'='*60}")

    # 创建异步客户端
    model_timeout = MODEL_TIMEOUTS.get(model_name, API_TIMEOUT)
    connect_timeout = 30.0 if "claude" not in model_name.lower() else 60.0

    client = AsyncOpenAI(
        api_key=model_config["api_key"],
        base_url=model_config["base_url"],
        timeout=model_timeout,
    )

    # 创建所有需要处理的任务
    tasks_to_process = [(i, data) for i, data in enumerate(data_list)]
    print(f"[{model_name}] 需要处理 {len(tasks_to_process)} 篇文章")

    # 使用信号量控制并发数
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    start_time = time.time()

    async def process_with_semaphore(index: int, data: Dict[str, Any]):
        async with semaphore:
            if interrupt_flag:
                raise asyncio.CancelledError()
            return await process_article_for_model(
                data,
                model_name,
                client,
                index,
                len(tasks_to_process),
                article_model_results,
                progress_counter,
            )

    # 创建所有任务
    tasks = [process_with_semaphore(index, data) for index, data in tasks_to_process]

    # 使用 as_completed 处理结果
    completed = 0

    try:
        for coro in asyncio.as_completed(tasks):
            try:
                await coro
                completed += 1

                # 每完成一定数量的任务后保存一次结果
                if completed % save_interval == 0:
                    completed_pct = completed / len(tasks) * 100 if tasks else 0
                    print(
                        f"\n[{model_name}] 进度: {completed}/{len(tasks)} ({completed_pct:.1f}%) - 保存结果中..."
                    )
                    save_results(article_model_results, data_list, model_configs)
                    print(f"[{model_name}] 结果已保存到 {OUTPUT_FILE}")
                elif completed % 10 == 0:
                    # 每10个任务打印一次进度（不保存）
                    completed_pct = completed / len(tasks) * 100 if tasks else 0
                    print(
                        f"[{model_name}] 进度: {completed}/{len(tasks)} ({completed_pct:.1f}%)"
                    )

            except asyncio.CancelledError:
                if interrupt_flag:
                    print(f"\n[{model_name}] 处理被中断")
                    break
            except Exception as e:
                print(f"[{model_name}] 处理任务时出错: {str(e)[:200]}")
                completed += 1

    finally:
        # 关闭客户端
        await client.close()

    # 模型处理完成后保存一次结果
    print(f"\n[{model_name}] 处理完成: {completed}/{len(tasks)} 篇文章，保存结果中...")
    save_results(article_model_results, data_list, model_configs)
    print(f"[{model_name}] 结果已保存到 {OUTPUT_FILE}")

    elapsed_time = time.time() - start_time
    print(f"[{model_name}] 耗时 {elapsed_time/60:.1f} 分钟")


def signal_handler(signum, frame):
    """处理中断信号"""
    global interrupt_flag
    print("\n\n收到中断信号 (Ctrl+C)，正在安全退出...")
    interrupt_flag = True


async def main():
    """主函数（异步版本）"""
    global interrupt_flag

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("多模型科普文章生成评测（异步版本）")
    print("提示: 按 Ctrl+C 可以安全退出（会保存已生成的结果）")
    print("=" * 60)

    # 加载所有模型配置
    print("\n加载模型配置...")
    model_configs = load_all_model_configs()
    print(f"已加载 {len(model_configs)} 个模型配置:")
    for model_name in model_configs.keys():
        print(f"  - {model_name}")

    # 检查输入文件是否存在
    if not os.path.exists(INPUT_FILE):
        print(f"\n错误: 输入文件 {INPUT_FILE} 不存在")
        return

    # 加载数据
    print(f"\n加载数据集: {INPUT_FILE}")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data_list = json.load(f)

    # 应用 sample 限制
    if sample is not None and sample > 0:
        data_list = data_list[:sample]
        print(f"使用 sample={sample}，只处理前 {len(data_list)} 条数据")

    print(f"成功加载 {len(data_list)} 条文章记录")

    # 创建输出目录
    output_dir = os.path.dirname(OUTPUT_FILE)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # 初始化结果
    article_model_results = {}
    for i in range(len(data_list)):
        article_model_results[i] = {}

    print(f"\n开始生成科普文章...")
    print(f"每个模型使用 {MAX_CONCURRENT} 并发")
    print(f"按顺序处理 {len(model_configs)} 个模型")
    print("-" * 60)

    start_time = time.time()
    progress_counter = {}

    # 按顺序处理每个模型
    for model_name, model_config in model_configs.items():
        if interrupt_flag:
            print("\n处理被中断")
            break

        try:
            await process_model(
                model_name,
                model_config,
                data_list,
                article_model_results,
                progress_counter,
                model_configs,
            )
        except KeyboardInterrupt:
            interrupt_flag = True
            break
        except Exception as e:
            print(f"处理模型 {model_name} 时出错: {str(e)}")
            continue

    # 合并结果
    print("\n合并结果...")
    results = []
    for i, data in enumerate(data_list):
        models_dict = {}
        for model_name in model_configs.keys():
            if i in article_model_results and model_name in article_model_results[i]:
                models_dict[model_name] = article_model_results[i][model_name]
            else:
                original_data = data.get("original_data", {})
                wiki_title = original_data.get("wikipedia_article", {}).get("title", "")
                models_dict[model_name] = {
                    "title": wiki_title + " - Generation Incomplete",
                    "content": "Generation Incomplete",
                }

        results.append(
            {
                "original_data": data,
                "models": models_dict,
            }
        )

    # 保存结果
    print(f"\n保存生成结果到 {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total_time = time.time() - start_time
    print(f"\n生成完成!")
    print(f"总共处理 {len(results)} 篇文章，耗时 {total_time/60:.1f} 分钟")

    # 打印统计信息
    print("\n" + "=" * 60)
    print("统计信息:")
    print("=" * 60)
    for model_name in model_configs.keys():
        success_count = sum(
            1
            for r in results
            if r.get("models", {}).get(model_name, {}).get("content", "")
            and "Generation failed"
            not in r.get("models", {}).get(model_name, {}).get("content", "")
            and "生成失败"
            not in r.get("models", {}).get(model_name, {}).get("content", "")
            and "Generation Incomplete"
            not in r.get("models", {}).get(model_name, {}).get("content", "")
            and "Generation Timeout"
            not in r.get("models", {}).get(model_name, {}).get("content", "")
        )
        print(
            f"{model_name}: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)"
        )


if __name__ == "__main__":
    asyncio.run(main())
