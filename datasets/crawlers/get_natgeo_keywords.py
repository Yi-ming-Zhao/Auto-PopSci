from  ...prompts.prompt_template import prompt
from ...auto_popsci.utils.utils import get_llm_response
import asyncio
import json

async def get_natgeo_keywords_and_summary(args, articles):
    tasks = []
    for article in articles:
        tasks.append(
            get_llm_response(
                args,
                prompt_text=prompt[args.prompt_template].format(
                    article_title=article["title"],
                    article_text=article["content"]
                ),
            )
        )
    keywords_and_summaries = await asyncio.gather(*tasks)
    for i, article in enumerate(articles):
        article['keyword'] = keywords_and_summaries[i].split('\n')[0]
        article['summary'] = keywords_and_summaries[i].split('\n')[1]
    json.dump(
        articles,
        open("datasets/our_dataset/natgeo_kids/all_natgeo_kids_articles.json", "w"),
        indent=4,
        ensure_ascii=False,
    )
    print(f"Processed {len(articles)} articles with keywords and summaries.")

with open("datasets/our_dataset/natgeo_kids/all_natgeo_kids_articles.json", "r") as f:
    natgeo_articles = json.load(f)
