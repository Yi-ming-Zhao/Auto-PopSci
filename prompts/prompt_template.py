prompt = {
    "key_fact_extraction": """
    You are an expert in extracting key facts from scientific papers. Your task is to extract the key facts from the following scientific paper. Your output should be a list of key facts, each fact should be formatted as a dictionary with the following keys: "entity", "behavior", "context". The "entity" key should contain the name of the entity, the "behavior" key should contain the behavior of the entity, the "context" key should contain the context in which the behavior occurs. The output string should be in JSON format, and should be able to directly parse into a JSON object, which means only the structured keyfacts should be included. Don't output anything like ```json at the beginning and ``` at the end. The scientific paper is as follows:
    
    {paper}
    """,
    "key_fact_extraction_with_priority": """
    You are an expert in extracting key facts from scientific papers. Your task is to extract the key facts from the following scientific paper. Your output should be a list of key facts, each fact should be formatted as a dictionary with the following keys: "entity", "behavior", "context" and "priority". The "entity" key should contain the name of the entity, the "behavior" key should contain the behavior of the entity, the "context" key should contain the context in which the behavior occurs, and the "priority" key should a digit from 1 to 3, where 1 means the key fact is directly related to the main topic of the paper, 2 means the key fact is an important detail that supports the main topic, and 3 means the key fact is a minor detail that is not directly related to the main topic. The output string should be in JSON format, and should be able to directly parse into a JSON object, which means only the structured keyfacts should be included. Don't output anything like ```json at the beginning and ``` at the end. The scientific paper is as follows:
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
    "popsci_generation_ordinary": """
    You are an expert in generating popular science articles from scientific papers. Your task is to generate a popular science article for children who are 8-12 years old. The article should be engaging and informative, and should not contain any technical jargon or complex concepts. The article should be written in a way that is suitable for children, and should be no more than 500 words long.
    
    Your output should be a dictionary with the following keys: "title", "synopsis", "content". The "title" key should contain the title of the article, the "synopsis" key should contain the synopsis of the article you generated, and the "content" key should contain the content of the article. The output string should be in JSON format, and should be able to directly parse into a JSON object, which means only the structured popsci article should be included. Don't output anything like ```json at the beginning and ``` at the end. 
    
    The original paper is as follows:
    {paper}
    """,
    "keyfact_alignment": """
    You are an expert in aligning key facts with the original paper. You will be given two lists of key facts, one is the ground truth key facts and the other is the generated key facts. Your task is to align the generated key facts with the original paper. You should perform the task in the following steps:
    1. Read the ground truth key facts and the generated key facts to fully understand the content.
    2. For each generated key fact, find the corresponding ground truth key fact. The corresponding ground truth key fact is the one that has the same entity and behavior as the generated key fact. If the generated key fact is found in the ground truth key facts, then it is considered as a true positive.If the generated key fact is not found in the ground truth key facts, then it is considered as a false positive.
    3. Return a list of tuples, where each tuple contains the related generated key fact and the corresponding ground truth key fact. That means you should only return the true positive key facts.
    4. The output string should be in JSON format, and should be able to directly parse into a JSON object, which means only the structured key facts should be included. Don't output anything like ```json at the beginning and ``` at the end.
    
    Here is a example of the output:
    [
        [
            {{
                "entity": "ultra-fine needle with integrated chip",
                "behavior": "detects and transmits nuclear magnetic resonance (NMR) data",
                "context": "probing nanoliter volumes of brain oxygen metabolism with high spatial and temporal resolution",
                "priority": 1
            }},
            {{
                "entity": "NMR-on-a-chip needle",
                "behavior": "enables in vivo measurements of blood oxygenation and flow in nanoliter volumes at 200 Hz sampling rate",
                "context": "brain physiology studies",
                "priority": 1
            }}
        ]
    ]
    
    The ground truth key facts are as follows:
    {ground_truth_key_facts}
    The generated key facts are as follows:
    {generated_key_facts}
    """,
}
