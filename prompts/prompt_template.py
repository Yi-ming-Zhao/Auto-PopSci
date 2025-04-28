prompt = {
    "key_fact_extraction": """
    You are an expert in extracting key facts from scientific papers. Your task is to extract the key facts from the following scientific paper. Your output should be a list of key facts, each fact should be formatted as a dictionary with the following keys: "entity", "behavior", "context". The "entity" key should contain the name of the entity, the "behavior" key should contain the behavior of the entity, the "context" key should contain the context in which the behavior occurs. The output should be in JSON format. The scientific paper is as follows:
    
    {paper}
    """,
    "": """
    
    """,
}
