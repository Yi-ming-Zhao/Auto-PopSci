"""
Compute precision and recall for keyfacts extraction.

This mirrors the API call pattern used in comprehensive_evaluation.py's generate_keyfacts.
"""
import json
import asyncio
import os
from datetime import datetime
from prompts.prompt_template import prompt
from auto_popsci.utils.utils import read_yaml_file

# Debug log file path.
DEBUG_LOG_FILE = "baselines/keyfacts_eval_debug.log"

# Global counter.
_call_counter = 0


async def _async_read_text(path: str) -> str:
    """Read a text file asynchronously without requiring aiofiles."""
    def _read():
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return await asyncio.to_thread(_read)


async def _async_append_text(path: str, content: str) -> None:
    """Append text asynchronously without requiring aiofiles."""
    def _write():
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
    await asyncio.to_thread(_write)


async def log_debug(prompt_text: str, response: str, task_id: int):
    """Save the prompt and response to the debug log."""
    global _call_counter
    _call_counter += 1
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = f"""
{'='*80}
[{timestamp}] Call #{_call_counter} | Task {task_id}
{'='*80}

>>> PROMPT <<<
{prompt_text}

>>> RESPONSE <<<
{response if response else '(None - API call failed)'}

{'='*80}
"""
    
    await _async_append_text(DEBUG_LOG_FILE, log_entry)


