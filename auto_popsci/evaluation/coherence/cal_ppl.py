#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compute perplexity (PPL) for the NatGeo Kids dataset using the cal_ppl function.
"""

import json
import sys
import os

try:
    import torch
except ImportError:
    torch = None

class PPLEvaluator:
    """Class to manage PPL Evaluation to avoid global state issues in multiprocessing"""
    def __init__(self, device=None):
        self.model = None
        self.tokenizer = None
        if torch is None:
            self.device = device or "cpu"
        else:
            self.device = torch.device(device) if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _load_model(self):
        if torch is None:
            raise RuntimeError("torch is not installed")
        if self.model is None:
            from transformers import GPT2LMHeadModel, GPT2Tokenizer
            try:
                self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2", local_files_only=True)
                self.model = GPT2LMHeadModel.from_pretrained("gpt2", local_files_only=True)
            except Exception:
                self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
                self.model = GPT2LMHeadModel.from_pretrained("gpt2")

            self.model.to(self.device).eval()

            # Set pad token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

    def calculate_ppl(self, texts, batch_size=32):
        if torch is None:
            print("torch is not installed; returning default PPL values.")
            if not isinstance(texts, list):
                return 1000.0
            return [1000.0] * len(texts)

        self._load_model()
        if not isinstance(texts, list):
            texts = [texts]
            
        results = []
        # Batch processing
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            valid_batch_texts = [t for t in batch_texts if t and t.strip()]
            
            # Init with default
            batch_results = [1000.0] * len(batch_texts)
            
            if not valid_batch_texts:
                results.extend(batch_results)
                continue
                
            try:
                inputs = self.tokenizer(valid_batch_texts, return_tensors='pt', padding=True, truncation=True, max_length=512).to(self.device)
                with torch.no_grad():
                    outputs = self.model(inputs.input_ids, attention_mask=inputs.attention_mask, labels=inputs.input_ids)
                    logits = outputs.logits

                # Shift logits
                shift_logits = logits[..., :-1, :].contiguous()
                shift_labels = inputs.input_ids[..., 1:].contiguous()
                shift_mask = inputs.attention_mask[..., 1:].contiguous()

                loss_fct = torch.nn.CrossEntropyLoss(reduction='none')
                flat_loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
                per_token_loss = flat_loss.view(shift_labels.size())
                
                # Mask
                masked_loss = per_token_loss * shift_mask
                sum_loss = masked_loss.sum(dim=1)
                num_valid = shift_mask.sum(dim=1)
                mean_loss = sum_loss / (num_valid + 1e-9)
                ppls = torch.exp(mean_loss).cpu().numpy()
                
                # Map back avoiding index errors if some texts were empty (logic simplified here)
                # Actually valid_batch_texts matches order of stripped texts.
                # If we filter empty texts, mapping back is tricky.
                # Let's keep empty strings but they result in 0 loss?
                # Actually tokenizer handles empty string by return empty -> error.
                # So we must map back.
                
                curr = 0
                for idx, t in enumerate(batch_texts):
                    if t and t.strip():
                        batch_results[idx] = float(ppls[curr])
                        curr += 1
                        
            except Exception as e:
                print(f"PPL Batch Error: {e}")
                
            results.extend(batch_results)
            
        return results if len(texts) > 1 else results[0]

# Global cache for model and tokenizer.
_cached_model = None
_cached_tokenizer = None

def simple_cal_ppl(text):
    """
    Simple perplexity calculation using GPT-2 from transformers.
    Results are cached globally to avoid reloading the model.
    """
    global _cached_model, _cached_tokenizer

    if torch is None:
        print("torch is not installed; using default perplexity value.")
        return 1000.0
    
    try:
        from transformers import GPT2LMHeadModel, GPT2Tokenizer

        # Load the model if not already cached.
        if _cached_model is None or _cached_tokenizer is None:
            try:
                print("Loading GPT-2 model...")
                # First try the local cache (avoid network issues).
                try:
                    _cached_tokenizer = GPT2Tokenizer.from_pretrained("gpt2", local_files_only=True)
                    _cached_model = GPT2LMHeadModel.from_pretrained("gpt2", local_files_only=True)
                    print("Successfully loaded GPT-2 model from local cache")
                except Exception as local_error:
                    # If local cache is missing, attempt to download (network issues may occur).
                    print(f"Local cache load failed; attempting download: {local_error}")
                    _cached_tokenizer = GPT2Tokenizer.from_pretrained("gpt2", local_files_only=False)
                    _cached_model = GPT2LMHeadModel.from_pretrained("gpt2", local_files_only=False)
                    print("Downloaded and loaded GPT-2 model successfully")
                
                _cached_model.eval()  # Set to evaluation mode.
            except Exception as e:
                print(f"Failed to load GPT-2 model: {e}")
                print("Skipping coherence evaluation and using default perplexity value")
                # Mark failure to avoid repeated attempts.
                _cached_model = "FAILED"
                _cached_tokenizer = "FAILED"
                return 1000.0  # Return a default high value.
        
        # If loading previously failed, return a default high value.
        if _cached_model == "FAILED" or _cached_tokenizer == "FAILED":
            return 1000.0

        # Use the cached model and tokenizer.
        inputs = _cached_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        input_ids = inputs.input_ids

        with torch.no_grad():
            outputs = _cached_model(input_ids, labels=input_ids)
            logits = outputs.logits

        # Compute per-token prediction probabilities.
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = input_ids[..., 1:].contiguous()

        # Compute cross-entropy loss.
        loss = torch.nn.functional.cross_entropy(
            shift_logits.view(-1, shift_logits.size(-1)),
            shift_labels.view(-1),
            reduction="mean",
        )

        nll = loss
        ppl = torch.exp(nll).item()
        return ppl
    except Exception as e:
        print(f"Perplexity calculation failed: {e}")
        return 1000.0  # Return a default high value.


def load_natgeo_dataset(file_path):
    """Load the NatGeo Kids dataset."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("JSON file format error: expected array")
            return None, None

        natgeo_texts = []
        wikipedia_texts = []

        valid_pairs = 0

        for item in data:
            natgeo_article = item.get('natgeo_article', {})
            wikipedia_content = item.get('wikipedia_content', '')

            if not natgeo_article or not wikipedia_content:
                continue

            natgeo_content = natgeo_article.get('content', '')

            if not natgeo_content:
                continue

            natgeo_texts.append(natgeo_content)
            wikipedia_texts.append(wikipedia_content)
            valid_pairs += 1

        print(f"Successfully loaded {valid_pairs} valid text pairs")
        return natgeo_texts, wikipedia_texts

    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None, None
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None


