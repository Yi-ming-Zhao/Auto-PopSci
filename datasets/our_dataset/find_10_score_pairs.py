import json
import collections
import sys

# 流式读取大JSON文件
scores = []
ten_point_pairs = []
count = 0

with open("datasets/our_dataset/science_alert_analyzed_articles.json", "r") as f:
    content = f.read()

content = json.loads(content)
for item in content:
    score = item["analysis"]["内容关联性评分"]
    if score == 10:
        ten_point_pairs.append(item)
        count += 1

with open(
    "datasets/our_dataset/science_alert_analyzed_articles_score_10.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(ten_point_pairs, f, ensure_ascii=False, indent=2)

# 计算分布
score_counts = collections.Counter(scores)
total = len(scores)

print("内容关联性评分分布报告")
print("=" * 50)
print(f"总数据条数: {total}")
print(f"处理行数: {count}")
print()

# 按评分从高到低排序
sorted_scores = sorted(score_counts.keys(), reverse=True)
for score in sorted_scores:
    count_score = score_counts[score]
    percentage = (count_score / total) * 100 if total > 0 else 0
    print(f"评分 {score}: {count_score} 条 ({percentage:.2f}%)")

if scores:
    print()
    print("评分范围统计:")
    print(f"最高评分: {max(scores)}")
    print(f"最低评分: {min(scores)}")
    print(f"平均评分: {sum(scores)/total:.2f}")
else:
    print("未找到任何评分数据")