async def async_calculate_precision_recall(
    ground_truth_path, keyfact_path, args
):
    """
    Calculate the precision and recall of key facts extraction.

    Args:
        ground_truth_path (str): Path to the ground truth key facts file.
        keyfact_path (str): Path to the extracted key facts file.
        args: Command line arguments containing LLM config.

    Returns:
        dict: Contains 'precisions' and 'recalls' dictionaries.
    """
    
    # Read the files.
    ground_truth = await _async_read_text(ground_truth_path)

    keyfacts = await _async_read_text(keyfact_path)

    # Parse JSON.
    ground_truth_dict = json.loads(ground_truth)
    keyfacts_dict = json.loads(keyfacts)

    # Normalize to a list.
    if isinstance(ground_truth_dict, dict):
        if "keyfacts" in ground_truth_dict:
            ground_truth_dict = ground_truth_dict["keyfacts"]
        elif "key_facts" in ground_truth_dict:
            ground_truth_dict = ground_truth_dict["key_facts"]
        else:
            for v in ground_truth_dict.values():
                if isinstance(v, list):
                    ground_truth_dict = v
                    break

    if isinstance(keyfacts_dict, dict):
        if "keyfacts" in keyfacts_dict:
            keyfacts_dict = keyfacts_dict["keyfacts"]
        elif "key_facts" in keyfacts_dict:
            keyfacts_dict = keyfacts_dict["key_facts"]
        else:
            for v in keyfacts_dict.values():
                if isinstance(v, list):
                    keyfacts_dict = v
                    break
                 
    # Ensure we have a list.
    if not isinstance(ground_truth_dict, list):
        ground_truth_dict = []
    if not isinstance(keyfacts_dict, list):
        keyfacts_dict = []

    tp_plus_fp_overall = len(keyfacts_dict)

    # Group by priority.
    ground_truth_priority_1 = [item for item in ground_truth_dict if item.get("priority") == 1]
    keyfacts_priority_1 = [item for item in keyfacts_dict if item.get("priority") == 1]

    ground_truth_priority_2 = [item for item in ground_truth_dict if item.get("priority") == 2]
    keyfacts_priority_2 = [item for item in keyfacts_dict if item.get("priority") == 2]

    ground_truth_priority_3 = [item for item in ground_truth_dict if item.get("priority") == 3]
    keyfacts_priority_3 = [item for item in keyfacts_dict if item.get("priority") == 3]

    tp_plus_fp_1 = len(keyfacts_priority_1)
    tp_plus_fp_2 = len(keyfacts_priority_2)
    tp_plus_fp_3 = len(keyfacts_priority_3)

    # Load the LLM configuration.
    auth_info = read_yaml_file("auth.yaml")
    
    user_specified_model = args.llm_type if args and hasattr(args, 'llm_type') else None
    if not user_specified_model:
        user_specified_model = 'gemini-3-flash-preview' # Default backup
        
    found_config = None
    api_key = ""
    base_url = ""
    model = user_specified_model

    # 1. Try to find the model key under each provider in auth.yaml.
    for provider_name, provider_config in auth_info.items():
        if isinstance(provider_config, dict):
                if user_specified_model in provider_config:
                    found_config = provider_config[user_specified_model]
                    break
    
    # 2. If not found, see if the user provided a provider name (for backward compatibility).
    if not found_config and user_specified_model in auth_info:
            provider_config = auth_info[user_specified_model]
            if isinstance(provider_config, dict):
                first_model_key = next(iter(provider_config.keys()))
                if isinstance(provider_config[first_model_key], dict):
                    found_config = provider_config[first_model_key]
                else:
                    found_config = provider_config

    if found_config:
        api_key = found_config.get("api_key", "")
        base_url = found_config.get("base_url", "")
        model = found_config.get("model", user_specified_model)
    else:
        # Try the final fallback (args.llm_type interpreted as provider name).
        try:
            api_key = auth_info[args.llm_type][args.model_type]["api_key"]
            base_url = auth_info[args.llm_type][args.model_type]["base_url"]
            model = auth_info[args.llm_type][args.model_type]["model"]
        except (KeyError, TypeError, AttributeError):
            print(f"Unable to locate LLM configuration for user-specified model: {user_specified_model}")
            return {'precisions': {'overall': -1.0}, 'recalls': {'overall': -1.0}}
    
    # Create the client with a 600-second timeout.
    from openai import AsyncOpenAI
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=600.0
    )
    
    # Prepare four tasks (three priorities plus overall).
    priority_data = [
        (ground_truth_priority_1, keyfacts_priority_1, "priority_1"),
        (ground_truth_priority_2, keyfacts_priority_2, "priority_2"),
        (ground_truth_priority_3, keyfacts_priority_3, "priority_3"),
        (ground_truth_dict, keyfacts_dict, "overall"),
    ]
    
    # Create a concurrent task function with retry logic.
    async def call_api(gt, gen, task_id, max_retries=10):
        gt_json = json.dumps(gt, ensure_ascii=False, indent=2)
        gen_json = json.dumps(gen, ensure_ascii=False, indent=2)
        
        prompt_text = prompt[args.prompt_template].format(
            ground_truth_key_facts=gt_json,
            generated_key_facts=gen_json
        )
        
        for attempt in range(max_retries):
            try:
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
                    
                    # Validate that the JSON is complete (try parsing).
                    if result:
                        try:
                            json.loads(result.strip())
                            # JSON parsed successfully; log and return.
                            await log_debug(prompt_text, result, task_id)
                            return result
                        except json.JSONDecodeError as e:
                            # JSON parsing failed (possibly truncated); retry.
                            if attempt < max_retries - 1:
                                print(f"Task {task_id} response was truncated; retrying {attempt + 1}/{max_retries}...")
                                await asyncio.sleep(2 * (attempt + 1))  # Wait 2, 4, 6 sec before retrying.
                                continue
                            else:
                                # The final retry also failed; log and return.
                                await log_debug(prompt_text, f"(TRUNCATED after {max_retries} retries): {result}", task_id)
                                print(f"Task {task_id} response was truncated after {max_retries} retries.")
                                return result  # Return the truncated result for outer handling.
                    
                await log_debug(prompt_text, "(empty response)", task_id)
                return "[]"
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"API call failed for task {task_id}; retrying {attempt + 1}/{max_retries}: {e}")
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                print(f"API call for task {task_id} ultimately failed: {e}")
                await log_debug(prompt_text, f"(ERROR: {e})", task_id)
                return None
        
        return None
    
    # Execute the four API calls concurrently.
    tasks = [call_api(gt, gen, i) for i, (gt, gen, _) in enumerate(priority_data)]
    results = await asyncio.gather(*tasks)
    
    # Parse the results.
    tp_p_1 = tp_r_1 = 0
    tp_p_2 = tp_r_2 = 0
    tp_p_3 = tp_r_3 = 0
    tp_p_overall = tp_r_overall = 0
    
    for i, response in enumerate(results):
        if response is None:
            print(f"API call for task {i} failed; skipping.")
            continue
       
        try:
            parsed_response = json.loads(response.strip())
        except json.JSONDecodeError as e:
            print(f"\n{'='*60}")
            print(f"JSON parsing failed for task {i}")
            print(f"Error: {e}")
            print(f"{'='*60}")
            print("Full response:")
            print(f"{'='*60}")
            print(response)
            print(f"{'='*60}\n")
            continue
        
        # Handle nested arrays [[...]] -> [...]
        if isinstance(parsed_response, list):
            # Smart trimming: keep Pair structures ([dict, dict]) while removing extra wrappers.
            current = parsed_response
            while True:
                if not current or not isinstance(current, list):
                    break
                
                # Inspect the first element.
                if len(current) > 0:
                    first_item = current[0]
                    
                    if isinstance(first_item, dict):
                        # Already a [dict, dict...] pair or the LLM did not return a pair.
                        # Stop flattening.
                        break
                        
                    if isinstance(first_item, list):
                        # Element is a list; inspect what it contains.
                        if len(first_item) > 0 and isinstance(first_item[0], dict):
                            # This is a Pair [dict, dict].
                            # Current level is the desired list of pairs.
                            # Stop flattening.
                            break
                        else:
                            # The nested list still contains lists or is empty.
                            # Indicates extra nesting, e.g., [[[pair], [pair]]].
                            # Need to flatten one more level.
                            flattened = []
                            for item in current:
                                if isinstance(item, list):
                                    flattened.extend(item)
                                else:
                                    flattened.append(item)
                            current = flattened
                            continue
                break
            
            parsed_response = current
            
            # Count unique matches to avoid duplicate scoring above 1.0.
            unique_gen = set()
            unique_gt = set()
            for pair in parsed_response:
                if isinstance(pair, list) and len(pair) >= 2:
                    try:
                        unique_gen.add(json.dumps(pair[0], sort_keys=True))
                        unique_gt.add(json.dumps(pair[1], sort_keys=True))
                    except:
                        pass
                elif isinstance(pair, dict):
                     # If only dicts remain, it might be a parsing artifact; handle conservatively.
                     pass

            tp_precision_count = len(unique_gen)
            tp_recall_count = len(unique_gt)

            if i == 0:
                tp_p_1, tp_r_1 = tp_precision_count, tp_recall_count
            elif i == 1:
                tp_p_2, tp_r_2 = tp_precision_count, tp_recall_count
            elif i == 2:
                tp_p_3, tp_r_3 = tp_precision_count, tp_recall_count
            else:
                tp_p_overall, tp_r_overall = tp_precision_count, tp_recall_count
        else:
            print(f"Unexpected response format: expected a list but got {type(parsed_response)}")

    precisions = {
        "priority_1": tp_p_1 / tp_plus_fp_1 if tp_plus_fp_1 > 0 else -1,
        "priority_2": tp_p_2 / tp_plus_fp_2 if tp_plus_fp_2 > 0 else -1,
        "priority_3": tp_p_3 / tp_plus_fp_3 if tp_plus_fp_3 > 0 else -1,
        "overall": tp_p_overall / tp_plus_fp_overall if tp_plus_fp_overall > 0 else -1,
    }
    recalls = {
        "priority_1": tp_r_1 / len(ground_truth_priority_1) if len(ground_truth_priority_1) > 0 else -1,
        "priority_2": tp_r_2 / len(ground_truth_priority_2) if len(ground_truth_priority_2) > 0 else -1,
        "priority_3": tp_r_3 / len(ground_truth_priority_3) if len(ground_truth_priority_3) > 0 else -1,
        "overall": tp_r_overall / len(ground_truth_dict) if len(ground_truth_dict) > 0 else -1,
    }

    # Final clipping step as a safeguard.
    for k in precisions:
        if precisions[k] > 1.0: precisions[k] = 1.0
    for k in recalls:
        if recalls[k] > 1.0: recalls[k] = 1.0

    return {
        "recalls": recalls,
        "precisions": precisions,
    }
