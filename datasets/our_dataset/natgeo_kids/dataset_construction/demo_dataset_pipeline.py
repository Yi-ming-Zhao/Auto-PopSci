#!/usr/bin/env python3
"""
演示Wikipedia-NatGeo数据集构建管道（使用模拟数据）
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 配置参数
NATGEO_DATA_PATH = "datasets/our_dataset/natgeo_kids/original_natgeo/all_natgeo_kids_articles.json"
OUTPUT_PATH = "datasets/our_dataset/natgeo_kids/natgeo_wikipedia.json"
SAMPLE_SIZE = 5  # 演示用，只处理5篇文章

# 模拟的Wikipedia数据
MOCK_WIKIPEDIA_DATA = {
    "Festival": {
        "title": "Festival",
        "content": """A festival is a special and celebratory event, usually organized by a community and centering on and celebrating some unique aspect of that community and its traditions. Festivals are often meant to celebrate specific times of year, harvests, or historical and religious themes. They provide a means for unity among families and for people to find mates.

Festivals have been significant in cultures throughout human history. Many festivals have religious origins and entwine cultural and religious significance in traditional activities. The most important religious festivals such as Christmas, Hanukkah, Diwali, and Eid al-Adha serve to mark out the year. Others, such as harvest festivals, celebrate seasonal change.

Food is central to most festivals, with special dishes and treats prepared for the occasion. Music, dancing, and performances are also common elements of festivals around the world. Many festivals feature parades, competitions, fireworks, and other public entertainment.""",
        "url": "https://en.wikipedia.org/wiki/Festival"
    },
    "Shark": {
        "title": "Shark",
        "content": """Sharks are a group of elasmobranch fish characterized by a cartilaginous skeleton, five to seven gill slits on the sides of the head, and pectoral fins that are not fused to the head. Modern sharks are classified within the clade Selachii (or Selachimorpha) and are the sister group to the rays. However, the term "shark" has also been used for extinct members of the subclass Elasmobranchii outside the Selachimorpha, such as Cladoselache and Xenacanthus, as well as other Chondrichthyes such as the holocephalid eugenedontidans.

Under this broader definition, the earliest known sharks date back to more than 420 million years ago. Since then, sharks have diversified into over 500 species. They range in size from the small dwarf lanternshark (Etmopterus perryi), a deep sea species of only 17 centimetres (6.7 in) in length, to the whale shark (Rhincodon typus), the largest fish in the world, which reaches approximately 12 metres (40 ft) in length. Sharks are found in all seas and are common to depths up to 2,000 metres (6,600 ft). They generally do not live in freshwater, although there are a few known exceptions, such as the bull shark and the river shark, which can be found in both seawater and freshwater.

Sharks have a covering of dermal denticles that protects their skin from damage and parasites in addition to improving their fluid dynamics. They have numerous sets of replaceable teeth.""",
        "url": "https://en.wikipedia.org/wiki/Shark"
    },
    "Independence Day (United States)": {
        "title": "Independence Day (United States)",
        "content": """Independence Day (colloquially the Fourth of July) is a federal holiday in the United States commemorating the Declaration of Independence of the United States, which was ratified by the Second Continental Congress on July 4, 1776. The Founding Father delegates of the Second Continental Congress declared that the Thirteen Colonies were no longer subject (and subordinate) to the monarch of Britain, King George III, and were now united, free, and independent states. The Congress had voted to declare independence two days earlier, on July 2, but it was not declared until July 4.

Independence Day is commonly associated with fireworks, parades, barbecues, carnivals, fairs, picnics, concerts, baseball games, family reunions, political speeches, and ceremonies, in addition to various other public and private events celebrating the history, government, and traditions of the United States. Independence Day is the national day of the United States.""",
        "url": "https://en.wikipedia.org/wiki/Independence_Day_(United_States)"
    },
    "Endangered Species Act of 1973": {
        "title": "Endangered Species Act of 1973",
        "content": """The Endangered Species Act of 1973 (ESA or "The Act"; 16 U.S.C. § 1531 et seq.) is the primary law in the United States for protecting imperiled species. Designed to protect critically imperiled species from extinction as a "consequence of economic growth and development untempered by adequate concern and conservation", the ESA was signed into law by President Richard Nixon on December 28, 1973. The U.S. Supreme Court called it "the most comprehensive legislation for the preservation of endangered species enacted by any nation".

The purpose of the ESA is to protect and recover imperiled species and the ecosystems upon which they depend. The U.S. Fish and Wildlife Service (FWS) and the National Oceanic and Atmospheric Administration (NOAA) National Marine Fisheries Service (NMFS) administer the ESA.

