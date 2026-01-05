#!/usr/bin/env python3
"""
筛选内容关联性评分为9或10的数据，并进行数据分析
"""

import json
import os
from typing import Dict, List, Any
from collections import Counter, defaultdict
import statistics

def load_json(file_path: str) -> List[Dict]:
    """加载JSON文件"""
    if not os.path.exists(file_path):
        print(f"⚠️  警告: 文件 {file_path} 不存在")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"✅ 已加载 {file_path}: {len(data)} 条记录")
            return data
    except Exception as e:
        print(f"❌ 加载 {file_path} 时出错: {str(e)}")
        return []

def filter_high_score_articles(articles: List[Dict], min_score: int = 9) -> List[Dict]:
    """筛选评分>=min_score的文章"""
    filtered = []
    skipped = []
    
    for article in articles:
        analysis = article.get("analysis", {})
        score = analysis.get("内容关联性评分", None)
        
        if score is not None:
            # 处理不同类型的评分
            if isinstance(score, (int, float)):
                score_value = float(score)
            elif isinstance(score, str):
                try:
                    score_value = float(score)
                except:
                    score_value = None
            else:
                score_value = None
            
            if score_value is not None and score_value >= min_score:
                filtered.append(article)
            else:
                skipped.append(article)
        else:
            skipped.append(article)
    
    return filtered, skipped

def analyze_filtered_data(articles: List[Dict]) -> Dict[str, Any]:
    """分析筛选后的数据"""
    results = {
        "total_articles": len(articles),
        "source_distribution": {},
        "score_distribution": {},
        "score_statistics": {},
        "category_distribution": {},
        "articles_with_wikipedia": 0,
        "articles_without_wikipedia": 0,
        "average_score": 0,
        "median_score": 0,
    }
    
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
                scores.append(float(score))
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
    
    # 分类分布
    category_counter = Counter(categories)
    results["category_distribution"] = dict(category_counter)
    
    # Wikipedia统计
    results["articles_with_wikipedia"] = has_wikipedia
    results["articles_without_wikipedia"] = no_wikipedia
    
    return results

def print_analysis_results(results: Dict[str, Any], filtered_count: int, original_count: int):
    """打印分析结果"""
    print("=" * 80)
    print("📊 高分数据集分析报告 (评分 ≥ 9)")
    print("=" * 80)
    
    print(f"\n📈 筛选统计:")
    print(f"   原始文章数: {original_count}")
    print(f"   筛选后文章数: {filtered_count}")
    print(f"   保留率: {(filtered_count / original_count * 100):.1f}%" if original_count > 0 else "N/A")
    
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
    
    if results["category_distribution"]:
        print(f"\n📂 分类分布 (Top 15):")
        sorted_categories = sorted(results["category_distribution"].items(), key=lambda x: x[1], reverse=True)[:15]
        for category, count in sorted_categories:
            percentage = (count / results["total_articles"] * 100) if results["total_articles"] > 0 else 0
            print(f"   {category}: {count} ({percentage:.1f}%)")
    
    print("\n" + "=" * 80)

def main():
    """主函数"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 输入文件（合并后的数据集）
    input_file = os.path.join(base_dir, "merged_all_analyzed_articles.json")
    
    # 输出文件
    output_file = os.path.join(base_dir, "filtered_high_score_articles.json")
    analysis_output_file = os.path.join(base_dir, "filtered_high_score_analysis.json")
    
    print("📂 开始加载合并后的数据集...\n")
    
    # 加载数据
    all_articles = load_json(input_file)
    if not all_articles:
        print("❌ 无法加载数据，程序退出")
        return
    
    original_count = len(all_articles)
    print(f"\n✅ 原始数据集: {original_count} 条记录")
    
    # 筛选评分9或10的文章
    print("\n🔍 开始筛选评分 ≥ 9 的文章...")
    filtered_articles, skipped_articles = filter_high_score_articles(all_articles, min_score=9)
    
    print(f"✅ 筛选完成:")
    print(f"   保留: {len(filtered_articles)} 条")
    print(f"   过滤: {len(skipped_articles)} 条")
    
    # 保存筛选后的数据
    print(f"\n💾 保存筛选数据到: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_articles, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 筛选数据保存完成！")
    
    # 进行数据分析
    print("\n📊 开始数据分析...\n")
    analysis_results = analyze_filtered_data(filtered_articles)
    
    # 保存分析结果
    print(f"\n💾 保存分析结果到: {analysis_output_file}")
    with open(analysis_output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, ensure_ascii=False, indent=2)
    
    # 打印分析结果
    print_analysis_results(analysis_results, len(filtered_articles), original_count)
    
    return filtered_articles, analysis_results

if __name__ == "__main__":
    main()

