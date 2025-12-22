#!/usr/bin/env python3
"""
为合并后的数据集提取Wikipedia文章
参考 natgeo_kids 中的构建方式，使用 Grok-4 提取关键词并搜索 Wikipedia
"""

import json
import os
import sys
import asyncio
import aiohttp
import wikipedia
import yaml
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple

# 获取项目根目录
# 文件位于 datasets/our_dataset/，需要向上两级到达项目根目录
_script_dir = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_script_dir, '../..'))
# 添加项目根目录到路径，以便导入工具函数
sys.path.insert(0, PROJECT_ROOT)

# 配置参数
MERGED_DATA_PATH = os.path.join(PROJECT_ROOT, "datasets/our_dataset/sciencealert_articles.json")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "datasets/our_dataset/sciencealert_articles_with_wikipedia.json")
SAMPLE_SIZE = None  # None表示处理全部文章

# 从 auth.yaml 加载 Grok API 配置
AUTH_YAML_PATH = os.path.join(PROJECT_ROOT, "auth.yaml")

def load_grok_config():
    """从 auth.yaml 加载 Grok 配置"""
    try:
        with open(AUTH_YAML_PATH, "r", encoding="utf-8") as f:
            auth_info = yaml.safe_load(f)
        
        grok_config = auth_info.get("grok", {})
        api_key = grok_config.get("api_key", "")
        base_url = grok_config.get("base_url", "")
        model = grok_config.get("model", "grok-4-1-fast-reasoning")
        
        # 构建完整的 API URL（如果 base_url 不包含 /chat/completions）
        if base_url.endswith("/"):
            api_url = f"{base_url}chat/completions"
        else:
            api_url = f"{base_url}/chat/completions"
        
        return api_key, api_url, model
    except Exception as e:
        print(f"❌ 加载 auth.yaml 配置失败: {e}")
        raise

# 加载配置
GROK_API_KEY, GROK_API_URL, GROK_MODEL = load_grok_config()


