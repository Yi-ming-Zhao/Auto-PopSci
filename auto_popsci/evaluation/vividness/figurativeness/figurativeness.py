"""
Figurativeness Evaluator using MelBERT
用于评估文本比喻丰富度的模块

Usage:
    evaluator = FigurativenessEvaluator()
    score = evaluator.evaluate_text("Your text here")
    scores = evaluator.evaluate_texts(["text1", "text2", ...])
"""

import os
import sys
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoConfig, AutoModel

# Add MelBERT directory to path
melbert_dir = os.path.join(os.path.dirname(__file__), "MelBERT")
sys.path.insert(0, melbert_dir)

# Import MelBERT model definition
try:
    from modeling import AutoModelForSequenceClassification_SPV_MIP
except ImportError:
    # Fallback definition if import fails
    class AutoModelForSequenceClassification_SPV_MIP(nn.Module):
        def __init__(self, args, Model, config, num_labels=2):
            super(AutoModelForSequenceClassification_SPV_MIP, self).__init__()
            self.num_labels = num_labels
            self.encoder = Model
            self.config = config
            self.dropout = nn.Dropout(args.drop_ratio)
            self.args = args

            self.SPV_linear = nn.Linear(config.hidden_size * 2, args.classifier_hidden)
            self.MIP_linear = nn.Linear(config.hidden_size * 2, args.classifier_hidden)
            self.classifier = nn.Linear(args.classifier_hidden * 2, num_labels)
            
            self.logsoftmax = nn.LogSoftmax(dim=1)

        def forward(self, input_ids, input_ids_2, target_mask, target_mask_2, attention_mask_2,
                    token_type_ids=None, attention_mask=None, labels=None, head_mask=None):
            
            # First encoder for full sentence
            outputs = self.encoder(
                input_ids,
                token_type_ids=token_type_ids,
                attention_mask=attention_mask,
                head_mask=head_mask,
            )
            sequence_output = outputs[0]  # [batch, max_len, hidden]
            pooled_output = outputs[1]  # [batch, hidden]

            # Get target ouput with target mask
            target_output = sequence_output * target_mask.unsqueeze(2)
            target_output = self.dropout(target_output)
            target_output = target_output.sum(1) / (target_mask.sum(1, keepdim=True) + 1e-9)

            # Second encoder for only the target word
            outputs_2 = self.encoder(input_ids_2, attention_mask=attention_mask_2, head_mask=head_mask)
            sequence_output_2 = outputs_2[0]

            # Get target ouput with target mask
            target_output_2 = sequence_output_2 * target_mask_2.unsqueeze(2)
            target_output_2 = self.dropout(target_output_2)
            target_output_2 = target_output_2.sum(1) / (target_mask_2.sum(1, keepdim=True) + 1e-9)

            # Get hidden vectors
            SPV_hidden = self.SPV_linear(torch.cat([pooled_output, target_output], dim=1))
            MIP_hidden = self.MIP_linear(torch.cat([target_output_2, target_output], dim=1))

            logits = self.classifier(self.dropout(torch.cat([SPV_hidden, MIP_hidden], dim=1)))
            logits = self.logsoftmax(logits)

            if labels is not None:
                loss_fct = nn.NLLLoss()
                loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))
                return loss
            return logits


