import json
import asyncio
import aiofiles
from openai import AsyncOpenAI
from prompts.prompt_template import prompt
from pprint import pprint
import os
import time
from ..utils.utils import read_yaml_file
from ..args import parse_args


async def get_llm_response(client, prompt_text, current_model):
    """
    Get the response from the LLM.

    Args:
        client (AsyncOpenAI): The OpenAI client.
        prompt_text (str): The prompt text to send to the LLM.
        current_model (str): The model to use.

    Returns:
        str: The response from the LLM.
    """
    try:
        response = await client.chat.completions.create(
            model=current_model,
            messages=[
                {
                    "role": "user",
                    "content": prompt_text,
                }
            ],
        )
    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}")
        # 检查是否是余额不足错误
        if "402" in error_msg or "Insufficient Balance" in error_msg or "insufficient" in error_msg.lower():
            return json.dumps([])  # 返回空列表的 JSON 字符串
        return json.dumps([])  # 其他错误也返回空列表

    if response and response.choices:
        result = response.choices[0].message.content
        # 检查结果是否包含错误信息
        if result and ("Error" in result or "error" in result.lower() or "Insufficient Balance" in result):
            print(f"⚠️ LLM 返回错误信息: {result[:200]}")
            return json.dumps([])  # 返回空列表
        return result
    else:
        return json.dumps([])  # 返回空列表的 JSON 字符串


async def async_single_paper_keyfacts_precision_calculation(
    ground_truth_path, keyfact_path, args
):
    """
    Calculate the precision of key facts extraction.

    Args:
        ground_truth_path (str): Path to the ground truth key facts file.
        keyfact_path (str): Path to the extracted key facts file.

    Returns:
        float: Precision score.
    """
    async with aiofiles.open(ground_truth_path, "r") as f:
        ground_truth = await f.read()

    async with aiofiles.open(keyfact_path, "r") as f:
        keyfacts = await f.read()

    # Convert JSON strings to dictionaries
    ground_truth_dict = json.loads(ground_truth)
    keyfacts_dict = json.loads(keyfacts)

    tp_plus_fp_overall = len(keyfacts_dict)

    ground_truth_priority_1 = [
        item for item in ground_truth_dict if item["priority"] == 1
    ]
    keyfacts_priority_1 = [item for item in keyfacts_dict if item["priority"] == 1]

    ground_truth_priority_2 = [
        item for item in ground_truth_dict if item["priority"] == 2
    ]
    keyfacts_priority_2 = [item for item in keyfacts_dict if item["priority"] == 2]

    ground_truth_priority_3 = [
        item for item in ground_truth_dict if item["priority"] == 3
    ]
    keyfacts_priority_3 = [item for item in keyfacts_dict if item["priority"] == 3]

    tp_plus_fp_1 = len(keyfacts_priority_1)
    tp_plus_fp_2 = len(keyfacts_priority_2)
    tp_plus_fp_3 = len(keyfacts_priority_3)

    tasks = []
    auth_info = read_yaml_file("auto_popsci/auth.yaml")
    # 评估 keyfacts precision/recall 时使用 grok
    grok_config = auth_info.get("grok", {})
    current_api_key = grok_config.get("api_key", "")
    current_base_url = grok_config.get("base_url", "")
    current_model = grok_config.get("model", "grok-4-1-fast-reasoning")
    
    # 如果 grok 配置不存在，回退到 args 中的配置
    if not current_api_key:
        current_api_key = auth_info[args.llm_type][args.model_type]["api_key"]
        current_base_url = auth_info[args.llm_type][args.model_type]["base_url"]
        current_model = auth_info[args.llm_type][args.model_type]["model"]
    
    client = AsyncOpenAI(
        api_key=current_api_key,
        base_url=current_base_url,
    )
    for i in range(3):
        if i == 0:
            ground_truth = ground_truth_priority_1
            keyfacts = keyfacts_priority_1
        elif i == 1:
            ground_truth = ground_truth_priority_2
            keyfacts = keyfacts_priority_2
        else:
            ground_truth = ground_truth_priority_3
            keyfacts = keyfacts_priority_3

        tasks.append(
            get_llm_response(
                client,
                prompt_text=prompt[args.prompt_template].format(
                    ground_truth_key_facts=ground_truth, generated_key_facts=keyfacts
                ),
                current_model=current_model,
            )
        )
    tasks.append(
        get_llm_response(
            client,
            prompt_text=prompt[args.prompt_template].format(
                ground_truth_key_facts=ground_truth_dict,
                generated_key_facts=keyfacts_dict,
            ),
            current_model=current_model,
        )
    )
    responses = await asyncio.gather(*tasks)
    # 初始化默认值
    tp_1 = 0
    tp_2 = 0
    tp_3 = 0
    tp_overall = 0
    
    for i, response in enumerate(responses):
        try:
            # 检查响应是否包含错误信息
            if isinstance(response, str) and ("Error" in response or "error" in response.lower()):
                print(f"⚠️ 响应包含错误信息: {response[:200]}")
                continue
            
            # 尝试解析 JSON
            parsed_response = json.loads(response)
            if isinstance(parsed_response, list):
                if i == 0:
                    tp_1 = len(parsed_response)
                elif i == 1:
                    tp_2 = len(parsed_response)
                elif i == 2:
                    tp_3 = len(parsed_response)
                else:
                    tp_overall = len(parsed_response)
            else:
                print(f"⚠️ 响应格式不正确，期望列表，得到: {type(parsed_response)}")
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON 解析失败 (任务 {i}): {e}")
            print(f"   响应内容: {response[:500] if response else 'None'}")
            # 继续处理其他响应
        except Exception as e:
            print(f"⚠️ 处理响应时出错 (任务 {i}): {e}")
            import traceback
            traceback.print_exc()

    precisions = {
        "priority_1": tp_1 / tp_plus_fp_1 if tp_plus_fp_1 > 0 else -1,
        "priority_2": tp_2 / tp_plus_fp_2 if tp_plus_fp_2 > 0 else -1,
        "priority_3": tp_3 / tp_plus_fp_3 if tp_plus_fp_3 > 0 else -1,
        "overall": tp_overall / tp_plus_fp_overall if tp_plus_fp_overall > 0 else -1,
    }
    recalls = {
        "priority_1": (
            tp_1 / len(ground_truth_priority_1)
            if len(ground_truth_priority_1) > 0
            else -1
        ),
        "priority_2": (
            tp_2 / len(ground_truth_priority_2)
            if len(ground_truth_priority_2) > 0
            else -1
        ),
        "priority_3": (
            tp_3 / len(ground_truth_priority_3)
            if len(ground_truth_priority_3) > 0
            else -1
        ),
        "overall": (
            tp_overall / len(ground_truth_dict) if len(ground_truth_dict) > 0 else -1
        ),
    }
    print(f"Recalls for paper: {recalls}")
    print(f"Precision for paper: {precisions}")
    res = {
        "recalls": recalls,
        "precisions": precisions,
    }
    return res