class WikipediaExtractor:
    def __init__(self):
        """初始化Wikipedia提取器"""
        self.api_key = GROK_API_KEY
        self.api_url = GROK_API_URL
        self.model = GROK_MODEL
        # 创建线程池用于执行同步的wikipedia操作
        self.executor = ThreadPoolExecutor(max_workers=500)

    async def extract_wikipedia_keyword_grok(
        self, session: aiohttp.ClientSession, title: str, content: str, max_retries: int = 3
    ) -> str:
        """使用Grok-4 从标题和内容中提取Wikipedia搜索关键词"""

        prompt_text = f"""你是一个专业的关键词提取专家，擅长从科普文章标题和内容中提取最适合在Wikipedia中搜索的关键词。

请分析以下科普文章的标题和内容，提取一个最核心、最准确的Wikipedia搜索关键词。

要求：
1. 关键词必须与文章主题直接相关，不能是泛泛的概念（如"Experience"、"Knowledge"等）
2. 关键词应该是一个具体的科学概念、生物名称、物理现象、化学物质、地理名称等专业术语
3. 优先从标题中提取核心概念，如果标题不明确，再从文章内容中提取
4. 关键词应该简洁明了，1-3个词为宜
5. 直接输出关键词，不要添加任何解释、引号或标点符号

文章标题：{title}
文章内容：{content}

Wikipedia搜索关键词："""

        # 添加重试逻辑
        result = None
        for attempt in range(max_retries):
            try:
                # 调用Grok-4 API
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是一个专业的关键词提取专家。"},
                        {"role": "user", "content": prompt_text},
                    ],
                    "max_tokens": 50,
                    "temperature": 0.3,
                }

                print(f"  正在调用Grok-4 ({self.model}) 提取关键词...")

                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status == 429:
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt  # 指数退避
                            print(f"  Grok API请求频率限制，{wait_time}秒后重试...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            print(f"  Grok API请求频率限制，已达最大重试次数")
                            return None
                    elif response.status != 200:
                        error_text = await response.text()
                        if attempt < max_retries - 1:
                            print(f"  Grok API响应错误: {response.status}，重试中...")
                            await asyncio.sleep(1)
                            continue
                        else:
                            print(f"  Grok API响应错误: {response.status}，已达最大重试次数")
                            return None

                    result = await response.json()
                    break  # 成功获取响应，跳出重试循环
                    
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    print(f"  Grok API请求超时，重试中...")
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    print(f"  Grok API请求超时，已达最大重试次数")
                    return None
            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    print(f"  Grok API网络请求失败: {e}，重试中...")
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    print(f"  Grok API网络请求失败: {e}，已达最大重试次数")
                    return None
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  提取关键词时出现错误: {e}，重试中...")
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    print(f"  提取关键词时出现未知错误: {e}，已达最大重试次数")
                    return None
        
        # 如果所有重试都失败了
        if result is None:
            return None

        # 处理API响应
        try:
            # 检查响应中是否有错误信息
            if "error" in result:
                error_info = result["error"]
                print(f"  Grok API返回错误: {error_info}")
                return None

            # 提取响应内容
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    keyword = choice["message"]["content"].strip()
                    # 清理可能的多余字符
                    keyword = keyword.strip("\"'")


                    # 验证关键词不为空且合理
                    if keyword and len(keyword) > 0:
                        # 过滤明显不合理的关键词
                        invalid_keywords = ["experience", "knowledge", "information", "thing", "stuff", "something"]
                        if keyword.lower() in invalid_keywords:
                            print(f"  Grok返回的关键词不合理: '{keyword}'，跳过")
                            return None
                        print(f"  Grok提取的关键词: '{keyword}'")
                        return keyword
                    else:
                        print(f"  Grok返回的关键词为空")
                        return None
                else:
                    print(f"  Grok响应格式异常")
                    return None
            else:
                print(f"  Grok API响应格式异常")
                return None
        except Exception as e:
            print(f"  处理Grok API响应时出错: {e}")
            return None

    def _search_wikipedia_sync(self, keyword: str, max_retries: int = 3) -> Optional[Tuple[str, str, str]]:
        """同步的Wikipedia搜索函数，在线程池中执行"""
        # 验证关键词不为空
        if not keyword or len(keyword.strip()) == 0:
            return None

        for attempt in range(max_retries):
            try:
                # 设置Wikipedia库的配置
                wikipedia.set_rate_limiting(True)
                wikipedia.set_lang("en")

                # 使用wikipedia库搜索
                try:
                    search_results = wikipedia.search(keyword, results=5)
                except Exception as e:
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(2 ** attempt)  # 指数退避
                        continue
                    else:
                        return None

                if not search_results:
                    return None

                # 获取第一个搜索结果
                page_title = search_results[0]

                # 获取页面内容（全文）
                try:
                    page = wikipedia.page(page_title, auto_suggest=False)
                    page_content = page.content  # 获取完整内容
                    page_url = page.url

                    # 验证内容长度
                    if len(page_content) < 100:
                        return None

                    return page_title, page_content, page_url

                except wikipedia.exceptions.DisambiguationError as e:
                    # 处理消歧义页面
                    try:
                        page = wikipedia.page(e.options[0], auto_suggest=False)
                        page_content = page.content
                        page_url = page.url
                        if len(page_content) < 100:
                            return None
                        return page.title, page_content, page_url
                    except Exception as e2:
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(2 ** attempt)
                            continue
                        return None

                except Exception as e:
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(2 ** attempt)
                        continue
                    return None

            except Exception as e:
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)
                    continue
                return None

        return None

    async def search_wikipedia(
        self, session: aiohttp.ClientSession, keyword: str, max_retries: int = 3
    ) -> Optional[Tuple[str, str, str]]:
        """在Wikipedia中搜索关键词，使用线程池实现并发"""
        # 验证关键词不为空
        if not keyword or len(keyword.strip()) == 0:
            print("  搜索关键词为空")
            return None

        print(f"  正在搜索Wikipedia: {keyword}")

        # 在线程池中执行同步的wikipedia操作
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._search_wikipedia_sync,
                keyword,
                max_retries
            )
            
            if result:
                page_title, page_content, page_url = result
                print(f"  找到Wikipedia页面: {page_title}")
                print(f"  成功获取完整内容，长度: {len(page_content)} 字符")
                return result
            else:
                print(f"  未找到关键词 '{keyword}' 的Wikipedia页面")
                return None
        except Exception as e:
            print(f"  Wikipedia搜索 '{keyword}' 时出错: {e}")
            return None

    async def extract_wikipedia_for_article(
        self,
        session: aiohttp.ClientSession,
        article: Dict,
        article_index: int,
        total_articles: int,
    ) -> Optional[Dict]:
        """为单篇文章提取Wikipedia信息，关键词提取和Wikipedia搜索并发执行"""
        print(f"\n处理第 {article_index+1}/{total_articles} 篇文章...")
        
        popsci_article = article.get("popsci_article", {})
        title = popsci_article.get("title", "N/A")
        print(f"标题: {title}")

        # 检查是否已有Wikipedia数据
        wikipedia_article = article.get("wikipedia_article", {})
        if wikipedia_article.get("title"):
            print(f"  已有Wikipedia数据，跳过: {wikipedia_article.get('title')}")
            return article  # 返回原文章，不更新

        try:
            # 获取标题和内容
            title = popsci_article.get("title", "")
            content = popsci_article.get("content", "")
            
            if not content:
                print("跳过：没有文章内容")
                return article  # 返回原文章，不更新
            
            if not title:
                print("跳过：没有文章标题")
                return article  # 返回原文章，不更新

            # 并发执行：提取关键词和准备Wikipedia搜索
            # 先提取关键词
            search_keyword = await self.extract_wikipedia_keyword_grok(session, title, content)
            if not search_keyword:
                print("跳过：Grok无法提取关键词")
                return article  # 返回原文章，不更新

            # 搜索Wikipedia（已经在并发环境中，通过线程池实现）
            wiki_result = await self.search_wikipedia(session, search_keyword, max_retries=3)
            
            if wiki_result:
                # 成功找到Wikipedia文章
                wiki_title, wiki_content, wiki_url = wiki_result
                print(f"  成功匹配: {wiki_title}")

                # 更新wikipedia_article
                article["wikipedia_article"] = {
                    "search_keyword": search_keyword,
                    "title": wiki_title,
                    "content": wiki_content,
                    "url": wiki_url,
                }
            else:
                # 未找到Wikipedia文章，但仍保存提取的关键词
                print(f"  未找到Wikipedia文章，保存关键词: {search_keyword}")
                
                # 更新wikipedia_article，title、content、url设为空字符串
                article["wikipedia_article"] = {
                    "search_keyword": search_keyword,
                    "title": "",
                    "content": "",
                    "url": "",
                }

            return article

        except Exception as e:
            print(f"处理文章时出错: {e}")
            return article  # 返回原文章，不更新


