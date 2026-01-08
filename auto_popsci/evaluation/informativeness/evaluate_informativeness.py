
import asyncio
import argparse
import json
import os
import sys
import yaml
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm as aio_tqdm

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Try importing utils and prompts
try:
    from auto_popsci.utils.utils import read_yaml_file, extract_keyfacts
    from prompts.prompt_template import prompt as prompt_templates
except ImportError as e:
    # If prompts not found, try adding auto_popsci to path or assuming structure
    try:
        sys.path.insert(0, os.path.join(project_root, "auto_popsci"))
        from auto_popsci.utils.utils import read_yaml_file, extract_keyfacts
        # prompt_template might be in root prompts/
        sys.path.insert(0, project_root)
        from prompts.prompt_template import prompt as prompt_templates
    except ImportError:
        print(f"Warning: Could not import utils or prompts: {e}")
        # We will handle missing prompts by defining fallbacks if needed
        pass

# Fallback Prompt templates if import fails or keys missing
KEYFACT_MATCHING_PROMPT = """
You are an expert in evaluating the factual accuracy of popular science articles compared to their source Wikipedia articles.

Your task is to identify which of the provided "Wikipedia Key Facts" are present in the "Generated PopSci Article Key Facts".

Wikipedia Key Facts:
{ground_truth_key_facts}

Generated PopSci Article Key Facts:
{generated_key_facts}

Output the list of Wikipedia Key Facts that are successfully covered/mentioned in the PopSci Article Key Facts. 
Output strictly in JSON format as a list of strings. Do not output anything else.
If no keyfacts match, output an empty list [].
"""

MCQ_GENERATION_PROMPT = """
You are an expert educational content creator.
Based on the following key facts, generate {num_questions} multiple-choice questions (MCQs) to test a reader's understanding of these facts.

Key Facts:
{keyfacts}

Each question should have:
- A clear question stem.
- 4 options (A, B, C, D).
- The correct answer (e.g., "A").

Output dictionary format in JSON:
[
  {{
    "question": "Question text...",
    "options": {{
      "A": "Option A...",
      "B": "Option B...",
      "C": "Option C...",
      "D": "Option D..."
    }},
    "answer": "A"
  }},
  ...
]
Do not include markdown formatting like ```json ... ```. Just the raw JSON string.
"""

READER_SIMULATION_PROMPT = """
You are a curious reader interested in science.
Read the following popular science article and answer the multiple-choice questions based ONLY on the information provided in the article.

Article:
{article}

Questions:
{questions}

For each question, provide your answer.
Output strictly in JSON format as a list of strings, corresponding to the order of questions. 
Example: ["A", "C", "B", "D", "A"]
If you cannot answer a question based on the article, output "Unknown".
"""

class DummyArgs:
    def __init__(self, llm_type, model_type, prompt_template):
        self.llm_type = llm_type
        self.model_type = model_type
        self.prompt_template = prompt_template

