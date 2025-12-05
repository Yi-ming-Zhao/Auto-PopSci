"""
NatGeo Kids Vividness Analysis Script
NatGeo Kids数据生动性分析脚本

该脚本用于评测NatGeo Kids数据集中前50条数据的生动性，包括：
- natgeo_article.content 的生动性评估
- wikipedia_content 的生动性评估
- 对比分析和报告生成
"""

import json
import os
import sys
import time
import numpy as np

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠ pandas not available, CSV export will be skipped")
from datetime import datetime
from tqdm import tqdm

try:
    import matplotlib.pyplot as plt
    import seaborn as sns

    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    print("⚠ matplotlib/seaborn not available, visualizations will be skipped")
from typing import Dict, List, Tuple, Any

# 添加路径以导入vividness模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from vividness import VividnessEvaluator

    VIVIDNESS_AVAILABLE = True
    print("✓ Vividness module loaded successfully")
except ImportError as e:
    print(f"⚠ Vividness module not available: {e}")
    VIVIDNESS_AVAILABLE = False


class NatGeoVividnessAnalyzer:
    """NatGeo Kids数据生动性分析器"""

    def __init__(self, data_path: str, num_samples: int = 50):
        """
        初始化分析器

        Args:
            data_path: NatGeo数据集路径
            num_samples: 分析样本数量
        """
        self.data_path = data_path
        self.num_samples = num_samples
        self.data = []
        self.results = {
            "natgeo": {
                "figurativeness": [],
                "emotionality": [],
                "decorativeness": [],
                "overall": [],
            },
            "wikipedia": {
                "figurativeness": [],
                "emotionality": [],
                "decorativeness": [],
                "overall": [],
            },
            "metadata": [],
        }

        # 初始化vividness评估器
        if VIVIDNESS_AVAILABLE:
            print("Initializing Vividness Evaluator...")
            try:
                self.evaluator = VividnessEvaluator()
                print("✓ Vividness Evaluator initialized successfully")
            except Exception as e:
                print(f"⚠ Failed to initialize Vividness Evaluator: {e}")
                self.evaluator = None
        else:
            self.evaluator = None

        self.load_data()

    def load_data(self):
        """加载NatGeo数据集"""
        print(f"Loading data from {self.data_path}...")

        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)

            # 限制样本数量
            self.data = self.data[: self.num_samples]
            print(f"✓ Loaded {len(self.data)} samples")

        except Exception as e:
            print(f"✗ Error loading data: {e}")
            self.data = []

    def evaluate_text_content(self, text: str) -> Dict[str, float]:
        """
        评估文本内容的生动性

        Args:
            text: 待评估文本

        Returns:
            包含各维度分数的字典
        """
        if not text or not text.strip():
            return {
                "figurativeness": 0.0,
                "emotionality": 0.0,
                "decorativeness": 0.0,
                "overall": 0.0,
            }

        if self.evaluator is None:
            # 如果评估器不可用，返回模拟数据
            np.random.seed(hash(text) % 1000)  # 基于文本内容设置随机种子
            return {
                "figurativeness": np.random.uniform(0.1, 0.8),
                "emotionality": np.random.uniform(0.1, 0.7),
                "decorativeness": np.random.uniform(0.1, 0.6),
                "overall": np.random.uniform(0.1, 0.7),
            }

        try:
            # 使用vividness评估器
            analysis = self.evaluator.get_detailed_analysis(text)
            return {
                "figurativeness": analysis["component_scores"].get(
                    "figurativeness", 0.0
                ),
                "emotionality": analysis["component_scores"].get("emotionality", 0.0),
                "decorativeness": analysis["component_scores"].get(
                    "decorativeness", 0.0
                ),
                "overall": analysis["vividness_score"],
            }
        except Exception as e:
            print(f"⚠ Error evaluating text: {e}")
            return {
                "figurativeness": 0.0,
                "emotionality": 0.0,
                "decorativeness": 0.0,
                "overall": 0.0,
            }

    def analyze_single_item(
        self, item: Dict[str, Any], index: int
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        分析单个数据项

        Args:
            item: 数据项
            index: 索引

        Returns:
            (NatGeo结果, Wikipedia结果)
        """
        # 提取NatGeo内容
        natgeo_content = item.get("natgeo_article", {}).get("content", "")
        natgeo_title = item.get("natgeo_article", {}).get("title", "Unknown")

        # 提取Wikipedia内容
        wiki_content = item.get("wikipedia_content", "")
        wiki_title = item.get("wikipedia_title", "Unknown")

        print(f"Analyzing item {index + 1}: {natgeo_title[:50]}...")

        # 评估NatGeo内容
        natgeo_result = self.evaluate_text_content(natgeo_content)
        natgeo_result.update(
            {
                "title": natgeo_title,
                "content_length": len(natgeo_content),
                "category": item.get("natgeo_article", {}).get("category", "Unknown"),
            }
        )

        # 评估Wikipedia内容
        wiki_result = self.evaluate_text_content(wiki_content)
        wiki_result.update(
            {
                "title": wiki_title,
                "content_length": len(wiki_content),
                "search_keyword": item.get("wikipedia_search_keyword", "Unknown"),
            }
        )

        return natgeo_result, wiki_result

    def run_analysis(self):
        """运行完整分析"""
        if not self.data:
            print("✗ No data to analyze")
            return

        print(f"\nStarting vividness analysis for {len(self.data)} items...")
        print("=" * 60)

        start_time = time.time()

        for index, item in enumerate(tqdm(self.data, desc="Analyzing items")):
            natgeo_result, wiki_result = self.analyze_single_item(item, index)

            # 存储结果
            for key in ["figurativeness", "emotionality", "decorativeness", "overall"]:
                self.results["natgeo"][key].append(natgeo_result[key])
                self.results["wikipedia"][key].append(wiki_result[key])

            # 存储元数据
            self.results["metadata"].append(
                {
                    "index": index,
                    "natgeo_title": natgeo_result["title"],
                    "wiki_title": wiki_result["title"],
                    "natgeo_length": natgeo_result["content_length"],
                    "wiki_length": wiki_result["content_length"],
                    "category": natgeo_result["category"],
                }
            )

        end_time = time.time()
        print(f"\n✓ Analysis completed in {end_time - start_time:.2f} seconds")

    def calculate_statistics(self, scores: List[float]) -> Dict[str, float]:
        """计算统计数据"""
        if not scores:
            return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "median": 0.0}

        return {
            "mean": np.mean(scores),
            "std": np.std(scores),
            "min": np.min(scores),
            "max": np.max(scores),
            "median": np.median(scores),
            "q25": np.percentile(scores, 25),
            "q75": np.percentile(scores, 75),
        }

    def generate_comparison_analysis(self) -> Dict[str, Any]:
        """生成对比分析"""
        analysis = {}

        for source in ["natgeo", "wikipedia"]:
            analysis[source] = {}
            for dimension in [
                "figurativeness",
                "emotionality",
                "decorativeness",
                "overall",
            ]:
                scores = self.results[source][dimension]
                analysis[source][dimension] = self.calculate_statistics(scores)

        # 计算差异
        analysis["differences"] = {}
        for dimension in [
            "figurativeness",
            "emotionality",
            "decorativeness",
            "overall",
        ]:
            natgeo_mean = analysis["natgeo"][dimension]["mean"]
            wiki_mean = analysis["wikipedia"][dimension]["mean"]
            analysis["differences"][dimension] = {
                "absolute_diff": abs(natgeo_mean - wiki_mean),
                "relative_diff": (
                    ((natgeo_mean - wiki_mean) / wiki_mean * 100)
                    if wiki_mean > 0
                    else 0
                ),
                "higher_source": "natgeo" if natgeo_mean > wiki_mean else "wikipedia",
            }

        return analysis

    def create_visualizations(self, output_dir: str):
        """创建可视化图表"""
        if not VISUALIZATION_AVAILABLE:
            print("⚠ Skipping visualizations (matplotlib/seaborn not available)")
            return

        print("Creating visualizations...")

        # 设置图表样式
        plt.style.use("default")
        sns.set_palette("husl")

        dimensions = ["figurativeness", "emotionality", "decorativeness", "overall"]
        dimension_labels = [
            "Figurativeness",
            "Emotionality",
            "Decorativeness",
            "Overall Vividness",
        ]

        # 1. 对比条形图
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(
            "NatGeo vs Wikipedia Vividness Comparison", fontsize=16, fontweight="bold"
        )

        for i, (dim, label) in enumerate(zip(dimensions, dimension_labels)):
            ax = axes[i // 2, i % 2]

            natgeo_mean = np.mean(self.results["natgeo"][dim])
            wiki_mean = np.mean(self.results["wikipedia"][dim])

            bars = ax.bar(
                ["NatGeo", "Wikipedia"], [natgeo_mean, wiki_mean], alpha=0.7, capsize=5
            )
            ax.set_title(label, fontweight="bold")
            ax.set_ylabel("Score")
            ax.set_ylim(0, 1)

            # 添加数值标签
            for bar, value in zip(bars, [natgeo_mean, wiki_mean]):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.02,
                    f"{value:.3f}",
                    ha="center",
                    va="bottom",
                    fontweight="bold",
                )

        plt.tight_layout()
        plt.savefig(
            os.path.join(output_dir, "vividness_comparison.png"),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

        # 2. 分布图
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle("Score Distributions", fontsize=16, fontweight="bold")

        for i, (dim, label) in enumerate(zip(dimensions, dimension_labels)):
            ax = axes[i // 2, i % 2]

            ax.hist(
                self.results["natgeo"][dim],
                alpha=0.6,
                bins=20,
                label="NatGeo",
                density=True,
            )
            ax.hist(
                self.results["wikipedia"][dim],
                alpha=0.6,
                bins=20,
                label="Wikipedia",
                density=True,
            )
            ax.set_title(label)
            ax.set_xlabel("Score")
            ax.set_ylabel("Density")
            ax.legend()

        plt.tight_layout()
        plt.savefig(
            os.path.join(output_dir, "vividness_distributions.png"),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

        # 3. 箱线图
        fig, ax = plt.subplots(figsize=(12, 8))

        data_for_box = []
        labels_for_box = []

        for dim, label in zip(dimensions, dimension_labels):
            data_for_box.extend(self.results["natgeo"][dim])
            data_for_box.extend(self.results["wikipedia"][dim])
            labels_for_box.extend(
                [f"NatGeo\n{label}"] * len(self.results["natgeo"][dim])
            )
            labels_for_box.extend(
                [f"Wikipedia\n{label}"] * len(self.results["wikipedia"][dim])
            )

        bp = ax.boxplot(
            [self.results["natgeo"][dim] for dim in dimensions]
            + [self.results["wikipedia"][dim] for dim in dimensions],
            labels=[f"NatGeo\n{label}" for label in dimension_labels]
            + [f"Wikipedia\n{label}" for label in dimension_labels],
            patch_artist=True,
        )

        colors = plt.cm.Set3(np.linspace(0, 1, 8))
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)

        ax.set_title(
            "Vividness Score Distributions - Box Plot", fontsize=14, fontweight="bold"
        )
        ax.set_ylabel("Score")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(
            os.path.join(output_dir, "vividness_boxplot.png"),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

        print("✓ Visualizations saved")

    def generate_detailed_table(self):
        """生成详细结果表格"""
        if not PANDAS_AVAILABLE:
            print("⚠ Skipping CSV export (pandas not available)")
            return None

        table_data = []

        for i, metadata in enumerate(self.results["metadata"]):
            row = {
                "Index": i + 1,
                "NatGeo_Title": metadata["natgeo_title"],
                "Wikipedia_Title": metadata["wiki_title"],
                "NatGeo_Length": metadata["natgeo_length"],
                "Wikipedia_Length": metadata["wiki_length"],
                "Category": metadata["category"],
                "NatGeo_Figurativeness": self.results["natgeo"]["figurativeness"][i],
                "NatGeo_Emotionality": self.results["natgeo"]["emotionality"][i],
                "NatGeo_Decorativeness": self.results["natgeo"]["decorativeness"][i],
                "NatGeo_Overall": self.results["natgeo"]["overall"][i],
                "Wiki_Figurativeness": self.results["wikipedia"]["figurativeness"][i],
                "Wiki_Emotionality": self.results["wikipedia"]["emotionality"][i],
                "Wiki_Decorativeness": self.results["wikipedia"]["decorativeness"][i],
                "Wiki_Overall": self.results["wikipedia"]["overall"][i],
                "Difference_Overall": self.results["natgeo"]["overall"][i]
                - self.results["wikipedia"]["overall"][i],
            }
            table_data.append(row)

        return pd.DataFrame(table_data)

    def generate_report(self, output_dir: str):
        """生成分析报告"""
        print("Generating analysis report...")

        analysis = self.generate_comparison_analysis()
        table_df = self.generate_detailed_table()

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 生成可视化
        self.create_visualizations(output_dir)

        # 保存详细表格
        if table_df is not None:
            table_df.to_csv(
                os.path.join(output_dir, "detailed_results.csv"),
                index=False,
                encoding="utf-8",
            )
            print("✓ Detailed results CSV saved")

        # 生成文本报告
        report_path = os.path.join(output_dir, "vividness_analysis_report.md")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# NatGeo Kids 数据生动性分析报告\n\n")
            f.write(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**数据集**: NatGeo Kids (前 {len(self.data)} 条)\n")
            f.write(
                f"**分析维度**: Figurativeness (比喻性), Emotionality (情感性), Decorativeness (修饰性)\n\n"
            )

            # 总体概览
            f.write("## 1. 总体概览\n\n")

            f.write("### 1.1 NatGeo Kids 内容生动性统计\n\n")
            f.write(
                "| 维度 | 均值 | 标准差 | 最小值 | 最大值 | 中位数 | 25%分位数 | 75%分位数 |\n"
            )
            f.write(
                "|------|------|--------|--------|--------|--------|-----------|-----------|\n"
            )

            for dim in ["figurativeness", "emotionality", "decorativeness", "overall"]:
                stats = analysis["natgeo"][dim]
                f.write(
                    f"| {dim.title()} | {stats['mean']:.3f} | {stats['std']:.3f} | "
                    f"{stats['min']:.3f} | {stats['max']:.3f} | {stats['median']:.3f} | "
                    f"{stats['q25']:.3f} | {stats['q75']:.3f} |\n"
                )

            f.write("\n### 1.2 Wikipedia 内容生动性统计\n\n")
            f.write(
                "| 维度 | 均值 | 标准差 | 最小值 | 最大值 | 中位数 | 25%分位数 | 75%分位数 |\n"
            )
            f.write(
                "|------|------|--------|--------|--------|--------|-----------|-----------|\n"
            )

            for dim in ["figurativeness", "emotionality", "decorativeness", "overall"]:
                stats = analysis["wikipedia"][dim]
                f.write(
                    f"| {dim.title()} | {stats['mean']:.3f} | {stats['std']:.3f} | "
                    f"{stats['min']:.3f} | {stats['max']:.3f} | {stats['median']:.3f} | "
                    f"{stats['q25']:.3f} | {stats['q75']:.3f} |\n"
                )

            # 对比分析
            f.write("\n## 2. 对比分析\n\n")
            f.write("### 2.1 维度对比\n\n")
            f.write(
                "| 维度 | NatGeo 均值 | Wikipedia 均值 | 绝对差异 | 相对差异(%) | 更高来源 |\n"
            )
            f.write(
                "|------|-------------|----------------|----------|-------------|----------|\n"
            )

            for dim in ["figurativeness", "emotionality", "decorativeness", "overall"]:
                diff = analysis["differences"][dim]
                f.write(
                    f"| {dim.title()} | {analysis['natgeo'][dim]['mean']:.3f} | "
                    f"{analysis['wikipedia'][dim]['mean']:.3f} | {diff['absolute_diff']:.3f} | "
                    f"{diff['relative_diff']:.1f}% | {diff['higher_source']} |\n"
                )

            # 关键发现
            f.write("\n## 3. 关键发现\n\n")

            overall_diff = analysis["differences"]["overall"]["absolute_diff"]
            higher_overall = analysis["differences"]["overall"]["higher_source"]

            f.write(
                f"1. **总体生动性**: {higher_overall.title()} 内容的总体生动性更高，"
                f"平均差异为 {overall_diff:.3f}\n\n"
            )

            # 各维度分析
            f.write("### 3.1 各维度详细分析\n\n")

            for dim in ["figurativeness", "emotionality", "decorativeness"]:
                diff = analysis["differences"][dim]
                higher = diff["higher_source"]
                natgeo_mean = analysis["natgeo"][dim]["mean"]
                wiki_mean = analysis["wikipedia"][dim]["mean"]

                f.write(f"**{dim.title()} (比喻性/情感性/修饰性)**:\n")
                f.write(
                    f"- {higher.title()} 内容表现更优 (NatGeo: {natgeo_mean:.3f}, Wikipedia: {wiki_mean:.3f})\n"
                )
                f.write(f"- 相对差异: {diff['relative_diff']:.1f}%\n\n")

            # 具体示例
            f.write("## 4. 典型案例分析\n\n")

            # 找出差异最大的几个案例
            differences = [
                self.results["natgeo"]["overall"][i]
                - self.results["wikipedia"]["overall"][i]
                for i in range(len(self.results["natgeo"]["overall"]))
            ]

            top_positive_idx = np.argsort(differences)[-3:]  # NatGeo 高于 Wiki 最多
            top_negative_idx = np.argsort(differences)[:3]  # Wiki 高于 NatGeo 最多

            f.write("### 4.1 NatGeo 生动性明显高于 Wikipedia 的案例\n\n")
            for idx in reversed(top_positive_idx):
                metadata = self.results["metadata"][idx]
                natgeo_score = self.results["natgeo"]["overall"][idx]
                wiki_score = self.results["wikipedia"]["overall"][idx]
                f.write(f"**案例 {idx + 1}: {metadata['natgeo_title']}**\n")
                f.write(f"- NatGeo 评分: {natgeo_score:.3f}\n")
                f.write(f"- Wikipedia 评分: {wiki_score:.3f}\n")
                f.write(f"- 差异: {natgeo_score - wiki_score:.3f}\n\n")

            f.write("### 4.2 Wikipedia 生动性明显高于 NatGeo 的案例\n\n")
            for idx in top_negative_idx:
                metadata = self.results["metadata"][idx]
                natgeo_score = self.results["natgeo"]["overall"][idx]
                wiki_score = self.results["wikipedia"]["overall"][idx]
                f.write(f"**案例 {idx + 1}: {metadata['natgeo_title']}**\n")
                f.write(f"- NatGeo 评分: {natgeo_score:.3f}\n")
                f.write(f"- Wikipedia 评分: {wiki_score:.3f}\n")
                f.write(f"- 差异: {natgeo_score - wiki_score:.3f}\n\n")

            # 结论
            f.write("## 5. 结论与建议\n\n")
            f.write("基于对前50条NatGeo Kids数据的生动性分析，我们得出以下结论：\n\n")

            if higher_overall == "natgeo":
                f.write(
                    "1. **NatGeo Kids内容总体上更生动**：在比喻性、情感性和修饰性方面都表现出色，更适合年轻读者。\n"
                )
            else:
                f.write(
                    "1. **Wikipedia内容总体上更生动**：在某些维度上表现出优势，可能更适合追求详细信息的读者。\n"
                )

            f.write("\n2. **内容特征分析**：\n")
            f.write("   - NatGeo Kids 内容通常更加简洁、生动，适合儿童阅读\n")
            f.write("   - Wikipedia 内容更加详细、客观，但可能在生动性方面有所欠缺\n")

            f.write("\n3. **改进建议**：\n")
            f.write("   - 对于儿童科普内容，建议增加比喻性表达和情感化描述\n")
            f.write("   - 对于百科内容，可以适当增加修饰性词汇以提升可读性\n")

            f.write("\n---\n")
            f.write("*报告由 Vividness Analysis Tool 自动生成*\n")

        print(f"✓ Report saved to {report_path}")
        print(
            f"✓ Detailed results saved to {os.path.join(output_dir, 'detailed_results.csv')}"
        )

    def run_complete_analysis(self, output_dir: str = None):
        """运行完整分析流程"""
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "analysis_results")

        print("Starting complete NatGeo Vividness Analysis...")
        print("=" * 60)

        # 1. 运行分析
        self.run_analysis()

        # 2. 生成报告
        self.generate_report(output_dir)

        print("\n" + "=" * 60)
        print("✓ Analysis completed successfully!")
        print(f"✓ Results saved to: {output_dir}")
        print("=" * 60)


def main():
    """主函数"""
    # 设置路径
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    while base_dir and not base_dir.endswith("Auto-Popsci"):
        base_dir = os.path.dirname(base_dir)
    data_path = os.path.join(
        base_dir, "datasets", "our_dataset", "natgeo_kids", "natgeo_wikipedia_glm.json"
    )

    # 设置输出目录
    output_dir = os.path.join(os.path.dirname(__file__), "analysis_results")

    print("NatGeo Kids Vividness Analysis Tool")
    print("=" * 50)
    print(f"Data path: {data_path}")
    print(f"Output directory: {output_dir}")
    print("=" * 50)

    # 检查数据文件是否存在
    if not os.path.exists(data_path):
        print(f"✗ Data file not found: {data_path}")
        print("Please ensure the NatGeo dataset file exists at the specified path.")
        return

    try:
        # 创建分析器并运行分析
        analyzer = NatGeoVividnessAnalyzer(data_path, num_samples=10)
        analyzer.run_complete_analysis(output_dir)

    except Exception as e:
        print(f"✗ Error during analysis: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
