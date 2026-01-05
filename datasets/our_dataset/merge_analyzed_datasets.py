#!/usr/bin/env python3
"""
合并多个analyzed数据集文件并进行数据分析
"""

import json
import os
from typing import Dict, List, Any
from collections import Counter, defaultdict
import statistics

def load_json(file_path: str) -> List[Dict]:
    """加载JSON文件"""
    if not os.path.exists(file_path):
        print(f"⚠️  警告: 文件 {file_path} 不存在，跳过")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"✅ 已加载 {file_path}: {len(data)} 条记录")
            return data
    except Exception as e:
        print(f"❌ 加载 {file_path} 时出错: {str(e)}")
        return []

def merge_datasets():
    """合并所有数据集"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 要合并的文件列表
    files_to_merge = [
        "science_alert_analyzed_articles_score_9.json",
        "science_alert_analyzed_articles_score_10.json",
        "analyzed_articles_score_9.json",
        "analyzed_articles_score_10.json",
        "snexplorers_analyzed_articles.json",
    ]
    
    # 输出路径
    output_path = os.path.join(base_dir, "merged_all_analyzed_articles.json")
    analysis_output_path = os.path.join(base_dir, "merged_datasets_analysis.json")
    
    print("📂 开始加载数据集...\n")
    
    # 加载所有数据
    all_articles = []
    file_stats = {}
    
    for filename in files_to_merge:
        file_path = os.path.join(base_dir, filename)
        data = load_json(file_path)
        if data:
            all_articles.extend(data)
            file_stats[filename] = len(data)
    
    print(f"\n✅ 总共加载 {len(all_articles)} 条记录")
    
    # 保存合并后的数据
    print(f"\n💾 保存合并数据到: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 合并完成！")
    
    # 进行数据分析
    print("\n📊 开始数据分析...\n")
    analysis_results = analyze_data(all_articles, file_stats)
    
    # 保存分析结果
    print(f"\n💾 保存分析结果到: {analysis_output_path}")
    with open(analysis_output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, ensure_ascii=False, indent=2)
    
    # 打印分析结果
    print_analysis_results(analysis_results)
    
    return all_articles, analysis_results

def analyze_data(articles: List[Dict], file_stats: Dict[str, int]) -> Dict[str, Any]:
    """分析数据"""
    results = {
        "file_statistics": file_stats,
        "total_articles": len(articles),
        "source_distribution": {},
        "score_distribution": {},
        "score_statistics": {},
        "category_distribution": {},
        "articles_with_wikipedia": 0,
        "articles_without_wikipedia": 0,
        "average_score": 0,
        "median_score": 0,
        "high_score_articles": {},
    }
    
    # 统计来源分布
    sources = []
    scores = []
    categories = []
    has_wikipedia = 0
    no_wikipedia = 0
    
    for article in articles:
        # 来源统计
        original_data = article.get("original_data", {})
        source = original_data.get("source", "unknown")
        sources.append(source)
        
        # 评分统计
        analysis = article.get("analysis", {})
        score = analysis.get("内容关联性评分", None)
        if score is not None:
            if isinstance(score, (int, float)):
                scores.append(score)
            elif isinstance(score, str):
                try:
                    scores.append(float(score))
                except:
                    pass
        
        # 分类统计
        popsci_article = original_data.get("popsci_article", {})
        category = popsci_article.get("category", "unknown")
        if category:
            categories.append(category)
        
        # Wikipedia统计
        wikipedia_article = original_data.get("wikipedia_article", {})
        if wikipedia_article and wikipedia_article.get("title"):
            has_wikipedia += 1
        else:
            no_wikipedia += 1
    
    # 来源分布
    source_counter = Counter(sources)
    results["source_distribution"] = dict(source_counter)
    
    # 评分分布
    if scores:
        score_counter = Counter(scores)
        results["score_distribution"] = {str(k): v for k, v in sorted(score_counter.items())}
        results["average_score"] = round(statistics.mean(scores), 2)
        results["median_score"] = round(statistics.median(scores), 2)
        results["score_statistics"] = {
            "min": min(scores),
            "max": max(scores),
            "mean": round(statistics.mean(scores), 2),
            "median": round(statistics.median(scores), 2),
            "stdev": round(statistics.stdev(scores), 2) if len(scores) > 1 else 0,
        }
        
        # 高分文章统计
        results["high_score_articles"] = {
            "score_10": sum(1 for s in scores if s == 10),
            "score_9": sum(1 for s in scores if s == 9),
            "score_8_plus": sum(1 for s in scores if s >= 8),
            "score_7_plus": sum(1 for s in scores if s >= 7),
        }
    
    # 分类分布
    category_counter = Counter(categories)
    results["category_distribution"] = dict(category_counter)
    
    # Wikipedia统计
    results["articles_with_wikipedia"] = has_wikipedia
    results["articles_without_wikipedia"] = no_wikipedia
    
    return results

def print_analysis_results(results: Dict[str, Any]):
    """打印分析结果"""
    print("=" * 80)
    print("📊 数据集分析报告")
    print("=" * 80)
    
    print("\n📁 文件统计:")
    for filename, count in results["file_statistics"].items():
        print(f"   {filename}: {count} 条")
    
    print(f"\n📈 总体统计:")
    print(f"   总文章数: {results['total_articles']}")
    print(f"   有Wikipedia文章: {results['articles_with_wikipedia']}")
    print(f"   无Wikipedia文章: {results['articles_without_wikipedia']}")
    
    print(f"\n📊 来源分布:")
    for source, count in sorted(results["source_distribution"].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / results["total_articles"] * 100) if results["total_articles"] > 0 else 0
        print(f"   {source}: {count} ({percentage:.1f}%)")
    
    if results["score_statistics"]:
        print(f"\n⭐ 评分统计:")
        stats = results["score_statistics"]
        print(f"   平均分: {stats['mean']}")
        print(f"   中位数: {stats['median']}")
        print(f"   最高分: {stats['max']}")
        print(f"   最低分: {stats['min']}")
        print(f"   标准差: {stats['stdev']}")
        
        print(f"\n📊 评分分布:")
        total_scored = sum(results["score_distribution"].values())
        for score, count in sorted(results["score_distribution"].items(), key=lambda x: float(x[0]), reverse=True):
            percentage = (count / total_scored * 100) if total_scored > 0 else 0
            print(f"   评分 {score}: {count} 条 ({percentage:.1f}%)")
        
        print(f"\n🏆 高分文章统计:")
        high_scores = results["high_score_articles"]
        print(f"   10分: {high_scores['score_10']} 条")
        print(f"   9分: {high_scores['score_9']} 条")
        print(f"   ≥8分: {high_scores['score_8_plus']} 条")
        print(f"   ≥7分: {high_scores['score_7_plus']} 条")
    
    if results["category_distribution"]:
        print(f"\n📂 分类分布 (Top 10):")
        sorted_categories = sorted(results["category_distribution"].items(), key=lambda x: x[1], reverse=True)[:10]
        for category, count in sorted_categories:
            percentage = (count / results["total_articles"] * 100) if results["total_articles"] > 0 else 0
            print(f"   {category}: {count} ({percentage:.1f}%)")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    merge_datasets()

