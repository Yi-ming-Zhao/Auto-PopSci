#!/bin/bash
# 通用数据集评测脚本的Shell包装器

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Python脚本路径
PYTHON_SCRIPT="$SCRIPT_DIR/evaluate_dataset.py"

# 默认参数
DEFAULT_LLM_TYPE="deepseek"
DEFAULT_PROMPT_TEMPLATE="keyfact_alignment"
DEFAULT_DATASET_FORMAT="json"

# 显示帮助信息
show_help() {
    cat << EOF
通用数据集评测脚本

用法:
    $0 --input_file <输入文件> --output_file <输出文件> [选项]

必需参数:
    --input_file <路径>          输入数据文件路径（JSON格式）
    --output_file <路径>         输出结果文件路径（JSON格式）

可选参数:
    --model_name <名称>          模型名称（如果不指定，将自动检测）
    --popsci_field <路径>        生成的科普文章字段路径（如: "model.content"）
    --original_field <路径>      Wikipedia原文字段路径（如: "original_data.wikipedia_article.content"）
    --reference_field <路径>     参考科普文章字段路径（可选）
    --skip_coherence             跳过连贯性评估（PPL）
    --no_auto_generate_keyfacts  禁用自动生成keyfacts
    --ground_truth_keyfacts_dir <路径>  参考keyfacts目录路径
    --generated_keyfacts_dir <路径>     生成的keyfacts目录路径
    --dataset_format <格式>       数据集格式（json或jsonl，默认: json）
    --llm_type <类型>            LLM类型（默认: deepseek）
    --prompt_template <名称>      Prompt模板名称（默认: keyfact_alignment）

示例:
    # 基本用法（自动检测所有字段）
    $0 --input_file data.json --output_file results.json

    # 指定模型名称
    $0 --input_file data.json --output_file results.json --model_name grok-4-1-fast-reasoning

    # 指定字段路径
    $0 --input_file data.json --output_file results.json \\
        --popsci_field "grok-4-1-fast-reasoning.content" \\
        --original_field "original_data.wikipedia_article.content"

    # 跳过连贯性评估
    $0 --input_file data.json --output_file results.json --skip_coherence

    # 使用文件中的keyfacts而不是自动生成
    $0 --input_file data.json --output_file results.json \\
        --ground_truth_keyfacts_dir "path/to/ground_truth_keyfacts" \\
        --generated_keyfacts_dir "path/to/generated_keyfacts" \\
        --no_auto_generate_keyfacts

EOF
}

# 检查参数
if [ $# -eq 0 ] || [[ "$*" =~ --help|-h ]]; then
    show_help
    exit 0
fi

# 检查Python脚本是否存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ 错误: Python脚本不存在: $PYTHON_SCRIPT"
    exit 1
fi

# 检查Python是否可用
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3 命令"
    exit 1
fi

# 切换到项目根目录
cd "$PROJECT_ROOT" || exit 1

# 执行Python脚本，传递所有参数
echo "🚀 启动评测..."
echo "工作目录: $PROJECT_ROOT"
echo ""

python3 "$PYTHON_SCRIPT" "$@"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "✅ 评测完成！"
else
    echo ""
    echo "❌ 评测失败，退出码: $exit_code"
fi

exit $exit_code

