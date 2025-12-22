from ..utils.utils import cal_ppl, cal_sari, get_papers_from_dataset
from ..args import parse_args
from .keyfacts_checking import async_single_paper_keyfacts_precision_calculation
import os
import json
import asyncio


async def main(args):
    popsci = []
    popsci_path = "auto_popsci/popsci_generation/output/dev_5/popsci_from_keyfacts/"
    popsci_files = [f for f in os.listdir(popsci_path)]
    popsci_paths = [os.path.join(popsci_path, f) for f in popsci_files]
    print("Popsci paths:", popsci_paths)
    for i, popsci_path in enumerate(popsci_paths):
        with open(popsci_path, "r") as f:
            popsci_data = f.read()
            popsci.append(popsci_data)
            print(f"Popsci {i + 1} content: {popsci_data}")
    print(f"Number of popsci: {len(popsci)}")

    papers, titles, news = get_papers_from_dataset(
        args.paper_path, args.dataset_format, args.is_paperbody_or_news
    )
    
    # Keyfacts paths
    ground_truth_keyfacts_path = "auto_popsci/evaluation/output/dev_5/R1_ground_truth/with_priority/reference_keyfacts/"
    generated_keyfacts_path = "auto_popsci/evaluation/output/dev_5/scinews_keyfacts/with_priority/reference_keyfacts/"
    
    # Get keyfacts file lists
    ground_truth_files = [
        f for f in os.listdir(ground_truth_keyfacts_path) if f.endswith(".json")
    ]
    generated_keyfacts_files = [
        f for f in os.listdir(generated_keyfacts_path) if f.endswith(".json")
    ]
    
    # Sort files to ensure matching
    ground_truth_files.sort()
    generated_keyfacts_files.sort()
    
    print("Ground truth keyfacts files:", ground_truth_files)
    print("Generated keyfacts files:", generated_keyfacts_files)
    
    if len(ground_truth_files) != len(generated_keyfacts_files):
        print(f"⚠️ 警告: ground truth 文件数量 ({len(ground_truth_files)}) 与 generated keyfacts 文件数量 ({len(generated_keyfacts_files)}) 不匹配")
    
    result = []
    for i, popsci_text in enumerate(popsci):
        print(f"\n处理文档 {i + 1}/{len(popsci)}")
        print(f"Popsci {i + 1} text: {popsci_text[:100]}...")
        print(f"Paper title {i + 1}: {titles[i]}")
        print(f"Paper content {i + 1}: {papers[i][:100]}...")
        print(f"News content {i + 1}: {news[i][:100]}...")
        
        # Calculate SARI score
        sari_score = cal_sari(popsci_text, papers[i], titles[i])
        print(f"SARI score for popsci {i + 1}: {sari_score}")
        
        # Calculate perplexity
        ppl_score = cal_ppl(popsci_text)
        print(f"Perplexity score for popsci {i + 1}: {ppl_score}")
        
        # Calculate keyfacts precision and recall
        keyfacts_result = {
            "precision": -1.0,
            "recall": -1.0,
            "precision_by_priority": {},
            "recall_by_priority": {}
        }
        
        if i < len(ground_truth_files) and i < len(generated_keyfacts_files):
            try:
                gt_path = os.path.join(ground_truth_keyfacts_path, ground_truth_files[i])
                gen_path = os.path.join(generated_keyfacts_path, generated_keyfacts_files[i])
                
                print(f"评估关键事实: {ground_truth_files[i]} vs {generated_keyfacts_files[i]}")
                keyfacts_eval_result = await async_single_paper_keyfacts_precision_calculation(
                    gt_path, gen_path, args
                )
                
                keyfacts_result = {
                    "precision": keyfacts_eval_result["precisions"].get("overall", -1.0),
                    "recall": keyfacts_eval_result["recalls"].get("overall", -1.0),
                    "precision_by_priority": {
                        "priority_1": keyfacts_eval_result["precisions"].get("priority_1", -1.0),
                        "priority_2": keyfacts_eval_result["precisions"].get("priority_2", -1.0),
                        "priority_3": keyfacts_eval_result["precisions"].get("priority_3", -1.0),
                    },
                    "recall_by_priority": {
                        "priority_1": keyfacts_eval_result["recalls"].get("priority_1", -1.0),
                        "priority_2": keyfacts_eval_result["recalls"].get("priority_2", -1.0),
                        "priority_3": keyfacts_eval_result["recalls"].get("priority_3", -1.0),
                    }
                }
                print(f"Keyfacts precision for popsci {i + 1}: {keyfacts_result['precision']}")
                print(f"Keyfacts recall for popsci {i + 1}: {keyfacts_result['recall']}")
            except Exception as e:
                print(f"⚠️ 关键事实评估失败: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️ 跳过关键事实评估（文件索引超出范围）")
        
        result.append(
            {
                "title": titles[i],
                "popsci_text": popsci_text,
                "sari_score": sari_score,
                "ppl_score": ppl_score,
                "keyfacts_precision": keyfacts_result["precision"],
                "keyfacts_recall": keyfacts_result["recall"],
                "keyfacts_precision_by_priority": keyfacts_result["precision_by_priority"],
                "keyfacts_recall_by_priority": keyfacts_result["recall_by_priority"],
            }
        )
        
        # Save intermediate results
        with open(
            "auto_popsci/evaluation/output/dev_5/popsci_evaluation.json", "w"
        ) as f:
            json.dump(result, f, indent=4)
    
    print(f"\n✅ 评估完成！共评估了 {len(result)} 个文档")
    print(f"结果已保存到: auto_popsci/evaluation/output/dev_5/popsci_evaluation.json")


if __name__ == "__main__":
    args = parse_args()
    args.paper_mode = "dataset"
    args.dataset_format = "json"
    args.paper_path = "datasets/scinews/dev_dataset_5.json"
    args.popsci_output_dir = (
        "auto_popsci/popsci_generation/output/dev_5/popsci_from_keyfacts/"
    )
    args.is_paperbody_or_news = "All"
    args.prompt_template = "keyfact_alignment"  # 用于 keyfacts 评估的 prompt template
    asyncio.run(main(args))
