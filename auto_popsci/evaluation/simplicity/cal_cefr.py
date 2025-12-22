#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用cefrpy包计算文本的CEFR分级
CEFR (Common European Framework of Reference) 欧洲语言共同参考框架
"""

import json
import sys
import os
import re
from typing import List, Dict, Optional, Tuple

try:
    from cefrpy import CEFRAnalyzer
    CEFRPY_AVAILABLE = True
except ImportError:
    print("⚠️ cefrpy库未安装，请运行: pip install cefrpy")
    CEFRPY_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.tag import pos_tag
    NLTK_AVAILABLE = True
    # 尝试下载必要的nltk数据
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("📥 下载nltk数据...")
        nltk.download('punkt', quiet=True)
        nltk.download('averaged_perceptron_tagger', quiet=True)
except ImportError:
    print("⚠️ nltk库未安装，将使用简单的分词方法")
    print("   建议安装: pip install nltk")
    NLTK_AVAILABLE = False


def get_cefr_level_name(level: float) -> str:
    """将CEFR数值等级转换为等级名称"""
    if level < 1.0:
        return "A1 (入门级)"
    elif level < 2.0:
        return "A2 (基础级)"
    elif level < 3.0:
        return "B1 (进阶级)"
    elif level < 4.0:
        return "B2 (高阶级)"
    elif level < 5.0:
        return "C1 (流利级)"
    else:
        return "C2 (精通级)"


def simple_tokenize(text: str) -> List[str]:
    """简单的分词方法（当nltk不可用时使用）"""
    # 移除标点符号，转换为小写，分割单词
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.lower().split()
    return words


def get_pos_tag_simple(word: str) -> str:
    """简单的词性标注（当nltk不可用时使用）"""
    # 这是一个非常简化的词性标注，实际应该使用nltk
    # 默认返回最常见的词性
    return "NN"  # 名词


def tokenize_and_tag(text: str) -> List[Tuple[str, str]]:
    """
    对文本进行分词和词性标注
    
    Returns:
        (单词, 词性标签) 元组列表
    """
    if NLTK_AVAILABLE:
        try:
            words = word_tokenize(text)
            tagged = pos_tag(words)
            # 转换nltk的词性标签为Penn Treebank格式（cefrpy需要的格式）
            return [(word.lower(), tag) for word, tag in tagged if word.isalpha()]
        except Exception as e:
            print(f"⚠️ nltk处理出错，使用简单方法: {e}")
            words = simple_tokenize(text)
            return [(word, get_pos_tag_simple(word)) for word in words]
    else:
        words = simple_tokenize(text)
        return [(word, get_pos_tag_simple(word)) for word in words]


def calculate_text_cefr(text: str, analyzer: CEFRAnalyzer) -> Dict:
    """
    计算单个文本的CEFR等级
    
    Args:
        text: 要分析的文本
        analyzer: CEFRAnalyzer实例
    
    Returns:
        包含CEFR等级信息的字典
    """
    if not text or not text.strip():
        return {
            'level': None,
            'level_name': 'N/A',
            'error': '文本为空',
            'word_count': 0,
            'analyzed_words': 0
        }
    
    try:
        # 分词和词性标注
        word_pos_pairs = tokenize_and_tag(text)
        
        if not word_pos_pairs:
            return {
                'level': None,
                'level_name': 'N/A',
                'error': '无法分词',
                'word_count': 0,
                'analyzed_words': 0
            }
        
        # 计算每个单词的CEFR等级
        levels = []
        analyzed_count = 0
        
        for word, pos_tag in word_pos_pairs:
            # 尝试获取单词在该词性下的CEFR等级
            level = analyzer.get_word_pos_level_float(word, pos_tag)
            if level is not None:
                levels.append(level)
                analyzed_count += 1
            else:
                # 如果特定词性下没有，尝试获取平均等级
                avg_level = analyzer.get_average_word_level_float(word)
                if avg_level is not None:
                    levels.append(avg_level)
                    analyzed_count += 1
        
        if not levels:
            return {
                'level': None,
                'level_name': 'N/A',
                'error': '没有找到任何单词的CEFR等级',
                'word_count': len(word_pos_pairs),
                'analyzed_words': 0
            }
        
        # 计算平均CEFR等级
        avg_level = sum(levels) / len(levels)
        
        return {
            'level': avg_level,
            'level_name': get_cefr_level_name(avg_level),
            'error': None,
            'word_count': len(word_pos_pairs),
            'analyzed_words': analyzed_count,
            'min_word_level': min(levels),
            'max_word_level': max(levels)
        }
    except Exception as e:
        return {
            'level': None,
            'level_name': 'N/A',
            'error': str(e),
            'word_count': 0,
            'analyzed_words': 0
        }


def calculate_corpus_cefr(texts: List[str], analyzer: CEFRAnalyzer) -> Dict:
    """
    计算文本集合的平均CEFR等级
    
    Args:
        texts: 文本列表
        analyzer: CEFRAnalyzer实例
    
    Returns:
        包含统计信息的字典
    """
    if not texts:
        return {
            'average_level': None,
            'average_level_name': 'N/A',
            'min_level': None,
            'max_level': None,
            'total_texts': 0,
            'valid_texts': 0
        }
    
    levels = []
    valid_count = 0
    
    for text in texts:
        result = calculate_text_cefr(text, analyzer)
        if result['level'] is not None:
            levels.append(result['level'])
            valid_count += 1
    
    if not levels:
        return {
            'average_level': None,
            'average_level_name': 'N/A',
            'min_level': None,
            'max_level': None,
            'total_texts': len(texts),
            'valid_texts': 0
        }
    
    avg_level = sum(levels) / len(levels)
    min_level = min(levels)
    max_level = max(levels)
    
    return {
        'average_level': avg_level,
        'average_level_name': get_cefr_level_name(avg_level),
        'min_level': min_level,
        'min_level_name': get_cefr_level_name(min_level),
        'max_level': max_level,
        'max_level_name': get_cefr_level_name(max_level),
        'total_texts': len(texts),
        'valid_texts': valid_count
    }


def load_articles_from_json(file_path: str, content_field: str = 'content') -> List[str]:
    """
    从JSON文件加载文章内容
    
    Args:
        file_path: JSON文件路径
        content_field: 内容字段名，默认为'content'
    
    Returns:
        文章内容列表
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        articles = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    content = item.get(content_field, '')
                    if content and content.strip():
                        articles.append(content.strip())
        elif isinstance(data, dict):
            content = data.get(content_field, '')
            if content and content.strip():
                articles.append(content.strip())
        
        return articles
    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
        return []
    except Exception as e:
        print(f"❌ 加载数据时出错: {e}")
        return []


