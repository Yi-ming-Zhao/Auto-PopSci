#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合评估科普文章的接口
包括以下评估指标：
- coherence: 连贯性（使用困惑度 PPL，值越低越好）
- simplicity: 简洁性（使用 FKGL，值越低表示越简单易读）
- vividness: 生动性（使用 VividnessEvaluator）
- keyfacts precision: 关键事实精确率
- keyfacts recall: 关键事实召回率
"""

import json
import os
import sys
import asyncio
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path

# 添加 easse 库路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
easse_path = os.path.join(project_root, 'easse')
if easse_path not in sys.path:
    sys.path.insert(0, easse_path)

from .coherence.cal_ppl import simple_cal_ppl
from .keyfacts_checking import async_single_paper_keyfacts_precision_calculation
from ..utils.utils import read_yaml_file, extract_keyfacts
from ..args import parse_args
from prompts.prompt_template import prompt
from openai import AsyncOpenAI
import json

# 延迟导入 VividnessEvaluator，避免在模块导入时下载 NLTK 数据
# 如果导入失败（例如网络问题导致无法下载 NLTK 数据），将跳过生动性评估
try:
    from .vividness import VividnessEvaluator
    VIVIDNESS_AVAILABLE = True
except (ImportError, Exception) as e:
    VIVIDNESS_AVAILABLE = False
    VividnessEvaluator = None
    # 只在导入时静默处理，不打印错误信息，避免干扰正常使用
    # 错误信息会在初始化时显示

# 导入 FKGL 函数
try:
    from easse.fkgl import corpus_fkgl
    EASSE_FKGL_AVAILABLE = True
except ImportError:
    EASSE_FKGL_AVAILABLE = False
    # 如果 EASSE 不可用，使用简单实现
    try:
        from .simplicity.cal_fkgl import simple_fkgl, count_syllables
    except ImportError:
        # 如果导入失败，定义简单的实现
        def count_syllables(word):
            """简单的音节计数"""
            word = word.lower()
            vowels = "aeiouy"
            syllable_count = 0
            prev_char_was_vowel = False
            for char in word:
                if char in vowels:
                    if not prev_char_was_vowel:
                        syllable_count += 1
                    prev_char_was_vowel = True
                else:
                    prev_char_was_vowel = False
            if word.endswith('e') and syllable_count > 1:
                syllable_count -= 1
            return max(1, syllable_count)
        
        def simple_fkgl(sentences):
            """简单的FKGL计算实现"""
            if not sentences:
                return 0.0
            total_words = 0
            total_syllables = 0
            total_sentences = len(sentences)
            for sentence in sentences:
                words = sentence.split()
                total_words += len(words)
                for word in words:
                    total_syllables += count_syllables(word)
            if total_sentences == 0 or total_words == 0:
                return 0.0
            fkgl = 0.39 * (total_words / total_sentences) + 11.8 * (total_syllables / total_words) - 15.59
            return max(0, fkgl)


class ComprehensiveEvaluator:
    """综合评估器，整合所有评估指标"""
    
    def __init__(self, args=None, vividness_weights=None, melbert_path=None, skip_coherence=False):
        """
        初始化综合评估器
        
        Args:
            args: 命令行参数对象（用于 keyfacts 评估）
            vividness_weights: 生动性评估的权重配置
            melbert_path: MelBERT 模型路径
            skip_coherence: 是否跳过连贯性评估（避免 GPT-2 模型下载问题）
        """
        self.args = args
        self.vividness_evaluator = None
        self.skip_coherence = skip_coherence
        
        # 初始化生动性评估器
        if not VIVIDNESS_AVAILABLE or VividnessEvaluator is None:
            print("⚠️ VividnessEvaluator 不可用（可能是导入失败，例如网络问题导致无法下载 NLTK 数据）")
            print("   将跳过生动性评估功能")
            self.vividness_evaluator = None
        else:
            try:
                self.vividness_evaluator = VividnessEvaluator(
                    weights=vividness_weights,
                    melbert_path=melbert_path
                )
                print("✅ VividnessEvaluator 初始化成功")
            except Exception as e:
                print(f"⚠️ VividnessEvaluator 初始化失败: {e}")
                print("   将跳过生动性评估")
                import traceback
                traceback.print_exc()
                self.vividness_evaluator = None
    
    def evaluate_coherence(self, text: str) -> float:
        """
        评估文本的连贯性（困惑度）
        
        Args:
            text: 待评估的文本
            
        Returns:
            float: 困惑度分数（值越低越好）
        """
        try:
            ppl = simple_cal_ppl(text)
            return ppl
        except Exception as e:
            print(f"⚠️ 连贯性评估失败: {e}")
            return -1.0
    
    def evaluate_simplicity(self, original_text: str, simplified_text: str, reference_text: Optional[str] = None) -> float:
        """
        评估文本的简洁性（使用 FKGL，值越低表示越简单易读）
        
        Args:
            original_text: 原始复杂文本
            simplified_text: 简化后的文本（待评估的科普文章）
            reference_text: 参考文本（可选，未使用）
            
        Returns:
            float: FKGL 分数（值越低表示越简单易读）
        """
        try:
            import re
            
            # 将文本分割成句子
            def split_sentences(text):
                # 简单的句子分割：按句号、问号、感叹号分割
                sentences = re.split(r'[.!?]+', text)
                sentences = [s.strip() for s in sentences if s.strip()]
                return sentences
            
            simplified_sentences = split_sentences(simplified_text)
            
            if not simplified_sentences:
                return -1.0
            
            # 计算 FKGL
            if EASSE_FKGL_AVAILABLE:
                fkgl_score = corpus_fkgl(
                    sentences=simplified_sentences,
                    tokenizer='13a'
                )
            else:
                # 使用简单实现
                fkgl_score = simple_fkgl(simplified_sentences)
            
            return fkgl_score
        except Exception as e:
            print(f"⚠️ 简洁性评估失败: {e}")
            import traceback
            traceback.print_exc()
            return -1.0
    
    def evaluate_vividness(self, text: str, return_components: bool = False) -> Union[float, Dict]:
        """
        评估文本的生动性
        
        Args:
            text: 待评估的文本
            return_components: 是否返回各子模块分数
            
        Returns:
            float or dict: 生动性分数，或包含各子模块分数的字典
        """
        if self.vividness_evaluator is None:
            return 0.0 if not return_components else {
                'vividness_score': 0.0,
                'figurativeness': 0.0,
                'emotionality': 0.0,
                'decorativeness': 0.0
            }
        
        try:
            return self.vividness_evaluator.evaluate_text(text, return_components=return_components)
        except Exception as e:
            print(f"⚠️ 生动性评估失败: {e}")
            return 0.0 if not return_components else {
                'vividness_score': 0.0,
                'figurativeness': 0.0,
                'emotionality': 0.0,
                'decorativeness': 0.0
            }
    
    async def generate_keyfacts(
        self,
        text: str,
        text_type: str = "wikipedia",
        llm_type: str = None,
        model_type: str = None
    ) -> Union[str, List[Dict]]:
        """
        生成关键事实
        
        Args:
            text: 待提取关键事实的文本
            text_type: 文本类型，"wikipedia" 和 "popsci" 都使用 grok
            llm_type: LLM 类型（可选，如果不提供则根据 text_type 自动选择）
            model_type: 模型类型（可选）
            
        Returns:
            str: JSON 格式的关键事实字符串，或解析后的字典列表
        """
        if self.args is None:
            print("⚠️ 缺少 args 参数，无法生成关键事实")
            return "[]"
        
        try:
            # 读取认证信息
            auth_info = read_yaml_file("auth.yaml")
            
            # 根据 text_type 选择模型和配置
            # 现在 Wikipedia 和科普 keyfacts 都使用 grok
            if text_type == "wikipedia" or text_type == "popsci":
                # Wikipedia 和科普 keyfacts 都使用 grok
                grok_config = auth_info.get("grok", {})
                api_key = grok_config.get("api_key", "")
                base_url = grok_config.get("base_url", "")
                model = grok_config.get("model", "grok-4-1-fast-reasoning")
            else:
                # 默认使用 args 中的配置
                target_llm_type = llm_type or self.args.llm_type
                target_model_type = model_type or self.args.model_type
                api_key = auth_info[target_llm_type][target_model_type]["api_key"]
                base_url = auth_info[target_llm_type][target_model_type]["base_url"]
                model = auth_info[target_llm_type][target_model_type]["model"]
            
            # 创建客户端
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            
            # 使用带优先级的 prompt template
            prompt_template_name = "key_fact_extraction_with_priority"
            prompt_text = prompt[prompt_template_name].format(paper=text)
            
            # 调用 API
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt_text,
                    }
                ],
            )
            
            if response and response.choices:
                result = response.choices[0].message.content
                print(f"✅ 成功生成 {text_type} keyfacts")
                return result
            else:
                print(f"⚠️ 生成 {text_type} keyfacts 失败：未收到有效响应")
                return "[]"
                
        except Exception as e:
            print(f"⚠️ 生成 {text_type} keyfacts 失败: {e}")
            import traceback
            traceback.print_exc()
            return "[]"
    
    async def evaluate_keyfacts(
        self,
        ground_truth_keyfacts: Union[str, List[Dict], Dict],
        generated_keyfacts: Union[str, List[Dict], Dict],
        ground_truth_path: Optional[str] = None,
        generated_keyfacts_path: Optional[str] = None
    ) -> Dict[str, float]:
        """
        评估关键事实的精确率和召回率
        
        Args:
            ground_truth_keyfacts: 真实关键事实（可以是 JSON 字符串、字典列表或字典）
            generated_keyfacts: 生成的关键事实（可以是 JSON 字符串、字典列表或字典）
            ground_truth_path: 真实关键事实文件路径（可选）
            generated_keyfacts_path: 生成关键事实文件路径（可选）
            
        Returns:
            dict: 包含 precision 和 recall 的字典
        """
        if self.args is None:
            print("⚠️ 缺少 args 参数，无法进行关键事实评估")
            return {
                'precision': -1.0,
                'recall': -1.0,
                'precision_by_priority': {},
                'recall_by_priority': {}
            }
        
        try:
            # 如果提供了文件路径，使用文件路径
            if ground_truth_path and generated_keyfacts_path:
                result = await async_single_paper_keyfacts_precision_calculation(
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
                # 如果没有文件路径，需要将数据写入临时文件
                import tempfile
                import aiofiles
                
                # 处理 ground_truth_keyfacts
                if isinstance(ground_truth_keyfacts, str):
                    gt_data = json.loads(ground_truth_keyfacts)
                else:
                    gt_data = ground_truth_keyfacts
                
                # 处理 generated_keyfacts
                if isinstance(generated_keyfacts, str):
                    gen_data = json.loads(generated_keyfacts)
                else:
                    gen_data = generated_keyfacts
                
                # 创建临时文件
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as gt_file:
                    json.dump(gt_data, gt_file, indent=2, ensure_ascii=False)
                    gt_path = gt_file.name
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as gen_file:
                    json.dump(gen_data, gen_file, indent=2, ensure_ascii=False)
                    gen_path = gen_file.name
                
                try:
                    result = await async_single_paper_keyfacts_precision_calculation(
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
                    # 清理临时文件
                    if os.path.exists(gt_path):
                        os.remove(gt_path)
                    if os.path.exists(gen_path):
                        os.remove(gen_path)
        except Exception as e:
            print(f"⚠️ 关键事实评估失败: {e}")
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
        include_keyfacts: bool = True
    ) -> Dict:
        """
        评估单个文档
        
        Args:
            popsci_text: 待评估的科普文章文本
            original_text: 原始复杂文本（用于简洁性评估）
            reference_text: 参考文本（用于简洁性评估，可选）
            ground_truth_keyfacts: 真实关键事实（用于关键事实评估）
            generated_keyfacts: 生成的关键事实（用于关键事实评估）
            ground_truth_keyfacts_path: 真实关键事实文件路径
            generated_keyfacts_path: 生成关键事实文件路径
            include_keyfacts: 是否包含关键事实评估
            
        Returns:
            dict: 包含所有评估指标的结果字典
        """
        result = {
            'popsci_text': popsci_text[:200] + '...' if len(popsci_text) > 200 else popsci_text,
            'coherence': {},
            'simplicity': {},
            'vividness': {},
            'keyfacts': {}
        }
        
        # 1. 评估连贯性
        if self.skip_coherence:
            print("⏭️  跳过连贯性评估")
            result['coherence'] = {
                'ppl_score': -1.0,
                'interpretation': '已跳过连贯性评估'
            }
        else:
            print("📊 评估连贯性（困惑度）...")
            coherence_score = self.evaluate_coherence(popsci_text)
            result['coherence'] = {
                'ppl_score': coherence_score,
                'interpretation': self._interpret_ppl(coherence_score)
            }
        
        # 2. 评估简洁性
        if original_text:
            print("📊 评估简洁性（FKGL）...")
            simplicity_score = self.evaluate_simplicity(original_text, popsci_text, reference_text)
            result['simplicity'] = {
                'fkgl_score': simplicity_score,
                'interpretation': self._interpret_fkgl(simplicity_score)
            }
        else:
            result['simplicity'] = {
                'fkgl_score': -1.0,
                'interpretation': '缺少原始文本，无法评估简洁性'
            }
        
        # 3. 评估生动性
        print("📊 评估生动性...")
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
        
        # 4. 评估关键事实（如果提供）
        if include_keyfacts:
            if ground_truth_keyfacts_path and generated_keyfacts_path:
                print("📊 评估关键事实精确率和召回率...")
                keyfacts_result = await self.evaluate_keyfacts(
                    None, None,
                    ground_truth_path=ground_truth_keyfacts_path,
                    generated_keyfacts_path=generated_keyfacts_path
                )
                result['keyfacts'] = keyfacts_result
            elif ground_truth_keyfacts and generated_keyfacts:
                print("📊 评估关键事实精确率和召回率...")
                keyfacts_result = await self.evaluate_keyfacts(
                    ground_truth_keyfacts,
                    generated_keyfacts
                )
                result['keyfacts'] = keyfacts_result
            else:
                result['keyfacts'] = {
                    'precision': -1.0,
                    'recall': -1.0,
                    'note': '缺少关键事实数据，跳过评估'
                }
        else:
            result['keyfacts'] = {
                'note': '未包含关键事实评估'
            }
        
        return result
    
    async def evaluate_document_pair(
        self,
        popsci_text_1: str,
        popsci_text_2: str,
        original_text: Optional[str] = None,
        reference_text: Optional[str] = None
    ) -> Dict:
        """
        评估文档对（比较两个科普文章）
        
        Args:
            popsci_text_1: 第一个科普文章文本
            popsci_text_2: 第二个科普文章文本
            original_text: 原始复杂文本（用于简洁性评估）
            reference_text: 参考文本（用于简洁性评估，可选）
            
        Returns:
            dict: 包含两个文档的评估结果和比较结果
        """
        print("📊 评估文档对...")
        
        # 评估第一个文档
        result_1 = await self.evaluate_single_document(
            popsci_text_1,
            original_text,
            reference_text,
            include_keyfacts=False
        )
        
        # 评估第二个文档
        result_2 = await self.evaluate_single_document(
            popsci_text_2,
            original_text,
            reference_text,
            include_keyfacts=False
        )
        
        # 比较结果
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
                'better': 'text_1' if result_1['simplicity']['fkgl_score'] < result_2['simplicity']['fkgl_score'] else 'text_2',  # FKGL 值越低越好
                'difference': abs(result_1['simplicity']['fkgl_score'] - result_2['simplicity']['fkgl_score'])
            },
            'vividness': {
                'text_1_score': result_1['vividness'].get('vividness_score', 0.0),
                'text_2_score': result_2['vividness'].get('vividness_score', 0.0),
                'better': 'text_1' if result_1['vividness'].get('vividness_score', 0.0) > result_2['vividness'].get('vividness_score', 0.0) else 'text_2',
                'difference': abs(result_1['vividness'].get('vividness_score', 0.0) - result_2['vividness'].get('vividness_score', 0.0))
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
        popsci_field: str = 'popsci_text',
        original_field: str = 'original_text',
        reference_field: Optional[str] = None,
        ground_truth_keyfacts_field: Optional[str] = None,
        generated_keyfacts_field: Optional[str] = None,
        ground_truth_keyfacts_dir: Optional[str] = None,
        generated_keyfacts_dir: Optional[str] = None,
        include_keyfacts: bool = True,
        auto_generate_keyfacts: bool = False
    ) -> Dict:
        """
        评估数据集格式的文档
        
        Args:
            dataset_path: 数据集文件路径
            output_path: 输出结果文件路径（如果为 None，则使用默认路径）
            dataset_format: 数据集格式（'json'）
            popsci_field: 科普文章文本字段名
            original_field: 原始文本字段名
            reference_field: 参考文本字段名（可选）
            ground_truth_keyfacts_field: 真实关键事实字段名（可选）
            generated_keyfacts_field: 生成关键事实字段名（可选）
            ground_truth_keyfacts_dir: 真实关键事实文件目录（可选）
                当提供此参数时，会尝试多种策略匹配文件：
                1. 使用 doc_id: {doc_id}_keyfacts.json
                2. 按索引匹配：目录中排序后的第 i 个文件
                3. 使用标题匹配：{title}_keyfacts.json 或 {title}_key_facts.json
            generated_keyfacts_dir: 生成关键事实文件目录（可选）
                匹配策略同上
            include_keyfacts: 是否包含关键事实评估
            auto_generate_keyfacts: 是否自动生成关键事实
                如果为 True，将从 original_text 生成 Wikipedia keyfacts（使用 gemini-3-pro-preview），
                从 popsci_text 生成科普 keyfacts（使用 grok）
                如果同时提供了文件路径或字段，优先使用文件/字段，否则才自动生成
            
        Returns:
            dict: 包含所有文档评估结果和统计信息的字典
                统计信息包括：
                - keyfacts_precision: 总体精确率统计
                - keyfacts_recall: 总体召回率统计
                - keyfacts_precision_by_priority: 按优先级的精确率统计
                - keyfacts_recall_by_priority: 按优先级的召回率统计
        """
        # 如果没有指定输出路径，使用默认路径
        if output_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            dataset_name = os.path.splitext(os.path.basename(dataset_path))[0]
            output_path = os.path.join(project_root, 'output', f'{dataset_name}_evaluation_results.json')
        
        print(f"📊 开始评估数据集: {dataset_path}")
        
        # 加载数据集
        if dataset_format == 'json':
            with open(dataset_path, 'r', encoding='utf-8') as f:
                dataset = json.load(f)
        else:
            raise ValueError(f"不支持的数据集格式: {dataset_format}")
        
        if not isinstance(dataset, list):
            raise ValueError("数据集格式错误：应为列表格式")
        
        results = []
        total = len(dataset)
        
        # 辅助函数：获取嵌套字段值（支持如 'popsci_article.content' 这样的嵌套字段）
        def get_nested_field(data, field_path, default=''):
            """获取嵌套字段值"""
            keys = field_path.split('.')
            value = data
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key, default)
                else:
                    return default
            return value if value else default
        
        # 如果启用了自动生成 keyfacts，先收集所有需要生成的任务，然后批量并发执行
        keyfacts_generation_tasks = []  # [(doc_index, text, text_type, is_gt), ...]
        doc_keyfacts_map = {}  # {doc_index: {'gt': None, 'gen': None}}
        
        # 第一遍：收集所有需要生成 keyfacts 的任务
        if auto_generate_keyfacts and include_keyfacts:
            print(f"\n🔍 收集需要生成 keyfacts 的任务...")
            for i, item in enumerate(dataset):
                popsci_text = get_nested_field(item, popsci_field, '')
                original_text = get_nested_field(item, original_field, None) if original_field else None
                
                if not popsci_text:
                    continue
                
                # 检查是否需要生成
                need_gt = False
                need_gen = False
                
                # 检查文件路径
                if ground_truth_keyfacts_dir and generated_keyfacts_dir:
                    doc_id = item.get('id', str(i))
                    gt_file = os.path.join(ground_truth_keyfacts_dir, f"{doc_id}_keyfacts.json")
                    gen_file = os.path.join(generated_keyfacts_dir, f"{doc_id}_keyfacts.json")
                    
                    if not os.path.exists(gt_file) and original_text:
                        need_gt = True
                    if not os.path.exists(gen_file) and popsci_text:
                        need_gen = True
                else:
                    if original_text:
                        need_gt = True
                    if popsci_text:
                        need_gen = True
                
                # 检查数据集字段
                if not need_gt and ground_truth_keyfacts_field:
                    gt_field = get_nested_field(item, ground_truth_keyfacts_field, None)
                    if not gt_field and original_text:
                        need_gt = True
                
                if not need_gen and generated_keyfacts_field:
                    gen_field = get_nested_field(item, generated_keyfacts_field, None)
                    if not gen_field and popsci_text:
                        need_gen = True
                
                # 添加到任务列表
                if need_gt:
                    keyfacts_generation_tasks.append((i, original_text, "wikipedia", True))
                if need_gen:
                    keyfacts_generation_tasks.append((i, popsci_text, "popsci", False))
                
                doc_keyfacts_map[i] = {'gt': None, 'gen': None}
            
            # 批量并发生成 keyfacts（使用 500 并发）
            if keyfacts_generation_tasks:
                print(f"🔑 开始批量生成 {len(keyfacts_generation_tasks)} 个 keyfacts 任务（并发数：500）...")
                
                # 使用 semaphore 限制并发数
                semaphore = asyncio.Semaphore(500)
                
                async def generate_with_semaphore(doc_idx, text, text_type, is_gt):
                    async with semaphore:
                        try:
                            result = await self.generate_keyfacts(text, text_type=text_type)
                            return (doc_idx, result, is_gt)
                        except Exception as e:
                            print(f"⚠️ 生成 keyfacts 失败（文档 {doc_idx}, {'GT' if is_gt else 'GEN'}）: {e}")
                            return (doc_idx, "[]", is_gt)
                
                # 创建所有任务
                tasks = [generate_with_semaphore(doc_idx, text, text_type, is_gt) 
                        for doc_idx, text, text_type, is_gt in keyfacts_generation_tasks]
                
                # 批量执行（每批最多 500 个）
                batch_size = 500
                for batch_start in range(0, len(tasks), batch_size):
                    batch_end = min(batch_start + batch_size, len(tasks))
                    batch_tasks = tasks[batch_start:batch_end]
                    batch_results = await asyncio.gather(*batch_tasks)
                    
                    # 处理结果
                    for doc_idx, result, is_gt in batch_results:
                        try:
                            parsed_result = json.loads(result)
                            if is_gt:
                                doc_keyfacts_map[doc_idx]['gt'] = parsed_result
                            else:
                                doc_keyfacts_map[doc_idx]['gen'] = parsed_result
                        except json.JSONDecodeError:
                            print(f"⚠️ 解析 keyfacts JSON 失败（文档 {doc_idx}, {'GT' if is_gt else 'GEN'}）")
                
                print(f"✅ 完成批量生成 keyfacts")
        
        # 第二遍：收集所有需要评估 keyfacts 的任务和文档信息（用于并发评估）
        keyfacts_evaluation_tasks = []  # [(doc_index, gt_keyfacts, gen_keyfacts, gt_path, gen_path), ...]
        doc_info_map = {}  # {doc_index: {item, popsci_text, original_text, ...}}
        
        # 收集所有文档信息和 keyfacts 评估任务
        for i, item in enumerate(dataset):
            print(f"\n处理文档 {i+1}/{total}...")
            
            # 提取字段（支持嵌套字段，如 'popsci_article.content'）
            popsci_text = get_nested_field(item, popsci_field, '')
            original_text = get_nested_field(item, original_field, None) if original_field else None
            reference_text = get_nested_field(item, reference_field, None) if reference_field else None
            
            if not popsci_text:
                print(f"⚠️ 文档 {i+1} 缺少科普文章文本，跳过")
                continue
            
            # 处理关键事实
            ground_truth_keyfacts = None
            generated_keyfacts = None
            ground_truth_keyfacts_path = None
            generated_keyfacts_path = None
            
            if include_keyfacts:
                # 优先级：文件路径 > 数据集字段 > 自动生成
                found_gt_keyfacts = False
                found_gen_keyfacts = False
                
                # 1. 尝试从文件目录中查找
                if ground_truth_keyfacts_dir and generated_keyfacts_dir:
                    # 策略1: 尝试使用 doc_id 匹配
                    doc_id = item.get('id', str(i))
                    gt_file = os.path.join(ground_truth_keyfacts_dir, f"{doc_id}_keyfacts.json")
                    gen_file = os.path.join(generated_keyfacts_dir, f"{doc_id}_keyfacts.json")
                    
                    # 策略2: 如果策略1失败，尝试按索引匹配（类似 overall_evaluation.py）
                    if not (os.path.exists(gt_file) and os.path.exists(gen_file)):
                        # 获取目录中的所有 JSON 文件并排序
                        gt_files = sorted([f for f in os.listdir(ground_truth_keyfacts_dir) if f.endswith(".json")])
                        gen_files = sorted([f for f in os.listdir(generated_keyfacts_dir) if f.endswith(".json")])
                        
                        if i < len(gt_files) and i < len(gen_files):
                            gt_file = os.path.join(ground_truth_keyfacts_dir, gt_files[i])
                            gen_file = os.path.join(generated_keyfacts_dir, gen_files[i])
                    
                    # 策略3: 尝试使用标题匹配
                    if not (os.path.exists(gt_file) and os.path.exists(gen_file)):
                        title = get_nested_field(item, 'title', '') or get_nested_field(item, 'popsci_article.title', '') or get_nested_field(item, 'wikipedia_article.title', '')
                        if title:
                            # 尝试多种可能的文件名格式
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
                        print(f"⚠️ 文档 {i+1} 未找到匹配的 keyfacts 文件")
                        print(f"  尝试查找: {gt_file}, {gen_file}")
                
                # 2. 如果文件不存在，尝试从数据集中提取（支持嵌套字段）
                if not found_gt_keyfacts:
                    if ground_truth_keyfacts_field:
                        ground_truth_keyfacts = get_nested_field(item, ground_truth_keyfacts_field, None)
                        if ground_truth_keyfacts:
                            found_gt_keyfacts = True
                
                if not found_gen_keyfacts:
                    if generated_keyfacts_field:
                        generated_keyfacts = get_nested_field(item, generated_keyfacts_field, None)
                        if generated_keyfacts:
                            found_gen_keyfacts = True
                
                # 3. 如果仍未找到且启用了自动生成，使用预先生成的结果
                if auto_generate_keyfacts:
                    if not found_gt_keyfacts and i in doc_keyfacts_map and doc_keyfacts_map[i]['gt'] is not None:
                        ground_truth_keyfacts = doc_keyfacts_map[i]['gt']
                        found_gt_keyfacts = True
                    
                    if not found_gen_keyfacts and i in doc_keyfacts_map and doc_keyfacts_map[i]['gen'] is not None:
                        generated_keyfacts = doc_keyfacts_map[i]['gen']
                        found_gen_keyfacts = True
                
                # 收集 keyfacts 评估任务（用于并发评估）
                if found_gt_keyfacts or found_gen_keyfacts:
                    keyfacts_evaluation_tasks.append((
                        i,
                        ground_truth_keyfacts,
                        generated_keyfacts,
                        ground_truth_keyfacts_path,
                        generated_keyfacts_path
                    ))
            
            # 保存文档信息（稍后进行非 LLM 评估）
            doc_info_map[i] = {
                'item': item,
                'popsci_text': popsci_text,
                'original_text': original_text,
                'reference_text': reference_text,
                'ground_truth_keyfacts': ground_truth_keyfacts if found_gt_keyfacts else None,
                'generated_keyfacts': generated_keyfacts if found_gen_keyfacts else None,
                'found_gt_keyfacts': found_gt_keyfacts,
                'found_gen_keyfacts': found_gen_keyfacts
            }
        
        # 第二阶段：批量并发评估 keyfacts precision/recall（使用 500 并发）
        doc_keyfacts_eval_map = {}  # {doc_index: keyfacts_evaluation_result}
        if include_keyfacts and keyfacts_evaluation_tasks:
            print(f"\n🔑 开始批量评估 {len(keyfacts_evaluation_tasks)} 个 keyfacts precision/recall（并发数：500）...")
            
            semaphore = asyncio.Semaphore(500)
            
            async def evaluate_keyfacts_with_semaphore(doc_idx, gt_keyfacts, gen_keyfacts, gt_path, gen_path):
                async with semaphore:
                    try:
                        eval_result = await self.evaluate_keyfacts(
                            gt_keyfacts,
                            gen_keyfacts,
                            ground_truth_path=gt_path,
                            generated_keyfacts_path=gen_path
                        )
                        return (doc_idx, eval_result)
                    except Exception as e:
                        print(f"⚠️ 评估 keyfacts 失败（文档 {doc_idx}）: {e}")
                        return (doc_idx, {
                            'precision': -1.0,
                            'recall': -1.0,
                            'precision_by_priority': {},
                            'recall_by_priority': {}
                        })
            
            # 创建所有评估任务
            tasks = [evaluate_keyfacts_with_semaphore(doc_idx, gt_keyfacts, gen_keyfacts, gt_path, gen_path)
                    for doc_idx, gt_keyfacts, gen_keyfacts, gt_path, gen_path in keyfacts_evaluation_tasks]
            
            # 批量执行（每批最多 500 个）
            batch_size = 500
            for batch_start in range(0, len(tasks), batch_size):
                batch_end = min(batch_start + batch_size, len(tasks))
                batch_tasks = tasks[batch_start:batch_end]
                batch_results = await asyncio.gather(*batch_tasks)
                
                # 保存评估结果
                for doc_idx, eval_result in batch_results:
                    doc_keyfacts_eval_map[doc_idx] = eval_result
            
            print(f"✅ 完成批量评估 keyfacts precision/recall")
        
        # 第三阶段：逐个文档进行非 LLM 评估（coherence、simplicity、vividness）
        print(f"\n📊 开始逐个文档进行非 LLM 评估...")
        results = []
        for i in sorted(doc_info_map.keys()):
            doc_info = doc_info_map[i]
            item = doc_info['item']
            popsci_text = doc_info['popsci_text']
            original_text = doc_info['original_text']
            reference_text = doc_info['reference_text']
            
            print(f"\n处理文档 {i+1}/{total}...")
            
            # 进行非 keyfacts 的评估（这些不需要 LLM）
            result = await self.evaluate_single_document(
                popsci_text,
                original_text,
                reference_text,
                doc_info['ground_truth_keyfacts'],
                doc_info['generated_keyfacts'],
                None,
                None,
                include_keyfacts=False  # 跳过 keyfacts 评估（已在第二阶段完成）
            )
            
            # 添加 keyfacts 评估结果（如果已评估）
            if i in doc_keyfacts_eval_map:
                result['keyfacts'] = doc_keyfacts_eval_map[i]
            elif include_keyfacts:
                result['keyfacts'] = {
                    'precision': -1.0,
                    'recall': -1.0,
                    'note': '未找到关键事实数据'
                }
            else:
                result['keyfacts'] = {
                    'note': '未包含关键事实评估'
                }
            
            # 添加文档标识和原始数据（支持嵌套字段）
            result['doc_id'] = get_nested_field(item, 'id', i)
            # 尝试从多个可能的字段获取标题
            title = (get_nested_field(item, 'title', '') or 
                    get_nested_field(item, 'popsci_article.title', '') or
                    get_nested_field(item, 'wikipedia_article.title', ''))
            result['title'] = title
            
            # 保存原始数据（完整的数据项）
            result['original_data'] = item
            
            # 保存 keyfacts 数据（如果已生成或找到）
            if include_keyfacts:
                result['ground_truth_keyfacts'] = doc_info['ground_truth_keyfacts']
                result['generated_keyfacts'] = doc_info['generated_keyfacts']
            
            results.append(result)
        
        # 计算统计信息
        statistics = self._calculate_statistics(results)
        
        # 保存结果（包含原始数据、keyfacts 和所有评测结果）
        output_data = {
            'dataset_path': dataset_path,
            'total_documents': total,
            'evaluated_documents': len(results),
            'results': results,  # 每条结果包含：original_data, keyfacts, coherence, simplicity, vividness 等
            'statistics': statistics
        }
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        else:
            # 如果 output_path 只是文件名，使用默认输出目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            output_dir = os.path.join(project_root, 'output')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, os.path.basename(output_path))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 评估完成！结果已保存到: {output_path}")
        
        return output_data
    
    def _calculate_statistics(self, results: List[Dict]) -> Dict:
        """计算统计信息"""
        if not results:
            return {}
        
        # 提取有效分数
        coherence_scores = [r['coherence']['ppl_score'] for r in results if r['coherence']['ppl_score'] >= 0]
        simplicity_scores = [r['simplicity']['fkgl_score'] for r in results if r['simplicity']['fkgl_score'] >= 0]
        vividness_scores = [r['vividness'].get('vividness_score', 0.0) for r in results]
        figurativeness_scores = [r['vividness'].get('figurativeness', 0.0) for r in results]
        emotionality_scores = [r['vividness'].get('emotionality', 0.0) for r in results]
        decorativeness_scores = [r['vividness'].get('decorativeness', 0.0) for r in results]
        
        keyfacts_precisions = []
        keyfacts_recalls = []
        keyfacts_precisions_priority_1 = []
        keyfacts_precisions_priority_2 = []
        keyfacts_precisions_priority_3 = []
        keyfacts_recalls_priority_1 = []
        keyfacts_recalls_priority_2 = []
        keyfacts_recalls_priority_3 = []
        
        for r in results:
            if 'keyfacts' in r:
                if 'precision' in r['keyfacts'] and r['keyfacts']['precision'] >= 0:
                    keyfacts_precisions.append(r['keyfacts']['precision'])
                if 'recall' in r['keyfacts'] and r['keyfacts']['recall'] >= 0:
                    keyfacts_recalls.append(r['keyfacts']['recall'])
                
                # 提取按优先级的 precision 和 recall
                if 'precision_by_priority' in r['keyfacts']:
                    p_by_pri = r['keyfacts']['precision_by_priority']
                    if 'priority_1' in p_by_pri and p_by_pri['priority_1'] >= 0:
                        keyfacts_precisions_priority_1.append(p_by_pri['priority_1'])
                    if 'priority_2' in p_by_pri and p_by_pri['priority_2'] >= 0:
                        keyfacts_precisions_priority_2.append(p_by_pri['priority_2'])
                    if 'priority_3' in p_by_pri and p_by_pri['priority_3'] >= 0:
                        keyfacts_precisions_priority_3.append(p_by_pri['priority_3'])
                
                if 'recall_by_priority' in r['keyfacts']:
                    r_by_pri = r['keyfacts']['recall_by_priority']
                    if 'priority_1' in r_by_pri and r_by_pri['priority_1'] >= 0:
                        keyfacts_recalls_priority_1.append(r_by_pri['priority_1'])
                    if 'priority_2' in r_by_pri and r_by_pri['priority_2'] >= 0:
                        keyfacts_recalls_priority_2.append(r_by_pri['priority_2'])
                    if 'priority_3' in r_by_pri and r_by_pri['priority_3'] >= 0:
                        keyfacts_recalls_priority_3.append(r_by_pri['priority_3'])
        
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
            'coherence': calc_stats(coherence_scores),
            'simplicity': calc_stats(simplicity_scores),
            'vividness': calc_stats(vividness_scores),
            'figurativeness': calc_stats(figurativeness_scores),
            'emotionality': calc_stats(emotionality_scores),
            'decorativeness': calc_stats(decorativeness_scores),
            'keyfacts_precision': calc_stats(keyfacts_precisions),
            'keyfacts_recall': calc_stats(keyfacts_recalls),
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
        """解释困惑度分数"""
        if ppl_score < 0:
            return "评估失败"
        elif ppl_score < 50:
            return "非常流畅"
        elif ppl_score < 100:
            return "相对流畅"
        elif ppl_score < 200:
            return "中等流畅"
        elif ppl_score < 500:
            return "不够流畅"
        else:
            return "非常不流畅"
    
    def _interpret_fkgl(self, fkgl_score: float) -> str:
        """解释 FKGL 分数（值越低表示越简单易读）"""
        if fkgl_score < 0:
            return "评估失败"
        elif fkgl_score <= 8:
            return "非常简洁（小学水平）"
        elif fkgl_score <= 12:
            return "相对简洁（中学水平）"
        elif fkgl_score <= 16:
            return "中等简洁（高中水平）"
        else:
            return "不够简洁（大学及以上水平）"


# 便捷函数
async def evaluate_single_document_async(
    popsci_text: str,
    original_text: Optional[str] = None,
    reference_text: Optional[str] = None,
    ground_truth_keyfacts: Optional[Union[str, List[Dict], Dict]] = None,
    generated_keyfacts: Optional[Union[str, List[Dict], Dict]] = None,
    args=None,
    vividness_weights=None
) -> Dict:
    """
    评估单个文档的便捷函数
    
    Args:
        popsci_text: 待评估的科普文章文本
        original_text: 原始复杂文本
        reference_text: 参考文本
        ground_truth_keyfacts: 真实关键事实
        generated_keyfacts: 生成的关键事实
        args: 命令行参数对象
        vividness_weights: 生动性评估权重
        
    Returns:
        dict: 评估结果
    """
    evaluator = ComprehensiveEvaluator(args=args, vividness_weights=vividness_weights)
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
    vividness_weights=None
) -> Dict:
    """
    评估文档对的便捷函数
    
    Args:
        popsci_text_1: 第一个科普文章文本
        popsci_text_2: 第二个科普文章文本
        original_text: 原始复杂文本
        reference_text: 参考文本
        args: 命令行参数对象
        vividness_weights: 生动性评估权重
        
    Returns:
        dict: 评估结果
    """
    evaluator = ComprehensiveEvaluator(args=args, vividness_weights=vividness_weights)
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
    **kwargs
) -> Dict:
    """
    评估数据集的便捷函数
    
    Args:
        dataset_path: 数据集文件路径
        output_path: 输出结果文件路径
        dataset_format: 数据集格式
        popsci_field: 科普文章文本字段名
        original_field: 原始文本字段名
        args: 命令行参数对象
        vividness_weights: 生动性评估权重
        **kwargs: 其他参数传递给 evaluate_dataset
        
    Returns:
        dict: 评估结果
    """
    evaluator = ComprehensiveEvaluator(args=args, vividness_weights=vividness_weights)
    return await evaluator.evaluate_dataset(
        dataset_path,
        output_path,
        dataset_format,
        popsci_field,
        original_field,
        **kwargs
    )


if __name__ == "__main__":
    # 示例用法
    import asyncio
    
    async def main():
        # 初始化评估器
        args = parse_args()
        evaluator = ComprehensiveEvaluator(args=args)
        
        # 示例：评估单个文档
        popsci_text = "This is a sample popular science article about science."
        original_text = "This is a complex scientific paper with technical jargon."
        
        result = await evaluator.evaluate_single_document(
            popsci_text,
            original_text=original_text
        )
        
        print("\n评估结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    asyncio.run(main())
