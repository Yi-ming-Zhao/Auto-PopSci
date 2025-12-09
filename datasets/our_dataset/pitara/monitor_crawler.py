#!/usr/bin/env python3
"""
监控 Pitara 爬虫进度
"""
import os
import json
import time
import subprocess
from datetime import datetime

def check_crawler_status():
    """检查爬虫状态"""
    print("=" * 60)
    print(f"Pitara 爬虫进度监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # 检查进程
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    is_running = 'pitara_crawler.py' in result.stdout
    
    if is_running:
        print("✅ 爬虫正在运行...")
        # 提取进程信息
        for line in result.stdout.split('\n'):
            if 'pitara_crawler.py' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) > 10:
                    cpu = parts[2]
                    mem = parts[3]
                    print(f"   CPU 使用率: {cpu}%")
                    print(f"   内存使用: {mem}%")
                    break
    else:
        print("❌ 爬虫未在运行")
    print()
    
    # 检查输出文件
    output_file = "datasets/our_dataset/pitara/all_pitara_articles.json"
    if os.path.exists(output_file):
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
        mtime = datetime.fromtimestamp(os.path.getmtime(output_file))
        
        print(f"📄 输出文件: {output_file}")
        print(f"📊 文件大小: {file_size:.2f} MB")
        print(f"⏰ 最后更新: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 读取并分析文件
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            total = len(articles)
            print(f"📈 文章总数: {total} / 2411")
            
            if total > 0:
                progress = (total / 2411) * 100
                print(f"📊 完成进度: {progress:.1f}%")
                
                # 检查内容质量（采样几篇文章）
                sample_size = min(5, total)
                has_full_content = 0
                avg_length = 0
                
                for i in range(0, min(sample_size * 10, total), max(1, total // sample_size)):
                    article = articles[i]
                    content = article.get('content', '')
                    if content:
                        avg_length += len(content)
                        if len(content) > 1000:  # 认为超过1000字符是完整内容
                            has_full_content += 1
                
                if sample_size > 0:
                    avg_length = avg_length / sample_size
                    print(f"📝 平均内容长度: {avg_length:.0f} 字符（采样{sample_size}篇）")
                    
                    # 检查是否有清理后的内容（不包含面包屑）
                    sample_article = articles[0] if articles else None
                    if sample_article:
                        content = sample_article.get('content', '')
                        has_breadcrumb = 'Home/' in content
                        has_metadata = bool(content and any(x in content for x in ['words |', 'Readability:', 'Filed under:']))
                        
                        if not has_breadcrumb and not has_metadata:
                            print("✨ 内容已清理（无面包屑和元数据）")
                        elif has_breadcrumb or has_metadata:
                            print("⚠️  内容可能未完全清理")
                            
        except Exception as e:
            print(f"⚠️  读取文件时出错: {e}")
    else:
        print("⏳ 输出文件尚未生成")
    
    print()
    print("=" * 60)
    print("💡 提示: 使用 'tail -f /tmp/pitara_crawl.log' 查看实时日志")
    print("=" * 60)

if __name__ == "__main__":
    check_crawler_status()

