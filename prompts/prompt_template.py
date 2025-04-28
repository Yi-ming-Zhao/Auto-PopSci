prompt = {
    "key_fact_extraction": """
    You are an expert in extracting key facts from scientific papers. Your task is to extract the key facts from the following scientific paper. Your output should be a list of key facts, each fact should be formatted as a dictionary with the following keys: "entity", "behavior", "context". The "entity" key should contain the name of the entity, the "behavior" key should contain the behavior of the entity, the "context" key should contain the context in which the behavior occurs. The output string should be in JSON format, and should be able to directly parse into a JSON object, which means only the structured keyfacts should be included. Don't output anything like ```json at the beginning and ``` at the end. The scientific paper is as follows:
    
    {paper}
    """,
    "popsci_generation_from_keyfacts": """
    You are an expert in generating popular science articles from scientific papers. Your task is to generate a popular science article for children who are 8-12 years old from a list of key facts, which are extracted from a scientific paper. You should perform the task in the following steps:
    1. Read the key facts and the original paper to fully understand the content.
    2. Since your audience will primarily be children, use personification to personify the entities in the key facts and draft a story synopsis that includes all the elements in the key facts list.
    3. According to the story synopsis, write a popular science article that is easy to understand for children aged 8-12. The article should be engaging and informative, and should not contain any technical jargon or complex concepts. The article should be written in a way that is suitable for children, and should be no more than 500 words long.
    
    Your output should be a dictionary with the following keys: "title", "synopsis", "content". The "title" key should contain the title of the article, the "synopsis" key should contain the synopsis of the article you generated, and the "content" key should contain the content of the article. The output string should be in JSON format, and should be able to directly parse into a JSON object, which means only the structured popsci article should be included. Don't output anything like ```json at the beginning and ``` at the end. 
    
    The key facts are as follows:
    {key_facts}
    
    The original paper is as follows:
    {paper}
    """,
}
