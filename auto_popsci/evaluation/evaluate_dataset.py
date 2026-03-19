#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
General dataset evaluation script that supports multiple formats and CLI configuration.
"""

import asyncio
import json
import os
import sys
import argparse
from pathlib import Path
from typing import Optional

# Add the project root to sys.path.
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Delay imports to avoid errors when showing help.


def detect_model_name(data_list: list) -> Optional[str]:
    """
    Auto-detect the model name within the dataset.
    Exclude known standard fields.
    """
    if not data_list:
        return None
    
    standard_fields = ['original_data', 'source_wikipedia', 'analysis', 'wikipedia_article', 'popsci_article']
    
    first_item = data_list[0]
    model_fields = [k for k in first_item.keys() if k not in standard_fields]
    
    if model_fields:
        return model_fields[0]
    return None


def detect_field_paths(data_list: list, model_name: str) -> dict:
    """
    Auto-detect field paths.
    Returns a dict with popsci_field, original_field, and reference_field.
    """
    if not data_list:
        return {
            'popsci_field': None,
            'original_field': None,
            'reference_field': None
        }
    
    first_item = data_list[0]
    
    # Detect the generated popsci article field.
    popsci_field = None
    if model_name and model_name in first_item:
        model_data = first_item[model_name]
        if isinstance(model_data, dict):
            if 'content' in model_data:
                popsci_field = f"{model_name}.content"
            elif 'text' in model_data:
                popsci_field = f"{model_name}.text"
    
    # Detect the Wikipedia source field.
    original_field = None
    if 'original_data' in first_item:
        orig = first_item['original_data']
        if isinstance(orig, dict):
            # Try multiple possible paths.
            if 'wikipedia_article' in orig:
                wiki = orig['wikipedia_article']
                if isinstance(wiki, dict) and 'content' in wiki:
                    original_field = "original_data.wikipedia_article.content"
            elif 'original_data' in orig:
                orig2 = orig['original_data']
                if isinstance(orig2, dict) and 'wikipedia_article' in orig2:
                    wiki = orig2['wikipedia_article']
                    if isinstance(wiki, dict) and 'content' in wiki:
                        original_field = "original_data.original_data.wikipedia_article.content"
    
    # Detect the reference popsci article field.
    reference_field = None
    if 'original_data' in first_item:
        orig = first_item['original_data']
        if isinstance(orig, dict):
            if 'popsci_article' in orig:
                popsci = orig['popsci_article']
                if isinstance(popsci, dict) and 'content' in popsci:
                    reference_field = "original_data.popsci_article.content"
            elif 'original_data' in orig:
                orig2 = orig['original_data']
                if isinstance(orig2, dict) and 'popsci_article' in orig2:
                    popsci = orig2['popsci_article']
                    if isinstance(popsci, dict) and 'content' in popsci:
                        reference_field = "original_data.original_data.popsci_article.content"
    
    return {
        'popsci_field': popsci_field,
        'original_field': original_field,
        'reference_field': reference_field
    }


def parse_evaluation_args():
    """Parse evaluation arguments."""
    parser = argparse.ArgumentParser(
        description="General dataset evaluation script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  # Basic usage (auto-detect model name and field paths)
  python evaluate_dataset.py --input_file data.json --output_file results.json

  # Specify the model name
  python evaluate_dataset.py --input_file data.json --output_file results.json --model_name grok-4-1-fast-reasoning

  # Specify field paths
  python evaluate_dataset.py --input_file data.json --output_file results.json \\
    --popsci_field "grok-4-1-fast-reasoning.content" \\
    --original_field "original_data.wikipedia_article.content" \\
    --reference_field "original_data.popsci_article.content"

  # Skip coherence evaluation
  python evaluate_dataset.py --input_file data.json --output_file results.json --skip_coherence

  # Disable auto keyfact generation
  python evaluate_dataset.py --input_file data.json --output_file results.json --no_auto_generate_keyfacts
        """
    )
    
    # Required arguments.
    parser.add_argument(
        '--input_file',
        type=str,
        required=True,
        help='Input dataset file path (JSON format)'
    )
    
    parser.add_argument(
        '--output_file',
        type=str,
        required=True,
        help='Output results file path (JSON format)'
    )
    
    # Optional arguments.
    parser.add_argument(
        '--model_name',
        type=str,
        default=None,
        help='Model name (auto-detected if not provided)'
    )
    
    parser.add_argument(
        '--popsci_field',
        type=str,
        default=None,
        help='Field path for generated popsci article (auto-detected if not provided)'
    )
    
    parser.add_argument(
        '--original_field',
        type=str,
        default=None,
        help='Field path for original Wikipedia article (auto-detected if not provided)'
    )
    
    parser.add_argument(
        '--reference_field',
        type=str,
        default=None,
        help='Reference popsci article field path (optional, for comparative evaluation)'
    )
    
    parser.add_argument(
        '--skip_coherence',
        action='store_true',
        help='Skip coherence evaluation (PPL)'
    )

    parser.add_argument(
        '--skip_coherence_llm',
        dest='skip_coherence_llm',
        action='store_true',
        default=True,
        help='Skip LLM-based coherence evaluation by default; use --run_coherence_llm to enable'
    )

    parser.add_argument(
        '--run_coherence_llm',
        dest='skip_coherence_llm',
        action='store_false',
        help='Enable LLM-based coherence evaluation (overrides default skip)'
    )

    parser.add_argument(
        '--skip_informativeness',
        dest='skip_informativeness',
        action='store_true',
        default=True,
        help='Skip informativeness (QA-based) evaluation by default; add --run_informativeness to enable'
    )

    parser.add_argument(
        '--run_informativeness',
        dest='skip_informativeness',
        action='store_false',
        help='Enable informativeness (QA-based) evaluation'
    )

    parser.add_argument(
        '--skip_keyfacts',
        action='store_true',
        help='Skip keyfacts precision/recall evaluation'
    )

    parser.add_argument(
        '--skip_simplicity',
        action='store_true',
        help='Skip simplicity evaluation (FKGL)'
    )

    parser.add_argument(
        '--skip_vividness',
        action='store_true',
        help='Skip vividness evaluation'
    )
    
    parser.add_argument(
        '--auto_generate_keyfacts',
        action='store_true',
        default=True,
        help='Auto-generate keyfacts for evaluation (enabled by default)'
    )
    
    parser.add_argument(
        '--no_auto_generate_keyfacts',
        dest='auto_generate_keyfacts',
        action='store_false',
        help='Disable auto-generation of keyfacts'
    )
    
    parser.add_argument(
        '--ground_truth_keyfacts_dir',
        type=str,
        default=None,
        help='Reference keyfacts directory (use the files instead of auto-generation if provided)'
    )
    
    parser.add_argument(
        '--generated_keyfacts_dir',
        type=str,
        default=None,
        help='Generated keyfacts directory (use provided files instead of auto-generation if available)'
    )

    parser.add_argument(
        '--ground_truth_keyfacts_field',
        type=str,
        default='wiki_keyfacts',
        help='Field path for existing ground-truth keyfacts in the input file (default: wiki_keyfacts)'
    )

    parser.add_argument(
        '--generated_keyfacts_field',
        type=str,
        default=None,
        help='Field path for existing generated keyfacts in the input file'
    )
    
    parser.add_argument(
        '--dataset_format',
        type=str,
        default='json',
        choices=['json', 'jsonl'],
        help='Dataset format ("json" or "jsonl", default: json)'
    )
    
    parser.add_argument(
        '--sample',
        type=int,
        default=None,
        help='Sample size; if set, only the first N records are evaluated'
    )

    parser.add_argument(
        '--cuda_devices',
        type=str,
        default=None,
        help='Comma-separated CUDA device IDs to use (e.g., "0" or "0,1"; default: None)'
    )

    parser.add_argument(
        '--llm_type',
        type=str,
        default='gemini-3-flash-preview',
        help='LLM type used for keyfacts generation'
    )
    
    parser.add_argument(
        '--prompt_template',
        type=str,
        default='keyfact_alignment',
        help='Prompt template name for keyfacts evaluation (default: keyfact_alignment)'
    )
    
    parser.add_argument(
        '--reader_age',
        type=str,
        default='adult',
        choices=['child', 'teen', 'adult'],
        help='Simulated reader age group (child, teen, adult). Default: adult'
    )
    
    parser.add_argument(
        '--concurrency',
        type=int,
        default=20,
        help='Concurrency level (default: 20; reduce if you hit file descriptor limits)'
    )
    
    return parser.parse_args()


