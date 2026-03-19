#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive evaluation interface for popsci articles.
Metrics covered include:
- coherence: Coherence measured by perplexity (lower is better).
- simplicity: Simplicity (FKGL; lower means easier readability).
- vividness: Vividness (via VividnessEvaluator).
- keyfacts precision: Keyfact precision.
- keyfacts recall: Keyfact recall.
"""

import json
import os
import sys
import asyncio
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path

# Add easse library path.
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
easse_path = os.path.join(project_root, 'easse')
if easse_path not in sys.path:
    sys.path.insert(0, easse_path)

from .coherence.cal_ppl import simple_cal_ppl
from .coherence.cal_ppl import simple_cal_ppl
from .informativeness.calculate_precision_recall import async_calculate_precision_recall
from ..utils.utils import read_yaml_file, extract_keyfacts
from ..args import parse_args
from prompts.prompt_template import prompt

# Import VividnessEvaluator.
from .vividness import VividnessEvaluator

# Import FKGL calculation function.
from easse.fkgl import corpus_fkgl
import logging

# Configure logging.
def setup_logging(log_file=None):
    """Configure the logger"""
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers,
        force=True
    )

logger = logging.getLogger(__name__)


def _clean_output_record(item: Dict, doc_result: Dict) -> Dict:
    """Build a flattened evaluation record without raw article texts or nested input payloads."""
    record = {
        'doc_id': doc_result.get('doc_id'),
        'title': doc_result.get('title'),
        'model_name': doc_result.get('model_name'),
    }

    optional_meta_fields = [
        'source',
        'content_relevance_score',
        'popsci_title',
        'popsci_url',
        'wiki_title',
        'wiki_url',
        'model_title',
    ]
    for field in optional_meta_fields:
        value = item.get(field)
        if value not in (None, '', [], {}):
            record[field] = value

    simplicity = doc_result.get('simplicity', {})
    if simplicity:
        record['simplicity_fkgl_score'] = simplicity.get('fkgl_score')
        record['simplicity_interpretation'] = simplicity.get('interpretation')

    coherence = doc_result.get('coherence', {})
    if coherence:
        record['coherence_ppl_score'] = coherence.get('ppl_score')
        record['coherence_interpretation'] = coherence.get('interpretation')
        if coherence.get('llm_score', -1.0) != -1.0:
            record['coherence_llm_score'] = coherence.get('llm_score')

    vividness = doc_result.get('vividness', {})
    if vividness:
        record['vividness_score'] = vividness.get('vividness_score')
        record['figurativeness'] = vividness.get('figurativeness')
        record['emotionality'] = vividness.get('emotionality')
        record['decorativeness'] = vividness.get('decorativeness')

    keyfacts = doc_result.get('keyfacts', {})
    if keyfacts:
        record['keyfacts_precision'] = keyfacts.get('precision')
        record['keyfacts_recall'] = keyfacts.get('recall')
        if keyfacts.get('precision_by_priority'):
            record['keyfacts_precision_by_priority'] = keyfacts.get('precision_by_priority')
        if keyfacts.get('recall_by_priority'):
            record['keyfacts_recall_by_priority'] = keyfacts.get('recall_by_priority')

    informativeness = doc_result.get('informativeness', {})
    if informativeness:
        if 'score' in informativeness:
            record['informativeness_score'] = informativeness.get('score')
        if informativeness.get('error'):
            record['informativeness_error'] = informativeness.get('error')
        if informativeness.get('note'):
            record['informativeness_note'] = informativeness.get('note')

    return {
        key: value for key, value in record.items()
        if value not in (None, '', [], {})
    }


def _process_chunk_worker(args):
    """
    Worker function for parallel processing of non-LLM evaluations
    """
    chunk_docs, device, config = args
    results = []
    import torch
    
    # 1. PPL
    from .coherence.cal_ppl import PPLEvaluator
    ppl_evaluator = None
    try:
        ppl_evaluator = PPLEvaluator(device=device)
    except Exception as e:
        print(f"Failed to init PPLEvaluator on {device}: {e}")
        
    # 2. Vividness
    from .vividness import VividnessEvaluator
    vividness_evaluator = None
    try:
        # Use config if provided
        weights = config.get('vividness_weights')
        melbert_path = config.get('melbert_path')
        
        vividness_evaluator = VividnessEvaluator(
            device=device,
            weights=weights,
            melbert_path=melbert_path
        )
    except Exception as e:
        print(f"Failed to init VividnessEvaluator on {device}: {e}")
        
    # Process docs
    for doc in chunk_docs:
        # doc is a dict of info.
        res = {}
        popsci_text = doc.get('popsci_text', '')
        
        # PPL
        if ppl_evaluator and popsci_text:
            try:
                res['ppl_score'] = ppl_evaluator.calculate_ppl(popsci_text)
            except Exception as e:
                import traceback
                print(f"PPL Calculation Error on {doc['id']}: {e}")
                traceback.print_exc()
                res['ppl_score'] = -1.0
        else:
            if not popsci_text:
                 # print(f"Empty popsci_text for doc {doc['id']}")
                 pass
            res['ppl_score'] = -1.0
            
        # Vividness
        res['vividness'] = None
        if vividness_evaluator and popsci_text:
            try:
                v_res = vividness_evaluator.evaluate_text(popsci_text, return_components=True)
                if isinstance(v_res, dict):
                    res['vividness'] = v_res
                else:
                    res['vividness'] = {
                        'vividness_score': v_res,
                        'figurativeness': 0.0,
                        'emotionality': 0.0, 
                        'decorativeness': 0.0
                    }
                    
            except Exception as e:
                print(f"Vividness Error on {device}: {e}")
                res['vividness'] = None
                
        results.append((doc['id'], res))
        
    return results

class ComprehensiveEvaluator:
    """Comprehensive evaluator that aggregates all metrics"""
    
    def __init__(self, args=None, vividness_weights=None, melbert_path=None, 
                 skip_coherence=False, skip_coherence_llm=False, skip_informativeness=False, 
                 skip_simplicity=False, skip_vividness=False, reader_age='adult',
                 cuda_devices=None, concurrency=20):
        """
        Initialize the comprehensive evaluator.
        
        Args:
            args: CLI arguments object (used for keyfacts evaluation).
            vividness_weights: Weight configuration for vividness.
            melbert_path: Path to the MelBERT model.
            skip_coherence: Whether to skip coherence (PPL).
            skip_coherence_llm: Whether to skip LLM-based coherence (LLM Judge).
            skip_informativeness: Whether to skip informativeness (QA-based).
            skip_simplicity: Whether to skip simplicity evaluation.
            skip_vividness: Whether to skip vividness evaluation.
            reader_age: Simulated reader age group ('child', 'teen', 'adult').
            cuda_devices: CUDA device IDs (comma-separated string, e.g. "0,1").
            concurrency: Number of concurrent tasks (default: 20).
        """
        self.args = args
        self.vividness_evaluator = None
        self.skip_coherence = skip_coherence
        self.skip_coherence_llm = skip_coherence_llm
        self.skip_informativeness = skip_informativeness
        self.skip_simplicity = skip_simplicity
        self.skip_vividness = skip_vividness
        self.reader_age = reader_age
        self.cuda_devices = cuda_devices
        self.concurrency = concurrency
        
        # Store config for workers
        self.vividness_weights = vividness_weights
        self.melbert_path = melbert_path
        
        # Note: In multiprocessing mode, vividness_evaluator needs to be initialized in workers.
        # But for 'evaluate_single_document' (fallback or if no cuda_devices), we might Init here.
        # However, initializing CUDA things here might break fork/spawn if not careful.
        # If cuda_devices is set, we skip main-process initialization of CUDA models to be safe?
        # Or we initialize it on cpu/default device as fallback.
        
        if not self.cuda_devices:
            # Initialize the vividness evaluator only when multiprocessing is not used.
            if not self.skip_vividness:
                self.vividness_evaluator = VividnessEvaluator(
                    weights=vividness_weights,
                    melbert_path=melbert_path
                )
            else:
                logger.info("Vividness evaluation is disabled")
        else:
            logger.info(
                "Multiprocessing mode enabled with devices: %s. Main process will skip model initialization.",
                cuda_devices,
            )

        # Initialize Informativeness Evaluator (QA)
        if not self.skip_informativeness:
            try:
                from .informativeness.evaluate_informativeness import InformativenessEvaluator
                # Configure reader_age in args if provided
                if args:
                    if hasattr(args, 'reader_age'):
                         pass # Already set
                    elif hasattr(self, 'reader_age'): # If passed to init but not in args
                         setattr(args, 'reader_age', self.reader_age)
                    else:
                         setattr(args, 'reader_age', 'adult') # Default
                
                self.informativeness_evaluator = InformativenessEvaluator(args=args)
                # logger.info("InformativenessEvaluator initialized successfully")
            except ImportError:
                logger.warning(
                    "InformativenessEvaluator import failed; skipping informativeness evaluation."
                )
                self.informativeness_evaluator = None

    async def evaluate_informativeness(self, wiki_text: str, popsci_text: str) -> Dict:
        """
        Evaluate informativeness (MCQ-based QA).
        """
        if not self.informativeness_evaluator:
            return {'score': 0.0, 'note': 'Evaluator not available'}
        
        try:
            return await self.informativeness_evaluator.evaluate_text_pair(wiki_text, popsci_text)
        except Exception as e:
            print(f"Informativeness evaluation failed: {e}")
            return {'score': 0.0, 'error': str(e)}
    
    def evaluate_coherence(self, text: str) -> float:
        """
        Evaluate coherence based on perplexity.
        
        Args:
            text: Text to evaluate.
            
        Returns:
            float: Perplexity score (lower is better).
        """
        try:
            ppl = simple_cal_ppl(text)
            return ppl
        except Exception as e:
            print(f"Coherence evaluation failed: {e}")
            return -1.0
    
    
    async def evaluate_coherence_llm(self, topic: str, article: str) -> dict:
        """
        Evaluate coherence using LLM as judge.
        """
        try:
            from openai import AsyncOpenAI
            auth_info = read_yaml_file("auth.yaml")
            
            # Use user specified llm_type
            # Prefer args configuration; default to gpt-4o if args or args.llm_type is missing.
            target_model = self.args.llm_type if (self.args and self.args.llm_type) else "gpt-4o"
            
            found_config = None
            api_key = ""
            base_url = ""
            model = target_model

            # Look up the corresponding model configuration in auth.yaml.
            for provider_name, provider_config in auth_info.items():
                if isinstance(provider_config, dict) and target_model in provider_config:
                    found_config = provider_config[target_model]
                    break
            
            if found_config:
                api_key = found_config.get("api_key", "")
                base_url = found_config.get("base_url", "")
                model = found_config.get("model", target_model)
            elif target_model == "gpt-4o":
                # Fallback implementation for legacy gpt-4o location if needed
                openai_config = auth_info.get("openai", {}).get("gpt-4o", {})
                api_key = openai_config.get("api_key", "")
                base_url = openai_config.get("base_url", "")
                model = openai_config.get("model", "gpt-4o")
            
            if not api_key:
                 logger.warning(f"No API key found for model '{target_model}' in auth.yaml")
                 return {"score": -1.0, "reason": f"No API key for {target_model}"}

            client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=180.0)
            
            # Use 'topic' or 'instruction'. If topic is long (like whole wikipedia text), we might want to truncate or summarize?
            # The prompt says 'Read the Topic/Instruction'. 
            # We will pass the full text for now.
            
            prompt_text = prompt["coherence_evaluation"].format(topic=topic, article=article)
            
            # Retry loop for Coherence LLM
            max_retries = 10
            response = None
            
            for attempt in range(max_retries):
                try:
                    # Default params from user
                    # Increase max_tokens to avoid cutting off response
                    # Reduce temperature slightly to ensure valid format, but keep it diverse enough for n=20
                    # Remove max_tokens restriction as per user request
                    response = await client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": prompt_text}],
                        temperature=1.2,
                        top_p=1,
                        frequency_penalty=0,
                        presence_penalty=0,
                        stop=None,
                        n=20
                    )
                    break # Success, exit loop
                except Exception as e:
                    error_msg = str(e)
                    is_retryable = (
                        "timeout" in error_msg.lower() or
                        "connection" in error_msg.lower() or
                        "rate limit" in error_msg.lower() or
                        "500" in error_msg or "502" in error_msg or "503" in error_msg or "504" in error_msg
                    )
                    
                    if is_retryable and attempt < max_retries - 1:
                        wait_time = 2 * (attempt + 1)
                        logger.warning(f"Coherence evaluation timeout/error (attempt {attempt+1}/{max_retries}); retrying in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                    else:
                        raise e # Re-raise if not retryable or max retries reached
            
            scores = []
            import re
            for choice in response.choices:
                content = choice.message.content
                # Parse score, looking for "Coherence: <digit>" or just digit
                match = re.search(r"Coherence:\s*(\d+(\.\d+)?)", content)
                if match:
                    scores.append(float(match.group(1)))
                else:
                    # Fallback: look for just a digit 1-5
                    match_digit = re.search(r"\b([1-5])\b", content)
                    if match_digit:
                        scores.append(float(match_digit.group(1)))
                    else:
                        logger.warning(f"Coherence parsing failed. Raw content: {content}")
            
            if scores:
                avg_score = sum(scores) / len(scores)
                return {
                    "score": avg_score, 
                    "raw_scores": scores,
                    "interpretation": f"Average of {len(scores)} samples (LLM Judge)"
                }
            else:
                return {"score": -1.0, "reason": "Could not parse scores from LLM response"}

        except Exception as e:
            logger.error(f"Coherence LLM evaluation failed: {e}")
            return {"score": -1.0, "error": str(e)}

    def evaluate_simplicity(self, original_text: str, simplified_text: str, reference_text: Optional[str] = None) -> float:
        """
        Evaluate simplicity using the FKGL score (lower is simpler).
        
        Args:
            original_text: Original complex text.
            simplified_text: Simplified text (popsci article to evaluate).
            reference_text: Reference text (optional, unused).
            
        Returns:
            float: FKGL score (lower values mean more readable).
        """
        try:
            import re
            
            # Split the text into sentences.
            def split_sentences(text):
                # Simple sentence splitting on punctuation.
                sentences = re.split(r'[.!?]+', text)
                sentences = [s.strip() for s in sentences if s.strip()]
                return sentences
            
            simplified_sentences = split_sentences(simplified_text)
            
            if not simplified_sentences:
                return -1.0
            
            # Calculate FKGL.
            fkgl_score = corpus_fkgl(
                sentences=simplified_sentences,
                tokenizer='13a'
            )
            
            return fkgl_score
        except Exception as e:
            print(f"Simplicity evaluation failed: {e}")
            import traceback
            traceback.print_exc()
            return -1.0
    
    def evaluate_vividness(self, text: str, return_components: bool = False) -> Union[float, Dict]:
        """
        Evaluate the vividness of the text.
        
        Args:
            text: Text to evaluate.
            return_components: Whether to return component scores.
            
        Returns:
            float or dict: A vividness score or a dict of component scores.
        """
        return self.vividness_evaluator.evaluate_text(text, return_components=return_components)
    
    async def generate_keyfacts(
        self,
        text: str,
        text_type: str = "wikipedia",
        llm_type: str = None,
        model_type: str = None,
        max_retries: int = 10
    ) -> Union[str, List[Dict]]:
        """
        Generate keyfacts with retry support.

        Args:
            text: Text to extract keyfacts from.
            text_type: Type of the text (wikipedia/popsci).
            llm_type: LLM type to use.
            model_type: Model identifier.
            max_retries: Maximum retry attempts.

        Returns:
            str: JSON string containing keyfacts.
        """
        if self.args is None:
            logger.error("Missing args parameter, cannot generate keyfacts.")
            return "[]"
        
        # Prepare the client and prompt (no retries needed; configure once).
        try:
            from openai import AsyncOpenAI
            # Read authentication info.
            auth_info = read_yaml_file("auth.yaml")
            
            # Use the user-specified llm_type (should be a concrete model name).
            # Compatibility: if llm_type is a provider name, find the first available model.
            # If llm_type is already a concrete model, search across providers.
            
            user_specified_model = llm_type or self.args.llm_type
            if not user_specified_model:
                user_specified_model = 'gemini-3-flash-preview' # Default backup
            
            found_config = None
            
            # 1. Try locating the model key directly under each provider in auth.yaml.
            for _, provider_config in auth_info.items():
                if isinstance(provider_config, dict):
                    if user_specified_model in provider_config:
                        found_config = provider_config[user_specified_model]
                        break
            
            # 2. If still not found, check if the user provided a provider name (for backward compatibility).
            if not found_config and user_specified_model in auth_info:
                provider_config = auth_info[user_specified_model]
                if isinstance(provider_config, dict):
                    # Take the first child model.
                    first_model_key = next(iter(provider_config.keys()))
                    if isinstance(provider_config[first_model_key], dict):
                        found_config = provider_config[first_model_key]
                    else:
                        # Or the provider uses a flat structure.
                        found_config = provider_config

            if found_config:
                api_key = found_config.get("api_key", "")
                base_url = found_config.get("base_url", "")
                model = found_config.get("model", user_specified_model)
            else:
                logger.warning(
                    "No configuration entry for model '%s' found in auth.yaml.",
                    user_specified_model,
                )
                return "[]"

            client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=180.0)
            prompt_template_name = "key_fact_extraction_with_priority"
            prompt_text = prompt[prompt_template_name].format(paper=text)

        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            return "[]"

        # Retry loop.
        for attempt in range(max_retries):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt_text}],
                )
                
                if response and response.choices:
                    result = response.choices[0].message.content
                    # logger.debug(f"Successfully generated {text_type} keyfacts")
                    return result
                else:
                    # Empty response; possibly temporary.
                    if attempt < max_retries - 1:
                        logger.warning(
                            "Empty response generating %s keyfacts; retry %s/%s",
                            text_type,
                            attempt + 1,
                            max_retries,
                        )
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    return "[]"

            except Exception as e:
                error_msg = str(e)
                # Check whether a retry is warranted.
                is_retryable = (
                    "timeout" in error_msg.lower() or
                    "connection" in error_msg.lower() or
                    "rate limit" in error_msg.lower() or
                    "500" in error_msg or "502" in error_msg or "503" in error_msg or "504" in error_msg or "524" in error_msg
                )

                if is_retryable and attempt < max_retries - 1:
                    wait_time = 2 * (attempt + 1) + 1
                    logger.warning(
                        "Keyfacts generation failed (%s) attempt %s/%s: %s. Waiting %ss before retry.",
                        text_type,
                        attempt + 1,
                        max_retries,
                        error_msg,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    if attempt == max_retries - 1:
                        logger.error(
                            "Keyfacts generation finally failed (%s): %s",
                            text_type,
                            error_msg,
                        )
                    else:
                        logger.warning(
                            "Non-retryable error generating %s keyfacts: %s",
                            text_type,
                            error_msg,
                        )
                    return "[]"

        return "[]"
    
    async def evaluate_keyfacts(
        self,
        ground_truth_keyfacts: Union[str, List[Dict], Dict],
        generated_keyfacts: Union[str, List[Dict], Dict],
        ground_truth_path: Optional[str] = None,
        generated_keyfacts_path: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Evaluate precision and recall for keyfacts.
        
        Args:
            ground_truth_keyfacts: Ground truth keyfacts (JSON string/list/dict).
            generated_keyfacts: Generated keyfacts (JSON string/list/dict).
            ground_truth_path: Optional path to ground truth keyfacts file.
            generated_keyfacts_path: Optional path to generated keyfacts file.
            
        Returns:
            dict: Dictionary containing precision and recall metrics.
        """
        if self.args is None:
            logger.error("Missing args parameter; cannot evaluate keyfacts.")
            return {
                'precision': -1.0,
                'recall': -1.0,
                'precision_by_priority': {},
                'recall_by_priority': {}
            }
        
        try:
            # Use provided file paths if available.
            if ground_truth_path and generated_keyfacts_path:
                result = await async_calculate_precision_recall(
                    ground_truth_path,
                    generated_keyfacts_path,
                    self.args
                )
                return {
                    'precision': result['precisions'].get('overall', -1.0),
                    'recall': result['recalls'].get('overall', -1.0),
                    'precision_by_priority': {
                        'priority_1': result['precisions'].get('priority_1', -1.0),
                        'priority_2': result['precisions'].get('priority_2', -1.0),
                        'priority_3': result['precisions'].get('priority_3', -1.0),
                    },
                    'recall_by_priority': {
                        'priority_1': result['recalls'].get('priority_1', -1.0),
                        'priority_2': result['recalls'].get('priority_2', -1.0),
                        'priority_3': result['recalls'].get('priority_3', -1.0),
                    }
                }
            else:
                # If no file paths, write the data to temporary files.
                import tempfile
                import aiofiles
                
                # Handle ground truth keyfacts.
                if isinstance(ground_truth_keyfacts, str):
                    gt_data = json.loads(ground_truth_keyfacts)
                else:
                    gt_data = ground_truth_keyfacts
                
                # Handle generated keyfacts.
                if isinstance(generated_keyfacts, str):
                    gen_data = json.loads(generated_keyfacts)
                else:
                    gen_data = generated_keyfacts
                
                # Create temporary files.
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as gt_file:
                    json.dump(gt_data, gt_file, indent=2, ensure_ascii=False)
                    gt_path = gt_file.name
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as gen_file:
                    json.dump(gen_data, gen_file, indent=2, ensure_ascii=False)
                    gen_path = gen_file.name
                
                try:
                    result = await async_calculate_precision_recall(
                        gt_path,
                        gen_path,
                        self.args
                    )
                    return {
                        'precision': result['precisions'].get('overall', -1.0),
                        'recall': result['recalls'].get('overall', -1.0),
                        'precision_by_priority': {
                            'priority_1': result['precisions'].get('priority_1', -1.0),
                            'priority_2': result['precisions'].get('priority_2', -1.0),
                            'priority_3': result['precisions'].get('priority_3', -1.0),
                        },
                        'recall_by_priority': {
                            'priority_1': result['recalls'].get('priority_1', -1.0),
                            'priority_2': result['recalls'].get('priority_2', -1.0),
                            'priority_3': result['recalls'].get('priority_3', -1.0),
                        }
                    }
                finally:
                    # Clean up temporary files.
                    if os.path.exists(gt_path):
                        os.remove(gt_path)
                    if os.path.exists(gen_path):
                        os.remove(gen_path)
        except Exception as e:
            logger.warning(f"Keyfacts evaluation failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                'precision': -1.0,
                'recall': -1.0,
                'precision_by_priority': {},
                'recall_by_priority': {}
            }
    
    async def evaluate_single_document(
        self,
        popsci_text: str,
        original_text: Optional[str] = None,
        reference_text: Optional[str] = None,
        ground_truth_keyfacts: Optional[Union[str, List[Dict], Dict]] = None,
        generated_keyfacts: Optional[Union[str, List[Dict], Dict]] = None,
        ground_truth_keyfacts_path: Optional[str] = None,
        generated_keyfacts_path: Optional[str] = None,
        include_keyfacts: bool = True,
        include_informativeness: bool = True,
        informativeness_result: Optional[Dict] = None
    ) -> Dict:
        """
        Evaluate a single document across all metrics.
        
        Args:
            popsci_text: Popsci article text to evaluate.
            original_text: Original complex text for simplicity.
            reference_text: Optional reference text for comparison.
            ground_truth_keyfacts: Ground truth keyfacts for evaluation.
            generated_keyfacts: Generated keyfacts to compare.
            ground_truth_keyfacts_path: Optional path to ground truth keyfacts file.
            generated_keyfacts_path: Optional path to generated keyfacts file.
            include_keyfacts: Whether to include keyfacts evaluation.
            include_informativeness: Whether to include informativeness evaluation.
            informativeness_result: Precomputed informativeness result (optional).
            
        Returns:
            dict: Dictionary containing results for all metrics.
        """
        result = {
            'popsci_text': popsci_text[:200] + '...' if len(popsci_text) > 200 else popsci_text,
            'coherence': {},
            'simplicity': {},
            'vividness': {},
            'keyfacts': {},
            'informativeness': {}
        }
        
        # ============================================================
        # Phase 1: Run evaluations that do not require LLMs (local models).
        # ============================================================
        
        # 1. Evaluate coherence (local GPT-2 model + optional LLM judge).
        if self.skip_coherence:
            logger.debug("Skipping coherence evaluation.")
            result['coherence'] = {
                'ppl_score': -1.0,
                'interpretation': 'Coherence evaluation skipped.'
            }
        else:
            logger.debug("Evaluating coherence (PPL)...")
            ppl_score = self.evaluate_coherence(popsci_text)
            
            # Evaluate with LLM (LLM as Judge)
            if self.skip_coherence_llm:
                logger.debug("Skipping LLM Judge coherence evaluation.")
                llm_result = {'score': -1.0, 'interpretation': 'Skipped LLM Judge'}
            else:
                logger.debug("Evaluating coherence with LLM Judge...")
                if original_text:
                    llm_result = await self.evaluate_coherence_llm(original_text, popsci_text)
                else:
                    llm_result = {'score': -1.0, 'reason': 'No original text provided'}
            
            result['coherence'] = {
                'ppl_score': ppl_score,
                'interpretation': self._interpret_ppl(ppl_score),
                'llm_score': llm_result.get('score', -1.0),
                'llm_details': llm_result
            }
        
        # 2. Evaluate simplicity (EASSE FKGL; no LLM required).
        if original_text:
            logger.debug("Evaluating simplicity (FKGL)...")
            simplicity_score = self.evaluate_simplicity(original_text, popsci_text, reference_text)
            result['simplicity'] = {
                'fkgl_score': simplicity_score,
                'interpretation': self._interpret_fkgl(simplicity_score)
            }
        else:
            result['simplicity'] = {
                'fkgl_score': -1.0,
                'interpretation': 'Original text unavailable; skipping simplicity evaluation.'
            }
        
        # 3. Evaluate vividness (local MelBERT/VADER/NLTK; no LLM required).
        if self.skip_vividness:
            logger.debug("Skipping vividness evaluation.")
            result['vividness'] = {
                'vividness_score': -1.0,
                'interpretation': 'Vividness evaluation skipped.',
                'figurativeness': 0.0,
                'emotionality': 0.0,
                'decorativeness': 0.0
            }
        else:
            logger.debug("Evaluating vividness...")
            try:
                vividness_result = self.evaluate_vividness(popsci_text, return_components=True)
                if isinstance(vividness_result, dict):
                    result['vividness'] = vividness_result
                else:
                    result['vividness'] = {
                        'vividness_score': vividness_result,
                        'figurativeness': 0.0,
                        'emotionality': 0.0,
                        'decorativeness': 0.0
                    }
            except Exception as e:
                logger.warning(f"Vividness evaluation failed: {e}")
                result['vividness'] = {
                    'vividness_score': -1.0,
                    'error': str(e),
                    'figurativeness': 0.0,
                    'emotionality': 0.0,
                    'decorativeness': 0.0
                }
        
        # ============================================================
        # Phase 2: Run evaluations requiring LLM APIs.
        # ============================================================
        
        # 4. Evaluate keyfacts (requires LLM-based alignment).
        if include_keyfacts:
            if ground_truth_keyfacts_path and generated_keyfacts_path:
                logger.debug("Evaluating keyfacts precision and recall...")
                keyfacts_result = await self.evaluate_keyfacts(
                    None, None,
                    ground_truth_path=ground_truth_keyfacts_path,
                    generated_keyfacts_path=generated_keyfacts_path
                )
                result['keyfacts'] = keyfacts_result
            elif ground_truth_keyfacts and generated_keyfacts:
                logger.debug("Evaluating keyfacts precision and recall...")
                keyfacts_result = await self.evaluate_keyfacts(
                    ground_truth_keyfacts,
                    generated_keyfacts
                )
                result['keyfacts'] = keyfacts_result
            else:
                result['keyfacts'] = {
                    'precision': -1.0,
                    'recall': -1.0,
                    'note': 'Missing keyfacts data; skipped evaluation.'
                }
        else:
            result['keyfacts'] = {
                'note': 'Keyfacts evaluation not enabled.'
            }

        # 5. Evaluate informativeness (QA-based).
        if informativeness_result:
            result['informativeness'] = informativeness_result
        elif include_informativeness:
            if original_text and popsci_text:
                logger.debug("Evaluating informativeness (QA-based)...")
                
                # Attempt to parse keyfacts.
                wiki_kf = None
                popsci_kf = None
                
                if isinstance(ground_truth_keyfacts, list): wiki_kf = ground_truth_keyfacts
                elif isinstance(ground_truth_keyfacts, str): 
                    try: wiki_kf = json.loads(ground_truth_keyfacts)
                    except: pass
                
                if isinstance(generated_keyfacts, list): popsci_kf = generated_keyfacts
                elif isinstance(generated_keyfacts, str):
                    try: popsci_kf = json.loads(generated_keyfacts)
                    except: pass
                
                try:
                    if self.informativeness_evaluator:
                        info_res = await self.informativeness_evaluator.evaluate_text_pair(
                            original_text, 
                            popsci_text, 
                            wiki_keyfacts=wiki_kf, 
                            popsci_keyfacts=popsci_kf
                        )
                        result['informativeness'] = info_res if info_res else {'score': 0.0, 'note': 'Evaluation returned None'}
                    else:
                         result['informativeness'] = {'score': 0.0, 'note': 'Evaluator not initialized'}
                except Exception as e:
                    logger.warning(f"Informativeness evaluation failed: {e}")
                    result['informativeness'] = {'score': 0.0, 'error': str(e)}
            else:
                 result['informativeness'] = {'score': 0.0, 'note': 'Missing original or popsci text'}
        else:
             result['informativeness'] = {'note': 'Informativeness evaluation not included'}
        
        return result
    
    async def evaluate_document_pair(
        self,
        popsci_text_1: str,
        popsci_text_2: str,
        original_text: Optional[str] = None,
        reference_text: Optional[str] = None
    ) -> Dict:
        """
        Evaluate a pair of documents.
        
        Args:
            popsci_text_1: Text of the first popsci article.
            popsci_text_2: Text of the second popsci article.
            original_text: Original complex text (used for simplicity).
            reference_text: Optional reference text for comparison.
            
        Returns:
            dict: Evaluation results for both documents and their comparison.
        """
        print("Evaluating document pair...")
        
        # Evaluate the first document.
        result_1 = await self.evaluate_single_document(
            popsci_text_1,
            original_text,
            reference_text,
            include_keyfacts=False,
            include_informativeness=True
        )
        
        # Evaluate the second document.
        result_2 = await self.evaluate_single_document(
            popsci_text_2,
            original_text,
            reference_text,
            include_keyfacts=False,
            include_informativeness=True
        )
        
        # Compare the results.
        comparison = {
            'coherence': {
                'text_1_ppl': result_1['coherence']['ppl_score'],
                'text_2_ppl': result_2['coherence']['ppl_score'],
                'better': 'text_1' if result_1['coherence']['ppl_score'] < result_2['coherence']['ppl_score'] else 'text_2',
                'difference': abs(result_1['coherence']['ppl_score'] - result_2['coherence']['ppl_score'])
            },
            'simplicity': {
                'text_1_fkgl': result_1['simplicity']['fkgl_score'],
                'text_2_fkgl': result_2['simplicity']['fkgl_score'],
                'better': 'text_1' if result_1['simplicity']['fkgl_score'] < result_2['simplicity']['fkgl_score'] else 'text_2',  # Lower FKGL is better.
                'difference': abs(result_1['simplicity']['fkgl_score'] - result_2['simplicity']['fkgl_score'])
            },
            'vividness': {
                'text_1_score': result_1['vividness'].get('vividness_score', 0.0),
                'text_2_score': result_2['vividness'].get('vividness_score', 0.0),
                'better': 'text_1' if result_1['vividness'].get('vividness_score', 0.0) > result_2['vividness'].get('vividness_score', 0.0) else 'text_2',
                'difference': abs(result_1['vividness'].get('vividness_score', 0.0) - result_2['vividness'].get('vividness_score', 0.0))
            },
            'informativeness': {
                'text_1_score': result_1['informativeness'].get('score', 0.0),
                'text_2_score': result_2['informativeness'].get('score', 0.0),
                'better': 'text_1' if result_1['informativeness'].get('score', 0.0) > result_2['informativeness'].get('score', 0.0) else 'text_2',
                'difference': abs(result_1['informativeness'].get('score', 0.0) - result_2['informativeness'].get('score', 0.0))
            }
        }
        
        return {
            'text_1': result_1,
            'text_2': result_2,
            'comparison': comparison
        }
    
    async def evaluate_dataset(
        self,
        dataset_path: str,
        output_path: Optional[str] = None,
        dataset_format: str = 'json',
        dataset_data: Optional[List[Dict]] = None,
        popsci_field: str = 'popsci_text',
        original_field: Optional[str] = 'original_text',
        reference_field: Optional[str] = None,
        ground_truth_keyfacts_field: Optional[str] = None,
        generated_keyfacts_field: Optional[str] = None,
        ground_truth_keyfacts_dir: Optional[str] = None,
        generated_keyfacts_dir: Optional[str] = None,
        include_keyfacts: bool = True,
        include_informativeness: bool = True,
        auto_generate_keyfacts: bool = False
    ) -> Dict:
        """
        Evaluate the dataset provided in the specified format.
        
        Args:
            dataset_path: Input dataset file path.
            output_path: Output file for storing results (defaults to auto-generated path).
            dataset_format: Dataset format ('json' or 'jsonl').
            dataset_data: Optional in-memory dataset. If provided, it overrides file loading.
            popsci_field: Field name for the popsci article text.
            original_field: Field name for the original article text.
            reference_field: Optional reference field name.
            ground_truth_keyfacts_field: Optional field name for true keyfacts.
            generated_keyfacts_field: Optional field name for generated keyfacts.
            ground_truth_keyfacts_dir: Optional directory containing ground truth keyfacts files.
                Matching strategies include:
                1. Use doc_id: {doc_id}_keyfacts.json.
                2. Match by index: the i-th file in the sorted directory.
                3. Match by title: {title}_keyfacts.json or {title}_key_facts.json.
            generated_keyfacts_dir: Optional directory for generated keyfacts files (same matching strategies).
            include_keyfacts: Whether to run keyfacts evaluation.
            include_informativeness: Whether to include informativeness evaluation.
            auto_generate_keyfacts: Whether to auto-generate keyfacts.
                If True, Wikipedia keyfacts are generated from original_text (gemini-3-pro-preview)
                and popsci keyfacts are generated from popsci_text (grok).
                Provided directories or fields take precedence over auto-generation.
            
        Returns:
            dict: Aggregated results and statistics for all documents.
                Statistics include:
                - keyfacts_precision: Overall precision metrics.
                - keyfacts_recall: Overall recall metrics.
                - keyfacts_precision_by_priority: Precision per priority.
                - keyfacts_recall_by_priority: Recall per priority.
        """
        # Helper to save progress
        def save_progress(current_dataset):
            if output_path:
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        # Wrap in structure if needed, or just list
                        # Ideally we want to match final output format
                        # But here we just dump the list as 'current_dataset' is likely the list
                        # The final output usually handles the wrapping. 
                        # Let's save as list for now or enrich later.
                        json.dump(current_dataset, f, indent=4, ensure_ascii=False)
                    # print("Progress saved") # Optional: reduce verbosity
                except Exception as e:
                    print(f"Failed to save progress: {e}")

        # Use the default output path if none was specified.
        if output_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            dataset_name = os.path.splitext(os.path.basename(dataset_path))[0]
            output_path = os.path.join(project_root, 'output', f'{dataset_name}_evaluation_results.json')
        
        logger.info(f"Starting dataset evaluation: {dataset_path}")
        
        # Load the dataset.
        if dataset_data is not None:
            dataset = dataset_data
        elif dataset_format == 'json':
            with open(dataset_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
        elif dataset_format == 'jsonl':
            dataset = []
            with open(dataset_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        dataset.append(json.loads(line))
        else:
            raise ValueError(f"Unsupported dataset format: {dataset_format}")
        
        if not isinstance(dataset, list):
            raise ValueError("Invalid dataset format: expected a list.")
        
        results = []
        total = len(dataset)
        
        # Helper: get nested field values (supports keys like 'popsci_article.content', including dots).
        def get_nested_field(data, field_path, default=''):
            """Get nested field values; supports dotted keys."""
            if not isinstance(data, dict) or not field_path:
                return default
                
            # 1. Try direct match (fastest).
            if field_path in data:
                result = data[field_path]
                return result if result else default
                
            # 2. Recursive lookup: split the path into prefix + remainder.
            def recursive_find(d, path_parts):
                # Attempt to combine the first i parts into a key.
                for i in range(1, len(path_parts) + 1):
                    current_key = ".".join(path_parts[:i])
                    if current_key in d:
                        # If at the last part, return the value.
                        if i == len(path_parts):
                            return d[current_key]
                        
                        # Otherwise recursively resolve the remainder.
                        val = d[current_key]
                        if isinstance(val, dict):
                            remaining_parts = path_parts[i:]
                            res = recursive_find(val, remaining_parts)
                            if res is not None:
                                return res
                return None

            parts = field_path.split('.')
            found_val = recursive_find(data, parts)
            
            if found_val is not None:
                return found_val if found_val else default
            return default
        
        # Helper: set nested field values.
        def set_nested_field(data, field_path, value):
            """Set nested field values."""
            keys = field_path.split('.')
            current = data
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = value
        
        # Compute the keyfacts storage path by replacing the last segment of popsci_field with 'keyfacts'.
        # For example: models.gemini-3-pro-preview.content -> models.gemini-3-pro-preview.keyfacts.
        popsci_field_parts = popsci_field.split('.')
        if len(popsci_field_parts) > 1:
            keyfacts_field_path = '.'.join(popsci_field_parts[:-1]) + '.keyfacts'
        else:
            keyfacts_field_path = 'generated_keyfacts'  # Default field.
        
        logger.info(f"Keyfacts will be stored at: {keyfacts_field_path}")
        
        # If auto-generation of keyfacts is enabled, collect all tasks first and then run them concurrently.
        keyfacts_generation_tasks = []  # [(doc_index, text, text_type, is_gt), ...]
        doc_keyfacts_map = {}  # {doc_index: {'gt': None, 'gen': None}}
        
        # First pass: collect all tasks that need keyfacts generation.
        if auto_generate_keyfacts and (include_keyfacts or include_informativeness):
            logger.info(f"\nCollecting keyfacts generation tasks...")
            for i, item in enumerate(dataset):
                popsci_text = get_nested_field(item, popsci_field, '')
                original_text = get_nested_field(item, original_field, None) if original_field else None
                
                if not popsci_text:
                    continue
                
                # Check whether generation is needed.
                need_gt = False
                need_gen = False
                
                doc_keyfacts_map[i] = {'gt': None, 'gen': None}

                # 1. First Priority: Check if keyfacts already exist in the dataset item itself
                # This allows resuming from a previous run result file
                if 'original_keyfacts' in item and item['original_keyfacts']:
                     doc_keyfacts_map[i]['gt'] = item['original_keyfacts']
                
                # 1.5 Priority: Check specific user-requested path for ground truth
                # original_data.original_data.wikipedia_article.keyfacts
                if not doc_keyfacts_map[i]['gt']:
                    special_gt = get_nested_field(item, "original_data.original_data.wikipedia_article.keyfacts", None)
                    if special_gt:
                        doc_keyfacts_map[i]['gt'] = special_gt

                # 1.55 Priority: Check passed ground_truth_keyfacts_field (moved up to avoid overwriting need_gt logic)
                if not doc_keyfacts_map[i]['gt'] and ground_truth_keyfacts_field:
                    gt_field = get_nested_field(item, ground_truth_keyfacts_field, None)
                    if gt_field:
                         doc_keyfacts_map[i]['gt'] = gt_field
                
                # 1.6 Priority: Check model-specific keyfacts field (e.g., models.gemini-3-pro-preview.keyfacts)
                if not doc_keyfacts_map[i]['gen']:
                    model_keyfacts = get_nested_field(item, keyfacts_field_path, None)
                    if model_keyfacts:
                        doc_keyfacts_map[i]['gen'] = model_keyfacts
                        logger.info(f"Document {i}: loaded existing keyfacts from {keyfacts_field_path}")
                
                # 1.7 Priority: Check top-level generated_keyfacts for backward compatibility
                if not doc_keyfacts_map[i]['gen'] and 'generated_keyfacts' in item and item['generated_keyfacts']:
                     doc_keyfacts_map[i]['gen'] = item['generated_keyfacts']

                # 1.8 Priority: Check passed generated_keyfacts_field
                if not doc_keyfacts_map[i]['gen'] and generated_keyfacts_field:
                    gen_field = get_nested_field(item, generated_keyfacts_field, None)
                    if gen_field:
                        doc_keyfacts_map[i]['gen'] = gen_field
                
                # 2. Second Priority: Check file paths (if provided)
                has_gt_file = False
                has_gen_file = False

                if ground_truth_keyfacts_dir and generated_keyfacts_dir:
                    doc_id = item.get('id', str(i))
                    
                    gt_file = None
                    gen_file = None
                    
                    # Try multiple naming formats.
                    # Prefer title, then ID.
                    title = get_nested_field(item, 'title', '').replace(' ', '_').replace('/', '_')
                    
                    # Strategy 1: Try matching by doc_id.
                    possible_gt_names = [f"{doc_id}_keyfacts.json"]
                    possible_gen_names = [f"{doc_id}_keyfacts.json"]
                    if title:
                        possible_gt_names.insert(0, f"{title}_keyfacts.json")
                        possible_gen_names.insert(0, f"{title}_keyfacts.json")
                    
                    for name in possible_gt_names:
                        temp_gt_file = os.path.join(ground_truth_keyfacts_dir, name)
                        if os.path.exists(temp_gt_file):
                            gt_file = temp_gt_file
                            break
                    for name in possible_gen_names:
                        temp_gen_file = os.path.join(generated_keyfacts_dir, name)
                        if os.path.exists(temp_gen_file):
                            gen_file = temp_gen_file
                            break

                    # Strategy 2: If that fails, match by index.
                    if not gt_file and not gen_file:
                        gt_files = sorted([f for f in os.listdir(ground_truth_keyfacts_dir) if f.endswith(".json")])
                        gen_files = sorted([f for f in os.listdir(generated_keyfacts_dir) if f.endswith(".json")])
                        if i < len(gt_files) and i < len(gen_files):
                            gt_file = os.path.join(ground_truth_keyfacts_dir, gt_files[i])
                            gen_file = os.path.join(generated_keyfacts_dir, gen_files[i])
                    
                    if gt_file and os.path.exists(gt_file):
                         has_gt_file = True

                    if gen_file and os.path.exists(gen_file):
                        has_gen_file = True

                # 3. Final Decision: Need Generate or Not
                if not doc_keyfacts_map[i]['gt'] and not has_gt_file and original_text:
                    need_gt = True
                
                if not doc_keyfacts_map[i]['gen'] and not has_gen_file and popsci_text:
                    need_gen = True
                
                # Add to the task list.
                if need_gt:
                    keyfacts_generation_tasks.append((i, original_text, "wikipedia", True))
                if need_gen:
                    keyfacts_generation_tasks.append((i, popsci_text, "popsci", False))
            
            # Generate keyfacts in batch concurrently.
            if keyfacts_generation_tasks:
                logger.info(f"Starting batch keyfacts generation for {len(keyfacts_generation_tasks)} tasks (concurrency: {self.concurrency}).")
                
                # Use a semaphore to limit concurrency (adjustable via --concurrency).
                semaphore = asyncio.Semaphore(self.concurrency)
                
                async def generate_with_semaphore(doc_idx, text, text_type, is_gt):
                    try:
                        async with semaphore:
                            result = await self.generate_keyfacts(text, text_type=text_type)
                            return (doc_idx, result, is_gt)
                    except Exception as e:
                        logger.warning(f"Keyfacts generation failed (doc {doc_idx}, {'GT' if is_gt else 'GEN'}): {e}")
                        return (doc_idx, "[]", is_gt)
                
                # Create all tasks.
                tasks = [generate_with_semaphore(doc_idx, text, text_type, is_gt) 
                        for doc_idx, text, text_type, is_gt in keyfacts_generation_tasks]
                
                # Execute in batches.
                from tqdm.asyncio import tqdm
                
                # Use tqdm for progress monitoring
                for i, result_or_task in enumerate(tqdm.as_completed(tasks, desc="Generating Keyfacts", total=len(tasks))):
                     # Wait for each task as it completes
                     doc_idx, result, is_gt = await result_or_task
                     
                     # Process result immediately
                     if result: # Only process if we got a string back
                         try:
                             parsed_result = json.loads(result)
                             if is_gt:
                                 doc_keyfacts_map[doc_idx]['gt'] = parsed_result
                                 # Persist back to dataset
                                 dataset[doc_idx]['original_keyfacts'] = parsed_result
                             else:
                                 doc_keyfacts_map[doc_idx]['gen'] = parsed_result
                                 # Persist back to dataset
                                 set_nested_field(dataset[doc_idx], keyfacts_field_path, parsed_result)
                                 dataset[doc_idx]['generated_keyfacts'] = parsed_result
                         except json.JSONDecodeError:
                             pass # logger.warning("Parsing keyfacts JSON failed")
                     
                     # Regularly save progress
                     if i % 20 == 0:
                         save_progress(dataset)

                # Final save
                save_progress(dataset)
                logger.info(f"Completed batch keyfacts generation.")
        
        # Second pass: collect keyfacts evaluation tasks and document metadata for concurrent evaluation.
        keyfacts_evaluation_tasks = []  # [(doc_index, gt_keyfacts, gen_keyfacts, gt_path, gen_path), ...]
        informativeness_evaluation_tasks = [] # [(doc_index, original_text, popsci_text, gt_keyfacts, gen_keyfacts), ...]
        doc_info_map = {}  # {doc_index: {item, popsci_text, original_text, ...}}
        
        # Collect document info and keyfacts evaluation tasks.
        for i, item in enumerate(dataset):
            print(f"\nProcessing document {i+1}/{total}...")
            
            # Extract fields (supports nested paths like 'popsci_article.content').
            popsci_text = get_nested_field(item, popsci_field, '')
            original_text = get_nested_field(item, original_field, None) if original_field else None
            reference_text = get_nested_field(item, reference_field, None) if reference_field else None
            
            if not popsci_text:
                print(f"Document {i+1} is missing popsci text; skipping.")
                continue
            
            # Process keyfacts data.
            ground_truth_keyfacts = None
            generated_keyfacts = None
            ground_truth_keyfacts_path = None
            generated_keyfacts_path = None
            
            # Try to load keyfacts regardless of include_keyfacts, as informativeness may still require them.
            if include_keyfacts or include_informativeness:
                # Priority: file paths > dataset fields > auto-generation.
                found_gt_keyfacts = False
                found_gen_keyfacts = False
                
                # 1. Try locating keyfacts from directory files.
                if ground_truth_keyfacts_dir and generated_keyfacts_dir:
                    # Strategy 1: Try matching by doc_id.
                    doc_id = item.get('id', str(i))
                    # Try multiple filename conventions.
                    # Prefer title, then id.
                    title = get_nested_field(item, 'title', '').replace(' ', '_').replace('/', '_')
                    
                    gt_file = None
                    gen_file = None
                    
                    # search logic... simplified for brevity as it was not changed
                    possible_gt_names = [f"{doc_id}_keyfacts.json"]
                    possible_gen_names = [f"{doc_id}_keyfacts.json"]
                    if title:
                        possible_gt_names.insert(0, f"{title}_keyfacts.json")
                        possible_gen_names.insert(0, f"{title}_keyfacts.json")
                    
                    if not (os.path.exists(gt_file) and os.path.exists(gen_file)):
                        # List and sort all JSON files in the directory.
                        gt_files = sorted([f for f in os.listdir(ground_truth_keyfacts_dir) if f.endswith(".json")])
                        gen_files = sorted([f for f in os.listdir(generated_keyfacts_dir) if f.endswith(".json")])
                        
                        if i < len(gt_files) and i < len(gen_files):
                            gt_file = os.path.join(ground_truth_keyfacts_dir, gt_files[i])
                            gen_file = os.path.join(generated_keyfacts_dir, gen_files[i])
                    
                    # Strategy 3: Try matching by title.
                    if not (os.path.exists(gt_file) and os.path.exists(gen_file)):
                        title = get_nested_field(item, 'title', '') or get_nested_field(item, 'popsci_article.title', '') or get_nested_field(item, 'wikipedia_article.title', '')
                        if title:
                            # Try multiple possible filename variations.
                            possible_gt_names = [
                                f"{title}_keyfacts.json",
                                f"{title}_key_facts.json",
                                f"{doc_id}_keyfacts.json",
                                f"{doc_id}_key_facts.json"
                            ]
                            possible_gen_names = [
                                f"{title}_keyfacts.json",
                                f"{title}_key_facts.json",
                                f"{doc_id}_keyfacts.json",
                                f"{doc_id}_key_facts.json"
                            ]
                            
                            for gt_name in possible_gt_names:
                                for gen_name in possible_gen_names:
                                    gt_path = os.path.join(ground_truth_keyfacts_dir, gt_name)
                                    gen_path = os.path.join(generated_keyfacts_dir, gen_name)
                                    if os.path.exists(gt_path) and os.path.exists(gen_path):
                                        gt_file = gt_path
                                        gen_file = gen_path
                                        break
                                if os.path.exists(gt_file) and os.path.exists(gen_file):
                                    break
                    
                    if os.path.exists(gt_file) and os.path.exists(gen_file):
                        ground_truth_keyfacts_path = gt_file
                        generated_keyfacts_path = gen_file
                        found_gt_keyfacts = True
                        found_gen_keyfacts = True
                    else:
                        print(f"Document {i+1} could not find matching keyfacts files")
                        print(f"  Attempted paths: {gt_file}, {gen_file}")
                
                # 2. If files are unavailable, extract from the dataset (supports nested paths).
                if not found_gt_keyfacts:
                    # 2.1 Check item['original_keyfacts']
                    if 'original_keyfacts' in item and item['original_keyfacts']:
                        ground_truth_keyfacts = item['original_keyfacts']
                        found_gt_keyfacts = True
                    
                    # 2.2 Check original_data.original_data.wikipedia_article.keyfacts
                    if not found_gt_keyfacts:
                        special_gt = get_nested_field(item, "original_data.original_data.wikipedia_article.keyfacts", None)
                        if special_gt:
                            ground_truth_keyfacts = special_gt
                            found_gt_keyfacts = True
                    
                    # 2.3 Check ground_truth_keyfacts_field
                    if not found_gt_keyfacts and ground_truth_keyfacts_field:
                        ground_truth_keyfacts = get_nested_field(item, ground_truth_keyfacts_field, None)
                        if ground_truth_keyfacts:
                            found_gt_keyfacts = True
                
                if not found_gen_keyfacts:
                    # 2.1 Check model-specific keyfacts field
                    model_keyfacts = get_nested_field(item, keyfacts_field_path, None)
                    if model_keyfacts:
                        generated_keyfacts = model_keyfacts
                        found_gen_keyfacts = True
                    
                    # 2.2 Check top-level generated_keyfacts
                    if not found_gen_keyfacts and 'generated_keyfacts' in item and item['generated_keyfacts']:
                        generated_keyfacts = item['generated_keyfacts']
                        found_gen_keyfacts = True

                    # 2.3 Check user-specified generated_keyfacts_field
                    if not found_gen_keyfacts and generated_keyfacts_field:
                        generated_keyfacts = get_nested_field(item, generated_keyfacts_field, None)
                        if generated_keyfacts:
                            found_gen_keyfacts = True
                
                # 3. If still missing and auto-generation enabled, use pre-generated results.
                if auto_generate_keyfacts:
                    if not found_gt_keyfacts and i in doc_keyfacts_map and doc_keyfacts_map[i]['gt'] is not None:
                        ground_truth_keyfacts = doc_keyfacts_map[i]['gt']
                        found_gt_keyfacts = True
                    
                    if not found_gen_keyfacts and i in doc_keyfacts_map and doc_keyfacts_map[i]['gen'] is not None:
                        generated_keyfacts = doc_keyfacts_map[i]['gen']
                        found_gen_keyfacts = True
                
                # Collect keyfacts evaluation tasks (for concurrent execution).
                if include_keyfacts and (found_gt_keyfacts or found_gen_keyfacts):
                    keyfacts_evaluation_tasks.append((
                        i,
                        ground_truth_keyfacts,
                        generated_keyfacts,
                        ground_truth_keyfacts_path,
                        generated_keyfacts_path
                    ))

                # Collect informativeness evaluation tasks.
                if include_informativeness and original_text and popsci_text:
                    informativeness_evaluation_tasks.append((
                        i,
                        original_text,
                        popsci_text,
                        ground_truth_keyfacts if found_gt_keyfacts else None,
                        generated_keyfacts if found_gen_keyfacts else None
                    ))
            
            # Save document info for later non-LLM evaluations.
            doc_info_map[i] = {
                'item': item,
                'popsci_text': popsci_text,
                'original_text': original_text,
                'reference_text': reference_text,
                'ground_truth_keyfacts': ground_truth_keyfacts if (include_keyfacts or include_informativeness) and found_gt_keyfacts else None,
                'generated_keyfacts': generated_keyfacts if (include_keyfacts or include_informativeness) and found_gen_keyfacts else None,
                'found_gt_keyfacts': found_gt_keyfacts if (include_keyfacts or include_informativeness) else False,
                'found_gen_keyfacts': found_gen_keyfacts if (include_keyfacts or include_informativeness) else False
            }

        # Phase 2: Parallel keyfacts precision/recall evaluation (uses 100 concurrency).
        doc_keyfacts_eval_map = {}  # {doc_index: keyfacts_evaluation_result}
        doc_informativeness_eval_map = {} # {doc_index: informativeness_evaluation_result}

        if include_keyfacts and keyfacts_evaluation_tasks:
            logger.info(f"Starting batch keyfacts precision/recall evaluation for {len(keyfacts_evaluation_tasks)} tasks (concurrency: {self.concurrency}).")
            
            # Use a semaphore to limit concurrency (adjustable via --concurrency).
            # Keyfacts evaluation requires minimal concurrency, as it mainly handles JSON processing.
            # However, if keyfacts computation invokes an LLM (as implemented), concurrency should be limited.
            semaphore = asyncio.Semaphore(self.concurrency)
            
            async def evaluate_keyfacts_with_semaphore(doc_idx, gt, gen, gt_path, gen_path):
                try:
                    async with semaphore:
                        result = await self.evaluate_keyfacts(
                            gt, gen,
                            ground_truth_path=gt_path,
                            generated_keyfacts_path=gen_path
                        )
                        return (doc_idx, result)
                except Exception as e:
                    logger.warning(f"Keyfacts evaluation failed (doc {doc_idx}): {e}")
                    return (doc_idx, {
                        'precision': -1.0,
                        'recall': -1.0,
                        'precision_by_priority': {},
                        'recall_by_priority': {}
                    })
            
            # Create all evaluation tasks.
            tasks = [evaluate_keyfacts_with_semaphore(doc_idx, gt, gen, gt_path, gen_path) 
                    for doc_idx, gt, gen, gt_path, gen_path in keyfacts_evaluation_tasks]
            
            # Show progress using tqdm.
            from tqdm.asyncio import tqdm
            for i, result_or_task in enumerate(tqdm.as_completed(tasks, desc="Evaluating Keyfacts", total=len(tasks))):
                 doc_idx, result = await result_or_task
                 doc_keyfacts_eval_map[doc_idx] = result
                 
                 # Save progress periodically.
                 if i % 100 == 0:
                     save_progress(dataset)
            
            logger.info(f"Completed batch keyfacts precision/recall evaluation.")

        # Phase 2.5: Batch concurrent evaluation of Informativeness (QA)
        # Phase 2.5: Batch concurrent evaluation of Informativeness (QA)
        if include_informativeness and informativeness_evaluation_tasks:
            logger.info(f"Starting batch informativeness evaluation for {len(informativeness_evaluation_tasks)} tasks (concurrency: {self.concurrency}).")
            
            semaphore = asyncio.Semaphore(self.concurrency)

            async def evaluate_informativeness_with_semaphore(doc_idx, wiki, popsci, gt_kf, gen_kf):
                 try:
                    async with semaphore:
                        if self.informativeness_evaluator:
                            # Note: wiki_keyfacts and popsci_keyfacts arguments match what we expect
                            res = await self.informativeness_evaluator.evaluate_text_pair(
                                wiki, popsci, wiki_keyfacts=gt_kf, popsci_keyfacts=gen_kf
                            )
                            return (doc_idx, res)
                        return (doc_idx, {'score': 0.0, 'note': 'Evaluator not initialized'})
                 except Exception as e:
                    logger.warning(f"Informativeness evaluation failed (doc {doc_idx}): {e}")
                    return (doc_idx, {'score': 0.0, 'error': str(e)})

            tasks = [evaluate_informativeness_with_semaphore(idx, w, p, gtk, genk) 
                     for idx, w, p, gtk, genk in informativeness_evaluation_tasks]
            
            # Report progress with tqdm.
            from tqdm.asyncio import tqdm
            for i, result_or_task in enumerate(tqdm.as_completed(tasks, desc="Evaluating Informativeness", total=len(tasks))):
                doc_idx, eval_result = await result_or_task
                doc_informativeness_eval_map[doc_idx] = eval_result
                
                # Persist intermediate result
                dataset[doc_idx]['informativeness_evaluation'] = eval_result
                
                # Save progress
                if i % 100 == 0:
                    save_progress(dataset)
            
            logger.info(f"Completed batch informativeness evaluation.")
        
        # Phase 3: Evaluate coherence, simplicity, and vividness per document without LLM.
        # Parallel optimization: use multiprocessing to distribute tasks across GPUs.
        logger.info(f"\nStarting non-LLM evaluations (Multiprocessing on {self.cuda_devices or 'CPU'})...")
        
        # Prepare input data for workers
        doc_indices = sorted(doc_info_map.keys())
        chunks_data = []
        
        # Determine devices
        devices = []
        if self.cuda_devices:
            # e.g., "0,1,2" -> ["cuda:0", "cuda:1", "cuda:2"]
            device_ids = self.cuda_devices.split(',')
            devices = [f"cuda:{d.strip()}" for d in device_ids if d.strip()]
        else:
            devices = ['cpu']
            
        num_devices = len(devices)
        if num_devices == 0: devices = ['cpu']; num_devices = 1
        
        # Split docs into chunks
        chunk_size = (len(doc_indices) + num_devices - 1) // num_devices
        
        # Prepare Config for workers
        worker_config = {
             # We can't access self.vividness_evaluator.weights if it's not initialized in main process
             # But self.vividness_evaluator is None in main process if cuda_devices is set.
             # So we must pass the params we received in __init__
             # Wait, __init__ stored them? No, __init__ just passed them to VividnessEvaluator or ignored.
             # We need to store them in __init__ if we want to pass them to workers.
             # Let's fix __init__ to store config.
             'vividness_weights': getattr(self, 'vividness_weights', None),
             'melbert_path': getattr(self, 'melbert_path', None)
        }
        
        for i in range(num_devices):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(doc_indices))
            if start_idx >= len(doc_indices):
                break
                
            chunk_indices = doc_indices[start_idx:end_idx]
            chunk_docs_list = []
            for idx in chunk_indices:
                info = doc_info_map[idx]
                chunk_docs_list.append({
                    'id': idx,
                    'popsci_text': info['popsci_text']
                })
            
            chunks_data.append((chunk_docs_list, devices[i], worker_config))
            
        logger.info(f"Splitting {len(doc_indices)} docs into {len(chunks_data)} chunks across {devices}")
        
        # Run multiprocessing
        import torch.multiprocessing as mp
        # Note: CUDA requires 'spawn'
        if self.cuda_devices:
            try:
                mp.set_start_method('spawn', force=True)
            except RuntimeError:
                pass
                
        chunk_results = []
        if len(chunks_data) > 0:
            with mp.Pool(processes=len(chunks_data)) as pool:
                 chunk_results = pool.map(_process_chunk_worker, chunks_data)
        else:
            logger.warning("No data chunks to process in multiprocessing pool (doc_indices is empty or splitting failed).")
             
        # Merge results
        # chunk_results is list of lists of (id, res_dict)
        results_map = {}
        for chunk_res in chunk_results:
            for doc_id, res in chunk_res:
                results_map[doc_id] = res
        
        logger.info("Multiprocessing evaluation complete. Merging results...")

        results = []
        from tqdm import tqdm as tqdm_sync
        
        # Assembly loop
        for i in tqdm_sync(sorted(doc_info_map.keys()), desc="Non-LLM Evaluation (Assembly)"):
            doc_info = doc_info_map[i]
            item = doc_info['item']
            popsci_text = doc_info['popsci_text']
            original_text = doc_info['original_text']
            reference_text = doc_info['reference_text']
            
            precomputed = results_map.get(i, {})
            
            # 5. Evaluate document
            # Reconstruct logic manually since evaluate_single_document is not easily pickle-able or we want to use precomputed
            
            doc_result = {}
            
            # Simplicity (CPU bound, fast, do it here)
            if original_text:
                simplicity_score = self.evaluate_simplicity(original_text, popsci_text, reference_text)
                doc_result['simplicity'] = {
                    'fkgl_score': simplicity_score,
                    'interpretation': self._interpret_fkgl(simplicity_score)
                }
            else:
                 doc_result['simplicity'] = {'fkgl_score': -1.0}
                 
            # Coherence
            doc_result['coherence'] = {
                'ppl_score': precomputed.get('ppl_score', -1.0),
                'interpretation': self._interpret_ppl(precomputed.get('ppl_score', -1.0)),
                'llm_score': -1.0 # Skipped or handled elsewhere
            }
            if not self.skip_coherence_llm:
                # LLM check is async, we skipped it in multiprocessing.
                # If we really need it, we must run it here (but it's slow).
                # User likely skipped it via flags.
                doc_result['coherence']['llm_score'] = -1.0
                doc_result['coherence']['interpretation'] = 'LLM Judge skipped in MP mode'

            # Vividness
            doc_result['vividness'] = precomputed.get('vividness', {
                'vividness_score': -1.0, 'figurativeness': 0.0, 'emotionality': 0.0, 'decorativeness': 0.0
            })
            if doc_result['vividness'] is None:
                doc_result['vividness'] = {'vividness_score': -1.0}

            # Merge other fields
            doc_result['model_name'] = get_nested_field(item, 'model_name', 'unknown')
            
            # Inject keyfacts
            if include_keyfacts and i in doc_keyfacts_eval_map:
                doc_result['keyfacts'] = doc_keyfacts_eval_map[i]
                item['keyfacts_evaluation'] = doc_result['keyfacts']
            elif include_keyfacts:
                 doc_result['keyfacts'] = {'precision': -1.0, 'recall': -1.0}
            
            if include_informativeness and i in doc_informativeness_eval_map:
                doc_result['informativeness'] = doc_informativeness_eval_map[i]
                item['informativeness_evaluation'] = doc_result['informativeness']

            title = (get_nested_field(item, 'title', '') or 
                    get_nested_field(item, 'popsci_article.title', ''))
            doc_result['title'] = title
            doc_result['doc_id'] = get_nested_field(item, 'id', i)
            
            clean_result = _clean_output_record(item, doc_result)
            results.append(clean_result)

            
            # Merge results back into dataset item for persistence
            for k, v in doc_result.items():
                dataset[i][k] = v
            
            # Save progress periodically (e.g., every 5 items)
            if (i + 1) % 5 == 0 or i == total - 1:
                save_progress(dataset)
        
        # Compute statistics.
        statistics = self._calculate_statistics(results)
        
        # Save the results (including raw data, keyfacts, and all evaluation results).
        output_data = {
            'dataset_path': dataset_path,
            'total_documents': total,
            'evaluated_documents': len(results),
            'results': results,  # Each entry contains original_data, keyfacts, coherence, simplicity, vividness, etc.
            'statistics': statistics
        }
        
        # Ensure the output directory exists.
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        else:
            # If output_path is just a filename, use the default output directory.
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            output_dir = os.path.join(project_root, 'output')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, os.path.basename(output_path))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nEvaluation completed. Results saved to: {output_path}")
        
        return output_data
    
    def _calculate_statistics(self, results: List[Dict]) -> Dict:
        """Compute aggregated statistics."""
        if not results:
            return {}
        
        # Extract valid scores.
        # Coherence
        coherence_ppl_scores = [
            r['coherence_ppl_score'] for r in results
            if isinstance(r.get('coherence_ppl_score'), (int, float)) and r.get('coherence_ppl_score', -1) >= 0
        ]
        coherence_llm_scores = [
            r['coherence_llm_score'] for r in results
            if isinstance(r.get('coherence_llm_score'), (int, float)) and r.get('coherence_llm_score', -1) >= 0
        ]
        
        # Simplicity
        simplicity_scores = [
            r['simplicity_fkgl_score'] for r in results
            if isinstance(r.get('simplicity_fkgl_score'), (int, float)) and r.get('simplicity_fkgl_score', -1) >= 0
        ]
        
        # Vividness
        vividness_scores = [r['vividness_score'] for r in results if isinstance(r.get('vividness_score'), (int, float))]
        figurativeness_scores = [r['figurativeness'] for r in results if isinstance(r.get('figurativeness'), (int, float))]
        emotionality_scores = [r['emotionality'] for r in results if isinstance(r.get('emotionality'), (int, float))]
        decorativeness_scores = [r['decorativeness'] for r in results if isinstance(r.get('decorativeness'), (int, float))]
        
        # Informativeness
        informativeness_scores = []
        for r in results:
            s = r.get('informativeness_score', -1)
            if isinstance(s, (int, float)) and s >= 0:
                informativeness_scores.append(s)

        # Keyfacts
        keyfacts_precisions = []
        keyfacts_recalls = []
        keyfacts_precisions_priority_1 = []
        keyfacts_precisions_priority_2 = []
        keyfacts_precisions_priority_3 = []
        keyfacts_recalls_priority_1 = []
        keyfacts_recalls_priority_2 = []
        keyfacts_recalls_priority_3 = []
        
        for r in results:
            val = r.get('keyfacts_precision')
            if val is not None and val != -1 and val >= 0:
                keyfacts_precisions.append(val)

            val = r.get('keyfacts_recall')
            if val is not None and val != -1 and val >= 0:
                keyfacts_recalls.append(val)

            p_by_pri = r.get('keyfacts_precision_by_priority', {})
            if 'priority_1' in p_by_pri:
                val = p_by_pri['priority_1']
                if val is not None and val != -1 and val >= 0:
                    keyfacts_precisions_priority_1.append(val)
            if 'priority_2' in p_by_pri:
                val = p_by_pri['priority_2']
                if val is not None and val != -1 and val >= 0:
                    keyfacts_precisions_priority_2.append(val)
            if 'priority_3' in p_by_pri:
                val = p_by_pri['priority_3']
                if val is not None and val != -1 and val >= 0:
                    keyfacts_precisions_priority_3.append(val)

            r_by_pri = r.get('keyfacts_recall_by_priority', {})
            if 'priority_1' in r_by_pri:
                val = r_by_pri['priority_1']
                if val is not None and val != -1 and val >= 0:
                    keyfacts_recalls_priority_1.append(val)
            if 'priority_2' in r_by_pri:
                val = r_by_pri['priority_2']
                if val is not None and val != -1 and val >= 0:
                    keyfacts_recalls_priority_2.append(val)
            if 'priority_3' in r_by_pri:
                val = r_by_pri['priority_3']
                if val is not None and val != -1 and val >= 0:
                    keyfacts_recalls_priority_3.append(val)
        
        def calc_stats(scores):
            if not scores:
                return {}
            return {
                'mean': sum(scores) / len(scores),
                'min': min(scores),
                'max': max(scores),
                'count': len(scores)
            }
        
        statistics = {
            'coherence': {
                **calc_stats(coherence_ppl_scores),
                'metrics': {
                    'ppl': calc_stats(coherence_ppl_scores),
                    'llm_score': calc_stats(coherence_llm_scores)
                }
            },
            'simplicity': {
                **calc_stats(simplicity_scores),
                'metrics': {
                    'fkgl': calc_stats(simplicity_scores)
                }
            },
            'vividness': {
                **calc_stats(vividness_scores),
                'metrics': {
                    'overall': calc_stats(vividness_scores),
                    'figurativeness': calc_stats(figurativeness_scores),
                    'emotionality': calc_stats(emotionality_scores),
                    'decorativeness': calc_stats(decorativeness_scores)
                }
            },
            'informativeness': {
                **calc_stats(informativeness_scores),
                'metrics': {
                    'qa_score': calc_stats(informativeness_scores)
                }
            },
            # Backward compatibility fields
            'figurativeness': calc_stats(figurativeness_scores),
            'emotionality': calc_stats(emotionality_scores),
            'decorativeness': calc_stats(decorativeness_scores),
            
            'keyfacts_precision': {
                **calc_stats(keyfacts_precisions),
                'metrics': {
                    'overall': calc_stats(keyfacts_precisions),
                    'priority_1': calc_stats(keyfacts_precisions_priority_1),
                    'priority_2': calc_stats(keyfacts_precisions_priority_2),
                    'priority_3': calc_stats(keyfacts_precisions_priority_3)
                }
            },
            'keyfacts_recall': {
                **calc_stats(keyfacts_recalls),
                'metrics': {
                    'overall': calc_stats(keyfacts_recalls),
                    'priority_1': calc_stats(keyfacts_recalls_priority_1),
                    'priority_2': calc_stats(keyfacts_recalls_priority_2),
                    'priority_3': calc_stats(keyfacts_recalls_priority_3)
                }
            },
            'keyfacts_precision_by_priority': {
                'priority_1': calc_stats(keyfacts_precisions_priority_1),
                'priority_2': calc_stats(keyfacts_precisions_priority_2),
                'priority_3': calc_stats(keyfacts_precisions_priority_3),
            },
            'keyfacts_recall_by_priority': {
                'priority_1': calc_stats(keyfacts_recalls_priority_1),
                'priority_2': calc_stats(keyfacts_recalls_priority_2),
                'priority_3': calc_stats(keyfacts_recalls_priority_3),
            }
        }
        
        return statistics
    
    def _interpret_ppl(self, ppl_score: float) -> str:
        """Interpret perplexity scores."""
        if ppl_score < 0:
            return "Evaluation failed"
        elif ppl_score < 50:
            return "Very fluent"
        elif ppl_score < 100:
            return "Relatively fluent"
        elif ppl_score < 200:
            return "Moderately fluent"
        elif ppl_score < 500:
            return "Less fluent"
        else:
            return "Not fluent"
    
    def _interpret_fkgl(self, fkgl_score: float) -> str:
        """Interpret FKGL score (lower means simpler)."""
        if fkgl_score < 0:
            return "Evaluation failed"
        elif fkgl_score <= 8:
            return "Very simple (elementary level)"
        elif fkgl_score <= 12:
            return "Relatively simple (middle school level)"
        elif fkgl_score <= 16:
            return "Moderately simple (high school level)"
        else:
            return "Not simple (college level or above)"


