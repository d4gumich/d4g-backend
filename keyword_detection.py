# @author Prithvijit Dasgupta


language = "en"
max_ngram_size = 4
deduplication_threshold = 0.7
deduplication_algo = 'seqm'
windowSize = 1


def generate_keywords(summary: str, top_n: int = 5) -> list:
    
    """
    Extract and generate a list of keywords from a summary using the YAKE algorithm.

    This function uses the YAKE (Yet Another Keyword Extractor) library to 
    extract a specified number of top keywords from a provided text summary. 
    It calculates a relative score for each keyword based on the range of 
    scores extracted by YAKE and formats each keyword with its corresponding score.

    Parameters:
    summary (str): The text summary to extract keywords from.
    top_n (int): The number of top keywords to extract (default is 5).

    Returns:
    (list): A list of strings where each string is a keyword followed by its 
          normalized score in the format "keyword (Score: X)".
    """
    
    import yake
    kw_extractor = yake.KeywordExtractor(lan=language, n=max_ngram_size,
                                         dedupLim=deduplication_threshold,
                                         dedupFunc=deduplication_algo,
                                         windowsSize=windowSize,
                                         top=top_n)
    del yake
    import gc
    gc.collect()

    keywords = kw_extractor.extract_keywords(summary)
    scores = [kw[1] for kw in keywords]
    return [f'{kw[0]} (Score: {round(kw[1]*100/(min(scores)-max(scores)))})' for kw in keywords]
