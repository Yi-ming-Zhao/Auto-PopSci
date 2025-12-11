import openai

def query_gpt4(question):
    openai.api_key = "sk-F8sMUgSUkCgbd4eg43CaD6Ba99494dA4A776C5F8C05248F1"
    openai.base_url = 'https://api.ai-gaochao.cn/v1/'

    try:
        response = openai.chat.completions.create(
            model="grok-4-1-fast-reasoning",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question}
            ]
        )
        print(response)
        return response['choices'][0].message['content']
    except Exception as e:
        return str(e)

# 问题
question = "你好"

# 获取打印并回答
answer = query_gpt4(question)
print(answer)