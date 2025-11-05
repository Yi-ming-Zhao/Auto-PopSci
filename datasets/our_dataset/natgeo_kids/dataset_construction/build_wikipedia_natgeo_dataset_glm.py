#!/usr/bin/env python3
"""
构建Wikipedia-NatGeo科普数据集
根据NatGeo Kids文章的description生成Wikipedia搜索关键词，获取对应的Wikipedia原文
构建Wikipedia原文-NatGeo科普对数据集
使用GLM-4.6进行关键词提取，包含多重后备机制
"""

import json
import os
import asyncio
import aiohttp
import wikipedia
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 配置参数
NATGEO_DATA_PATH = "/Users/yzxbb/Desktop/Auto-Popsci/datasets/our_dataset/natgeo_kids/original_natgeo/all_natgeo_kids_articles.json"
OUTPUT_PATH = "/Users/yzxbb/Desktop/Auto-Popsci/datasets/our_dataset/natgeo_kids/natgeo_wikipedia_glm.json"
SAMPLE_SIZE = None  # 处理的文章数量，设为None表示处理全部

# GLM-4.6 API配置
GLM_API_KEY = "3a65782d25f640e1992485321d0fe76e.gTqRhVSVcVS5PbAK"
GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


@dataclass
class WikipediaNatgeoPair:
    """Wikipedia原文-NatGeo科普对数据结构"""

    natgeo_article: Dict
    wikipedia_search_keyword: str
    wikipedia_title: str
    wikipedia_content: str
    wikipedia_url: str

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "natgeo_article": {
                "title": self.natgeo_article.get("title", ""),
                "description": self.natgeo_article.get("description", ""),
                "content": self.natgeo_article.get("content", ""),
                "url": self.natgeo_article.get("url", ""),
                "category": self.natgeo_article.get("category", ""),
                "image_url": self.natgeo_article.get("image_url", ""),
            },
            "wikipedia_search_keyword": self.wikipedia_search_keyword,
            "wikipedia_title": self.wikipedia_title,
            "wikipedia_content": self.wikipedia_content,
            "wikipedia_url": self.wikipedia_url,
        }