async def process_all_articles():
    """处理所有文章"""
    print("📂 开始加载合并后的数据集...")

    # 加载数据
    with open(MERGED_DATA_PATH, "r", encoding="utf-8") as f:
        articles = json.load(f)

    # 如果设置了SAMPLE_SIZE，从第一个没有Wikipedia数据的文章开始处理
    if SAMPLE_SIZE:
        # 找到第一个没有Wikipedia数据的文章索引
        start_index = 0
        for i, article in enumerate(articles):
            if not article.get("wikipedia_article", {}).get("title"):
                start_index = i
                break
        articles = articles[start_index : start_index + SAMPLE_SIZE]
        print(f"   从第 {start_index + 1} 篇开始处理 {SAMPLE_SIZE} 篇文章")

    print(f"✅ 已加载 {len(articles)} 篇文章")

    # 统计已有Wikipedia数据的文章数
    has_wikipedia = sum(
        1
        for article in articles
        if article.get("wikipedia_article", {}).get("title")
    )
    print(f"   其中已有Wikipedia数据: {has_wikipedia} 篇")
    print(f"   需要提取Wikipedia数据: {len(articles) - has_wikipedia} 篇")

    # 创建提取器
    extractor = WikipediaExtractor()
    
    try:
        # 创建aiohttp会话
        connector = aiohttp.TCPConnector(
            limit=500,  # 增加总连接数限制
            limit_per_host=500,  # 增加每个主机的连接数限制，匹配并发数
            ttl_dns_cache=5000,
            use_dns_cache=True,
            keepalive_timeout=60,
            enable_cleanup_closed=True,
        )
        timeout = aiohttp.ClientTimeout(total=120, connect=30, sock_read=30)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "AutoPopsci-Bot/1.0 (Educational Research)"},
        ) as session:
            # 使用信号量控制并发数量
            semaphore = asyncio.Semaphore(500)  # 限制并发数为500

            async def process_with_semaphore(article, index):
                async with semaphore:
                    result = await extractor.extract_wikipedia_for_article(
                        session, article, index, len(articles)
                    )
                    # 添加延迟以避免API限制
                    await asyncio.sleep(0.1)  # 减少延迟，因为我们有更多的并发
                    return result

            # 创建并发任务
            tasks = [
                process_with_semaphore(article, i) for i, article in enumerate(articles)
            ]

            # 执行所有任务
            print("\n🔄 开始处理文章...")
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            updated_articles = []
            failed_count = 0
            skipped_count = 0
            updated_count = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"处理文章 {i+1} 时出现异常: {result}")
                    failed_count += 1
                    updated_articles.append(articles[i])  # 保留原文章
                elif result is not None:
                    # 检查是否更新了Wikipedia数据
                    original_has_wiki = bool(
                        articles[i].get("wikipedia_article", {}).get("title")
                    )
                    new_has_wiki = bool(result.get("wikipedia_article", {}).get("title"))
                    
                    if not original_has_wiki and new_has_wiki:
                        updated_count += 1
                    elif original_has_wiki:
                        skipped_count += 1
                    
                    updated_articles.append(result)
                else:
                    failed_count += 1
                    updated_articles.append(articles[i])  # 保留原文章

        # 保存更新后的数据
        print(f"\n💾 保存到: {OUTPUT_PATH}")
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(updated_articles, f, ensure_ascii=False, indent=2)

        print(f"✅ 处理完成！")

        # 统计信息
        print("\n📊 统计信息:")
        final_has_wikipedia = sum(
            1
            for article in updated_articles
            if article.get("wikipedia_article", {}).get("title")
        )
        print(f"   总文章数: {len(updated_articles)}")
        print(f"   已有Wikipedia数据: {has_wikipedia} 篇（跳过）")
        print(f"   新提取Wikipedia数据: {updated_count} 篇")
        print(f"   最终有Wikipedia数据: {final_has_wikipedia} 篇")
        print(f"   失败: {failed_count} 篇")

        # 按来源统计
        sources = {}
        for article in updated_articles:
            source = article.get("source", "unknown")
            has_wiki = bool(article.get("wikipedia_article", {}).get("title"))
            if source not in sources:
                sources[source] = {"total": 0, "with_wiki": 0}
            sources[source]["total"] += 1
            if has_wiki:
                sources[source]["with_wiki"] += 1

        print("\n📊 按来源统计:")
        for source, stats in sources.items():
            print(
                f"   {source}: {stats['total']} 篇，其中 {stats['with_wiki']} 篇有Wikipedia数据"
            )
    
    finally:
        # 清理线程池
        extractor.executor.shutdown(wait=True)


if __name__ == "__main__":
    asyncio.run(process_all_articles())