class InformativenessEvaluator:
    def __init__(self, args=None):
        if args is None:
            # Default args for library usage
            self.args = DummyArgs("openai", "grok-4-1-fast-reasoning", "key_fact_extraction")
        else:
            self.args = args
        self.auth_info = read_yaml_file("auth.yaml")
        # Hardcoded model requirement
        self.model = "grok-4-1-fast-reasoning" 
        self.llm_type, self.client = self._init_client_and_type()

    def _init_client_and_type(self):
        api_key = None
        base_url = None
        found_llm_type = self.args.llm_type # Start with default

        # 1. Check if model is explicitly under a provider in auth.yaml
        for provider, models in self.auth_info.items():
            if isinstance(models, dict):
                if self.model in models:
                    found_llm_type = provider
                    api_key = models[self.model].get("api_key")
                    base_url = models[self.model].get("base_url")
                    break
        
        # 2. If not found, check if 'grok' or 'xai' exists as top level
        if not api_key:
            for provider in ['grok', 'xai', 'openai']:
                if provider in self.auth_info:
                    # Check if it has api_key directly or under 'default' or similar if checking for provider broadly
                    # But we need specific model config if possible.
                    # Assuming standard structure: provider -> model -> config
                    pass

        # 3. Fallback: use args provided constraints to look up
        if not api_key:
             # Try using the args.llm_type if it claims to have the model (which might not be true if we hardcoded model name)
             # We rely on step 1 mostly.
             pass
             
        if not api_key:
             # Last ditch: Look for any api_key in 'grok' section if exists
             if 'grok' in self.auth_info:
                 found_llm_type = 'grok'
                 # It might be in 'grok' -> 'grok-4-1-fast-reasoning' OR just 'grok' -> 'api_key' ?
                 # Based on utils.py: auth_info[args.llm_type][args.model_type]["api_key"]
                 # So it must be nested.
                 if self.model in self.auth_info['grok']:
                     api_key = self.auth_info['grok'][self.model].get("api_key")
                     base_url = self.auth_info['grok'][self.model].get("base_url")

        if not api_key:
            print(f"Warning: API key for {self.model} not found in auth.yaml. Checking env vars...")
            api_key = os.getenv("OPENAI_API_KEY") # Fallback to env
            if not api_key:
                raise ValueError(f"Could not find API key for {self.model}")

        print(f"Initialized client with model {self.model} (provider: {found_llm_type})")
        return found_llm_type, AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def get_llm_response(self, prompt_text, json_mode=True):
        try:
            messages = [{"role": "user", "content": prompt_text}]
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0 if json_mode else 0.7 
            )
            content = response.choices[0].message.content.strip()
            # Clean markdown code blocks
            if content.startswith("```"):
                lines = content.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines)
            return content
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return None

    async def extract_keyfacts_wrapper(self, text, title):
        # Use utils.extract_keyfacts
        # It needs 'args' with llm_type, model_type, prompt_template
        # We need to know the prompt template key for extraction.
        # Assuming "keyfact_extraction" based on common sense or existing files.
        # If imports failed, we implement our own extraction.
        
        template_name = "key_fact_extraction" # Correct key from prompts/prompt_template.py
        
        # Create dummy args
        d_args = DummyArgs(self.llm_type, self.model, template_name)
        
        try:
            return await extract_keyfacts(d_args, text, title)
        except Exception as e:
            print(f"Error in extract_keyfacts: {e}. Fallback to direct call.")
            # Fallback
            # We need a prompt for extraction if utils failed.
            # Ideally utils should work.
            return "[]"

    async def match_keyfacts(self, wiki_keyfacts, popsci_keyfacts, wiki_is_ground_truth=True):
        # wiki_keyfacts and popsci_keyfacts can be strings or lists.
        # Normalize to json string for prompt
        
        def normalize(kf):
            if isinstance(kf, str):
                return kf
            return json.dumps(kf, indent=2)

        w_text = normalize(wiki_keyfacts)
        p_text = normalize(popsci_keyfacts)
        
        # Use existing prompt template if available
        # prompt_templates['keyfact_alignment']
        prompt_text = ""
        if 'keyfact_alignment' in prompt_templates:
            prompt_text = prompt_templates['keyfact_alignment'].format(
                ground_truth_key_facts=w_text, 
                generated_key_facts=p_text
            )
        else:
            prompt_text = KEYFACT_MATCHING_PROMPT.format(
                ground_truth_key_facts=w_text, 
                generated_key_facts=p_text
            )

        response = await self.get_llm_response(prompt_text)
        try:
            matched = json.loads(response)
            if isinstance(matched, list):
                return matched
            return []
        except:
            return []

    async def generate_mcqs(self, keyfacts, num_questions=5):
        if not keyfacts or len(keyfacts) == 0:
            return []
        
        kf_text = json.dumps(keyfacts, indent=2) if isinstance(keyfacts, list) else str(keyfacts)
        prompt = MCQ_GENERATION_PROMPT.format(num_questions=num_questions, keyfacts=kf_text)
        
        response = await self.get_llm_response(prompt)
        
        try:
            questions = json.loads(response)
            return questions
        except:
            print(f"Failed to parse MCQs response: {response[:100]}...")
            return []

    async def simulate_reader(self, article_text, questions):
        if not questions:
            return []
        
        # Format questions for reader
        q_formatted = json.dumps(questions, indent=2)
        
        prompt = READER_SIMULATION_PROMPT.format(article=article_text, questions=q_formatted)
        response = await self.get_llm_response(prompt)
        
        try:
            answers = json.loads(response)
            return answers
        except:
            print(f"Failed to parse Answers response: {response[:100]}...")
            return []

    async def evaluate_text_pair(self, wiki_text, popsci_text, wiki_keyfacts=None, popsci_keyfacts=None):
        """
        Evaluate informativeness for a pair of texts (Wiki and PopSci).
        Returns a dictionary with score and details.
        """
        if not wiki_text or not popsci_text:
            return None

        # 3. Get or Extract Wiki Keyfacts
        if not wiki_keyfacts:
            # print("Extracting Wiki Keyfacts...")
            kf_str = await self.extract_keyfacts_wrapper(wiki_text, "Wiki Article")
            try:
                wiki_keyfacts = json.loads(kf_str)
            except:
                wiki_keyfacts = []
        
        # 4. Get or Extract PopSci Keyfacts
        if not popsci_keyfacts:
            # print("Extracting PopSci Keyfacts...")
            kf_str = await self.extract_keyfacts_wrapper(popsci_text, "PopSci Article")
            try:
                popsci_keyfacts = json.loads(kf_str)
            except:
                popsci_keyfacts = []

        # 5. Match Keyfacts (Wiki facts supported by PopSci)
        matched_keyfacts = await self.match_keyfacts(wiki_keyfacts, popsci_keyfacts)
        
        if not matched_keyfacts:
            matched_keyfacts = []

        # 6. Generate MCQs based on MATCHED keyfacts
        # Max 5
        mcqs = await self.generate_mcqs(matched_keyfacts[:20], num_questions=5) # Limit context
        
        # 7. Simulate Reader
        reader_answers = await self.simulate_reader(popsci_text, mcqs)
        
        # 8. Score
        score = 0.0
        correct_count = 0
        total_questions = len(mcqs)
        
        if total_questions > 0 and len(reader_answers) == total_questions:
            for i, q in enumerate(mcqs):
                correct_ans = q.get("answer", "").strip().upper()
                reader_ans = reader_answers[i].strip().upper()
                if reader_ans == correct_ans:
                    correct_count += 1
            score = correct_count / total_questions

        return {
            "wiki_keyfacts": wiki_keyfacts,
            "popsci_keyfacts": popsci_keyfacts,
            "matched_keyfacts": matched_keyfacts,
            "mcqs": mcqs,
            "reader_answers": reader_answers,
            "score": score,
            "correct_count": correct_count,
            "total_questions": total_questions
        }

    async def process_item(self, item, model_name):
        try:
            # 1. Get Wiki Content
            wiki_data = None
            if "original_data" in item:
                orig = item["original_data"]
                if "original_data" in orig:
                    if "wikipedia_articles" in orig["original_data"]:
                        wiki_data = orig["original_data"]["wikipedia_articles"]
                    elif "wikipedia_article" in orig["original_data"]:
                        wiki_data = orig["original_data"]["wikipedia_article"]
                
                if not wiki_data and "wikipedia_articles" in orig:
                    wiki_data = orig["wikipedia_articles"]
            
            wiki_text = ""
            if isinstance(wiki_data, str):
                wiki_text = wiki_data
            elif isinstance(wiki_data, dict):
                wiki_text = wiki_data.get("content", "") or str(wiki_data)
            
            if not wiki_text:
                print("No wiki text found, skipping item.")
                return None

            # 2. Get PopSci Content
            popsci_entry = item.get(model_name, {})
            popsci_text = popsci_entry.get("content") or popsci_entry.get("text", "")
            
            if not popsci_text:
                print("No popsci text found, skipping item.")
                return None

            # 3. Get existing keyfacts if available
            wiki_keyfacts = None
            if "keyfacts" in item:
                 wiki_keyfacts = item["keyfacts"]
            elif "original_data" in item and "keyfacts" in item["original_data"]:
                 wiki_keyfacts = item["original_data"]["keyfacts"]
            
            popsci_keyfacts = None
            if popsci_entry.get("keyfacts"):
                popsci_keyfacts = popsci_entry.get("keyfacts")

            return await self.evaluate_text_pair(wiki_text, popsci_text, wiki_keyfacts, popsci_keyfacts)

        except Exception as e:
            print(f"Error processing item: {e}")
            import traceback
            traceback.print_exc()
            return None