class DatasetBuilder:
    def __init__(self):
        """初始化数据集构建器"""
        # GLM-4.6 API配置
        self.api_key = GLM_API_KEY
        self.api_url = GLM_API_URL

    async def extract_wikipedia_keyword_glm(
        self, session: aiohttp.ClientSession, description: str
    ) -> str:
        """使用GLM-4.6从描述中提取Wikipedia搜索关键词"""

        prompt_text = f"""你是一个专业的关键词提取专家，擅长从科普文章描述中提取最适合在Wikipedia中搜索的关键词。

请分析以下NatGeo Kids文章的描述，提取一个最核心、最准确的Wikipedia搜索关键词。

要求：
1. 关键词应该是一个具体的名词或短语，适合在Wikipedia中搜索
2. 关键词应该描述文章所介绍的对象
3. 关键词应该简洁明了，1-2个词为宜
4. 优先选择科学概念、动物名称、地理名词等专业术语
5. 直接输出关键词，不要添加任何解释或引号

文章描述：{description}

Wikipedia搜索关键词："""

        try:
            # 调用GLM-4.6 API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": "glm-4-air-250414",  # 使用更新的模型
                "messages": [
                    {"role": "system", "content": "你是一个专业的关键词提取专家。"},
                    {"role": "user", "content": prompt_text},
                ],
                "max_tokens": 50,
                "temperature": 0.3,
            }

            print(f"  正在调用GLM-4.6提取关键词...")

            async with session.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                if response.status == 429:
                    print(f"  GLM API请求频率限制")
                    return None
                elif response.status != 200:
                    error_text = await response.text()
                    print(f"  GLM API响应错误: {response.status}")
                    return None

                result = await response.json()

            # 检查响应中是否有错误信息
            if "error" in result:
                error_info = result["error"]
                print(f"  GLM API返回错误: {error_info}")
                return None

            # 提取响应内容
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    keyword = choice["message"]["content"].strip()
                    # 清理可能的多余字符
                    keyword = keyword.strip("\"'")

                    # 验证关键词不为空
                    if keyword and len(keyword) > 0:
                        print(f"  GLM提取的关键词: '{keyword}'")
                        return keyword
                    else:
                        print(f"  GLM返回的关键词为空")
                        return None
                else:
                    print(f"  GLM响应格式异常")
                    return None
            else:
                print(f"  GLM API响应格式异常")
                return None

        except asyncio.TimeoutError:
            print(f"  GLM API请求超时")
            return None
        except aiohttp.ClientError as e:
            print(f"  GLM API网络请求失败: {e}")
            return None
        except Exception as e:
            print(f"  提取关键词时出现未知错误: {e}")
            return None

    async def extract_wikipedia_keyword(
        self, session: aiohttp.ClientSession, description: str
    ) -> str:
        """使用GLM-4.6提取Wikipedia搜索关键词"""
        # 直接使用GLM-4.6提取关键词
        keyword = await self.extract_wikipedia_keyword_glm(session, description)
        if keyword and len(keyword.strip()) > 0:
            return keyword
        else:
            # GLM无法提取关键词，返回None
            return None

    async def search_wikipedia(
        self, session: aiohttp.ClientSession, keyword: str
    ) -> Optional[Tuple[str, str, str]]:
        """在Wikipedia中搜索关键词，使用稳定的wikipedia库"""
        try:
            print(f"  正在搜索Wikipedia: {keyword}")

            # 验证关键词不为空
            if not keyword or len(keyword.strip()) == 0:
                print("  搜索关键词为空")
                return None

            # 使用wikipedia库搜索
            search_results = wikipedia.search(keyword)
            if not search_results:
                print(f"  未找到关键词 '{keyword}' 的Wikipedia页面")
                return None

            # 获取第一个搜索结果
            page_title = search_results[0]
            print(f"  找到Wikipedia页面: {page_title}")

            # 获取页面内容（全文）
            try:
                page = wikipedia.page(page_title, auto_suggest=False)
                page_content = page.content  # 获取完整内容
                page_url = page.url

                print(f"  成功获取完整内容，长度: {len(page_content)} 字符")

                # 验证内容长度
                if len(page_content) < 100:
                    print(f"  警告：内容过短，可能不完整")
                    return None

                return page_title, page_content, page_url

            except Exception as e:
                print(f"  获取页面内容时出错: {e}")
                return None

        except Exception as e:
            print(f"  Wikipedia搜索 '{keyword}' 时出错: {e}")
            return None

    def _search_with_fallback(self, keyword: str) -> Optional[Tuple[str, str, str]]:
        """后备搜索策略：使用预定义的映射和简化的关键词"""
        # 预定义的关键词映射
        fallback_mapping = {
            "festival": (
                "Festival",
                self._get_mock_content("Festival"),
                "https://en.wikipedia.org/wiki/Festival",
            ),
            "festivals": (
                "Festival",
                self._get_mock_content("Festival"),
                "https://en.wikipedia.org/wiki/Festival",
            ),
            "festivals celebration": (
                "Festival",
                self._get_mock_content("Festival"),
                "https://en.wikipedia.org/wiki/Festival",
            ),
            "celebration": (
                "Festival",
                self._get_mock_content("Festival"),
                "https://en.wikipedia.org/wiki/Festival",
            ),
            "shark": (
                "Shark",
                self._get_mock_content("Shark"),
                "https://en.wikipedia.org/wiki/Shark",
            ),
            "independence day (united states)": (
                "Independence Day (United States)",
                self._get_mock_content("Independence Day (United States)"),
                "https://en.wikipedia.org/wiki/Independence_Day_(United_States)",
            ),
            "endangered species act of 1973": (
                "Endangered Species Act of 1973",
                self._get_mock_content("Endangered Species Act of 1973"),
                "https://en.wikipedia.org/wiki/Endangered_Species_Act_of_1973",
            ),
            "women's suffrage": (
                "Women's suffrage",
                self._get_mock_content("Women's suffrage"),
                "https://en.wikipedia.org/wiki/Women's_suffrage",
            ),
        }

        keyword_lower = keyword.lower()

        # 检查精确匹配
        if keyword_lower in fallback_mapping:
            title, content, url = fallback_mapping[keyword_lower]
            print(f"  使用预定义映射: {title}")
            return title, content, url

        # 检查部分匹配
        for key, (title, content, url) in fallback_mapping.items():
            if key in keyword_lower or keyword_lower in key:
                print(f"  使用部分匹配映射: {title}")
                return title, content, url

        # 如果关键词中包含常见词汇，使用默认映射
        common_keywords = ["festival", "celebration", "tradition", "culture"]
        for common in common_keywords:
            if common in keyword_lower:
                print(f"  使用默认关键词映射: Festival")
                return (
                    "Festival",
                    self._get_mock_content("Festival"),
                    "https://en.wikipedia.org/wiki/Festival",
                )

        # 最后的后备方案：返回通用的Festival内容
        print(f"  使用最终后备方案: Festival")
        return (
            "Festival",
            self._get_mock_content("Festival"),
            "https://en.wikipedia.org/wiki/Festival",
        )

    def _get_mock_content(self, topic: str) -> str:
        """获取模拟的Wikipedia内容（用于演示）"""
        mock_content = {
            "Festival": """A festival is a special and celebratory event, usually organized by a community and centering on and celebrating some unique aspect of that community and its traditions. Festivals are often meant to celebrate specific times of year, harvests, or historical and religious themes.""",
            "Shark": """Sharks are a group of elasmobranch fish characterized by a cartilaginous skeleton, five to seven gill slits on the sides of the head, and pectoral fins that are not fused to the head. Modern sharks are classified within the clade Selachii and are the sister group to the rays.""",
            "Independence Day (United States)": """Independence Day (colloquially the Fourth of July) is a federal holiday in the United States commemorating the Declaration of Independence of the United States, which was ratified by the Second Continental Congress on July 4, 1776.""",
            "Endangered Species Act of 1973": """The Endangered Species Act of 1973 (ESA) is the primary law in the United States for protecting imperiled species. Designed to protect critically imperiled species from extinction as a consequence of economic growth and development untempered by adequate concern and conservation.""",
            "Women's suffrage": """Women's suffrage is the right of women to vote in elections. Beginning in the late 19th century, besides women working for broad-based economic and political equality and for social reforms, women sought to change voting laws to allow them to vote.""",
        }

        return mock_content.get(
            topic,
            f"This is mock content for {topic} due to Wikipedia API access restrictions.",
        )

    def load_natgeo_articles(
        self, file_path: str, sample_size: Optional[int] = None
    ) -> List[Dict]:
        """加载NatGeo Kids文章数据"""
        with open(file_path, "r", encoding="utf-8") as f:
            articles = json.load(f)

        if sample_size:
            articles = articles[:sample_size]

        print(f"加载了 {len(articles)} 篇NatGeo Kids文章")
        return articles

    async def process_article(
        self,
        session: aiohttp.ClientSession,
        article: Dict,
        article_index: int,
        total_articles: int,
    ) -> Optional[WikipediaNatgeoPair]:
        """处理单篇文章的异步函数"""
        print(f"\n处理第 {article_index+1}/{total_articles} 篇文章...")
        print(f"标题: {article.get('title', 'N/A')}")

        try:
            # 提取Wikipedia搜索关键词
            description = article.get("description", "")
            if not description:
                # 如果没有description，使用全部content作为描述
                content = article.get("content", "")
                if content:
                    # 使用全部内容作为description
                    description = content
                    print(
                        f"  没有description，使用全部文章内容: {description[:100]}..."
                    )
                else:
                    print("跳过：没有描述内容和文章内容")
                    return None

            search_keyword = await self.extract_wikipedia_keyword(session, description)
            if not search_keyword:
                print("跳过：GLM无法提取关键词")
                return None

            # 搜索Wikipedia
            wiki_result = await self.search_wikipedia(session, search_keyword)
            if not wiki_result:
                print("跳过：Wikipedia搜索失败")
                return None

            wiki_title, wiki_content, wiki_url = wiki_result
            print(f"  成功匹配: {wiki_title}")

            # 创建数据对
            pair = WikipediaNatgeoPair(
                natgeo_article=article,
                wikipedia_search_keyword=search_keyword,
                wikipedia_title=wiki_title,
                wikipedia_content=wiki_content,
                wikipedia_url=wiki_url,
            )

            return pair

        except Exception as e:
            print(f"处理文章时出错: {e}")
            return None

    async def build_dataset(
        self, natgeo_file: str, output_file: str, sample_size: Optional[int] = None
    ) -> List[WikipediaNatgeoPair]:
        """构建Wikipedia-NatGeo数据集（异步并发版本）"""
        # 加载NatGeo文章
        articles = self.load_natgeo_articles(natgeo_file, sample_size)

        # 创建aiohttp会话，优化网络配置
        connector = aiohttp.TCPConnector(
            limit=20,  # 总连接池大小
            limit_per_host=10,  # 每个主机的连接数
            ttl_dns_cache=300,  # DNS缓存5分钟
            use_dns_cache=True,  # 启用DNS缓存
            keepalive_timeout=60,  # 保持连接时间
            enable_cleanup_closed=True,  # 启用清理已关闭连接
        )
        timeout = aiohttp.ClientTimeout(
            total=120, connect=30, sock_read=30  # 总超时时间  # 连接超时  # 读取超时
        )

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "AutoPopsci-Bot/1.0 (Educational Research)"},
        ) as session:
            # 使用异步生成器处理文章，控制并发数量
            semaphore = asyncio.Semaphore(10)  # 限制并发数为3，避免API限制

            async def process_with_semaphore(article, index):
                async with semaphore:
                    result = await self.process_article(
                        session, article, index, len(articles)
                    )
                    # 添加延迟以避免API限制
                    await asyncio.sleep(0.5)
                    return result

            # 创建并发任务
            tasks = [
                process_with_semaphore(article, i) for i, article in enumerate(articles)
            ]

            # 执行所有任务
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            pairs = []
            failed_count = 0

            for result in results:
                if isinstance(result, Exception):
                    print(f"处理文章时出现异常: {result}")
                    failed_count += 1
                elif result is not None:
                    pairs.append(result)
                else:
                    failed_count += 1

        # 保存数据集
        dataset = [pair.to_dict() for pair in pairs]
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)

        print(f"\n数据集构建完成！")
        print(f"成功处理: {len(pairs)} 篇文章")
        print(f"失败: {failed_count} 篇文章")
        print(f"数据已保存到: {output_file}")

        return pairs


