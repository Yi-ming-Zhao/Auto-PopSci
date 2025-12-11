# 大文件下载说明

由于Git和GitHub的文件大小限制，某些大文件无法直接包含在此仓库中。

## 大文件列表和下载位置

1. datasets/our_dataset/merged_popular_science_articles.json (58.59 MB)
   - 已压缩为 datasets/our_dataset/merged_popular_science_articles.json.gz
   - 下载链接：[请上传到云存储后提供链接]

2. auto_popsci/evaluation/vividness/figurativeness/MelBERT/melbert_ckpt/pytorch_model.bin (484.60 MB)
   - 下载链接：[请上传到云存储后提供链接]

## 如何使用这些文件

1. 下载上述大文件
2. 将它们放置在指定的目录中
3. 对于压缩的JSON文件，请使用以下命令解压：
   ```
   gunzip datasets/our_dataset/merged_popular_science_articles.json.gz
   ```

## 推荐的云存储服务

- Google Drive
- 百度网盘
- 阿里云盘
- Mega.nz

## Git LFS备选方案

如果您有Git LFS的访问权限，可以使用以下命令获取这些文件：
```
git lfs pull
```
