# Wikipedia Keyfacts提取工具

## 功能说明

这个脚本用于从 `wikids_final.json` 数据集中提取Wikipedia文章的keyfacts，并将结果保存回数据集的 `original_data.wikipedia_article` 字段下。

## 使用方法

```bash
cd datasets/our_dataset
python extract_wikipedia_keyfacts.py
```

## 功能特性

- ✅ 自动检测已有keyfacts，跳过已处理的记录
- ✅ 并发处理，提高效率（默认50并发）
- ✅ 分块处理，避免内存溢出
- ✅ 自动备份原始文件
- ✅ 中间结果保存，防止数据丢失
- ✅ 进度显示和预计剩余时间

## 处理流程

1. **创建备份**: 自动创建 `wikids_final_backup.json` 备份文件
2. **统计信息**: 显示需要处理的记录数
3. **分块处理**: 每次处理100条记录
4. **并发提取**: 使用gemini-3-pro-preview API并发提取keyfacts
5. **保存结果**: 每处理一个块就保存一次中间结果
6. **最终保存**: 保存到 `wikids_final_with_keyfacts.json`

## 输出格式

提取的keyfacts会以JSON字符串格式保存在 `original_data.wikipedia_article.keyfacts` 字段下：

```json
{
  "original_data": {
    "wikipedia_article": {
      "title": "Article Title",
      "content": "Article content...",
      "keyfacts": "[{\"entity\": \"...\", \"behavior\": \"...\", \"context\": \"...\", \"priority\": 1}]"
    }
  }
}
```

## 注意事项

1. **API配置**: 确保 `auth.yaml` 文件中配置了 `gemini-3-pro-preview` 的API密钥
2. **处理时间**: 处理大量数据可能需要较长时间，请耐心等待
3. **网络连接**: 需要稳定的网络连接来调用API
4. **磁盘空间**: 确保有足够的磁盘空间保存结果文件
5. **中断恢复**: 如果处理中断，可以重新运行脚本，已处理的记录会被跳过

## 配置参数

可以在脚本中修改以下参数：

- `chunk_size`: 每次处理的记录数（默认100）
- `max_concurrent`: 最大并发数（默认50）
- `llm_type`: LLM类型（默认"gemini-3-pro-preview"）

## 示例输出

```
================================================================================
Wikipedia Keyfacts提取工具
================================================================================

💾 创建备份文件: datasets/our_dataset/wikids_final_backup.json
✅ 备份完成

📖 加载数据文件...
✅ 总共 6627 条记录

📊 统计信息:
  - 已有keyfacts: 0
  - 需要提取: 6627
  - 无内容: 0

⚠️  将处理 6627 条记录，这可能需要较长时间
是否继续？(y/n): y

🔄 处理数据块 [0 - 99]
📝 提取keyfacts: Article Title 1
📝 提取keyfacts: Article Title 2
...
✅ 成功提取keyfacts (2.5秒): Article Title 1
✅ 已更新keyfacts: Article Title 1
...

📈 进度: 100/6627 (1.5%)
   已用时间: 2.1分钟
   预计剩余: 138.9分钟
💾 保存中间结果...
✅ 已保存到: datasets/our_dataset/wikids_final_with_keyfacts.json
```