async def main():
    """主函数（异步版本）"""
    print("开始构建Wikipedia-NatGeo科普数据集（使用GLM-4.6 + 多重后备机制）...")

    # 检查输入文件是否存在
    if not os.path.exists(NATGEO_DATA_PATH):
        print(f"错误：找不到NatGeo数据文件 {NATGEO_DATA_PATH}")
        return

    # 创建数据集构建器
    try:
        builder = DatasetBuilder()
        print("已初始化GLM-4.6数据集构建器（包含后备机制）")
    except Exception as e:
        print(f"错误：{e}")
        return

    # 构建数据集
    pairs = await builder.build_dataset(
        natgeo_file=NATGEO_DATA_PATH, output_file=OUTPUT_PATH, sample_size=SAMPLE_SIZE
    )

    # 显示统计信息
    if pairs:
        print(f"\n=== 数据集统计 ===")
        print(f"总数据对数量: {len(pairs)}")
        print(f"使用GLM-4.6进行关键词提取，包含多重后备机制")
        print(f"处理文章数量: {SAMPLE_SIZE if SAMPLE_SIZE else '全部'}")

        # 显示几个示例
        print(f"\n=== 示例数据对 ===")
        for i, pair in enumerate(pairs[:3]):
            print(f"\n示例 {i+1}:")
            print(f"NatGeo标题: {pair.natgeo_article.get('title', 'N/A')}")
            print(f"提取的关键词: {pair.wikipedia_search_keyword}")
            print(f"Wikipedia标题: {pair.wikipedia_title}")
            print(f"Wikipedia内容长度: {len(pair.wikipedia_content)} 字符")


if __name__ == "__main__":
    asyncio.run(main())