# Convenience functions.
async def evaluate_single_document_async(
    popsci_text: str,
    original_text: Optional[str] = None,
    reference_text: Optional[str] = None,
    ground_truth_keyfacts: Optional[Union[str, List[Dict], Dict]] = None,
    generated_keyfacts: Optional[Union[str, List[Dict], Dict]] = None,
    args=None,
    vividness_weights=None,
    reader_age='adult'
) -> Dict:
    """
    Convenience wrapper for evaluating a single document.
    
    Args:
        popsci_text: Popsci article text to evaluate.
        original_text: Original complex text.
        reference_text: Reference text for comparison.
        ground_truth_keyfacts: Ground truth keyfacts.
        generated_keyfacts: Generated keyfacts.
        args: CLI arguments object.
        vividness_weights: Vividness weight configuration.
        reader_age: Simulated reader age group.
        
    Returns:
        dict: Evaluation results.
    """
    evaluator = ComprehensiveEvaluator(args=args, vividness_weights=vividness_weights, reader_age=reader_age)
    return await evaluator.evaluate_single_document(
        popsci_text,
        original_text,
        reference_text,
        ground_truth_keyfacts,
        generated_keyfacts
    )


async def evaluate_document_pair_async(
    popsci_text_1: str,
    popsci_text_2: str,
    original_text: Optional[str] = None,
    reference_text: Optional[str] = None,
    args=None,
    vividness_weights=None,
    reader_age='adult'
) -> Dict:
    """
    Convenience wrapper for evaluating a pair of documents.
    
    Args:
        popsci_text_1: First popsci article text.
        popsci_text_2: Second popsci article text.
        original_text: Original complex text.
        reference_text: Reference text.
        args: CLI arguments object.
        vividness_weights: Vividness weight configuration.
        reader_age: Simulated reader age group.
        
    Returns:
        dict: Evaluation results.
    """
    evaluator = ComprehensiveEvaluator(args=args, vividness_weights=vividness_weights, reader_age=reader_age)
    return await evaluator.evaluate_document_pair(
        popsci_text_1,
        popsci_text_2,
        original_text,
        reference_text
    )