async def async_multiple_keyfacts_precision_calculation(
    ground_truth_paths, keyfact_paths, args
):
    """
    Calculate the precision of key facts extraction for multiple papers.

    Args:
        ground_truth_path (str): Path to the ground truth key facts file.
        keyfact_paths (list): List of paths to the extracted key facts files.

    Returns:
        list: List of precision scores for each paper.
    """
    precision_scores = []
    tasks = []
    for i, keyfact_path in enumerate(keyfact_paths):
        print(f"Calculating precision for paper {i + 1}/{len(keyfact_paths)}")
        tasks.append(
            async_single_paper_keyfacts_precision_calculation(
                ground_truth_paths[i], keyfact_path, args
            )
        )
    scores = await asyncio.gather(*tasks)
    return scores


async def main(args):
    """
    Main function to run the precision calculation.
    """
    ground_truth_path = "auto_popsci/evaluation/output/dev_5/R1_ground_truth/with_priority/reference_keyfacts/"
    keyfact_path = "auto_popsci/evaluation/output/dev_5/scinews_keyfacts/with_priority/reference_keyfacts/"

    # List of ground truth paths
    ground_truth_files = [
        f for f in os.listdir(ground_truth_path) if f.endswith(".json")
    ]
    keyfact_files = [f for f in os.listdir(keyfact_path) if f.endswith(".json")]
    print("Ground truth files:", ground_truth_files)
    print("Key fact files:", keyfact_files)

    # Ensure both lists are of the same length
    if len(ground_truth_files) != len(keyfact_files):
        raise ValueError("Mismatch in number of ground truth and key fact files.")
    ground_truth_paths = [
        os.path.join(ground_truth_path, f) for f in ground_truth_files
    ]
    keyfact_paths = [os.path.join(keyfact_path, f) for f in keyfact_files]
    print("Ground truth paths:", ground_truth_paths)
    print("Key fact paths:", keyfact_paths)
    # Calculate precision scores
    scores = await async_multiple_keyfacts_precision_calculation(
        ground_truth_paths, keyfact_paths, args
    )
    # Print precision scores
    for i, score in enumerate(scores):
        print(f"Precision for paper {i + 1}: ", score["precisions"])
        print(f"Recall for paper {i + 1}: ", score["recalls"])

    # Save precision scores to a file
    output_file = os.path.join(
        "auto_popsci/evaluation/output/dev_5/", "precision_scores.json"
    )

    with open(output_file, "w") as f:
        json.dump(
            scores,
            f,
            indent=4,
        )
    print(f"Precision scores saved to {output_file}")


if __name__ == "__main__":
    args = parse_args()
    args.prompt_template = "keyfact_alignment"
    asyncio.run(main(args))