class FigurativenessEvaluator:
    """使用MelBERT模型评估文本比喻丰富度"""

    def __init__(self, model_path=None):
        """
        初始化比喻性评估器
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Path setup
        if model_path is None:
            model_path = os.path.join(melbert_dir, "melbert_ckpt")
        
        self.model_path = model_path
        self.max_seq_length = 128  # Default from MelBERT config usually around 128-150
        
        # Load components
        try:
            self._load_model()
            self.initialized = True
        except Exception as e:
            print(f"Error initializing FigurativenessEvaluator: {e}")
            self.initialized = False

    def _load_model(self):
        """加载模型和分词器"""
        print(f"Loading MelBERT from {self.model_path}...")
        
        # MelBERT specific args
        class MelBERTArgs:
            def __init__(self):
                self.drop_ratio = 0.1
                self.classifier_hidden = 768 # Matches the checkpoint size
                self.bert_model = "roberta-base"
                self.model_type = "MELBERT"
        
        args = MelBERTArgs()
        
        # 1. Tokenizer - use local checkpoint files if available
        tokenizer_files = [f for f in os.listdir(self.model_path) if f in ["vocab.json", "merges.txt"]]
        if len(tokenizer_files) >= 2:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        else:
            self.tokenizer = AutoTokenizer.from_pretrained("roberta-base")
            
        # 2. Load base RoBERTa model with ORIGINAL config first (to avoid weight loading mismatch)
        # roberta-base has type_vocab_size=1 by default
        bert_model = AutoModel.from_pretrained("roberta-base")
        config = bert_model.config
        
        # 3. Now modify config and token_type_embeddings for MelBERT (which uses 4 token types)
        config.type_vocab_size = 4
        bert_model.embeddings.token_type_embeddings = nn.Embedding(
            config.type_vocab_size, config.hidden_size
        )
        # Initialize new embeddings
        bert_model._init_weights(bert_model.embeddings.token_type_embeddings)
        
        # 4. Initialize MelBERT wrapper
        self.model = AutoModelForSequenceClassification_SPV_MIP(
            args=args,
            Model=bert_model,
            config=config,
            num_labels=2
        )
        
        # 5. Load MelBERT pretrained weights
        weights_path = os.path.join(self.model_path, "pytorch_model.bin")
        if os.path.exists(weights_path):
            state_dict = torch.load(weights_path, map_location=self.device)
            model_state = self.model.state_dict()
            
            # Filter out any keys with shape mismatch (just in case)
            keys_to_del = []
            for k, v in list(state_dict.items()):
                if k in model_state:
                    if v.shape != model_state[k].shape:
                        print(f"Skipping key {k}: checkpoint {v.shape} vs model {model_state[k].shape}")
                        keys_to_del.append(k)
            
            for k in keys_to_del:
                del state_dict[k]
                
            self.model.load_state_dict(state_dict, strict=False)
            print("Loaded MelBERT weights successfully.")
        else:
            raise FileNotFoundError(f"Model weights not found at {weights_path}")
            
        self.model.to(self.device)
        self.model.eval()

    def _create_features(self, text, target_index):
        """
        为MelBERT创建输入特征
        
        Args:
            text (str): 输入句子
            target_index (int): 目标词在单词列表中的索引
            
        Returns:
            dict: 模型输入张量
        """
        words = text.split()
        if target_index >= len(words):
            return None
            
        # Tokenize sentence
        tokens_a = self.tokenizer.tokenize(text)
        
        # Find token span for target word
        # We need to align word index to token index
        token_index = 0
        target_token_start = -1
        target_token_end = -1
        
        current_word_idx = 0
        for i, token in enumerate(tokens_a):
            # Simple alignment heuristic: RoBERTa tokens start with Ġ for new words
            if token.startswith('Ġ') or i == 0:
                if i > 0: current_word_idx += 1
            
            if current_word_idx == target_index:
                if target_token_start == -1:
                    target_token_start = i
                target_token_end = i
            elif current_word_idx > target_index:
                break
                
        if target_token_start == -1:
            # Fallback: try to find by word matching if alignment failed
            target_word = words[target_index]
            target_tokens = self.tokenizer.tokenize(" " + target_word) # add space for RoBERTa
            # This is simplified and might not work for all edge cases
            return None

        # Truncate if needed
        if len(tokens_a) > self.max_seq_length - 2:
            tokens_a = tokens_a[:self.max_seq_length - 2]
            if target_token_end >= len(tokens_a):
                return None

        # Construct Input 1: Sentence
        tokens = [self.tokenizer.cls_token] + tokens_a + [self.tokenizer.sep_token]
        input_ids = self.tokenizer.convert_tokens_to_ids(tokens)
        segment_ids = [0] * len(input_ids)
        input_mask = [1] * len(input_ids)
        
        # Mark target tokens in segment_ids (offset by 1 for CLS)
        for i in range(target_token_start, target_token_end + 1):
            if i + 1 < len(segment_ids):
                segment_ids[i + 1] = 1
                
        # Padding
        padding_len = self.max_seq_length - len(input_ids)
        input_ids += [self.tokenizer.pad_token_id] * padding_len
        input_mask += [0] * padding_len
        segment_ids += [0] * padding_len
        
        # Construct Input 2: Target Word isolated
        # Get target tokens from the sentence tokens
        target_tokens_seq = tokens_a[target_token_start : target_token_end + 1]
        tokens_2 = [self.tokenizer.cls_token] + target_tokens_seq + [self.tokenizer.sep_token]
        input_ids_2 = self.tokenizer.convert_tokens_to_ids(tokens_2)
        segment_ids_2 = [0] * len(input_ids_2)
        input_mask_2 = [1] * len(input_ids_2)
        
        # Mark target tokens in segment_ids_2
        for i in range(1, len(tokens_2) - 1):
            segment_ids_2[i] = 1
            
        # Padding 2
        padding_len_2 = self.max_seq_length - len(input_ids_2)
        input_ids_2 += [self.tokenizer.pad_token_id] * padding_len_2
        input_mask_2 += [0] * padding_len_2
        segment_ids_2 += [0] * padding_len_2
        
        return {
            "input_ids": torch.tensor([input_ids], dtype=torch.long).to(self.device),
            "input_ids_2": torch.tensor([input_ids_2], dtype=torch.long).to(self.device),
            "target_mask": torch.tensor([segment_ids], dtype=torch.long).to(self.device), # Using segment_ids as mask logic
            "target_mask_2": torch.tensor([segment_ids_2], dtype=torch.long).to(self.device),
            "attention_mask": torch.tensor([input_mask], dtype=torch.long).to(self.device),
            "attention_mask_2": torch.tensor([input_mask_2], dtype=torch.long).to(self.device),
            "token_type_ids": torch.tensor([segment_ids], dtype=torch.long).to(self.device)
        }

    def evaluate_text(self, text):
        """
        评估文本
        """
        if not self.initialized or not text.strip():
            return 0.0
            
        words = text.split()
        scores = []
        
        # Evaluate each word
        for i, word in enumerate(words):
            # Skip very short words or non-alphabetic to speed up
            if len(word) < 2 or not word.isalpha():
                continue
                
            features = self._create_features(text, i)
            if features is None:
                continue
                
            try:
                with torch.no_grad():
                    logits = self.model(**features)
                    probs = torch.exp(logits) # LogSoftmax -> Prob
                    metaphor_prob = probs[0][1].item() # Class 1 is metaphor
                    scores.append(metaphor_prob)
            except Exception:
                continue
                
        if not scores:
            return 0.0
            
        # Aggregate scores - use average or max?
        # For vividness, maybe the presence of strong metaphors matters more than density?
        # Let's use a combination: max score * 0.5 + average score * 0.5
        # Or simply average of top 3? 
        # For now, simple average of identified metaphors (prob > 0.5) or just average prob
        return np.mean(scores)

    def evaluate_texts(self, texts):
        """批量评估"""
        return [self.evaluate_text(t) for t in texts]

    def get_score_interpretation(self, score):
        if score >= 0.4: return "High"
        elif score >= 0.2: return "Medium"
        else: return "Low"

def main():
    evaluator = FigurativenessEvaluator()
    text = "The sun is a golden coin in the sky."
    print(f"Text: {text}")
    print(f"Score: {evaluator.evaluate_text(text)}")

if __name__ == "__main__":
    main()
