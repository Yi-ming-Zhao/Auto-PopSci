import sys
import os
import torch

# Add project root to path
sys.path.append(os.getcwd())

# Inspect checkpoint
ckpt_path = "auto_popsci/evaluation/vividness/figurativeness/MelBERT/melbert_ckpt/pytorch_model.bin"
if os.path.exists(ckpt_path):
    print(f"Inspecting checkpoint: {ckpt_path}")
    state_dict = torch.load(ckpt_path, map_location="cpu")
    for k, v in state_dict.items():
        if "token_type_embeddings" in k:
            print(f"{k}: {v.shape}")
else:
    print(f"Checkpoint not found at {ckpt_path}")

print("-" * 20)

try:
    from auto_popsci.evaluation.vividness.figurativeness.figurativeness import FigurativenessEvaluator
    evaluator = FigurativenessEvaluator()
    print("FigurativenessEvaluator initialized successfully")
    text = "The sun is a golden coin in the sky."
    score = evaluator.evaluate_text(text)
    print(f"Text: {text}")
    print(f"Score: {score}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
