import asyncio
import os
import sys
import json
from auto_popsci.evaluation.comprehensive_evaluation import ComprehensiveEvaluator

# Add project root to sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

async def main():
    print("🚀 Starting Informativeness Evaluation Verification...")
    
    dataset_path = "baselines/test_multi_model_generation_output.json"
    
    # Check if dataset exists
    if not os.path.exists(dataset_path):
        print(f"❌ Dataset not found: {dataset_path}")
        return

    # Initialize evaluator
    # Skip coherence to focus on informativeness
    evaluator = ComprehensiveEvaluator(skip_coherence=True) 
    
    # We will evaluate only the first 1 item to save time and API costs
    with open(dataset_path, 'r') as f:
        data = json.load(f)
    
    small_data = data[:1] 
    temp_dataset_path = "temp_test_dataset.json"
    with open(temp_dataset_path, 'w') as f:
        json.dump(small_data, f)
        
    print(f"📝 Created temp dataset with {len(small_data)} items at {temp_dataset_path}")
    
    try:
        # Run evaluation
        # We point popsci_field to one of the models
        popsci_field = "models.grok-4-1-fast-reasoning.content"
        original_field = "original_data.original_data.wikipedia_article.content"
        
        print(f"🔍 Evaluating with popsci_field='{popsci_field}'")
        
        results = await evaluator.evaluate_dataset(
            dataset_path=temp_dataset_path,
            popsci_field=popsci_field,
            original_field=original_field,
            include_informativeness=True,
            include_keyfacts=False, # Disable keyfacts metric to isolate informativeness (which uses keyfacts internally)
            auto_generate_keyfacts=False # Let informativeness evaluator handle generation on the fly
        )
        
        print("\n✅ Evaluation finished!")
        
        # Verify results
        if results['results']:
            first_res = results['results'][0]
            print("\n🧐 Inspecting first result:")
            
            # Check Informativeness
            if 'informativeness' in first_res:
                info = first_res['informativeness']
                print(f"  - Informativeness Result: {json.dumps(info, indent=2, ensure_ascii=False)}")
                
                if info.get('score') is not None:
                    print(f"  ✅ Informativeness score present: {info.get('score')}")
                else:
                    print("  ⚠️ Informativeness score is None")
            else:
                print("  ❌ 'informativeness' key missing in result!")

            # Check if other metrics are present/skipped
            print(f"  - Coherence: {first_res.get('coherence')}")
            print(f"  - Simplicity: {first_res.get('simplicity')}")
            
    except Exception as e:
        print(f"❌ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(temp_dataset_path):
            os.remove(temp_dataset_path)

if __name__ == "__main__":
    asyncio.run(main())