async def main():
    parser = argparse.ArgumentParser(description="Evaluate Informativeness")
    parser.add_argument("--input_file", type=str, required=True)
    parser.add_argument("--output_file", type=str, required=True)
    parser.add_argument("--sample", type=int, default=None)
    
    # These args are maintained for compatibility with utils but ignored for model choice as we enforce grok
    parser.add_argument("--llm_type", type=str, default="openai")
    parser.add_argument("--prompt_template", type=str, default="key_fact_extraction", help="Prompt template name")
    parser.add_argument("--model_type", type=str, default="grok-4-1-fast-reasoning")
    
    args = parser.parse_args()
    
    print(f"Loading data from {args.input_file}...")
    with open(args.input_file, 'r') as f:
        data = json.load(f)
        if isinstance(data, dict): 
            data_list = [data]
        else:
            data_list = data
    
    if args.sample:
        data_list = data_list[:args.sample]
        print(f"Sampling {args.sample} items.")

    evaluator = InformativenessEvaluator(args)
    
    # Detect Model Structure
    # 1. Check if items have "models" key (nested structure)
    # 2. Else check for specific model keys
    
    sample_item = data_list[0]
    has_models_key = "models" in sample_item and isinstance(sample_item["models"], dict)
    
    target_models = []
    if has_models_key:
        print("Detected 'models' key. Evaluating all models found within it.")
        # Collect all unique model names across a few samples to be safe, or just use first
        target_models = list(sample_item["models"].keys())
    else:
        # Heuristic: First key that is not 'original_data' etc
        ignore_keys = {'original_data', 'source_wikipedia', 'analysis', 'keyfacts', 'source'}
        for k in sample_item.keys():
            if k not in ignore_keys:
                target_models.append(k)
        print(f"Detected top-level model keys: {target_models}")

    if not target_models:
        print("Could not detect any target models in data. Exiting.")
        return

    print(f"Target models to evaluate: {target_models}")

    results = []
    
    # Process concurrently with semaphore
    sem = asyncio.Semaphore(5) # Limit concurrency
    
    async def task_wrapper(item, model_name):
        async with sem:
            # Prepare item structure for process_item
            # process_item expects item to have [model_name] or we pass the sub-dict?
            # process_item signature: process_item(item, model_name)
            # It does: popsci_entry = item.get(model_name, {})
            
            # If we have 'models' key, we need to adapt.
            # Let's flatten or adjust process_item.
            # Easier to adjust process_item or wrap the item.
            
            item_to_process = item
            if has_models_key:
                # Create a temporary item view where model_name is top level
                # Be careful not to mutate original too much if shared (though we are reading)
                # Shallow copy
                item_to_process = item.copy()
                if model_name in item["models"]:
                    item_to_process[model_name] = item["models"][model_name]
                else:
                    return None # This model not in this item
            
            res = await evaluator.process_item(item_to_process, model_name)
            if res:
                res["model_name"] = model_name
                return res
            return None

    tasks = []
    for item in data_list:
        for model_name in target_models:
            tasks.append(task_wrapper(item, model_name))
    
    scores = {} # model_name -> list of scores
    processed_results = []
    
    for f in aio_tqdm.as_completed(tasks, total=len(tasks)):
        res = await f
        if res:
            processed_results.append(res)
            m = res["model_name"]
            if m not in scores: scores[m] = []
            scores[m].append(res["score"])
    
    # Calculate Average Scores
    print("\nEvaluation Results:")
    final_stats = {}
    for m, s_list in scores.items():
        avg = sum(s_list) / len(s_list) if s_list else 0
        final_stats[m] = {
            "average_score": avg,
            "count": len(s_list)
        }
        print(f"Model: {m} | Average Score: {avg:.4f} | Count: {len(s_list)}")
    
    final_output = {
        "statistics": final_stats,
        "results": processed_results
    }
    
    with open(args.output_file, 'w') as f:
        json.dump(final_output, f, indent=4, ensure_ascii=False)
    
    print(f"Results saved to {args.output_file}")

if __name__ == "__main__":
    asyncio.run(main())