def main():
    """主函数"""
    if not CEFRPY_AVAILABLE:
        print("❌ cefrpy库未安装，无法继续")
        print("   请运行: pip install cefrpy")
        return
    
    print("🔧 使用cefrpy计算文本CEFR分级...")
    
    # 初始化CEFR分析器
    try:
        analyzer = CEFRAnalyzer()
        print("✅ CEFR分析器初始化成功")
    except Exception as e:
        print(f"❌ CEFR分析器初始化失败: {e}")
        return
    
    # 示例1: 分析单个文本
    print("\n" + "="*60)
    print("示例1: 分析单个文本")
    print("="*60)
    
    sample_text = "The sun is very bright today. It makes me happy."
    print(f"文本: {sample_text}")
    result = calculate_text_cefr(sample_text, analyzer)
    print(f"CEFR等级: {result['level']:.2f}")
    print(f"CEFR等级名称: {result['level_name']}")
    
    # 示例2: 从JSON文件加载并分析
    print("\n" + "="*60)
    print("示例2: 分析JSON文件中的文章")
    print("="*60)
    
    # 检查是否有命令行参数指定文件路径
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        # 默认使用nasa_kids_articles.json
        json_file = 'datasets/our_dataset/nasa_kids_articles.json'
    
    if os.path.exists(json_file):
        print(f"📂 加载文件: {json_file}")
        articles = load_articles_from_json(json_file)
        
        if articles:
            print(f"✅ 成功加载 {len(articles)} 篇文章")
            
            # 计算每篇文章的CEFR等级
            print("\n📊 开始计算CEFR等级...")
            results = []
            for i, article in enumerate(articles[:10], 1):  # 只分析前10篇作为示例
                result = calculate_text_cefr(article, analyzer)
                results.append({
                    'article_index': i,
                    'text_length': len(article),
                    **result
                })
                print(f"文章 {i}: CEFR等级 = {result['level']:.2f} ({result['level_name']})")
            
            # 计算整体统计
            print("\n" + "="*60)
            print("整体统计")
            print("="*60)
            corpus_stats = calculate_corpus_cefr(articles, analyzer)
            print(f"总文章数: {corpus_stats['total_texts']}")
            print(f"有效文章数: {corpus_stats['valid_texts']}")
            print(f"平均CEFR等级: {corpus_stats['average_level']:.2f}")
            print(f"平均CEFR等级名称: {corpus_stats['average_level_name']}")
            print(f"最低CEFR等级: {corpus_stats['min_level']:.2f} ({corpus_stats['min_level_name']})")
            print(f"最高CEFR等级: {corpus_stats['max_level']:.2f} ({corpus_stats['max_level_name']})")
            
            # 保存结果
            output_file = 'cefr_results.json'
            output_data = {
                'file_analyzed': json_file,
                'corpus_statistics': corpus_stats,
                'sample_results': results[:10]  # 保存前10篇的详细结果
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 详细结果已保存到: {output_file}")
        else:
            print("⚠️ 文件中没有找到有效的文章内容")
    else:
        print(f"⚠️ 文件不存在: {json_file}")
        print("   使用方法: python cal_cefr.py <json_file_path>")
        print("   或直接运行脚本，将使用默认文件路径")


if __name__ == "__main__":
    main()