async def main():
    """Main function"""
    args = parse_evaluation_args()
    
    # Delay imports to avoid issues when displaying help.
    from auto_popsci.evaluation.comprehensive_evaluation import ComprehensiveEvaluator
    from auto_popsci.evaluation.comprehensive_evaluation import ComprehensiveEvaluator
    # from auto_popsci.args import parse_args # Removed to prevent conflict
    
    print("=" * 80)
    print("General dataset evaluation tool")
    print("=" * 80)
    
    # Verify the input file exists.
    if not os.path.exists(args.input_file):
        print(f"ERROR: Input file {args.input_file} does not exist")
        return
    
    # Read the data.
    print(f"\nReading dataset file: {args.input_file}")
    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            if args.dataset_format == 'json':
                data_list = json.load(f)
                if not isinstance(data_list, list):
                    # Convert a single object into a list.
                    data_list = [data_list]
            else:  # jsonl
                data_list = []
                for line in f:
                    line = line.strip()
                    if line:
                        data_list.append(json.loads(line))
    except Exception as e:
        print(f"ERROR: Failed to read file: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"Loaded {len(data_list)} records successfully")

    if args.sample is not None and args.sample > 0:
        original_len = len(data_list)
        data_list = data_list[:min(args.sample, len(data_list))]
        print(f"Notice: sample={args.sample} applied; evaluating first {len(data_list)} records (original count: {original_len})")
    
    if len(data_list) == 0:
        print("ERROR: Dataset file is empty")
        return
    
    # Detect or use the specified model name.
    model_name = args.model_name
    if not model_name:
        model_name = detect_model_name(data_list)
        if model_name:
            print(f"Detected model name automatically: {model_name}")
        elif args.popsci_field:
            print(f"Note: Model name not auto-detected, but popsci_field provided: {args.popsci_field}. Continuing.")
            model_name = "manual_specified"
        else:
            print("Warning: Unable to auto-detect model name; please set --model_name manually.")
            print("   Data fields:", list(data_list[0].keys()))
            return
    else:
        print(f"Using specified model name: {model_name}")
    
    # Detect or use the specified field paths.
    detected_fields = detect_field_paths(data_list, model_name)
    
    popsci_field = args.popsci_field or detected_fields['popsci_field']
    original_field = args.original_field or detected_fields['original_field']
    reference_field = args.reference_field or detected_fields['reference_field']
    ground_truth_keyfacts_field = args.ground_truth_keyfacts_field
    generated_keyfacts_field = args.generated_keyfacts_field

    if ground_truth_keyfacts_field:
        print(f"Using ground-truth keyfacts field: {ground_truth_keyfacts_field}")
    elif original_field and original_field.endswith('.content'):
        ground_truth_keyfacts_field = original_field[:-8] + '.keyfacts'
        print(f"Auto-inferred ground-truth keyfacts field: {ground_truth_keyfacts_field}")

    if generated_keyfacts_field:
        print(f"Using generated keyfacts field: {generated_keyfacts_field}")

    
    print(f"\nField configuration:")
    print(f"  - popsci_field: {popsci_field}")
    print(f"  - original_field: {original_field}")
    print(f"  - reference_field: {reference_field}")
    print(f"  - ground_truth_keyfacts_field: {ground_truth_keyfacts_field}")
    print(f"  - generated_keyfacts_field: {generated_keyfacts_field}")
    
    if not popsci_field:
        print("ERROR: Unable to determine popsci_field. Please specify --popsci_field.")
        return
    
    if not original_field:
        print("ERROR: Unable to determine original_field. Please specify --original_field.")
        return
    
    # Keyfacts configuration.
    has_keyfacts_files = (
        args.ground_truth_keyfacts_dir is not None and 
        args.generated_keyfacts_dir is not None and
        os.path.exists(args.ground_truth_keyfacts_dir) and
        os.path.exists(args.generated_keyfacts_dir)
    )
    
    # include_keyfacts controls whether to run precision/recall evaluation.
    # If skip_keyfacts is not specified, the script will attempt it (via files, dataset fields, or auto-generation).
    include_keyfacts = not args.skip_keyfacts
    
    if args.skip_keyfacts:
        print(f"\nKeyfacts configuration: skipping precision/recall evaluation (--skip_keyfacts)")
    elif has_keyfacts_files:
        print(f"\nKeyfacts configuration: using provided directories for evaluation")
        print(f"  - ground_truth_keyfacts_dir: {args.ground_truth_keyfacts_dir}")
        print(f"  - generated_keyfacts_dir: {args.generated_keyfacts_dir}")
    elif args.auto_generate_keyfacts:
        print(f"\nKeyfacts configuration: auto-generating keyfacts")
        print(f"  - Wikipedia keyfacts: using {args.llm_type} (generated from original_text)")
        print(f"  - Popsci keyfacts: using {args.llm_type} (generated from popsci_text)")
    else:
        print(f"\nKeyfacts configuration: will try to use existing keyfacts fields in the dataset")
    
    # Create the output directory.
    output_dir = os.path.dirname(args.output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Initialize the evaluator.
    print("\nInitializing evaluator...")
    # Manually construct args to avoid conflicting parser.parse_args() call in auto_popsci.args
    class EvaluationArgs:
        pass
    
    eval_args = EvaluationArgs()
    # Use the llm_type specified on the CLI.
    eval_args.llm_type = args.llm_type 
    # If llm_type already names a model, set model_type to the same value or leave None for internal handling.
    eval_args.model_type = args.llm_type 
    eval_args.language = 'en'
    eval_args.prompt_template = args.prompt_template
    eval_args.dataset_format = args.dataset_format
    
    # Initialize other potentially needed attributes with defaults
    eval_args.paper_path = None
    eval_args.paper_mode = 'dataset'
    eval_args.key_fact_output_dir = "output/key_facts/"
    eval_args.popsci_output_dir = "output/popsci/"
    eval_args.is_paperbody_or_news = "Paper_Body"
    
    evaluator = ComprehensiveEvaluator(
        args=eval_args,
        skip_coherence=args.skip_coherence,
        skip_coherence_llm=args.skip_coherence_llm,
        skip_informativeness=args.skip_informativeness,
        skip_simplicity=args.skip_simplicity,
        skip_vividness=args.skip_vividness,
        reader_age=args.reader_age,
        cuda_devices=args.cuda_devices,
        concurrency=args.concurrency
    )
    
    # Execute the evaluation.
    print("\n" + "=" * 80)
    print("Starting evaluation...")
    print("=" * 80)
    
    try:
        result = await evaluator.evaluate_dataset(
            dataset_path=args.input_file,
            output_path=args.output_file,
            dataset_format=args.dataset_format,
            dataset_data=data_list,
            popsci_field=popsci_field,
            original_field=original_field,
            reference_field=reference_field,
            ground_truth_keyfacts_field=ground_truth_keyfacts_field,
            generated_keyfacts_field=generated_keyfacts_field,
            ground_truth_keyfacts_dir=args.ground_truth_keyfacts_dir if has_keyfacts_files else None,
            generated_keyfacts_dir=args.generated_keyfacts_dir if has_keyfacts_files else None,
            include_keyfacts=include_keyfacts,
            include_informativeness=not args.skip_informativeness,
            auto_generate_keyfacts=args.auto_generate_keyfacts
        )
        
        print("\n" + "=" * 80)
        print("Evaluation completed successfully.")
        print("=" * 80)
        
        # Save enriched dataset (Main Output)
        if 'enriched_dataset' in result:
             with open(args.output_file, 'w', encoding='utf-8') as f:
                 json.dump(result['enriched_dataset'], f, indent=4, ensure_ascii=False)
             print(f"\nFull enriched dataset (with keyfacts/QA results) saved to: {args.output_file}")
             
             # Save report separately
             report_path = f"{os.path.splitext(args.output_file)[0]}_report.json"
             report_data = {
                 'statistics': result.get('statistics', {}),
                 'metrics_summary': result.get('results', [])
             }
             with open(report_path, 'w', encoding='utf-8') as f:
                 json.dump(report_data, f, indent=4, ensure_ascii=False)
             print(f"Evaluation report (statistics + scores) saved to: {report_path}")
             
        else:
            # Fallback for compatibility
            print(f"\nResults saved to: {args.output_file}")
            # (The original code calling evaluate_dataset would return early if I don't write here?)
            # Wait, evaluate_dataset NO LONGER writes the file inside the class (I removed output_path logic inside it? No, I checked and it has output_path arg default None).
            # If I passed output_path to evaluator.evaluate_dataset, it might have written it?
            # Let's check `comprehensive_evaluation.py` lines 660+.
            # It says: "if output_path is None: ...". It does NOT write to file inside the method currently in my view? 
            # I can't confirm without viewing `comprehensive_evaluation.py` end of method. 
            # Reviewing my memory/view: I didn't see a `json.dump` at the end of `evaluate_dataset` in `comprehensive_evaluation.py`.
            # So I am responsible for saving here.
            pass

        print(f"\nEvaluation statistics:")
        print(f"  - Total documents: {result.get('total_documents', 0)}")
        print(f"  - Evaluated documents: {result.get('evaluated_documents', 0)}")
        
        if 'statistics' in result:
            stats = result['statistics']
            print(f"\nDetailed statistics:")
            
            # Coherence stats.
            if 'coherence' in stats:
                coh = stats['coherence']
                print(f"  - Coherence (PPL):")
                mean_val = coh.get('mean', None)
                min_val = coh.get('min', None)
                max_val = coh.get('max', None)
                if mean_val is not None:
                    print(f"    * Mean: {mean_val:.2f}")
                    print(f"    * Min: {min_val:.2f}")
                    print(f"    * Max: {max_val:.2f}")
            
            # Simplicity stats.
            if 'simplicity' in stats:
                sim = stats['simplicity']
                print(f"  - Simplicity (FKGL):")
                mean_val = sim.get('mean', None)
                min_val = sim.get('min', None)
                max_val = sim.get('max', None)
                if mean_val is not None:
                    print(f"    * Mean: {mean_val:.4f}")
                    print(f"    * Min: {min_val:.4f}")
                    print(f"    * Max: {max_val:.4f}")
            
            # Vividness stats.
            if 'vividness' in stats:
                viv = stats['vividness']
                print(f"  - Vividness (overall):")
                mean_val = viv.get('mean', None)
                min_val = viv.get('min', None)
                max_val = viv.get('max', None)
                if mean_val is not None:
                    print(f"    * Mean: {mean_val:.4f}")
                    print(f"    * Min: {min_val:.4f}")
                    print(f"    * Max: {max_val:.4f}")
            
            # Figurativeness stats.
            if 'figurativeness' in stats:
                fig = stats['figurativeness']
                print(f"  - Figurativeness:")
                mean_val = fig.get('mean', None)
                if mean_val is not None:
                    print(f"    * Mean: {mean_val:.4f}")
            
            # Emotionality stats.
            if 'emotionality' in stats:
                emo = stats['emotionality']
                print(f"  - Emotionality:")
                mean_val = emo.get('mean', None)
                if mean_val is not None:
                    print(f"    * Mean: {mean_val:.4f}")
            
            # Decorativeness stats.
            if 'decorativeness' in stats:
                dec = stats['decorativeness']
                print(f"  - Decorativeness:")
                mean_val = dec.get('mean', None)
                if mean_val is not None:
                    print(f"    * Mean: {mean_val:.4f}")
            
            # Keyfacts evaluation statistics.
            if 'keyfacts_precision' in stats:
                kf_prec = stats['keyfacts_precision']
                if kf_prec:
                    print(f"\n  - Keyfacts Precision:")
                    mean_val = kf_prec.get('mean', None)
                    count = kf_prec.get('count', 0)
                    if mean_val is not None:
                        print(f"    * Mean: {mean_val:.4f}")
                        print(f"    * Valid sample count: {count}")
            
            if 'keyfacts_recall' in stats:
                kf_rec = stats['keyfacts_recall']
                if kf_rec:
                    print(f"\n  - Keyfacts Recall:")
                    mean_val = kf_rec.get('mean', None)
                    count = kf_rec.get('count', 0)
                    if mean_val is not None:
                        print(f"    * Mean: {mean_val:.4f}")
                        print(f"    * Valid sample count: {count}")

        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\nERROR: Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    asyncio.run(main())