The Act was passed with strong bipartisan support (92–0 in the Senate, 394–4 in the House) and was seen as a balanced approach to protecting the nation's plant and animal heritage. It has been described as the world's most powerful environmental law, with protections extended to species both domestic and foreign, and to the ecosystems upon which they depend.""",
        "url": "https://en.wikipedia.org/wiki/Endangered_Species_Act_of_1973"
    }
}

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
                "image_url": self.natgeo_article.get("image_url", "")
            },
            "wikipedia_search_keyword": self.wikipedia_search_keyword,
            "wikipedia_title": self.wikipedia_title,
            "wikipedia_content": self.wikipedia_content,
            "wikipedia_url": self.wikipedia_url
        }

def extract_keyword_simple(description: str) -> str:
    """使用简单规则提取Wikipedia搜索关键词"""
    # 常见的科普主题关键词
    animal_keywords = ["shark", "whale", "dolphin", "turtle", "elephant", "lion", "tiger", "penguin", "bear", "wolf"]
    science_keywords = ["climate", "space", "planet", "star", "energy", "environment", "ocean", "forest", "volcano", "earthquake"]
    festival_keywords = ["festival", "celebration", "tradition", "culture"]
    holiday_keywords = ["independence day", "fourth of july", "july 4"]
    law_keywords = ["endangered species", "law", "act", "protect", "animals"]

    description_lower = description.lower()

    # 检查节日关键词
    for festival in festival_keywords:
        if festival in description_lower:
            return "Festival"

    # 检查动物关键词
    for animal in animal_keywords:
        if animal in description_lower:
            return "Shark"  # 演示用，统一返回Shark

    # 检查假日关键词
    for holiday in holiday_keywords:
        if holiday in description_lower:
            return "Independence Day (United States)"

    # 检查法律关键词
    for law in law_keywords:
        if law in description_lower:
            return "Endangered Species Act of 1973"

    # 检查科学关键词
    for science in science_keywords:
        if science in description_lower:
            return science.capitalize()

    # 如果没有匹配的关键词，提取描述中的第一个名词短语
    words = description.split()
    if len(words) >= 3:
        return " ".join(words[:3])
    else:
        return description

def search_wikipedia_mock(keyword: str) -> Optional[Tuple[str, str, str]]:
    """模拟Wikipedia搜索功能"""
    print(f"  正在搜索Wikipedia: {keyword}")

    # 根据关键词返回模拟数据
    if "festival" in keyword.lower():
        result = MOCK_WIKIPEDIA_DATA["Festival"]
    elif "shark" in keyword.lower():
        result = MOCK_WIKIPEDIA_DATA["Shark"]
    elif "independence" in keyword.lower() or "july" in keyword.lower():
        result = MOCK_WIKIPEDIA_DATA["Independence Day (United States)"]
    elif "endangered" in keyword.lower() or "law" in keyword.lower():
        result = MOCK_WIKIPEDIA_DATA["Endangered Species Act of 1973"]
    else:
        print(f"  未找到关键词 '{keyword}' 的模拟Wikipedia页面")
        return None

    print(f"  找到Wikipedia页面: {result['title']}")
    return result["title"], result["content"], result["url"]

def load_natgeo_articles(file_path: str, sample_size: Optional[int] = None) -> List[Dict]:
    """加载NatGeo Kids文章数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    if sample_size:
        articles = articles[:sample_size]

    print(f"加载了 {len(articles)} 篇NatGeo Kids文章")
    return articles

def build_demo_dataset():
    """构建演示数据集"""
    print("开始构建演示数据集...")

    # 检查输入文件是否存在
    if not os.path.exists(NATGEO_DATA_PATH):
        print(f"错误：找不到NatGeo数据文件 {NATGEO_DATA_PATH}")
        return

    # 加载NatGeo文章
    articles = load_natgeo_articles(NATGEO_DATA_PATH, SAMPLE_SIZE)

    pairs = []
    failed_count = 0

    for i, article in enumerate(articles):
        print(f"\n处理第 {i+1}/{len(articles)} 篇文章...")
        print(f"标题: {article.get('title', 'N/A')}")
        print(f"描述: {article.get('description', 'N/A')}")

        try:
            # 提取Wikipedia搜索关键词
            description = article.get('description', '')
            if not description:
                print("跳过：没有描述内容")
                failed_count += 1
                continue

            search_keyword = extract_keyword_simple(description)
            print(f"提取的关键词: {search_keyword}")

            # 搜索Wikipedia（使用模拟数据）
            wiki_result = search_wikipedia_mock(search_keyword)
            if not wiki_result:
                print("跳过：Wikipedia搜索失败")
                failed_count += 1
                continue

            wiki_title, wiki_content, wiki_url = wiki_result
            print(f"Wikipedia页面: {wiki_title}")
            print(f"Wikipedia内容长度: {len(wiki_content)} 字符")

            # 创建数据对
            pair = WikipediaNatgeoPair(
                natgeo_article=article,
                wikipedia_search_keyword=search_keyword,
                wikipedia_title=wiki_title,
                wikipedia_content=wiki_content,
                wikipedia_url=wiki_url
            )

            pairs.append(pair)

        except Exception as e:
            print(f"处理文章时出错: {e}")
            failed_count += 1
            continue

    # 保存数据集
    dataset = [pair.to_dict() for pair in pairs]
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"\n=== 演示数据集构建完成 ===")
    print(f"成功处理: {len(pairs)} 篇文章")
    print(f"失败: {failed_count} 篇文章")
    print(f"数据已保存到: {OUTPUT_PATH}")

    # 显示统计信息
    if pairs:
        print(f"\n=== 示例数据对 ===")
        for i, pair in enumerate(pairs):
            print(f"\n示例 {i+1}:")
            print(f"NatGeo标题: {pair.natgeo_article.get('title', 'N/A')}")
            print(f"Wikipedia搜索关键词: {pair.wikipedia_search_keyword}")
            print(f"Wikipedia标题: {pair.wikipedia_title}")
            print(f"Wikipedia内容预览: {pair.wikipedia_content[:200]}...")

if __name__ == "__main__":
    build_demo_dataset()