def calculate_text_ppl(text_list, text_type, max_samples=20):
    """Calculate perplexity for a list of texts, limiting samples to speed up processing."""
    if not text_list:
        return 0.0

    print(f"Starting to calculate perplexity for {text_type}...")

    # Limit the number of samples to speed up processing.
    if len(text_list) > max_samples:
        text_list = text_list[:max_samples]
        print(f"   Limited to first {max_samples} samples for faster processing")

    ppl_scores = []
    valid_texts = 0

    for i, text in enumerate(text_list):
        if len(text.strip()) < 50:  # Skip very short texts.
            continue

        try:
            # Calculate perplexity for each text.
            ppl = simple_cal_ppl(text)
            if ppl > 0 and ppl < 10000:  # Filter out anomalous values.
                ppl_scores.append(ppl)
                valid_texts += 1
                if (i + 1) % 5 == 0:  # Print progress every 5 texts.
                    print(f"   Processed {i+1}/{len(text_list)} texts, {valid_texts} valid")
        except Exception as e:
            print(f"Error calculating PPL for text {i+1}: {e}")
            continue

    if not ppl_scores:
        return 0.0

    avg_ppl = sum(ppl_scores) / len(ppl_scores)
    print(f"Completed PPL calculation for {valid_texts} valid texts")

    return avg_ppl, ppl_scores, valid_texts


def interpret_ppl_score(ppl_score):
    """Interpret a perplexity score."""
    if ppl_score < 50:
        return "Very Fluent"
    elif ppl_score < 100:
        return "Relatively Fluent"
    elif ppl_score < 200:
        return "Moderately Fluent"
    elif ppl_score < 500:
        return "Less Fluent"
    else:
        return "Very Disfluent"


