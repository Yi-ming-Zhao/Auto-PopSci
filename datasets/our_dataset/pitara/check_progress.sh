#!/bin/bash
# 监控 Pitara 爬虫进度

echo "=== Pitara 爬虫进度监控 ==="
echo ""

# 检查进程是否运行
if ps aux | grep -q "[p]itara_crawler.py"; then
    echo "✅ 爬虫正在运行..."
    echo ""
    
    # 显示进程信息
    ps aux | grep "[p]itara_crawler.py" | head -1
    echo ""
    
    # 检查输出文件
    output_file="datasets/our_dataset/pitara/all_pitara_articles.json"
    if [ -f "$output_file" ]; then
        file_size=$(du -h "$output_file" | cut -f1)
        echo "📄 输出文件: $output_file"
        echo "📊 文件大小: $file_size"
        
        # 计算已爬取的文章数量
        if command -v python3 &> /dev/null; then
            article_count=$(python3 -c "import json; f=open('$output_file'); data=json.load(f); print(len(data))" 2>/dev/null || echo "0")
            echo "📈 已爬取文章数: $article_count / 2411"
            
            if [ "$article_count" != "0" ]; then
                progress=$(echo "scale=1; $article_count * 100 / 2411" | bc 2>/dev/null || echo "0")
                echo "📊 完成进度: ${progress}%"
            fi
        fi
    else
        echo "⏳ 输出文件尚未生成，爬虫正在初始化..."
    fi
else
    echo "❌ 爬虫未在运行"
    echo ""
    echo "查看日志: tail -f /tmp/pitara_crawl.log"
fi

echo ""
echo "查看实时日志: tail -f /tmp/pitara_crawl.log"

