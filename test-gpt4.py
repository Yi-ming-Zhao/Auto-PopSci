from openai import OpenAI

api_key = "sk-FelEphmzVJfpe3YfF7C76d116e2d441aA6D41bE70594A447"
client = OpenAI(api_key=api_key, base_url="https://api.ai-gaochao.cn/v1")
# api_key = "sk-YqLwkz8SpYzoWitZ5c160d9e91164b7194E5A6BdF3314227"
# client = OpenAI(api_key=api_key, base_url="https://apix.ai-gaochao.cn")

completion = client.chat.completions.create(
    model="deepseek-v3",
    messages=[
        {"role": "system", "content": ""},
        {"role": "user", "content": "解释一下什么是CUDA."},
    ],
)

print(completion.choices[0].message)