def main():
    """Main function"""
    print("Calculating perplexity for NatGeo Kids dataset using cal_ppl function...")

    # Dataset path (relative to the project root).
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Ascend from auto_popsci/evaluation/coherence back to the project root.
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    dataset_path = os.path.join(project_root, 'datasets', 'our_dataset', 'natgeo_kids', 'natgeo_wikipedia_glm.json')
    print(f"Looking for dataset at: {dataset_path}")

    # Load the dataset.
    natgeo_texts, wiki_texts = load_natgeo_dataset(dataset_path)

    if natgeo_texts is None or wiki_texts is None:
        print("Data loading failed")
        return

    if not natgeo_texts or not wiki_texts:
        print("No valid data to analyze")
        return

    print(f"Starting perplexity calculation...")
    print(f"   NatGeo articles: {len(natgeo_texts)}")
    print(f"   Wikipedia articles: {len(wiki_texts)}")

    try:
        # Calculate perplexity for NatGeo articles.
        print(f"\nCalculating perplexity for NatGeo articles...")
        natgeo_avg_ppl, natgeo_ppl_scores, natgeo_valid = calculate_text_ppl(
            natgeo_texts, "NatGeo articles", max_samples=15
        )

        print(f"\nCalculating perplexity for Wikipedia content...")
        wiki_avg_ppl, wiki_ppl_scores, wiki_valid = calculate_text_ppl(
            wiki_texts, "Wikipedia content", max_samples=15
        )

        # Calculate the overall perplexity.
        all_texts = natgeo_texts + wiki_texts
        print(f"\nCalculating perplexity for overall text...")
        overall_avg_ppl, overall_ppl_scores, overall_valid = calculate_text_ppl(
            all_texts, "overall text", max_samples=25
        )

        print(f"\nPerplexity (PPL) Analysis Results:")
        print(f"   Valid NatGeo articles: {natgeo_valid}/{len(natgeo_texts)}")
        print(f"   Valid Wikipedia articles: {wiki_valid}/{len(wiki_texts)}")
        print(f"   Overall valid articles: {overall_valid}/{len(all_texts)}")
        print(f"")
        print(f"   NatGeo average PPL: {natgeo_avg_ppl:.2f}")
        print(f"   Wikipedia average PPL: {wiki_avg_ppl:.2f}")
        print(f"   Overall average PPL: {overall_avg_ppl:.2f}")

        # PPL interpretation.
        print(f"\nPPL Score Interpretation:")
        print(f"   <50: Very fluent")
        print(f"   50-100: Relatively fluent")
        print(f"   100-200: Moderately fluent")
        print(f"   200-500: Less fluent")
        print(f"   >500: Very disfluent")

        # Provide fluency assessment based on scores.
        print(f"\nFluency Assessment:")
        print(f"   NatGeo Kids articles: {interpret_ppl_score(natgeo_avg_ppl)} (PPL: {natgeo_avg_ppl:.2f})")
        print(f"   Wikipedia content: {interpret_ppl_score(wiki_avg_ppl)} (PPL: {wiki_avg_ppl:.2f})")
        print(f"   Overall text: {interpret_ppl_score(overall_avg_ppl)} (PPL: {overall_avg_ppl:.2f})")

        # Comparative analysis.
        print(f"\nComparative Analysis:")
        if natgeo_avg_ppl < wiki_avg_ppl:
            ppl_diff = wiki_avg_ppl - natgeo_avg_ppl
            print(f"   NatGeo articles are more fluent than Wikipedia content (difference: {ppl_diff:.2f})")
        elif natgeo_avg_ppl > wiki_avg_ppl:
            ppl_diff = natgeo_avg_ppl - wiki_avg_ppl
            print(f"   NatGeo articles are less fluent than Wikipedia content (difference: {ppl_diff:.2f})")
        else:
            print(f"   NatGeo articles and Wikipedia content have similar fluency")

        # Compute statistical information.
        def calculate_stats(scores):
            if not scores:
                return {"min": 0, "max": 0, "median": 0, "std": 0}
            scores_sorted = sorted(scores)
            import math
            mean = sum(scores) / len(scores)
            variance = sum((x - mean) ** 2 for x in scores) / len(scores)
            std = math.sqrt(variance)
            return {
                "min": min(scores),
                "max": max(scores),
                "median": scores_sorted[len(scores_sorted) // 2],
                "std": std
            }

        natgeo_stats = calculate_stats(natgeo_ppl_scores)
        wiki_stats = calculate_stats(wiki_ppl_scores)

        print(f"\nStatistical Information:")
        print(f"   NatGeo PPL: min={natgeo_stats['min']:.2f}, max={natgeo_stats['max']:.2f}, "
              f"median={natgeo_stats['median']:.2f}, std={natgeo_stats['std']:.2f}")
        print(f"   Wikipedia PPL: min={wiki_stats['min']:.2f}, max={wiki_stats['max']:.2f}, "
              f"median={wiki_stats['median']:.2f}, std={wiki_stats['std']:.2f}")

        # Save summary results.
        results = {
            'total_natgeo_texts': len(natgeo_texts),
            'total_wikipedia_texts': len(wiki_texts),
            'valid_natgeo_texts': natgeo_valid,
            'valid_wikipedia_texts': wiki_valid,
            'overall_valid_texts': overall_valid,
            'natgeo_avg_ppl': natgeo_avg_ppl,
            'wikipedia_avg_ppl': wiki_avg_ppl,
            'overall_avg_ppl': overall_avg_ppl,
            'natgeo_stats': natgeo_stats,
            'wikipedia_stats': wiki_stats,
            'fluency_assessment': {
                'natgeo_fluency': interpret_ppl_score(natgeo_avg_ppl),
                'wikipedia_fluency': interpret_ppl_score(wiki_avg_ppl),
                'overall_fluency': interpret_ppl_score(overall_avg_ppl)
            },
            'ppl_difference': abs(natgeo_avg_ppl - wiki_avg_ppl),
            'method': 'GPT-2_Perplexity',
            'model': 'gpt2',
            'note': f'Limited to first 15-25 samples for faster processing'
        }

        # Save detailed scores.
        results['natgeo_ppl_scores'] = natgeo_ppl_scores
        results['wikipedia_ppl_scores'] = wiki_ppl_scores
        results['overall_ppl_scores'] = overall_ppl_scores

        with open('ppl_analysis_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\nDetailed results saved to: ppl_analysis_results.json")

    except Exception as e:
        print(f"Error calculating perplexity: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
