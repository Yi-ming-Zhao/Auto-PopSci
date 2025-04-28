from utils import read_yaml_file
import asyncio
from prompts.prompt_template import prompt
from openai import AsyncOpenAI


async def extract_keyfacts(args, paper):
    """
    Extract keyfacts from the provided paper.
    """
    auth_info = read_yaml_file("auth.yaml")
    current_api_key = auth_info[args.llm_type][args.model_type]["api_key"]
    current_base_url = auth_info[args.llm_type][args.model_type]["base_url"]
    current_model = auth_info[args.llm_type][args.model_type]["model"]
    client = AsyncOpenAI(
        api_key=current_api_key,
        base_url=current_base_url,
    )
    prompt_text = prompt["key_fact_extraction"].format(paper=paper)
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
        print(f"Error: {e}")
        return "API connection Error: " + str(e)

    if response and response.choices:
        result = response.choices[0].message.content
        return result
    else:
        return "No keyfacts found."
