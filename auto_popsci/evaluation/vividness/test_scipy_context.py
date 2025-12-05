
import sys
import os
import scipy
print(f"Scipy version: {scipy.__version__}")
print(f"Scipy file: {scipy.__file__}")

# Add MelBERT path
melbert_path = os.path.join(os.path.dirname(__file__), "figurativeness", "MelBERT")
sys.path.insert(0, melbert_path)
print(f"Added {melbert_path} to sys.path")

try:
    import run_classifier_dataset_utils
    print("Successfully imported run_classifier_dataset_utils")
except ImportError as e:
    print(f"Failed to import run_classifier_dataset_utils: {e}")

