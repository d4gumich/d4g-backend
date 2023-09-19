# @author Prithvijit Dasgupta
import yake

language = "en"
max_ngram_size = 4
deduplication_threshold = 0.7
deduplication_algo = 'seqm'
windowSize = 1


def generate_keywords(summary: str, top_n: int = 5) -> list:
    kw_extractor = yake.KeywordExtractor(lan=language, n=max_ngram_size,
                                         dedupLim=deduplication_threshold,
                                         dedupFunc=deduplication_algo,
                                         windowsSize=windowSize,
                                         top=top_n)

    keywords = kw_extractor.extract_keywords(summary)
    scores = [kw[1] for kw in keywords]
    return [f'{kw[0]} (Score: {round(kw[1]*100/(min(scores)-max(scores)))})' for kw in keywords]