async def evaluate_dataset_async(
    dataset_path: str,
    output_path: str,
    dataset_format: str = 'json',
    popsci_field: str = 'popsci_text',
    original_field: str = 'original_text',
    args=None,
    vividness_weights=None,
    reader_age='adult',
    **kwargs
) -> Dict:
    """
    Convenience wrapper for evaluating a dataset.
    
    Args:
        dataset_path: Path to the dataset file.
        output_path: Output file path.
        dataset_format: Dataset format.
        popsci_field: Popsci article field name.
        original_field: Original article field name.
        args: CLI arguments object.
        vividness_weights: Vividness weight configuration.
        reader_age: Simulated reader age group.
        **kwargs: Additional kwargs passed to evaluate_dataset.
        
    Returns:
        dict: Evaluation results.
    """
    evaluator = ComprehensiveEvaluator(args=args, vividness_weights=vividness_weights, reader_age=reader_age)
    return await evaluator.evaluate_dataset(
        dataset_path,
        output_path,
        dataset_format,
        popsci_field,
        original_field,
        **kwargs
    )


if __name__ == "__main__":
    # Example usage.
    import asyncio
    
    async def main():
        # Initialize the evaluator.
        args = parse_args()
        evaluator = ComprehensiveEvaluator(args=args)
        
        # Example: evaluate a single document.
        popsci_text = "This is a sample popular science article about science."
        original_text = "This is a complex scientific paper with technical jargon."
        
        result = await evaluator.evaluate_single_document(
            popsci_text,
            original_text=original_text
        )
        
        print("\nEvaluation results:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(main())
