import wikipedia
import tiktoken

query = "Climate Change"
results = wikipedia.search(query)

page = wikipedia.page(results[0])
print("\n页面标题：", page.title)
print("页面URL：", page.url)
print("页面内容预览：", page.content)  # 打印前500

content_length = len(page.content)
print("页面内容长度（字符数）：", content_length)

# 使用tiktoken将content转换为token并统计长度
encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
tokens = encoding.encode(page.content)
token_count = len(tokens)
print("页面内容长度（token数）：", token_count)

# 也可以显示前几个token作为示例
print("前10个token示例：", tokens[:10])
print("前10个token解码后的文本：", encoding.decode(tokens[:10]))
print(len("apple\n"))
